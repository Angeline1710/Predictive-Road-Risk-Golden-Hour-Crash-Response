# Model Card — Predictive Road-Risk & Golden-Hour Crash Response

| | |
|---|---|
| **Version** | 1.1 — adds the verified deployable (raw-audio) export for Model A |
| **Date** | 2026-08-17 |
| **Models** | A — `crash_fusion_v1` (multi-modal on-device crash detection) · B — `risk_model_v1` (segment × hour road-risk) |
| **Companion to** | `PRD.md` v1.1, `UX-APPFLOW.md` v1.0, `MVP-PLAN.md` |
| **Status** | Pipeline complete and reproducible, including a client-ready TFLite artifact (§2.2b). **Neither model is validated for deployment against real-world data.** |

---

## 0. Read this before quoting any number

**Model A's accuracy figures are not evidence that it detects crashes.**

There is no public corpus of real vehicle-crash smartphone telemetry. Model A is therefore trained and evaluated on a corpus where the positives are physics-simulated and I wrote both the generator and the detector. Under those conditions near-perfect separation is the *default* outcome, not an achievement: any structural difference introduced between classes becomes learnable by a 77k-parameter CNN over 200 timesteps.

Four rounds of leak-hunting (§4.4) each found and removed a genuine artifact, and the headline numbers barely moved. That is the finding. The benchmark's difficulty is a property of the generator, and I can move it in either direction by choosing how much the classes overlap.

**What Model A's results DO support:**
- the pipeline runs end to end, from Hugging Face data to a verified, deployable 299.5 KB TFLite artifact that takes raw sensor input and needs no client-side feature computation or normalisation (§2.2b)
- graceful degradation works — the model holds up with any single modality removed
- hard negatives with crash-sized kinematics (panic stops shedding more speed than the average crash) are rejected at the chosen operating point
- the Stage-A gate analysis (§5.1), which is a real and actionable finding about the PRD's design

**What they do NOT support:** any claim about real-world recall or false-positive rate. That requires the instrumented-drive collection in PRD Q4. This is exactly the hazard PRD R10 flagged.

**Model B is on firmer ground.** Its spatial intensity is calibrated to real Tamil Nadu administrative crash counts, so its 15.9× lift at top-1% is a defensible number — with the scope limits in §6.5.

---

## 1. Data provenance

### 1.1 Hugging Face sources

| Dataset | Content | Role | Licence |
|---|---|---|---|
| [`udayl/UCI_HAR`](https://hf.co/datasets/udayl/UCI_HAR) | 10,299 windows, 50 Hz smartphone accel+gyro, 30 subjects, raw `Inertial Signals/` in physical units | **Real** IMU backgrounds | UCI / CC BY 4.0 |
| [`Titung/car-crash-audio-cc`](https://hf.co/datasets/Titung/car-crash-audio-cc) | 46 clips / 863 s of genuine crash audio from 38 CC-BY videos | **Real** impact acoustics | CC BY 3.0 |
| [`ashraq/esc50`](https://hf.co/datasets/ashraq/esc50) | 1,000 clips, 50 classes — cabin background + impulsive confusers + 16 `glass_breaking` | **Real** acoustic negatives | **CC BY-NC** |

> **Mirror choice matters.** The tidier parquet UCI-HAR mirrors (e.g. `pranavmr/UCI-HAR`) are z-scored **per window**: every activity has std exactly 1.000, so walking and lying down are numerically identical. That destroys the amplitude information a crash detector depends on. The raw text release preserves physical units — walking 0.29 g vs standing 0.019 g, a 15× separation.
>
> **ESC-50 is CC BY-NC.** Fine for the hackathon, research and evaluation. It must be replaced with a commercially-licensed corpus before any paid deployment.

### 1.2 Supplied reference data

**`tn_road_accident_dataset_original.csv` — real, official, used as labels.**
43 TN districts; 55,681 accidents, 14,746 fatal, 15,383 deaths (2021). Fatal share ranges **0.152 – 0.354** across districts (2.3× real spatial variation); vulnerable-road-user deaths are **44.6%** of the total. Same administrative lineage as the iRAD/TARA pipeline that IIT Madras RBG Labs runs with TN Police and the TN Trauma Commission. Sets Model B's absolute intensity and spatial ordering.

**`indian_roads_dataset.csv` — schema and condition prior only, NOT labels.**
Profiling before use found `accident_severity` is statistically independent of every feature:

| feature | min P(fatal) | max P(fatal) | spread | marginal |
|---|---|---|---|---|
| cause | 0.1346 | 0.1568 | 0.0221 | 0.1494 |
| road_type | 0.1454 | 0.1540 | 0.0087 | 0.1494 |
| visibility | 0.1483 | 0.1532 | 0.0049 | 0.1494 |
| weather | 0.1483 | 0.1500 | 0.0017 | 0.1494 |
| is_peak_hour | 0.1493 | 0.1496 | 0.0003 | 0.1494 |

Fog 0.1500 vs clear 0.1483. Every conditional equals the marginal to three decimals — the column is random assignment. A severity classifier trained on it can only reproduce the base rate.

`risk_score` is a near-deterministic function of (weather, visibility, traffic_density, is_peak_hour), quantised to 0.05. Predicting it is reverse-engineering a formula. It *is* a reasonable encoding of domain priors, so it was used to extract **condition multipliers** (fog 1.35×, clear 0.54×, low visibility 1.35×, peak hour 1.38×, bimodal hour-of-day peaking 09:00 and 18:00) — from the supplied data, not invented here.

### 1.3 iRAD alignment

The [iRAD/TARA reference](https://ed.iitm.ac.in/~vb/rbg/Research/PublicPolicy/iRAD.html) confirms Tamil Nadu as the pilot geography and describes the police → trauma-registry → transport integration this product feeds into. Model B's 500 m segment unit and the ≥5-severe-in-3-years black-spot rule are matched to that methodology so outputs compare like-for-like with official black-spot lists.

---

## 2. Model A — `crash_fusion_v1`

### 2.1 Why multi-modal

Consumer Android accelerometers rail at **±8–16 g**. A 40 km/h delta-V impact produces far more than that at a loose object in the cabin, so **the sensor clips and peak acceleration is unmeasurable**. Apple's answer was hardware — a dedicated 256 g accelerometer in the iPhone 14 exists specifically for Crash Detection. We cannot add hardware, so the saturation *signature* becomes the feature.

Each modality covers the others' blind spot:

| | Strength | Blind spot |
|---|---|---|
| **IMU** 50 Hz | Fast, high-resolution pulse shape | **Saturates** — cannot measure crash magnitude |
| **GPS** 1 Hz | Measures delta-V directly, the quantity the railed IMU lost | Cannot see the ~120 ms pulse at all |
| **Audio** 16 kHz | Independent physical channel; separates "large deceleration" from "large deceleration *plus destruction*" | Noisy; level is not the discriminator |

### 2.2 Architecture

```
IMU   (200, 9)     accel xyz + gyro xyz + per-axis CLIP MASK  -> 1D-CNN (32/64/64) -> 48
AUDIO (64, 126, 1) log-mel                                    -> 2D-CNN (16/32/64) -> 32
GPS   (12,)        1 Hz speed trace                           -> MLP               -> 24
TAB   (26,)        saturation + kinematic + acoustic scalars   -> MLP               -> 32
                      |
              ModalityDropout(p=0.15) on every branch
                      |
              concat -> 64 -> 32 -> {crash sigmoid, severity softmax(5)}
```

- **The clip mask is an input channel, not just a derived scalar**, so convolutions can learn the *temporal shape* of saturation — what remains once peak magnitude is gone.
- **`ModalityDropout` is a product requirement, not regularisation.** Mic permission gets denied; GPS drops in tunnels and urban canyons. A fusion model that collapses when one sensor is missing is useless on exactly the rural and highway stretches this targets.
- **Severity is 5-class** (4 delta-V bands + explicit `NONE`). The alternative — 4 classes with the severity loss masked on negatives via per-output sample weights — is rejected by Keras 3 and was never the better design.

| | |
|---|---|
| Parameters | **76,814** |
| TFLite (float16), precomputed-mel input | **176.7 KB** — the evaluation artifact; not what ships |
| TFLite (float16), **deployable** (raw audio in) | **299.5 KB** — see §2.2b; this is what actually runs on a phone |
| Corpus | 30,000 events; **16,890** pass Stage-A |

### 2.2b The deployable model — raw audio in, nothing normalised client-side

Everything above trains and evaluates on a **precomputed** mel spectrogram (librosa, offline). A phone has a microphone, not offline librosa, so that model is not what ships. `ml/crash_detection/mel_frontend.py` + `model.build_deployable_model` close that gap:

```
raw_audio (64000,)  -> LogMelFrontend (STFT + librosa-matched mel filterbank, baked in)
                          -> log-mel (64, 126, 1)
imu, mel, gps, tab inputs each -> Normalize(mean, std)   [baked-in constants, not client-side arithmetic]
                          -> the SAME trained branch weights as the evaluation model
```

Two skew risks, both closed by construction rather than by convention:

- **The mel computation itself.** `tf.signal.mel_weight_matrix` uses a different mel-scale definition than `librosa.filters.mel` (what generated every training-time spectrogram). Using it would silently retrain the model on a different feature space than what it sees on-device. The librosa filterbank is computed once in Python and baked in as a constant matrix instead — the on-device transform is identical to training by construction, not merely similar. (Also verified independently: `tf.signal.stft` converts to standard TFLite ops with no Flex delegate needed, at ~11 KB; one op — `x[..., tf.newaxis]` — silently required Flex and was replaced with the equivalent `tf.expand_dims`, which does not.)
- **Normalisation.** The trained branches expect normalised input. Shipping that as a contract would require the Android app to reproduce four different `(x-μ)/σ` steps from a stats file in Kotlin — precisely the class of silent mismatch that produced four rounds of leak-hunting in §2.6. Normalisation for all four modalities is baked into the graph as constant weights instead, so the on-device contract is *feed raw sensor values in their physical units*.

Every branch is built as a named, reusable Keras sub-model (`imu_branch`, `audio_branch`, `gps_branch`, `tab_branch`) precisely so the deployable graph can reassemble the trained weights around a raw-audio input **without retraining**.

**Verified before being allowed to save**, via `ml/crash_detection/export_deployable.py`: 300 fresh synthetic events are regenerated from the same held-out source pools as the real test split (same `partition_sources` call, so no leakage), run through both the evaluation model (precomputed mel) and the deployable model (raw audio → on-device frontend) end to end, and the two are asserted to agree before export proceeds.

| Check | Result |
|---|---|
| Decision agreement (300 samples, 87 positive) | **100%** |
| Mean / max / p99 probability difference | **0.0000 / 0.0000 / 0.0000** |
| TFLite vs. deployable Keras model | **0.0000** max diff |

A negative control confirms this is a real check, not one that passes unconditionally: deliberately omitting the audio-branch normalisation step drops decision agreement and pushes the mean probability difference to 0.33 — **6.7× over the assertion's 0.05 threshold** — on an otherwise-identical graph. The check catches the bug it exists to catch.

### 2.3 Corpus construction

```
observed IMU = device( real UCI-HAR background + simulated event physics )
observed AUD = real ESC-50 cabin background    + real crash / confuser audio
observed GPS = kinematically consistent speed trace
```

The device model (clipping, bias, noise, per-handset rail sampled from ±8/16/32 g) is applied **last**, so saturation acts on the summed signal exactly as on a handset. Crash pulses are haversine/half-sine scaled so their integral equals the requested delta-V, which is what makes the severity label physically meaningful.

Nine event types: `CRASH`, `EMERGENCY_STOP`, `HARD_BRAKE`, `POTHOLE`, `SPEED_BUMP`, `PHONE_DROP`, `DOOR_SLAM`, `ROUGH_ROAD`, `NORMAL_DRIVE`. The mix is weighted toward hard negatives because the operative metric is false positives per driving hour, not balanced accuracy.

### 2.4 Split protocol

Disjoint on **three axes simultaneously**, assigned at generation time:

| Axis | train / val / test |
|---|---|
| UCI-HAR subject (IMU background) | 18 / 6 / 6 |
| Crash recording (impact audio) | 27 / 9 / 10 |
| ESC-50 recording | 60% / 20% / 20% |

The split cannot be made post hoc — only the generator knows which source each sample drew from. Grouping by subject alone leaves the same 46 crash waveforms on both sides, which is what produced an audio-only PR-AUC of 1.000 in round 2.

**This leaves ~10 unseen crash recordings in test.** With 38 unique source videos, any audio-branch result is a small-corpus result. Stated, not engineered away.

### 2.5 Results

Operating point chosen on validation to hold FP/100 h inside budget; recall read off on test. These are from the run that also produced the deployable-model verification in §2.2b — corpus, split, and model code are all as currently committed.

| | Degraded gate (no GPS) | Full gate |
|---|---|---|
| Recall | 0.9817 | 0.9840 |
| Precision | 1.0000 | 0.9985 |
| PR-AUC | 0.9999 | 0.9998 |
| FP / 100 driving-h | **0.00** | 1.36 |
| Severity macro-F1 | 0.914 | 0.899 |

Zero false positives at the degraded-gate operating point: `tp=1292, fp=0, fn=24, tn=2063` on the held-out test split.

**Recall by crash severity (delta-V band), degraded gate:**

| Band | 8–18 km/h | 18–30 km/h | 30–48 km/h | 48–80 km/h |
|---|---|---|---|---|
| Recall | 0.955 | 0.977 | 0.984 | 0.997 |

**Baselines (PR-AUC), identical protocol:**

| Baseline | Degraded | Full |
|---|---|---|
| IMU only | 0.9999 | 1.0000 |
| GPS only | 0.9972 | 0.9976 |
| Audio only | 0.9596 | 0.9470 |
| `tab_imu` (saturation scalars) | 0.9964 | 0.9970 |
| `tab_gps` (kinematic scalars) | 0.9903 | 0.9910 |
| `tab_aud` (acoustic scalars) | **0.6955** | **0.6045** |
| `tab_all_handcrafted` (fusion, no deep learning) | 0.9996 | 0.9989 |

> `tab_all_handcrafted` is **not** a unimodal baseline — its 26 scalars span all three sensors. It is the "could you skip deep learning entirely?" comparison. On this corpus the answer is yes, which is another symptom of benchmark saturation.

**Modality removal at inference** (recall / precision / PR-AUC), degraded gate — the result that survives the saturation critique:

| Missing | Recall | Precision | PR-AUC |
|---|---|---|---|
| nothing | 0.982 | 1.000 | 0.9999 |
| audio (`no_mel`) | 1.000 | 0.987 | 0.9999 |
| GPS (`no_gps`) | 0.978 | 0.997 | 0.9997 |
| audio + GPS | 1.000 | 0.968 | 0.9999 |
| **IMU** | 0.966 | 0.985 | 0.9983 |

No branch is load-bearing. Modality dropout did its job — removing IMU, the modality every existing phone crash detector depends on exclusively, costs 1.6 points of recall, not the model.

**Fire rate by event** at the operating point:

| Event | Degraded | Full |
|---|---|---|
| CRASH *(want high)* | 98.2% | 98.4% |
| EMERGENCY_STOP | **0.0%** | **0.0%** |
| POTHOLE | 0.0% | 0.0% |
| SPEED_BUMP | 0.0% | 0.0% |
| PHONE_DROP | 0.0% | 0.3% |
| DOOR_SLAM | 0.0% | — |

`EMERGENCY_STOP` sheds **65.4 km/h** on average against `CRASH`'s **37.1** — a panic stop loses *nearly twice* the speed of the average crash — and none fired. That is the discrimination the fusion design exists for.

### 2.6 Benchmark saturation — the four correction rounds

| # | Leak | Evidence | Fix |
|---|---|---|---|
| 1 | Every negative had a *steady* GPS trace | `gps_drop_kmh` AUC **1.0000**; crashes 13–89 km/h, negatives 0–6, zero overlap | Realistic speed dynamics for negatives; added `EMERGENCY_STOP` |
| 1 | Phone drops fixed at 0–6 km/h | Speed gate rejected 100% for free | Drops now 0–95 km/h (people drop phones in moving cars) |
| 1 | Crash audio mixed 4× louder | `aud_peak_db` AUC **0.9920** | Overlapping gain distributions |
| 2 | **Audio clip leakage** | Same 46 crash clips in train *and* test; audio-only PR-AUC 1.000 | Split-disjoint source pools |
| 2 | GPS positional cue | Crashes collapsed at step 8; negatives braked at random indices | Anchor negatives' reaction to the trigger |
| 3 | GPS pre-impact texture | Crash = white noise around a constant (1.291), negative = random walk (0.933) — class identifiable *before impact* | Shared `_gps_base()` for all events |
| 3 | IMU post-event energy | Crash 0.058 g vs negative 0.305 g — negatives had **zero** ring-down | Suspension response (12 Hz wheel hop, 1.6 Hz body) on negatives |
| 4 | **Gyro smoothness** | AUC **0.804** — only crashes had sustained rotation; clean exponential (1.35) vs jittery bursts (4.68) | Rotational realism: body roll after potholes, phone tumbling, pitch under braking |

After all four: gyro cues at chance (0.507), audio 1.000 → 0.936, acoustic scalars 0.600. **IMU-only stayed at 0.9999.**

The crash pulse is generated by a different functional form from any negative, and a CNN over 200 timesteps finds that no matter how many scalar statistics are matched. Further rounds would keep finding artifacts; the correct conclusion is that this class of benchmark cannot validate a detector.

---

## 3. Model B — `risk_model_v1`

### 3.1 Framing

A severe crash on one 500 m stretch in one specific hour is a near-never event (0.90% of cells). Framing that as classification invites a model that is 99.1% accurate and useless. Production needs an **ordering**, so the primary model is a **LightGBM Poisson regressor** on the 3-year severe-crash count; a binary head is trained alongside only for comparability.

| | |
|---|---|
| Panel | 39,999 segments × 168 hour-of-week = 6.7 M rows (2.5 M after stratified downsampling, all positives kept) |
| Features | 29 |
| Positive rate | 0.90% |
| Black-spot prevalence | 5.15% (iRAD rule, ≥5 severe / 3 y) |
| Crash concentration | top 10% of segments hold **59.9%** of severe crashes |

### 3.2 Validation

Blocked in space (whole districts held out) and time (whole hour-of-day blocks). Weather is drawn per district-hour, so neighbouring segments share conditions — random k-fold would split a district-hour across train and test.

| CV design | PR-AUC | Precision@top-1% | Lift |
|---|---|---|---|
| **Spatial-blocked** | 0.0836 ± 0.0077 | **0.1442** | **15.9×** |
| Temporal-blocked | 0.0832 ± 0.0071 | 0.1430 | 15.8× |
| Random k-fold *(reference)* | 0.0840 ± 0.0021 | 0.1454 | 16.1× |
| Binary, spatial-blocked | 0.0845 ± 0.0080 | 0.1446 | 15.9× |

Of the 1% of segment-hours flagged, **14.4% saw a severe crash** against a 0.90% base rate.

**Risk bands** (quantiles of predicted rate) — monotonic, 126× end to end:

| Band | Observed crash rate |
|---|---|
| Low | 0.09% |
| Moderate | 0.56% |
| High | 2.66% |
| **Severe** | **11.45%** |

**SHAP (mean |contribution|):** `hist_severe_3y` 0.782 ≫ `weather` 0.545 > `traffic_density` 0.194 > `exposure` 0.155 > `district` 0.093 > `is_peak_hour` 0.093 > `visibility` 0.066 > `curvature_deg` 0.045.

History dominating is correct for crash prediction. Driver-facing phrasing renders end to end — top flagged cells read *"crash history here, adverse weather, heavy traffic"*, satisfying PRD FR-4.6.

### 3.3 The optimism gap is +0.0004 — and that is a warning, not a result

Spatial-blocked and random CV are essentially identical. I built the blocked design expecting a gap and there isn't one.

**This is a limitation of the panel, not a vindication of the method.** The generator's spatial structure is fully captured by observed district features (`district_fatal_share`, `district_total_2021`), and weather is i.i.d. per district-hour with no residual spatial autocorrelation. Holding out a district costs the model nothing.

Real iRAD data will have unobserved spatial confounders — enforcement intensity, encroachment, sight lines, local reporting practice. **Keep the blocking.** On real data, a gap of ~0 should be read as a red flag that features are leaking district identity.

---

## 4. Findings that feed back into the PRD

### 4.1 The 4 g Stage-A gate is the recall ceiling

The gate passes only **88.0%** of crashes, and the failures are concentrated at low delta-V:

| delta-V | gate pass |
|---|---|
| 8–18 km/h | **56.4%** |
| 18–30 km/h | 93.0% |
| 30–48 km/h | 99.4% |
| 48–80 km/h | 100% |

No classifier can recover a crash the gate discarded. PRD §7.1 targets ≥90% recall; the gate caps it at 88.0% **before the model runs**. Post-gate recall at 8–18 km/h is 0.955 (§2.5), so the model is not the bottleneck — the gate is.

**Recommendation:** lower the threshold to ~3 g, or make it speed-adaptive (a lower bar above 60 km/h, where a low delta-V event is more likely to be a real impact). Quantifying the FP cost needs a real driving corpus.

### 4.2 The speed pre-condition is load-bearing — and fragile

The `speed ≥ 20 km/h` clause rejects **100%** of dropped phones, which peak at 15.15 g — *harder* than the average crash. But it only works while GPS is alive. With GPS lost (tunnels, urban canyons, cold start), 100% of drops reach the classifier. Both gate configurations are therefore evaluated separately throughout, and the model is trained on the degraded superset so it is correct in both.

### 4.3 Two-wheelers remain unmodelled

PRD Q7 is unresolved and this work does not close it. Two-wheelers are the majority of Indian road fatalities (TN data: VRU deaths are 44.6% of the total) and have a fundamentally different sensor signature — no cabin, no crumple structure, rider separation, the phone often in a jacket or handlebar mount. **Model A is scoped to four-wheelers.** Applying it to two-wheelers without retraining would be unsafe.

### 4.4 Training-loss instability, observed but not investigated

During the 30k retrain, `val_loss` and `val_severity_loss` intermittently spiked by two to three orders of magnitude between otherwise-adjacent epochs (e.g. `val_loss` 0.047 → 5.51 → 22.11 → 0.007 across four consecutive epochs), while `val_crash_auc`, `val_crash_precision`, and `val_crash_recall` stayed flat and near-optimal (0.998–1.000) throughout the same stretch. The pattern — loss detonating while every ranking/threshold metric stays stable — is consistent with a small number of validation examples where the model is extremely *confident and wrong*, which a cross-entropy-family loss punishes far more severely than it rewards confident-and-right examples, without necessarily flipping many decisions.

**This did not affect what shipped.** `EarlyStopping` and `ReduceLROnPlateau` both monitor `val_crash_auc`, not loss, and `restore_best_weights=True` — so the exported model is the best-AUC checkpoint, and every number in §2.5 comes from `model.predict()` on that checkpoint, not from the noisy per-epoch loss log. But the instability itself is a real signal worth chasing before scaling to more epochs or a larger corpus: candidates are label smoothing on the severity head, gradient clipping, or reducing `BinaryFocalCrossentropy`'s `gamma`. Not investigated here for lack of time; flagged rather than silently left out.

---

## 5. Reproducing

```bash
python -m ml.crash_detection.imu_data          # fetch + cache UCI HAR raw signals
python -m ml.crash_detection.audio_data        # fetch + cache crash audio + ESC-50
python -m ml.crash_detection.mel_frontend      # self-test: on-device frontend vs librosa vs TFLite
python -m ml.crash_detection.build_dataset     # 30k multimodal corpus (~15 min)
python -m ml.crash_detection.train             # train + ablate + export both TFLite artifacts
python -m ml.crash_detection.export_deployable # standalone: rebuild + reverify the deployable model

python -m ml.risk_model.ingest             # profile TN + condition multipliers
python -m ml.risk_model.build_panel        # 6.7M-row segment x hour panel
python -m ml.risk_model.train              # blocked CV + final model
python -m ml.risk_model.explain            # SHAP + driver-facing reasons
```

`train.py` calls `export_deployable.py` automatically after training the degraded-gate model — the standalone invocation above is for re-exporting from an already-trained `.keras` file without retraining.

**Artifacts:** `crash_fusion_v1.tflite` (176.7 KB, precomputed-mel, evaluation only) · **`crash_fusion_deployable_v1.tflite` (299.5 KB, raw audio in — this is what ships)** · `crash_fusion_v1.keras` · `crash_fusion_norm.npz` · `risk_model_v1.txt` · `risk_features.json`
**Reports:** `crash_detection_results.json` (includes the `deployable` verification block) · `risk_model_results.json` · `risk_shap_global.csv` · `risk_reason_frequency.json`

Seed 20260815 throughout.

---

## 6. Before any deployment

| # | Requirement | Why |
|---|---|---|
| 1 | **Collect real crash telemetry** — instrumented drives, controlled low-speed impacts, a shake rig | Nothing in §2.5 substitutes for this. PRD Q3/Q4 |
| 2 | **Collect real hard negatives at scale** — the cancel-window feedback loop (PRD FR-1.6) | The FP rate is the deployment-critical number and is currently unmeasurable |
| 3 | Re-run the §2.6 leak audit against real data | Confirms whether the ablation gaps survive |
| 4 | Replace ESC-50 | CC BY-NC blocks commercial use |
| 5 | Obtain real iRAD segment data | Replaces `build_panel.py`; trainer, CV design and metrics are unchanged |
| 6 | Re-check the optimism gap | On real data it should be > 0; ~0 means feature leakage |
| 7 | Battery profiling on 3 device tiers | PRD NFR-B1–B4, untested here |
| 8 | Fairness audit across district socioeconomic strata | PRD §7.3; rural under-reporting is a known artifact of Indian crash data |
| 9 | Decide the two-wheeler question | PRD Q7 |

**Model A must not be connected to a live dispatch path** — not even the simulated gateway in a public demo — until items 1–3 are done. A demo may show it firing on a shake rig, clearly labelled as a synthetic-data model.
