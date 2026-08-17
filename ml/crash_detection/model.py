"""CrashFusionNet -- multi-modal on-device crash detector.

Four branches, late fusion, two heads.

    IMU    (200, 9)      accel xyz + gyro xyz + per-axis clip mask
                         -> 1D-CNN.  The clip mask is fed as INPUT CHANNELS,
                            not just as derived features, so the convolutions
                            can learn the temporal shape of saturation --
                            which is what remains once peak magnitude is gone.
    AUDIO  (64, 126, 1)  log-mel -> small 2D-CNN
    GPS    (12,)         1 Hz speed trace -> MLP
    TAB    (26,)         saturation / kinematic / acoustic scalars -> MLP

Heads:
    crash     sigmoid, binary
    severity  softmax over 4 bands, supervised only on positives

MODALITY DROPOUT is the key training trick. Each branch is randomly zeroed
during training (p=0.15), so the network cannot become dependent on any single
input. That is not regularisation for its own sake -- it is a product
requirement. Microphone permission is frequently denied, GPS drops in tunnels
and urban canyons, and the PRD's whole architecture is built on graceful
degradation. A fusion model that collapses when one sensor is missing would be
useless on exactly the rural and highway stretches this product targets.
"""
from __future__ import annotations

import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers as L
import keras as _keras_pkg  # tf.keras is a lazy loader and lacks .saving; use the real package for it

from ml.common.config import AUDIO_LEN, GPS_LEN, N_MELS, SEVERITY, WIN_LEN


@_keras_pkg.saving.register_keras_serializable(package="rrx")
class Normalize(L.Layer):
    """(x - mean) / std, with mean/std baked in as constants.

    Used only in the deployable export. Training normalises every input with
    stats computed in train.py and applies them in Python (`inputs()`); if the
    shipped model expected pre-normalised input, the Android app would have to
    reproduce that same (x-mu)/sigma arithmetic in Kotlin for four different
    modalities from a stats file -- another place for silent train/serve skew,
    on top of the mel computation this module already had to solve. Baking
    normalisation into the graph means the on-device contract is simply "feed
    raw sensor values in their physical units", with nothing left to get wrong
    on the client.
    """

    def __init__(self, mean, std, **kw):
        super().__init__(**kw)
        self._mean_init = np.asarray(mean, dtype=np.float32)
        self._std_init = np.asarray(std, dtype=np.float32)

    def build(self, input_shape):
        self.mean = self.add_weight(
            shape=self._mean_init.shape, initializer=keras.initializers.Constant(self._mean_init),
            trainable=False, name="mean")
        self.std = self.add_weight(
            shape=self._std_init.shape, initializer=keras.initializers.Constant(self._std_init),
            trainable=False, name="std")

    def call(self, x):
        return (x - self.mean) / self.std

    def get_config(self):
        return {**super().get_config(),
                "mean": self._mean_init.tolist(), "std": self._std_init.tolist()}


@_keras_pkg.saving.register_keras_serializable(package="rrx")
class ModalityDropout(L.Layer):
    """Zero an entire branch embedding with probability p, at training time."""

    def __init__(self, p: float = 0.15, **kw):
        super().__init__(**kw)
        self.p = p

    def call(self, x, training=None):
        if not training or self.p <= 0:
            return x
        keep = tf.cast(
            tf.random.uniform((tf.shape(x)[0], 1)) >= self.p, x.dtype
        )
        return x * keep

    def get_config(self):
        return {**super().get_config(), "p": self.p}


def _imu_branch(inp, width=32):
    x = inp
    for f, k in ((width, 7), (width * 2, 5), (width * 2, 3)):
        x = L.Conv1D(f, k, padding="same", use_bias=False)(x)
        x = L.BatchNormalization()(x)
        x = L.Activation("relu")(x)
        x = L.MaxPooling1D(2)(x)
    # Max pooling matters more than average here: a crash is a localised event
    # and its signature must survive being averaged against 4 s of background.
    x = L.Concatenate()([L.GlobalMaxPooling1D()(x), L.GlobalAveragePooling1D()(x)])
    return L.Dense(48, activation="relu")(x)


def _audio_branch(inp, width=16):
    x = inp
    for f in (width, width * 2, width * 4):
        x = L.Conv2D(f, 3, padding="same", use_bias=False)(x)
        x = L.BatchNormalization()(x)
        x = L.Activation("relu")(x)
        x = L.MaxPooling2D(2)(x)
    x = L.GlobalMaxPooling2D()(x)
    return L.Dense(32, activation="relu")(x)


def _mlp_branch(inp, units, out):
    x = inp
    for u in units:
        x = L.Dense(u, activation="relu")(x)
    return L.Dense(out, activation="relu")(x)


# ---------------------------------------------------------------- reusable
# submodels
#
# Each branch is built as its own named keras.Model rather than inlined
# directly into the fusion graph. Functionally identical either way -- but
# an explicit submodel is a REUSABLE, WEIGHT-SHARING OBJECT: once
# `build_model` trains it as part of the full graph, that same object (with
# its trained weights) can be called again on a *different* input tensor
# elsewhere, which is exactly what `build_deployable_model` below needs to
# splice the on-device mel frontend in front of the trained audio CNN
# without retraining it from scratch.

def _make_imu_submodel(width=32) -> keras.Model:
    inp = keras.Input((WIN_LEN, 9), name="imu_raw")
    return keras.Model(inp, _imu_branch(inp, width), name="imu_branch")


def _make_audio_submodel(mel_frames, width=16) -> keras.Model:
    inp = keras.Input((N_MELS, mel_frames, 1), name="mel_raw")
    return keras.Model(inp, _audio_branch(inp, width), name="audio_branch")


def _make_gps_submodel() -> keras.Model:
    inp = keras.Input((GPS_LEN,), name="gps_raw")
    return keras.Model(inp, _mlp_branch(inp, (32, 32), 24), name="gps_branch")


def _make_tab_submodel(n_tab) -> keras.Model:
    inp = keras.Input((n_tab,), name="tab_raw")
    return keras.Model(inp, _mlp_branch(inp, (64, 48), 32), name="tab_branch")


def build_model(n_tab: int, mel_frames: int, mod_dropout: float = 0.15,
                lr: float = 1e-3) -> keras.Model:
    imu_in = keras.Input((WIN_LEN, 9), name="imu")
    mel_in = keras.Input((N_MELS, mel_frames, 1), name="mel")
    gps_in = keras.Input((GPS_LEN,), name="gps")
    tab_in = keras.Input((n_tab,), name="tab")

    e_imu = ModalityDropout(mod_dropout, name="drop_imu")(_make_imu_submodel()(imu_in))
    e_mel = ModalityDropout(mod_dropout, name="drop_mel")(_make_audio_submodel(mel_frames)(mel_in))
    e_gps = ModalityDropout(mod_dropout, name="drop_gps")(_make_gps_submodel()(gps_in))
    e_tab = ModalityDropout(mod_dropout, name="drop_tab")(_make_tab_submodel(n_tab)(tab_in))

    h = L.Concatenate(name="fusion_concat")([e_imu, e_mel, e_gps, e_tab])
    h = L.Dense(64, activation="relu", name="fusion_dense1")(h)
    h = L.Dropout(0.3, name="fusion_dropout")(h)
    h = L.Dense(32, activation="relu", name="fusion_dense2")(h)

    crash = L.Dense(1, activation="sigmoid", name="crash")(h)
    # 5 classes: the 4 severity bands plus an explicit NONE for negatives.
    # The alternative -- 4 classes with the severity loss masked off on
    # negatives via per-output sample weights -- is what Keras 3 rejects, and
    # it was never the better design: an explicit "not a crash" state keeps the
    # loss well-defined on every sample and keeps the two heads consistent.
    sev = L.Dense(len(SEVERITY) + 1, activation="softmax", name="severity")(h)

    m = keras.Model([imu_in, mel_in, gps_in, tab_in], [crash, sev],
                    name="CrashFusionNet")
    m.compile(
        optimizer=keras.optimizers.Adam(lr),
        loss={
            "crash": keras.losses.BinaryFocalCrossentropy(gamma=2.0, from_logits=False),
            "severity": keras.losses.SparseCategoricalCrossentropy(),
        },
        loss_weights={"crash": 1.0, "severity": 0.35},
        metrics={"crash": [keras.metrics.AUC(name="auc", curve="PR"),
                           keras.metrics.Recall(name="recall"),
                           keras.metrics.Precision(name="prec")]},
    )
    return m


def build_deployable_model(trained: keras.Model, n_tab: int, mel_frames: int,
                           norm_stats: dict) -> keras.Model:
    """Reassemble the trained fusion graph with a RAW AUDIO input and every
    normalisation step BAKED IN.

    Resolves MVP-PLAN.md 4.1. `trained` must come from `build_model` (so its
    branches exist as the named submodels above, and its fusion layers carry
    the names set there). This function does not retrain anything -- it
    reuses those same layer objects, weights included, and calls them on a
    new graph where `mel_frontend.LogMelFrontend` computes the spectrogram
    from a raw waveform instead of it being supplied precomputed.

    `norm_stats` is the `{modality: (mean, std)}` dict train.py computed from
    the training split (`norm_stats()` there). Wrapping every branch input in
    a `Normalize(mean, std)` means the deployed contract is "feed raw sensor
    values in physical units" -- the Android app does not reimplement any
    normalisation arithmetic, which removes an entire class of train/serve
    skew (four modalities' worth of (x-mu)/sigma, each a chance to get a sign
    or a stat wrong) on top of the mel computation this module already solves.

    The result is numerically equivalent to the training-time model up to the
    frontend's own measured divergence from librosa (mean ~0.007 dB, see
    mel_frontend.py) -- not equivalent by assumption, but verified by
    `export_deployable.py` before any artifact produced here is shipped.
    """
    from ml.crash_detection.mel_frontend import LogMelFrontend

    imu_in = keras.Input((WIN_LEN, 9), name="imu")
    raw_audio_in = keras.Input((AUDIO_LEN,), name="raw_audio")
    gps_in = keras.Input((GPS_LEN,), name="gps")
    tab_in = keras.Input((n_tab,), name="tab")

    mel = LogMelFrontend(name="log_mel")(raw_audio_in)

    n_imu = Normalize(*norm_stats["imu"], name="norm_imu")(imu_in)
    n_mel = Normalize(*norm_stats["mel"], name="norm_mel")(mel)
    n_gps = Normalize(*norm_stats["gps"], name="norm_gps")(gps_in)
    n_tab = Normalize(*norm_stats["tab"], name="norm_tab")(tab_in)

    e_imu = trained.get_layer("drop_imu")(trained.get_layer("imu_branch")(n_imu))
    e_mel = trained.get_layer("drop_mel")(trained.get_layer("audio_branch")(n_mel))
    e_gps = trained.get_layer("drop_gps")(trained.get_layer("gps_branch")(n_gps))
    e_tab = trained.get_layer("drop_tab")(trained.get_layer("tab_branch")(n_tab))

    h = trained.get_layer("fusion_concat")([e_imu, e_mel, e_gps, e_tab])
    h = trained.get_layer("fusion_dense1")(h)
    h = trained.get_layer("fusion_dropout")(h)
    h = trained.get_layer("fusion_dense2")(h)
    crash = trained.get_layer("crash")(h)
    sev = trained.get_layer("severity")(h)

    return keras.Model([imu_in, raw_audio_in, gps_in, tab_in], [crash, sev],
                       name="CrashFusionNet_Deployable")


def build_unimodal(which: str, n_tab: int, mel_frames: int, lr: float = 1e-3) -> keras.Model:
    """Single-modality baseline, for the ablation table.

    `imu` is the important one: it is what every existing phone-based crash
    detector does, and it is the number the fusion model has to beat.
    """
    if which == "imu":
        inp = keras.Input((WIN_LEN, 9), name="imu")
        h = _imu_branch(inp)
    elif which == "audio":
        inp = keras.Input((N_MELS, mel_frames, 1), name="mel")
        h = _audio_branch(inp)
    elif which == "gps":
        inp = keras.Input((GPS_LEN,), name="gps")
        h = _mlp_branch(inp, (32, 32), 24)
    else:
        inp = keras.Input((n_tab,), name="tab")
        h = _mlp_branch(inp, (64, 48), 32)

    h = L.Dense(32, activation="relu")(h)
    h = L.Dropout(0.3)(h)
    out = L.Dense(1, activation="sigmoid", name="crash")(h)
    m = keras.Model(inp, out, name=f"Unimodal_{which}")
    m.compile(
        optimizer=keras.optimizers.Adam(lr),
        loss=keras.losses.BinaryFocalCrossentropy(gamma=2.0),
        metrics=[keras.metrics.AUC(name="auc", curve="PR")],
    )
    return m


def export_tflite(model: keras.Model, path, float16: bool = True) -> int:
    """Convert to TFLite. Returns the artifact size in bytes."""
    conv = tf.lite.TFLiteConverter.from_keras_model(model)
    conv.optimizations = [tf.lite.Optimize.DEFAULT]
    if float16:
        conv.target_spec.supported_types = [tf.float16]
    blob = conv.convert()
    path = str(path)
    with open(path, "wb") as f:
        f.write(blob)
    return len(blob)
