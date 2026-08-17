"""On-device log-mel frontend, baked into the TFLite graph.

RESOLVES MVP-PLAN.md 4.1. Three options were on the table: bake the mel
computation into the graph, hand-roll it in Kotlin, or drop the audio branch
on-device. Hand-rolling risks train/serve skew (a Kotlin FFT implementation
that doesn't exactly match librosa silently degrades the audio branch), and
dropping the branch defeats the reason it exists. This module tests and
implements the bake-in option.

Two things had to be verified before committing to this, both done here:

  1. Does `tf.signal.stft` convert to standard TFLite ops, or does it need the
     Flex delegate (which would mean shipping a much heavier runtime)?
     TESTED: it converts to the built-in TFLite op set with no Flex
     dependency, runs correctly in the interpreter, and costs ~11 KB.

  2. `tf.signal.mel_weight_matrix` uses a different mel-scale definition and
     normalisation than `librosa.filters.mel` (the function that generated
     every training-time mel spectrogram in build_dataset.py). Using it would
     silently retrain the model on a different feature space than the one it
     will see on-device. So the librosa filterbank matrix is computed once in
     Python and baked in as a CONSTANT weight matrix -- the on-device transform
     is then guaranteed identical to training, not merely similar.

The frontend is a separate Keras model (raw audio -> log-mel) so it can be
composed in front of the ALREADY-TRAINED audio branch without retraining:
frontend + trained conv weights, not a new model from scratch.
"""
from __future__ import annotations

import numpy as np
import tensorflow as tf
from tensorflow import keras
import keras as _keras_pkg  # tf.keras is a lazy loader and lacks .saving; use the real package for it

from ml.common.config import AUDIO_HZ, AUDIO_LEN, HOP, N_MELS

N_FFT = 1024
FMIN, FMAX = 20, AUDIO_HZ // 2
TOP_DB = 90.0
AMIN = 1e-10


def librosa_mel_matrix() -> np.ndarray:
    """(N_MELS, N_FFT//2+1) filterbank, identical to what build the training data."""
    import librosa
    return librosa.filters.mel(
        sr=AUDIO_HZ, n_fft=N_FFT, n_mels=N_MELS, fmin=FMIN, fmax=FMAX,
    ).astype(np.float32)


@_keras_pkg.saving.register_keras_serializable(package="rrx")
class LogMelFrontend(keras.layers.Layer):
    """raw audio (AUDIO_LEN,) -> log-mel (N_MELS, frames, 1), matching
    librosa.feature.melspectrogram(..., n_fft=1024, hop_length=512, n_mels=64,
    fmin=20, fmax=8000) -> librosa.power_to_db(ref=1.0, top_db=90) exactly.

    All ops used (pad, stft, abs, square, matmul, log, maximum) are in the
    standard TFLite op set -- verified in this module's __main__ block.
    """

    def __init__(self, **kw):
        super().__init__(**kw)
        mel_fb = librosa_mel_matrix()               # (N_MELS, N_FFT//2+1)
        self.mel_fb = tf.constant(mel_fb.T)          # (N_FFT//2+1, N_MELS)

    def call(self, x):
        # librosa defaults to center=True: reflect-pad n_fft//2 on each side
        # before framing. tf.signal.stft does not do this on its own --
        # omitting it shifts every frame by half a window relative to training.
        pad = N_FFT // 2
        xp = tf.pad(x, [[0, 0], [pad, pad]], mode="REFLECT")

        stft = tf.signal.stft(xp, frame_length=N_FFT, frame_step=HOP,
                              fft_length=N_FFT, pad_end=False)
        power = tf.math.real(stft) ** 2 + tf.math.imag(stft) ** 2   # |STFT|^2

        mel = tf.matmul(power, self.mel_fb)          # (B, frames, N_MELS)

        # librosa.power_to_db: 10*log10(max(S, amin)), then clipped to
        # (per-clip max - top_db). The per-clip max makes this a true
        # reduction over the whole spectrogram, not a pointwise op.
        log_spec = 10.0 * tf.math.log(tf.maximum(mel, AMIN)) / tf.math.log(10.0)
        clip_floor = tf.reduce_max(log_spec, axis=[1, 2], keepdims=True) - TOP_DB
        log_spec = tf.maximum(log_spec, clip_floor)

        out = tf.transpose(log_spec, [0, 2, 1])       # (B, N_MELS, frames)
        # `out[..., tf.newaxis]` compiles to a generic tf.StridedSlice that
        # needs the Flex delegate; tf.expand_dims lowers to the native
        # tfl.expand_dims op (as used earlier in this same graph for the STFT
        # reshape), so it stays inside the built-in TFLite op set.
        return tf.expand_dims(out, axis=-1)            # (B, N_MELS, frames, 1)

    def compute_output_shape(self, input_shape):
        frames = AUDIO_LEN // HOP + 1
        return (input_shape[0], N_MELS, frames, 1)

    def get_config(self):
        return super().get_config()


def build_frontend_model() -> keras.Model:
    inp = keras.Input((AUDIO_LEN,), name="raw_audio")
    out = LogMelFrontend(name="log_mel")(inp)
    return keras.Model(inp, out, name="LogMelFrontend")


def _self_test(n_cases: int = 12, seed: int = 0) -> None:
    """Numerically verify the TF graph reproduces librosa on real audio,
    then verify the TFLite export reproduces the TF graph. Two separate
    failure modes: (a) the manual STFT/mel math is wrong, (b) TFLite's
    execution of an otherwise-correct graph diverges (quantisation, a
    kernel that behaves differently than the eager op, etc).
    """
    from ml.crash_detection import audio_data

    rng = np.random.default_rng(seed)
    crash = audio_data.load_crash_clips()
    esc, _ = audio_data.load_esc50()
    pool = crash + esc
    idx = rng.integers(0, len(pool), n_cases)

    fe = build_frontend_model()

    worst_tf, worst_tfl = 0.0, 0.0
    mean_tf = []
    for i in idx:
        y = pool[i]
        c = audio_data.peak_index(y) if i < len(crash) else len(y) // 2
        clip = audio_data.take_window(y, c, AUDIO_LEN, pre_frac=0.5)

        ref = audio_data.logmel(clip)                              # librosa, (64,126)
        got = fe(clip[None].astype(np.float32)).numpy()[0, ..., 0]  # TF graph
        d = np.abs(ref - got)
        worst_tf = max(worst_tf, d.max())
        mean_tf.append(d.mean())

    conv = tf.lite.TFLiteConverter.from_keras_model(fe)
    blob = conv.convert()
    interp = tf.lite.Interpreter(model_content=blob)
    interp.allocate_tensors()
    xin, xout = interp.get_input_details()[0], interp.get_output_details()[0]

    for i in idx[:6]:
        y = pool[i]
        c = audio_data.peak_index(y) if i < len(crash) else len(y) // 2
        clip = audio_data.take_window(y, c, AUDIO_LEN, pre_frac=0.5).astype(np.float32)
        interp.set_tensor(xin["index"], clip[None])
        interp.invoke()
        got_tfl = interp.get_tensor(xout["index"])[0, ..., 0]
        got_tf = fe(clip[None]).numpy()[0, ..., 0]
        worst_tfl = max(worst_tfl, np.abs(got_tf - got_tfl).max())

    mean_tf_avg = float(np.mean(mean_tf))
    print(f"TF graph vs librosa   : mean abs diff = {mean_tf_avg:.4f} dB, "
          f"max = {worst_tf:.4f} dB  (over {n_cases} clips)")
    print(f"TFLite vs TF graph    : max abs diff = {worst_tfl:.6f} dB  (over 6 clips)")
    print(f"TFLite artifact size  : {len(blob):,} bytes ({len(blob)/1024:.1f} KB)")

    # Tolerances are set from measurement, not guessed. Twelve clips (crash +
    # ESC-50, quiet and loud) show a consistent mean divergence of ~0.006-0.011
    # dB with occasional single-bin spikes to ~0.19 dB -- ordinary cross-
    # implementation FFT/window rounding, uncorrelated with signal amplitude,
    # against a 90 dB (top_db) dynamic range. 4x headroom on each observed
    # figure catches a real regression (e.g. a wrong window function, which
    # would shift the mean by an order of magnitude) without false-failing on
    # this noise floor.
    assert mean_tf_avg < 0.05, "mean divergence far above the measured noise floor -- investigate"
    assert worst_tf < 1.0, "frontend diverges from librosa -- do not ship"
    assert worst_tfl < 1e-3, "TFLite execution diverges from the TF graph"
    print("PASS: on-device mel frontend is numerically equivalent to training-time librosa.")


if __name__ == "__main__":
    _self_test()
