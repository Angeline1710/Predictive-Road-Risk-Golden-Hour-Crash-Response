# UI/UX & Application Flow Specification
## Predictive Road-Risk & Golden-Hour Crash Response

| Field | Value |
|---|---|
| **Document version** | 1.0 |
| **Date** | 2026-08-14 |
| **Companion to** | `PRD.md` v1.0 |
| **Design system name** | **Milestone** |
| **Surfaces covered** | Android driver app (`rrx-app`), Government operations dashboard (`rrx-ops`) |
| **Status** | Draft — for design review |

---

# PART I — DESIGN THESIS

## 1. The problem this interface has to solve

Most government software fails at one of two things: it is either **institutionally correct and unusable**, or **visually pleasant and untrustworthy**. This product cannot afford either failure, because it has two users at opposite ends of the human stress spectrum:

| | Driver app | Ops dashboard |
|---|---|---|
| **User state** | Possibly injured, in the dark, in pain, adrenalised, one-handed, phone screen possibly cracked | Calm, seated, 8-hour shift, multiple monitors, possibly projected in an ops room |
| **Comprehension budget** | **Under 1 second** | Minutes |
| **Failure cost** | A person dies | A person dies slower |
| **Design imperative** | Ruthless reduction | Dense but calm information |

A single visual language has to stretch across both without becoming two products. That is the central design problem, and everything below is an answer to it.

## 2. Six design principles

**P1 — One decision per screen, always.**
The crash screen has exactly one control. The dashboard's incident view has exactly one primary action. Ambiguity is a latency cost, and latency is the product's entire value proposition.

**P2 — Degradation must be visible, never silent.**
This system is architecturally built on graceful fallback (data → SMS → local siren; live model → cached → historical). If the interface hides which rung it is on, the user builds false confidence. **Every degraded state gets a visible, named badge.** A system that quietly does less is a system that lies.

**P3 — Colour carries meaning; it is never decoration.**
There are exactly four risk bands and four incident severities in this product. Every hue in the palette is spoken for. If a colour appears on screen, it means something specific, and it means the same thing on every surface.

**P4 — Simulation is disclosed loudly, by design, not by disclaimer.**
The government gateway is mocked. That fact gets a dedicated visual treatment (§7.5) applied at the component level, not a footnote in a modal. Honesty is a design system component here.

**P5 — Institutional gravity without institutional dreariness.**
This will sit in front of MoRTH, NHAI, and state road-safety cells. It must read as *serious infrastructure* — measured, precise, instrument-grade. It must not read as a startup dashboard, and it must not read as a 2011 government portal.

**P6 — Legibility beats beauty, but they are rarely in conflict.**
Where they conflict, legibility wins without discussion. In practice, the constraints of this product (huge type, high contrast, warm night-safe tones, monospace telemetry) *produce* the distinctive look. The aesthetic is downstream of the requirements, which is why it doesn't look like anything else.

## 3. The concept: **Milestone**

> The design language is drawn from the physical vocabulary of the Indian road — not from software convention.

Three real-world objects supply the entire visual system:

**① The kilometre stone.** India's roadside milestone is one of the most quietly distinctive pieces of public design in the country: a white stone with a coloured cap that encodes the road class (yellow = National Highway, green = State Highway, black = district road, orange = village road). It is a **data marker that has existed on Indian roads for a century**. It becomes our map marker, our incident card shape, and our segment token.

**② The sodium-vapour highway lamp.** The specific amber of Indian highway lighting and of hazard lights. It is warm, it is night-safe, it is unmistakably associated with *road* and with *caution* — and critically, **amber, not red, is the international signal for a vehicle in distress**. It becomes our signature accent and the colour of the crash screen.

**③ The NH signboard.** Deep institutional green with white type. It supplies our surface and chrome colours, and gives the product its governmental register without a single drop of the default blue.

**Why this beats a blue government template:** blue is the colour of every civic dashboard on earth, carries no domain meaning, and performs poorly in the two contexts that matter most here — night driving (blue light impairs dark adaptation) and high-glare daylight. Amber-on-bitumen is *correct* before it is *attractive*.

---

# PART II — THE DESIGN LANGUAGE

## 4. Colour system

### 4.1 Palette architecture

Four families. Nothing outside these ships.

| Family | Role | Emotional register |
|---|---|---|
| **Bitumen** | Grounds and surfaces (dark theme) | Night asphalt. Green-shifted black, never blue-black |
| **Paper** | Grounds and surfaces (light theme) | Warm document stock. Never pure white |
| **Sodium** | The signature accent, all primary actions, the crash screen | Highway lamp, hazard light, golden hour |
| **Highway** | Institutional chrome, confirmed/safe states, government surfaces | NH signage green |

Plus two **semantic-only** ramps that are never used decoratively: the **Risk Band** ramp and the **Flare** critical colour.

### 4.2 Bitumen — dark theme grounds

The dark theme is the **default for the driver app at all times** and for the dashboard's Live Operations view. The green cast (rather than a neutral or blue-black) is deliberate: it makes the amber accent read as *warm light on asphalt* rather than as a floating UI element, and it is measurably calmer at night.

| Token | Hex | Use |
|---|---|---|
| `bitumen-000` | `#0A0F0D` | Page ground, deepest. Full-screen map base |
| `bitumen-050` | `#0E1512` | Default app canvas |
| `bitumen-100` | `#141C18` | Card and panel surface |
| `bitumen-200` | `#1B241F` | Elevated surface, modals, popovers |
| `bitumen-300` | `#24302A` | Hover / pressed state fill |
| `bitumen-400` | `#33413A` | Borders, dividers, chart gridlines |
| `bitumen-500` | `#475A50` | Strong border, disabled control fill |

### 4.3 Paper — light theme grounds

Light theme is the default for the dashboard's **Analytics, Reports, and Export** views — the ones that get printed, projected, and pasted into government presentations. Warm off-white, never `#FFFFFF`: pure white on a projector in a lit ops room is fatiguing, and warm paper harmonises with the amber accent instead of fighting it.

| Token | Hex | Use |
|---|---|---|
| `paper-000` | `#FBFAF6` | Page ground |
| `paper-100` | `#F4F2EA` | Card surface |
| `paper-200` | `#EAE7DB` | Elevated / inset surface |
| `paper-300` | `#DCD8C8` | Hover fill |
| `paper-400` | `#C6C1AE` | Borders, gridlines |

### 4.4 Ink — typography colours

| Token | Dark theme | Light theme | Use |
|---|---|---|---|
| `ink-primary` | `#F4F1EA` | `#141A16` | Body and headings |
| `ink-secondary` | `#C6C0B2` | `#3E4740` | Supporting copy, labels |
| `ink-muted` | `#8E887A` | `#6B7369` | Captions, metadata, timestamps |
| `ink-disabled` | `#5A564C` | `#9DA398` | Disabled state |
| `ink-inverse` | `#0E1512` | `#FBFAF6` | Text on Sodium and Flare fills |

> **Never pure white text.** `#F4F1EA` is a warm off-white. At night, on a phone held 40cm from the face, pure white causes visible halation around glyphs. This single substitution is the difference between "readable at 2am" and "squint."

### 4.5 Sodium — the signature accent

The hero colour. Primary buttons, active states, the risk-warning voice cue, the crash screen fill, live-data indicators.

| Token | Hex | Use |
|---|---|---|
| `sodium-200` | `#FFE3B8` | Faint tint, chart fills, selected-row background (light theme) |
| `sodium-300` | `#FFCC80` | Hover tint, secondary emphasis |
| `sodium-400` | `#F5B14C` | Hover state of primary control |
| `sodium-500` | `#E8971C` | **Primary accent.** Buttons, active nav, focus ring, crash-screen fill |
| `sodium-600` | `#C87C0D` | Pressed state |
| `sodium-700` | `#94590A` | Borders on sodium fills, dark-theme dividers on amber surfaces |

> **Contrast rule:** `sodium-500` against `bitumen-050` = **6.6:1** — passes AA for normal text and AAA for large text. But text placed *on* a `sodium-500` fill must be `ink-inverse` (`#0E1512`), **never white**. White on amber is 2.1:1 and fails everything. This is the single most common way teams break this palette.

### 4.6 Highway — institutional green

Used for: confirmed and successful states, the government-integration surfaces, dashboard chrome, and the "protection active" indicator. It is the colour of the system *working*.

| Token | Hex | Use |
|---|---|---|
| `highway-300` | `#5FBF95` | Success text on dark, active status dot |
| `highway-500` | `#1F6B4A` | Institutional fill, secondary buttons, gov-surface header |
| `highway-600` | `#175339` | Pressed |
| `highway-700` | `#0F3A28` | Deep fill, sidebar ground on the ops dashboard |

### 4.7 Risk Band ramp — semantic, four values only

This ramp appears on the map, the Segment Ribbon, the risk chips, and every chart axis that encodes risk. It is **the most important colour decision in the product**, because a driver reads it at 80 km/h and an analyst reads it across 50,000 segments.

| Band | Token | Hex | Pattern | Letter | Map stroke |
|---|---|---|---|---|---|
| **Low** | `risk-low` | `#3E8C74` | Solid | `L` | 3 px |
| **Moderate** | `risk-mod` | `#D9A227` | 45° hatch, 6px pitch | `M` | 4 px |
| **High** | `risk-high` | `#D9622B` | 45° hatch, 3px pitch | `H` | 5 px |
| **Severe** | `risk-severe` | `#B4232F` | Cross-hatch, 3px pitch | `S` | 6 px |
| **No data** | `risk-none` | `#4A554E` | Dashed outline, no fill | `–` | 2 px dashed |

**Triple encoding is mandatory (NFR-A3).** Every risk band carries **hue + pattern + letter token**, and on the map additionally **stroke weight**. Reasons:

- ~8% of Indian men have red-green colour vision deficiency. Under deuteranopia, `risk-mod` / `risk-high` / `risk-severe` compress toward a single olive-brown. Hue alone would render three of four bands identical to a meaningful share of both drivers and operators.
- Government documents get **photocopied and faxed in greyscale.** A risk map that becomes four identical grey ribbons on a printout is worthless in exactly the meeting where it matters. Patterns survive greyscale; hue does not.

**Why not a traffic light (green/yellow/red).** Two reasons. First, an actual traffic signal on a road-safety map means "there is a signal here" — a direct semantic collision. Second, a literal traffic-light ramp puts "safe green" on stretches that are merely *less lethal than average*, which overstates safety. The sage-teal `risk-low` reads as *measured*, not as *safe*, which is the honest message.

### 4.8 Flare — critical, and deliberately scarce

| Token | Hex | Use |
|---|---|---|
| `flare-500` | `#E03131` | **Only**: irreversible failure, delivery failed on all channels, gateway rejection, destructive confirmation |
| `flare-100` | `#FFE0E0` | Failure banner ground (light theme) |

> **Red is not the crash colour.** See §5.1. Red in this product means *the system failed*, never *an emergency occurred*. Keeping these separate is what lets an operator distinguish "a crash happened" (routine, expected, handled) from "our pipeline broke" (rare, alarming) at a glance across a wall display.

### 4.9 Contrast conformance table

| Pair | Ratio | Verdict |
|---|---|---|
| `ink-primary` on `bitumen-050` | 15.8:1 | AAA |
| `ink-primary` on `paper-000` | 16.1:1 | AAA |
| `ink-muted` on `bitumen-050` | 5.4:1 | AA normal, AAA large |
| `sodium-500` on `bitumen-050` | 6.6:1 | AA normal, AAA large |
| `ink-inverse` on `sodium-500` | 6.6:1 | AA normal, AAA large |
| `highway-300` on `bitumen-050` | 7.9:1 | AAA |
| `risk-low` on `bitumen-050` | 5.1:1 | AA normal |
| `risk-severe` on `paper-000` | 6.2:1 | AA normal |
| ⚠ White on `sodium-500` | 2.1:1 | **FAIL — never ship** |

---

## 5. The colour decision that defines the product

### 5.1 Why the crash screen is amber, not red

The single highest-stakes screen in this product is the 10-second cancel window. Convention says: red, full-bleed, klaxon. We are rejecting that, deliberately, for four reasons:

1. **Amber is the true-world signal.** A vehicle in distress on a road anywhere on earth shows **amber hazard lights**. Red on a road means *stop* or *brake*. We are not asking the user to stop; we are telling them help is being summoned. Amber is semantically correct, and correctness compounds under stress — people fall back on trained associations when adrenalised.

2. **Red degrades decision-making at exactly the wrong moment.** The user has ~10 seconds to make a judgement (*am I actually hurt, or did I just drop the phone?*). A full-bleed red panic field measurably increases arousal and impairs that judgement. We need them **calm enough to think and physically able to press one button.**

3. **We need red to mean something else.** Red is reserved for `flare-500` — system failure. If red is spent on "a crash happened," the operator can no longer distinguish an ordinary incident from a broken pipeline on a wall display. Semantic scarcity is what makes a colour system work.

4. **Amber is legible in both conditions this screen actually occurs in.** Direct 2pm highway glare and pitch-black 2am. Deep red at maximum brightness in sunlight goes muddy; amber holds. Red at night in a dark cabin destroys dark adaptation for 20+ minutes — for a user who may still need to see the road.

**The crash screen is a full-bleed `sodium-500` field with `ink-inverse` type.** It looks like your hazard lights turned on. Nobody else's safety app looks like this, and it is the right answer before it is the distinctive one.

---

## 6. Typography

### 6.1 The three-voice system

| Voice | Latin family | Indic family | Role |
|---|---|---|---|
| **Display** | **Fraunces** (variable; `SOFT 0`, `WONK 0`, opsz linked to size) | **Noto Serif** Devanagari / Tamil / Telugu / Bengali | Screen titles, section headings, incident headlines, the number in the countdown |
| **Interface** | **Inter** (variable) | **Noto Sans** Devanagari / Tamil / Telugu / Bengali | All body copy, labels, buttons, navigation, tables |
| **Telemetry** | **IBM Plex Mono** | *(Latin numerals in all locales — see §6.4)* | Every number that is a measurement: coordinates, speed, g-force, timers, IDs, latency, timestamps |

**Why a serif display face in a government product.** A high-contrast transitional serif carries institutional authority that a grotesque cannot — it is the typographic register of statutes, gazettes, and survey documents. Fraunces supplies that gravity while being unmistakably contemporary (variable, optically sized, drawn this decade). Set with `WONK` at 0 it is restrained and official; the axis exists if a marketing surface later wants more character. It is the single strongest signal that this is *public infrastructure*, not a consumer app — and it is the opposite of the Arial/Verdana register of legacy government portals.

**Why monospace for every measurement.** This is the product's most distinctive typographic move and it is functional, not stylistic:

- **Tabular figures align in columns without effort.** An operator scanning 40 incident latencies down a rail compares magnitudes by *glyph position*, pre-attentively, without reading.
- **Digits do not reflow as they change.** A live countdown or a ticking latency counter set in a proportional face jitters horizontally on every tick — visible, cheap-looking, and genuinely distracting on a screen someone stares at for eight hours.
- **It reads as instrument output.** Monospaced numerals are the visual grammar of scientific and engineering instruments. A coordinate set in Plex Mono is *read as a measurement*; the same coordinate in Inter is read as *text about a measurement*. For a system whose credibility with MoRTH rests on being instrument-grade, this is worth the extra font.

### 6.2 Type scale

Base 16px / 16sp. Ratio 1.25 (major third), with two deliberate breaks at the top for the crash screen.

| Token | Size | Line height | Weight | Family | Use |
|---|---|---|---|---|---|
| `type-countdown` | **200sp** | 1.0 | 600 | Display | The cancel-window numeral. Only ever used once |
| `type-hero` | 72 / 72sp | 1.05 | 600 | Display | Crash-screen headline, dashboard hero stat |
| `type-display-1` | 48 | 1.1 | 600 | Display | Page title |
| `type-display-2` | 36 | 1.15 | 600 | Display | Section heading, incident headline |
| `type-heading-1` | 28 | 1.25 | 600 | Display | Card title |
| `type-heading-2` | 22 | 1.3 | 600 | Interface | Panel header |
| `type-heading-3` | 18 | 1.4 | 600 | Interface | Sub-header, table group |
| `type-body-lg` | 17 | 1.55 | 400 | Interface | Driver-app body (larger than web — read at arm's length in motion) |
| `type-body` | 15 | 1.6 | 400 | Interface | Dashboard body |
| `type-label` | 13 | 1.4 | 500 | Interface | Form labels, chips, nav |
| `type-caption` | 12 | 1.4 | 400 | Interface | Metadata, timestamps, helper text |
| `type-overline` | 11 | 1.2 | 600, `+0.09em` | Interface | Section eyebrows, uppercase. Used sparingly |
| `type-telemetry-lg` | 32 | 1.1 | 500 | Telemetry | Hero metrics, Golden Hour clock |
| `type-telemetry` | 15 | 1.5 | 400 | Telemetry | Coordinates, IDs, measurements |
| `type-telemetry-sm` | 12 | 1.4 | 400 | Telemetry | Table cells, dense readouts |

### 6.3 Typographic rules

- **Never a weight below 400.** Thin and light weights disintegrate on low-DPI budget Android panels and vanish in sunlight. The whole install base this product exists to serve is on those panels.
- **Measure capped at 68 characters** for body copy. Consent copy capped at **52** — it must be genuinely readable, because consent that isn't read isn't consent.
- **No text over 3 lines in the driver app** outside onboarding and settings.
- **Sentence case everywhere.** Uppercase only for `type-overline` and the three-letter channel badges (`SMS`, `SOS`).
- **Tabular figures on** (`font-variant-numeric: tabular-nums`) for every Interface-family number too, not just Telemetry.

### 6.4 Multi-script typography

Five languages at demo: **English, हिन्दी, தமிழ், తెలుగు, বাংলা**. Architecture supports all 22 scheduled languages.

| Concern | Specification |
|---|---|
| **Vertical metrics** | Devanagari, Tamil, Telugu, and Bengali all need more vertical room than Latin — ascenders, matras, and conjuncts. **All line heights increase by 0.15 when the locale is Indic.** A container sized for English will clip Devanagari matras; every container must be height-flexible, never fixed |
| **Optical size compensation** | Noto Sans Devanagari at 15px reads noticeably smaller than Inter at 15px. Apply a **per-script size multiplier**: Devanagari ×1.06, Bengali ×1.06, Tamil ×1.10, Telugu ×1.10 |
| **Numerals** | **Latin/Western Arabic numerals in every locale, without exception.** Indian usage is overwhelmingly Western-numeral across all these scripts, and every telemetry value must remain comparable across an operator's screen regardless of the reporting device's locale. Devanagari numerals (०१२) are never used |
| **Text expansion** | Hindi runs ~15–20% longer than English; Tamil and Telugu can run 25%+. **All layouts are specified and reviewed at Tamil length, not English.** English-first layout review is the standard way multilingual products break |
| **The countdown numeral** | Language-independent by construction — it is a digit. This is deliberate: the highest-stakes glyph on the highest-stakes screen requires zero localisation and zero literacy |
| **Font budget** | ~2.1 MB of subsetted variable fonts in the APK. Subset to the actual glyph coverage required; ship Latin + the device's primary Indic script, download others on demand |

---

## 7. Signature components

These seven components are what make the product recognisable. They are shared across both surfaces.

### 7.1 Milestone Marker

**What it is.** The map marker and incident token, shaped after the Indian roadside kilometre stone: a vertical rounded-top form with a coloured cap band.

**Function.** Encodes risk band (on risk maps) or incident severity (on the incident map) in its cap. Replaces the generic teardrop pin, which carries no information and appears in every mapping product ever shipped.

**How it looks.**
```
      ╭─────────╮   ← cap: 12px tall, radius 10px top corners
      │▨▨▨▨▨▨▨▨▨│      fill = risk band / severity colour
      ├─────────┤      carries the band's hatch pattern
      │   S     │   ← letter token, Telemetry 12px, ink-inverse
      │  0.84   │   ← risk score or incident time, Telemetry 11px
      ╰─────────╯   ← body: paper-000 (light) / bitumen-100 (dark)
           ▼          1px border bitumen-400
                      2px pointer stem, 6px triangle foot
```
- **Dimensions:** 40 × 52 px at 1×; scales to 32 × 42 at map zoom < 11, collapses to a 12 px cap-coloured dot below zoom 9.
- **Live incident state:** a `sodium-500` halo pulses at 1.4 s intervals, 0 → 20 px, opacity 0.5 → 0. Stops the moment the incident is acknowledged. **Only unacknowledged incidents pulse** — so an operator's eye is drawn only to what needs them.
- **Selected state:** scales to 1.15×, cap gains a 2px `sodium-500` outline, body lifts to `bitumen-200`.

### 7.2 Segment Ribbon

**What it is.** The product's most-used component. A horizontal strip of 500 m road segments, each rendered as a cell coloured and hatched by risk band.

**Function.** Shows risk *along a length of road* — which is the actual shape of the data. The 500 m cell is not arbitrary: it is deliberately matched to MoRTH's own iRAD blackspot unit, so an analyst comparing our output against the official blackspot list is comparing like with like, cell for cell.

**How it looks.**
```
 NOW                                                    5 km AHEAD
 ┌────┬────┬────┬────┬────┬────┬────┬────┬────┬────┐
 │▓▓▓▓│▓▓▓▓│░░░░│▒▒▒▒│████│████│▒▒▒▒│░░░░│░░░░│▓▓▓▓│
 └────┴────┴────┴────┴────┴────┴────┴────┴────┴────┘
   L    L    M    H    S    S    H    M    M    L
        ▲
    you are here — sodium-500 chevron below the strip
```
- **Cell:** 32 px tall (app) / 24 px (dashboard), 1 px `bitumen-400` gap between cells.
- **Position indicator:** a `sodium-500` chevron beneath the current cell; the ribbon scrolls under a fixed chevron rather than the chevron moving — motion is smoother and the "now" position stays in a fixed, learnable place.
- **Letter row** below each cell in Telemetry 11px (this is the greyscale/colour-blind fallback).
- **Tap/hover** a cell → popover with segment ID, score, and the SHAP top-3 factors.
- **Dashboard variant:** horizontally scrollable across a full corridor with a kilometre ruler above and a 24-hour time-scrubber below, turning it into a corridor heat-strip.

### 7.3 Golden Hour Dial

**What it is.** The product's emotional centre and its namesake — a 60-minute radial countdown that begins the instant a crash is confirmed.

**Function.** Makes the stake visible. Every incident record, on every screen, shows how much of the golden hour remains. This is the single most persuasive element in a jury demo and the single most operationally useful element for a dispatcher, because it converts an abstract clinical concept into an unignorable, ticking object.

**How it looks.**
```
        ╭───────────────╮
      ╱ ┆ ┆ ┆ ┆ ┆ ┆ ┆ ┆ ╲     ← 60 tick marks, one per minute
     │  ┆             ┆  │      elapsed ticks: bitumen-400
     │                   │      remaining ticks: gradient sodium→flare
     │      41:18        │    ← Telemetry 32px, ink-primary
     │   REMAINING       │    ← Overline 11px, ink-muted
      ╲                 ╱
        ╰───────────────╯
```
- **Diameter:** 160 px (incident detail) / 72 px (list row, numeral only, no label).
- **Progress arc:** 6 px stroke, sweeps clockwise from 12 o'clock. Colour interpolates across the drain: `sodium-500` (60–40 min) → `sodium-600` (40–20) → `risk-high` (20–10) → `flare-500` (<10 min).
- **Under 10 minutes:** the arc pulses at 1 s (one pulse per second — a heartbeat cadence, not a strobe), and the row is pinned to the top of the incident rail.
- **At zero:** the dial does **not** disappear or turn into a failure state. It flips to a **count-up** in `ink-muted` labelled `+12:04 ELAPSED`. The golden hour passing is not a system error and must never be styled as one — care continues, and treating it as a failure would be both wrong and demoralising for the operators watching.
- **Never used decoratively.** One dial per incident, nowhere else.

### 7.4 Channel Badge

**What it is.** A three-state badge showing how an alert reached the system.

**Function.** The delivery channel is the product's core differentiator — a `SMS` badge means *this alert came from somewhere with no data connectivity, and would not exist in any other system*. It deserves visual weight, not a table column.

**How it looks.**

| Badge | Fill | Text | Glyph | Meaning |
|---|---|---|---|---|
| `DATA` | `bitumen-300` | `ink-secondary` | Signal bars | Arrived over HTTPS, full payload with sensor trace |
| `SMS` | transparent, **1.5 px `sodium-500` border** | `sodium-500` | Envelope | **Arrived over SMS — zero data connectivity.** Outlined, never filled, so it stands out against filled neighbours |
| `SOS` | `flare-500` | `ink-inverse` | Hand | Manually triggered by a human, not detected |

- 22 px tall, 8 px horizontal padding, 4 px radius, Overline 11px.
- The `SMS` badge additionally carries a `PARTIAL` sub-chip when `has_trace = false`, because the operator must know the sensor trace is missing rather than assume the record is complete.

### 7.5 Simulation Seal

**What it is.** A mandatory, non-dismissible visual treatment applied to every element representing the simulated government gateway.

**Function.** Design-level enforcement of PRD §11. It must be impossible for a jury member, an operator, or a screenshot to mistake simulated dispatch for real dispatch. **This is an ethics requirement expressed as a component.**

**How it looks.**
```
╔═══════════════════════════════════════════════════╗
║ ⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋ ║
║  SIMULATED DISPATCH — no live government link     ║
║ ⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋ ║
╟───────────────────────────────────────────────────╢
║  Ticket SIM-2026-0814-004417                      ║
║  Assigned  Chengalpattu GH Trauma · 6.2 km        ║
╚═══════════════════════════════════════════════════╝
```
- **Border:** 2 px dashed `flare-500`, 6 px dash / 4 px gap, on every side.
- **Header strip:** 28 px, `flare-500` at 12% opacity, with 45° diagonal hatching at 8 px pitch.
- **Label:** `SIMULATED DISPATCH` in Overline `flare-500`, plus a plain-language clause. Never an abbreviation, never an icon alone.
- **Rules:** cannot be dismissed, collapsed, or themed away. Persists in every PDF and PNG export. Applies to the ticket ID, responder assignment, ETA, and acknowledgement — every field the simulation produced. Real fields on the same screen (location, severity, sensor trace) sit **outside** the seal, so the boundary between measured and mocked is drawn in pixels.

> This is the **one** place `flare-500` red appears outside a genuine failure, and the exception is deliberate: "you are looking at something that is not real" warrants the strongest signal in the system.

### 7.6 Trace Sparkline

**What it is.** The 12-second accelerometer trace rendered as a filled area chart.

**Function.** It is the evidence. It converts "our model says this was a crash" into something a human — an operator, a jury member, a road-safety official — can verify with their own eyes in under a second. The shape of a genuine crash pulse is visually unmistakable from a phone drop.

**How it looks.**
- 100 px tall, full panel width. X-axis: −8 s to +4 s around impact. Y: acceleration magnitude in g.
- Fill: vertical gradient `sodium-500` at 35% → transparent. Stroke: 1.5 px `sodium-500`.
- **Impact moment:** a 1 px vertical `flare-500` rule with a `T=0` label and the peak-g value in Telemetry.
- **The 4 g detection threshold** drawn as a dashed `bitumen-500` horizontal rule with a `4.0 g` label — so a viewer can see *why* the system triggered, not just that it did.
- **Post-impact region** (T>0) tinted 6% `flare-500` when `still_moving = true` — an at-a-glance secondary-collision risk cue.
- Hover scrubs a Telemetry readout of the exact value at that timestamp.

### 7.7 System Honesty Bar

**What it is.** A persistent 32 px strip along the bottom of the ops dashboard showing the live health of every dependency.

**Function.** Direct expression of principle **P2**. This architecture is built on graceful degradation, so the operator must always know which rung the system is on. An operator who doesn't know the weather feed is 3 hours stale will over-trust a risk score.

**How it looks.**
```
┌──────────────────────────────────────────────────────────────────────────┐
│ ● WEATHER 4m  ● TRAFFIC 2m  ◐ IMD 3h STALE  ● SMS GW  ◆ GATEWAY SIMULATED │
│                                          INGEST p95 218ms  ·  1,284 DEVICES│
└──────────────────────────────────────────────────────────────────────────┘
```
- **Status glyphs:** `●` healthy (`highway-300`) · `◐` degraded (`sodium-500`) · `○` down (`flare-500`) · `◆` simulated (`flare-500`).
- Each feed shows **data age in Telemetry**, not a vague "connected" — age is the number that actually tells you whether to trust the map.
- Clicking a feed opens its 24-hour availability strip.
- The gateway indicator is permanently `◆ GATEWAY SIMULATED` in v1 and cannot be hidden.

---

## 8. Layout, elevation, and motion

### 8.1 Spacing and grid

4 px base unit. Scale: `4 · 8 · 12 · 16 · 24 · 32 · 48 · 64 · 96`.

| Surface | Grid |
|---|---|
| **Dashboard** | 12-column, 24 px gutter, 1440 px max content width, 32 px page padding. Ops view breaks the max-width and goes edge-to-edge (map wants every pixel) |
| **App** | Single column, 20 px horizontal margin, 16 px between cards |
| **Touch targets** | 48 dp minimum. **Crash-screen cancel button: 96 dp tall, full width minus margins** |

### 8.2 Radius and elevation

| Token | Value | Use |
|---|---|---|
| `radius-sm` | 4 px | Chips, badges, input fields |
| `radius-md` | 8 px | Cards, buttons, panels |
| `radius-lg` | 12 px | Modals, bottom sheets |
| `radius-full` | 999 px | Status dots, avatars, the dial |

**Elevation is expressed by surface colour, not shadow, in dark theme.** Shadows on near-black grounds are invisible and only add render cost; stepping `bitumen-100` → `200` → `300` reads cleanly. Light theme uses two soft shadows only:
- `shadow-card`: `0 1px 2px rgba(20,26,22,.06), 0 2px 8px rgba(20,26,22,.04)`
- `shadow-modal`: `0 8px 32px rgba(20,26,22,.16)`

No glassmorphism, no blur-backdrop panels, no neumorphism. All three reduce contrast, and this product cannot spend contrast.

### 8.3 Motion

| Token | Duration | Easing | Use |
|---|---|---|---|
| `motion-instant` | 0 ms | — | **The entire crash path.** Nothing animates in |
| `motion-fast` | 120 ms | `cubic-bezier(.2,0,0,1)` | Hover, focus, chip toggle |
| `motion-base` | 180 ms | `cubic-bezier(.2,0,0,1)` | Panel open, tab switch |
| `motion-emphasis` | 280 ms | `cubic-bezier(.3,0,0,1)` | Bottom sheet, modal, map fly-to |
| `motion-ambient` | 1400 ms | `ease-in-out`, infinite | Live-incident pulse, breathing indicators |

**Rules:**
- **The cancel window has zero entrance animation.** It appears fully formed on frame one. A 280 ms fade-in on a 10-second countdown is 2.8% of the user's decision budget spent on decoration.
- **`prefers-reduced-motion` disables every ambient animation.** The countdown numeral, the Golden Hour dial, and all colour-state changes continue — they are information, not motion, and suppressing them would remove content.
- **No spring physics, no bounce, no overshoot** anywhere. Bounce reads as playful. Nothing here is playful.

### 8.4 The signature motion: **Headlight Sweep**

Replaces the generic skeleton shimmer for all loading and live-refresh states.

A soft 120 px-wide `sodium-500` gradient band at 8% opacity travels left→right across the loading surface at a constant 900 ms, with a 400 ms pause between passes. Angled 12° off vertical, so it reads as **headlights passing a stationary object at night**, not as a shimmer.

Used for: skeleton loaders, the live-tile refresh on the risk map, the "awaiting acknowledgement" state on an incident card. Ties every waiting moment back to the product's world, and — because 8% opacity on `bitumen-100` is genuinely subtle — it never competes with content.

## 9. Iconography

- **Library:** Phosphor Icons, `regular` (1.5 px) for UI, `fill` for status. Chosen for its wide, geometric, low-contrast strokes, which survive small sizes on low-DPI panels far better than Feather's thin 2 px strokes.
- **Sizes:** 16 / 20 / 24 px. Driver app minimum 24 px.
- **Nine domain glyphs are custom-drawn**, because no library has them and they carry the product's identity: *kilometre stone · road segment · hazard triangle · cancel window (a stopwatch with a segmented ring) · SMS fallback (an envelope over a signal-less mast) · rollover · impact vector (a directional burst) · trauma centre · ambulance*.
- **No emoji anywhere in product UI.** Emoji render differently per OEM, break on older Android, carry unintended tone, and are the single fastest way to make a government product look unserious.

---

# PART III — DRIVER APP FLOW

Platform Android, Jetpack Compose, Material 3 as a **structural** base only — Material's default colour roles, elevation shadows, and dynamic-colour theming are all overridden. **Dark theme always, no light theme.** Rationale: the app's critical moments happen in a vehicle, disproportionately at night, and a theme switch introduces a state where a driver could face an unexpectedly bright screen at 2 a.m.

## 10. Flow map

```
 First run ─→ Onboarding (9 steps) ─→ HOME (idle)
                                        │
                             drive detected (Activity Recognition)
                                        ↓
                                   DRIVE MODE ←──────────┐
                                        │                │
                        ┌───────────────┼──────────┐     │
                        ↓               ↓          ↓     │
                RISK WARNING     CRASH DETECTED   long-press SOS
                (High/Severe)    (cancel window)   │     │
                        │               │          │     │
                        └───────────────┤          │     │
                                        ↓          ↓     │
                                   ┌─ CANCELLED ───────→─┘
                                   │
                                   ↓
                                SENDING ─→ SENT ─→ ACKNOWLEDGED
                                   │                    │
                                   ↓                    ↓
                            ALL CHANNELS FAILED    GOLDEN HOUR ACTIVE
                            (local escalation)          │
                                                        ↓
                                                   TRIP SUMMARY
```

## 11. Onboarding

Nine steps. Consent is the hardest design problem in this product: we are asking for background location, motion sensors, and SMS-send — the three most alarming permissions on Android — from a user who has just installed a free app. **Every step earns the next one.**

### 11.1 Step 1 — The promise

| Element | Function | Appearance |
|---|---|---|
| **Ground** | Set the register immediately | Full-bleed `bitumen-000`. A faint `sodium-500` at 4% radial gradient from the bottom edge — a distant highway lamp. No photograph, no illustration |
| **Headline** | The entire value proposition in one sentence | Display 48 / `ink-primary`, max 3 lines: *"If you crash and can't call, your phone will."* |
| **Sub** | Establish scope honestly | Body-lg / `ink-secondary`: *"Works on this phone. Works without internet. Works in your language."* Three clauses, three differentiators, no adjectives |
| **Milestone graphic** | Introduce the motif | A single Milestone Marker, 96 px, `sodium-500` cap, centred above the headline. Static |
| **Primary CTA** | Advance | Full-width 56 dp, `sodium-500` fill, `ink-inverse` label *"Set up protection"*, `radius-md` |
| **Tertiary** | Respect the sceptic | Text button `ink-muted`: *"How this works"* → a 4-panel plain-language explainer. Non-blocking. Users who read this convert better and uninstall less |

### 11.2 Step 2 — Language

| Element | Function | Appearance |
|---|---|---|
| **List** | Choose the voice language | Five rows, 64 dp each. Each shows the language **in its own script at Heading-2**, with the English name below in Caption `ink-muted`. Never flags — flags denote countries, not languages, and are politically loaded in the Indian context |
| **Preview** | Prove the voice works before it matters | Each row has a 40 dp play button that speaks the actual crash line: *"Crash detected. Sending alert in ten seconds."* **This is the only chance the user has to hear the alert before it's real.** If the TTS voice pack is missing, the row shows a `sodium-500` `VOICE PACK NEEDED` chip with a one-tap install |
| **Selected** | Confirm | Row fills `bitumen-200`, 2 px left border `sodium-500`, check glyph `sodium-500` |

### 11.3 Steps 3–5 — Consent cards

One permission per screen. Never a batch request. Each uses the same **Consent Card**:

```
┌───────────────────────────────────────────┐
│  ◐  LOCATION                              │  ← Overline sodium-500 + 24px glyph
│                                           │
│  So responders know where to come         │  ← Heading-1 ink-primary
│                                           │
│  ✓ Sent only when a crash is confirmed    │  ← highway-300 check
│  ✓ Used to warn you about the road ahead  │
│  ✕ Never continuously uploaded            │  ← flare-500 cross
│  ✕ Never sold, shared, or advertised      │
│                                           │
│  ┌─────────────────────────────────────┐  │
│  │ WHAT WE STORE                       │  │  ← inset bitumen-200 panel
│  │ Your crash position. A ~250 km²     │  │
│  │ area for weather. Nothing else.     │  │
│  └─────────────────────────────────────┘  │
│                                           │
│  [        Allow location        ]         │  ← sodium-500, 56dp
│  [        Not now               ]         │  ← ghost, ink-muted
└───────────────────────────────────────────┘
```

| Element | Function | Design reasoning |
|---|---|---|
| **The ✕ list** | State what we *don't* do | This is the most important element on the screen. Every user's real question is *"are you tracking me?"* Answering it before it's asked, in `flare-500` so it's read first, is what converts. Most apps list only benefits and get denied |
| **"What we store"** | Make abstraction concrete | Naming the actual retained data — a point and a 250 km² cell — beats any privacy-policy link |
| **"Not now"** | Preserve trust | Present and equally reachable. A user who declines SMS still gets a working app; the flow adapts and re-asks in context later, when the value is obvious |
| **Order** | Sequence by comfort | Location → Motion → SMS. SMS is asked **last**, after the user has seen the risk map work, because `SEND_SMS` is the scariest permission on Android and needs earned trust |

**Step 5 (SMS) carries an extra line**, because this permission is genuinely unusual: *"Only ever one message, only when you've crashed, only if there's no internet. Standard SMS rates apply. We never read your messages."*

### 11.4 Step 6 — Emergency contacts · Step 7 — Medical profile

| Element | Function | Appearance |
|---|---|---|
| **Contact rows** | Up to 5, priority-ordered | Drag handle, name, masked number (`+91 ••••• •4471`), priority chip. Adding via contact picker only — never manual typing, which is error-prone under no time pressure and impossible under it |
| **Medical fields** | Blood group, allergies, conditions, organ-donor flag | All optional, each with an explicit skip. Blood group as a 8-chip selector, not a dropdown — one tap |
| **The encryption line** | Earn the medical disclosure | Below the fields, a lock glyph and Caption `highway-300`: *"Encrypted on this device. Only sent to emergency services, only after a confirmed crash."* |
| **Preview card** | Show them what a responder sees | A small rendering of the exact payload block that reaches a responder. Nothing builds confidence like showing the output |

### 11.5 Step 8 — Battery optimisation

The most-skipped and most-important step. On Xiaomi, Oppo, Vivo, and Realme, aggressive background-process killing will silently disable detection — and a user who thinks they are protected but is not is **worse off than one who never installed the app.**

| Element | Function | Appearance |
|---|---|---|
| **Headline** | State the stakes plainly | Display-2: *"One more thing, or this won't work"* |
| **Body** | Name their exact phone | Detect the OEM and render brand-specific instructions with a screenshot of *their* settings screen: *"On Xiaomi, you need to set Battery saver → No restrictions."* Generic instructions get ignored |
| **CTA** | Deep-link | `sodium-500` *"Open battery settings"* — deep-links to the OEM-specific intent where one exists, falls back to `ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS` |
| **Verification** | Confirm it took | On return, the app checks the actual permission state and shows either `highway-300` `PROTECTION ACTIVE` or a persistent `sodium-500` `PROTECTION LIMITED` banner that stays on Home until resolved. **Never claim success without verifying it** |

### 11.6 Step 9 — Ready

Full-bleed `highway-700`. A single large `highway-300` check. Display-1: *"You're protected."* Below, three Telemetry status lines confirming detection, fallback, and language are each live. One CTA: *"Done"*.

## 12. HOME — idle

The screen the user sees 99.9% of the time. Its job is to **be reassuring and get out of the way.** It must never feel like it wants attention.

```
┌───────────────────────────────────────┐
│  Milestone                      ⚙     │  ← Heading-2 + settings glyph
│                                       │
│    ● PROTECTION ACTIVE                │  ← highway-300 dot + Overline
│      Watching for crashes             │  ← Caption ink-muted
│                                       │
│  ┌─────────────────────────────────┐  │
│  │  ROAD AHEAD                     │  │  ← Overline ink-muted
│  │                                 │  │
│  │  Start driving to see live      │  │
│  │  risk on your route             │  │
│  │                                 │  │
│  │  [ ░░▒▒▓▓ dimmed ribbon ]       │  │  ← Segment Ribbon at 25% opacity
│  └─────────────────────────────────┘  │
│                                       │
│  ┌─────────────────────────────────┐  │
│  │  LAST 30 DAYS                   │  │
│  │  1,284 km   ·   0 incidents     │  │  ← Telemetry-lg + Telemetry
│  │  ▁▂▁▃▂▁▁▂▄▂▁▁▂▁▃▂▁▁▂▁▃▁▂▁▁▂▁▃▂  │  │  ← 30-day bar, sodium-500 @ 40%
│  └─────────────────────────────────┘  │
│                                       │
│         ╭───────────────────╮         │
│         │       SOS         │         │  ← 88dp, flare-500 1.5px outline
│         │  hold 2 seconds   │         │     transparent fill
│         ╰───────────────────╯         │
└───────────────────────────────────────┘
```

| Element | Function | Design reasoning |
|---|---|---|
| **Protection status** | The one thing the user needs | A `highway-300` dot breathing at 3 s — slow enough to read as *alive*, not as *demanding*. If protection is limited (OEM kill, permission revoked, battery <15%), the dot goes `sodium-500` and the row becomes a tappable banner with the fix |
| **Dimmed ribbon** | Teach the component before it matters | Introducing the Segment Ribbon in a calm moment means the user has already parsed it when it appears at 80 km/h. Interfaces must be learned before they are needed |
| **Distance stat** | Justify the battery cost | The user is spending 3–4%/hour on this app. Showing accumulated protected distance makes that trade legible and is the primary retention lever |
| **SOS button** | Manual trigger, for witnessing someone else's crash | Outlined, not filled — it must be findable in a panic but never accidentally pressable. **2-second hold with a `flare-500` ring filling clockwise**, plus haptic ticks at 0.5 s intervals. Releasing early cancels with no penalty and no dialog |

## 13. DRIVE MODE

Entered automatically on Activity Recognition `IN_VEHICLE` > 75% confidence. Screen-on optional — the app is fully functional with the screen off and the phone in a pocket. This screen is for users who mount their phone.

```
┌───────────────────────────────────────┐
│  ● ACTIVE   68 km/h   NH-45      ⚙    │  ← Telemetry, 44dp status bar
├───────────────────────────────────────┤
│                                       │
│         [ live risk map ]             │  ← map fills remaining height
│      route ahead coloured by band     │     bitumen-000 base
│      Milestone markers at blackspots  │     roads bitumen-400
│                                       │     your route: banded, 6px
│                                       │
│                 ▲                     │  ← heading arrow, sodium-500
│                                       │
├───────────────────────────────────────┤
│ ┌───────────────────────────────────┐ │
│ │ ROAD AHEAD              ● LIVE    │ │  ← highway-300 dot when fresh
│ │ ┌──┬──┬──┬──┬──┬──┬──┬──┬──┬──┐  │ │
│ │ │▓▓│▓▓│░░│▒▒│██│██│▒▒│░░│░░│▓▓│  │ │  ← Segment Ribbon
│ │ └──┴──┴──┴──┴──┴──┴──┴──┴──┴──┘  │ │
│ │   L  L  M  H  S  S  H  M  M  L    │ │
│ │      ▲                            │ │
│ │ 2.1 km ahead · Severe · sharp     │ │  ← next notable segment
│ │ curve, heavy rain, night          │ │     SHAP top-3, plain language
│ └───────────────────────────────────┘ │
└───────────────────────────────────────┘
```

| Element | Function | Design reasoning |
|---|---|---|
| **Status bar** | Confirm the system is awake | Speed in Telemetry-lg — it is the one number a driver glances at, and monospace means it doesn't jitter as it changes. Road name from map-matching, which also proves positioning is working |
| **Map** | Spatial context | Deliberately **low-detail**: no POIs, no business labels, no satellite. Only road geometry, the banded route, and Milestone Markers. A driver has ~0.5 s of glance budget; every non-risk pixel steals from it |
| **`● LIVE` / `◐ CACHED`** | Principle P2 | When risk comes from cache (offline), the dot goes `sodium-500`, the label reads `CACHED 14m`, and the ribbon drops to 70% opacity. **The user must never mistake stale risk for live risk** |
| **Next-notable line** | Turn a score into a reason | *"sharp curve, heavy rain, night"* — the SHAP top-3 rendered as plain language. A driver ignores "risk 0.84" and slows down for "sharp curve in heavy rain." This line is where the ML model earns its place in the product |

**Ambient (screen-off) behaviour.** The persistent notification is a first-class surface: `● Active · 68 km/h · NH-45 · Next: Severe in 2.1 km`, with the risk band as the notification's accent colour. Many users never open the app while driving; the notification *is* the interface.

## 14. RISK WARNING

Triggered on entering a **High** or **Severe** segment, above 25 km/h, at most once per segment per 15 min.

| Band | Treatment |
|---|---|
| **Low / Moderate** | Ribbon colour only. **No sound, no overlay, no haptic.** Silence is a feature — an app that speaks constantly gets muted, and a muted app can't warn you about the one that matters |
| **High** | Voice only: *"High risk ahead. Sharp curve in heavy rain."* Ribbon cell pulses once. No visual overlay — the driver should not look at the phone |
| **Severe** | Voice + double haptic + a **bottom-anchored** overlay card |

**Severe overlay:**
- Slides up 88 dp from the bottom over `motion-emphasis`. **Bottom-anchored deliberately**: it stays out of the mirror-and-road sightline and lands in thumb reach.
- `bitumen-200` fill, 2 px top border `risk-severe`, cross-hatch texture at 6% in the background.
- **Left:** the `risk-severe` band glyph at 32 px with the `S` token.
- **Centre:** Heading-2 `SEVERE — 400 m ahead`, below it Body `ink-secondary` with the three factors.
- **Right:** distance countdown in Telemetry-lg, live-updating (`400 m` → `380 m` → …). Monospace matters here — this number changes every ~0.3 s and would jitter in a proportional face.
- **Auto-dismisses** on exiting the segment. No close button — the driver's hands belong on the wheel.

## 15. ⚠ CRASH DETECTED — the cancel window

**The most important screen in the product.** Everything else exists to make this moment work.

### 15.1 Context assumptions

Design for the worst plausible case, every time:

- The user may be **injured, disoriented, or unconscious**
- It may be **pitch dark** or **direct 2 p.m. glare**
- The phone may be **on the floor of the vehicle, face-down, or across the cabin**
- The **screen may be cracked and the digitiser partly dead**
- The user may have **one usable hand**
- The user may **not read** the interface language, or may not read at all
- There are **ten seconds**

### 15.2 The screen

```
╔═══════════════════════════════════════╗
║                                       ║
║   CRASH DETECTED                      ║  ← Display-2, ink-inverse
║                                       ║
║                                       ║
║                                       ║
║            1 0                        ║  ← type-countdown, 200sp
║                                       ║     ink-inverse, weight 600
║                                       ║
║   Sending alert to emergency          ║  ← Heading-2, ink-inverse
║   services                            ║
║                                       ║
║   ████████████████████░░░░░░░░░░░░    ║  ← drain bar, 12dp tall
║                                       ║
║                                       ║
║  ┌─────────────────────────────────┐  ║
║  │                                 │  ║
║  │      I'M OK — CANCEL            │  ║  ← 96dp, bitumen-050 fill
║  │                                 │  ║     ink-primary label
║  └─────────────────────────────────┘  ║
║                                       ║
║   or press any volume button          ║  ← Caption, ink-inverse @70%
╚═══════════════════════════════════════╝
     full bleed sodium-500 (#E8971C)
```

### 15.3 Element specification

| Element | Function | Specification and reasoning |
|---|---|---|
| **Ground** | Instant recognition | Full-bleed `sodium-500`. **Screen brightness forced to maximum**, overriding auto-brightness, for the full 10 s. Amber rationale in §5.1 |
| **Countdown numeral** | The single most important glyph in the product | **200sp**, Display 600, `ink-inverse`. Legible from across a vehicle cabin, at an angle, through a cracked screen, by someone who cannot read the language — **because it is a digit.** It changes on the second, with no transition; a fade or scale on a countdown is decoration in a place with no budget for it |
| **Drain bar** | Redundant encoding of time | 12 dp tall, full width minus margins, `ink-inverse` fill draining left→right, `bitumen-050` at 25% track. Linear, never eased. Serves users who cannot parse the numeral fast enough, and remains readable in peripheral vision |
| **Headline** | Name the event | `CRASH DETECTED`, Display-2. Present tense, no hedging. Not "Possible crash?" — hedged language invites deliberation, and deliberation costs seconds |
| **Sub-line** | State what is happening | *"Sending alert to emergency services."* Declarative. The system has already decided; the user's only job is to stop it if it's wrong |
| **Cancel button** | The one control | **96 dp tall**, full width minus 20 dp margins, bottom-anchored in the natural thumb arc. `bitumen-050` fill with `ink-primary` label — **the only dark element on the screen**, so it is unmissable against the amber field. Label reads *"I'M OK — CANCEL"*: first-person, plain, and it names the user's actual state rather than an abstract action |
| **800 ms enable delay** | Prevent accidental cancel | The button renders immediately but is inert for 800 ms, shown by a subtle `sodium-700` progress fill. A crash frequently ends with a hand or body striking the phone; without this delay, the impact itself can cancel the alert. **The button is visible from frame one** — only its activation is delayed, so the user's eye finds it while their hand is still moving |
| **Volume-button cancel** | Accessibility under damage | Either volume key cancels. **This is not a convenience — it is a hard requirement.** A shattered digitiser is a common outcome of the exact event that brings up this screen, and if touch is the only input, a conscious, uninjured user with a broken screen cannot stop a false dispatch |
| **Audio** | The primary channel | Escalating two-tone siren at **maximum volume, overriding silent and Do Not Disturb**, plus TTS counting down in the user's language. Loops. **Audio, not the screen, is the primary channel** — the phone is frequently not visible after a crash |
| **Haptic** | Third channel | Continuous 200 ms pulse per second, synchronised to the numeral. Reaches a user whose phone is in a pocket and whose ears are ringing |
| **Lock-screen behaviour** | Zero friction | `setShowWhenLocked` + `setTurnScreenOn` + full-screen intent. **No unlock, no PIN, no biometric.** A locked screen must never stand between a user and cancelling a false alert |
| **What is absent** | Reduce to one decision | No back gesture, no home affordance, no notification shade, no settings, no "why did this trigger?", no severity display, no map. **One decision, one control** (P1). Severity is on screen only as a single word beneath the headline when `CRITICAL` |

### 15.4 Severity variants

| Severity | Window | Difference |
|---|---|---|
| `MINOR` / `MODERATE` | 10 s | As specified |
| `SEVERE` | 10 s | Headline gains `SEVERE IMPACT` in Overline above |
| `CRITICAL` + no post-impact motion + phone not picked up | **5 s** | Numeral starts at 5. Ground shifts to `sodium-600` (deeper amber — reads as *more urgent* without becoming red). Sub-line: *"Serious impact detected. Sending now."* |

### 15.5 Expiry

At zero the screen transitions **immediately** (`motion-instant`) to SENDING. No confirmation, no "are you sure," no summary. The system's entire premise is that silence means unconsciousness.

## 16. CANCELLED

Reached by button or volume key.

- Ground snaps to `bitumen-050` in 120 ms — the amber leaving the screen *is* the confirmation.
- A `highway-300` check, Display-2 **"Alert cancelled"**, Body `ink-secondary`: *"No one was contacted. Drive safe."*
- **A single quiet request**, Body `ink-muted`, with two ghost buttons: *"Help us improve — what happened?"* → `Hard braking` · `Phone dropped` · `Pothole` · `Real crash, I'm OK` · `Something else`. **Skippable, never modal, auto-dismisses in 8 s.**
  - This is the hard-negative pipeline (PRD §7.1) surfaced as one optional tap. It is the product's single most valuable data source, and it is asked for gently, once, at the only moment the user has ground truth.
- Auto-returns to Drive Mode after 8 s.

## 17. SENDING → SENT → ACKNOWLEDGED

A single screen with three states. **The user must always know where their alert is** — this is the anxiety-management screen.

```
┌───────────────────────────────────────┐
│                                       │
│   ●━━━━━●━━━━━●━━━━━○                 │  ← 4-node channel ladder
│   det   sent  recv  ack               │
│                                       │
│   ALERT SENT                          │  ← Display-2
│                                       │
│   ┌─────────────────────────────────┐ │
│   │ ✓ Crash detected      18:32:11  │ │  ← Telemetry timestamps
│   │ ✓ Sent over SMS       18:32:14  │ │  ← channel named explicitly
│   │ ✓ Received by server  18:32:19  │ │
│   │ ◐ Awaiting dispatch…            │ │  ← headlight sweep on this row
│   └─────────────────────────────────┘ │
│                                       │
│   ┌─────────────────────────────────┐ │
│   │      ╭─────────╮                │ │
│   │      │  59:41  │  GOLDEN HOUR   │ │  ← Golden Hour Dial, 72px
│   │      ╰─────────╯  REMAINING     │ │
│   └─────────────────────────────────┘ │
│                                       │
│   Your location and medical details   │
│   were sent. Contacts notified.       │
│                                       │
│   [ Call 112 directly ]               │  ← always available, ghost
└───────────────────────────────────────┘
```

| Element | Function | Reasoning |
|---|---|---|
| **Channel ladder** | Show the alert's position in the pipeline | Four nodes, filling `highway-300` as each completes. Reduces the "did it work?" anxiety that otherwise makes users repeatedly re-trigger |
| **Named channel** | Principle P2 | *"Sent over SMS"*, never "Sent." If it went by SMS, the user is in a dead zone and should know their situation — and that the system handled it |
| **Timestamps** | Evidence | Telemetry, second precision. These are also the user's record if anything is later disputed |
| **Golden Hour Dial** | Orient the user in time | Starts on confirmation. Gives a person who may be waiting alone on a highway a truthful, non-panicking sense of time |
| **Call 112 button** | Never trap the user | Always present, at every state. Software must never be the only path to help |

**ACKNOWLEDGED state:** the fourth node fills, the card gains a 2 px `highway-500` border, headline becomes *"Help is on the way."* Responder name, type, and distance render in Telemetry. **The Simulation Seal (§7.5) wraps this entire block in v1** — even in the driver app, even at the most emotionally loaded moment, the mock is disclosed. Copy inside the seal reads: *"Demonstration mode — this dispatch is simulated."*

## 18. ALL CHANNELS FAILED

The worst case: no data, SMS send failed, nothing acknowledged. Design must **escalate to the physical world**.

- Ground `flare-500` — this is a genuine system failure and the one place in the driver app red is correct.
- Display-2 `ink-inverse`: **"Couldn't reach emergency services."**
- Body: *"Your phone has no signal. Here's what to do."*
- **The phone becomes a beacon:** flashlight strobes at 1 Hz, siren loops at max volume, and the screen alternates `flare-500` / `bitumen-000` at 0.5 Hz. Visible from a distance on a dark highway. Software has failed; the device becomes a physical signal.
- Two large actions: **`Call 112`** (works on any network, including one with no SIM service) and **`Retry`**.
- **Location displayed in large Telemetry** — `12.91845 N, 80.22456 E` — plus the nearest landmark, so the user can read coordinates aloud to a passer-by or a 112 operator on a borrowed phone.
- A background retry continues silently every 30 s; success transitions straight to SENT.

## 19. Settings & privacy

Reached from the Home gear. Ordered by what users actually come here for.

| Section | Contents | Notable design |
|---|---|---|
| **Protection** | Master pause toggle, sensitivity (Standard / High), cancel-window length (10 s / 15 s) | The pause toggle is `flare-500` when off, with a persistent Home banner. Pausing safety software should never be quiet |
| **My details** | Emergency contacts, medical profile, language | Same components as onboarding |
| **Battery** | Live drain estimate, adaptive-sampling toggle, per-OEM protection status | Shows measured `%/hour` in Telemetry from actual usage, not a claim |
| **Privacy & data** | What we collect (plain language), download my data, **delete everything** | The delete action is a full-screen flow, not a modal: names precisely what is destroyed, requires typing `DELETE`, and states the 30-day statutory window (NFR-PR5). `flare-500` |
| **Trip history** | Distance, risk exposure, cancelled alerts | The cancellation list is honest and visible — users should be able to audit the system's false positives against their own memory |
| **About** | Version, model versions, licences, **`GATEWAY: SIMULATED`** | Model versions in Telemetry. The gateway line carries the Simulation Seal |

---

# PART IV — OPERATIONS DASHBOARD FLOW

React + TypeScript. **Dark theme default** for Live Operations (ops rooms are dark, wall displays glare); **light theme default** for Analytics and Reports (they get printed and projected). Full manual override, persisted per user.

## 20. Shell

```
┌────┬────────────────────────────────────────────────────────────────────┐
│    │  Live Operations                              [dark|light]  RS ▾   │
│ ▣  ├────────────────────────────────────────────────────────────────────┤
│ ◈  │                                                                    │
│ ◐  │                                                                    │
│ ▤  │                         [ view content ]                           │
│ ⚗  │                                                                    │
│    │                                                                    │
│    ├────────────────────────────────────────────────────────────────────┤
│ ?  │ ● WEATHER 4m ● TRAFFIC 2m ◐ IMD 3h ● SMS GW ◆ GATEWAY SIMULATED    │
└────┴────────────────────────────────────────────────────────────────────┘
  ↑                                          ↑
  64px rail, highway-700                  System Honesty Bar (§7.7)
```

| Element | Function | Appearance |
|---|---|---|
| **Nav rail** | Five destinations, icon-only | 64 px, `highway-700`. Active item: `sodium-500` 3 px left bar + `sodium-500` glyph + `bitumen-300` fill. Labels on hover after 400 ms. Five items: **Live Operations · Incidents · Risk Map · Analytics · Simulator** |
| **Top bar** | Context and identity | 56 px, `bitumen-100`, 1 px bottom border. View title in Heading-2, theme toggle, user menu with role chip (`OPERATOR` / `ANALYST` / `ADMIN`) |
| **Honesty bar** | §7.7 | 32 px, persistent, never scrolls away |

**Emblem and branding note.** The State Emblem of India is governed by the **State Emblem of India (Prohibition of Improper Use) Act, 2005**, and may not be used without authorisation. Until a formal government engagement exists, **no emblem, no ministry logo, no `.gov.in` styling, no tricolour device.** The product carries only its own Milestone mark. Adopting government insignia prematurely is both unlawful and exactly the kind of overreach that undermines a real partnership. Institutional register comes from typography and colour, which is what §4 and §6 are for. Design review should also check the build against **GIGW** (Guidelines for Indian Government Websites and Apps, NIC/MeitY) before any government pilot — verify the current version and its WCAG conformance requirement directly with NIC, as it is periodically revised.

## 21. Live Operations

The default view and the wall-display view. Split: map left (fluid), incident rail right (400 px fixed).

```
┌──────────────────────────────────────────┬──────────────────────────────┐
│                                          │ LIVE INCIDENTS          4 ●  │
│                                          ├──────────────────────────────┤
│              [ live map ]                │ ┌──────────────────────────┐ │
│                                          │ │ ╭───╮  SEVERE      SMS   │ │
│         ╭─╮        ╭─╮                   │ │ │08 │  NH-45 · Chengal…  │ │
│         │▨│  ← pulsing Milestone         │ │ │:41│  12.91845 80.22456 │ │
│         ╰─╯        ╰─╯                   │ │ ╰───╯  2 min ago         │ │
│                                          │ │  ⚠ AWAITING DISPATCH     │ │
│    risk overlay, banded segments         │ └──────────────────────────┘ │
│                                          │ ┌──────────────────────────┐ │
│  ┌────────────────────┐                  │ │ ╭───╮  MODERATE    DATA  │ │
│  │ ◉ Risk  ○ Weather  │  ← layer control │ │ │47 │  SH-49 · Kanchee…  │ │
│  │ ○ Traffic ○ Black… │                  │ │ │:02│  ✓ Dispatched      │ │
│  └────────────────────┘                  │ │ ╰───╯                    │ │
│                                          │ └──────────────────────────┘ │
├──────────────────────────────────────────┴──────────────────────────────┤
│ ● WEATHER 4m  ● TRAFFIC 2m  ◐ IMD 3h  ● SMS GW  ◆ GATEWAY SIMULATED     │
└─────────────────────────────────────────────────────────────────────────┘
```

### 21.1 The map

| Element | Function | Specification |
|---|---|---|
| **Base** | Context without noise | Custom Milestone tile style: `bitumen-000` ground, `bitumen-300` minor roads, `bitumen-400` major roads, `ink-muted` labels at 11px. **No POIs, no buildings, no landuse fill.** Every non-risk pixel competes with the data |
| **Risk overlay** | The core data | Segments stroked by band with hatch patterns (§4.7), 60% opacity so geometry stays readable. Below zoom 11, aggregates to H3 hexes |
| **Incident markers** | Live crashes | Milestone Markers (§7.1) with severity caps. Unacknowledged pulse; acknowledged do not |
| **Layer control** | Analytical comparison | Bottom-left card. **The `Blackspots` layer is the strategic one** — overlaying official MoRTH blackspots on our live risk surface is the product's central argument, made visible in one toggle. Renders as a 2 px dashed `ink-muted` outline so it reads as *reference*, not as *our data* |
| **Time scrubber** | Replay | Bottom-centre, 24 h. Dragging replays the risk surface and incidents. `LIVE` snaps to now, and while scrubbed a `sodium-500` `HISTORICAL — 14:20` banner sits across the top (P2) |

### 21.2 Incident rail

| Element | Function | Specification |
|---|---|---|
| **Header** | Load at a glance | `LIVE INCIDENTS` Overline + count in Telemetry-lg. A `flare-500` dot appears when any incident is unacknowledged |
| **Card** | One incident | `bitumen-100`, `radius-md`, 4 px left border in the severity colour. Hover lifts to `bitumen-200`; selected gains a `sodium-500` outline and flies the map to it |
| **Golden Hour Dial** | Urgency | 72 px, numeral only, left of the card |
| **Severity + Channel** | Classification | Severity in Heading-3 + severity colour. Channel Badge (§7.4) right-aligned — the `SMS` badge's amber outline makes dead-zone alerts pop out of a scan |
| **Location** | Where | Road and district in Body; coordinates in Telemetry-sm `ink-muted` beneath. Both, always — operators need the human name to speak and the numbers to relay |
| **Status strip** | What's needed | `⚠ AWAITING DISPATCH` (`sodium-500`, animated headlight sweep) → `✓ DISPATCHED` (`highway-300`) → `● CLOSED` (`ink-muted`) |
| **Sort** | Triage | Unacknowledged first, then by Golden Hour remaining ascending. **Never by recency** — the incident with 8 minutes left matters more than the one from 30 seconds ago |

## 22. Incident Detail

Opened from a card. Full-width, three columns.

```
┌─────────────────────────────────────────────────────────────────────────┐
│  ← Incidents          INCIDENT SIM-2026-0814-004417        [ Export ▾ ] │
├───────────────────────┬─────────────────────────┬───────────────────────┤
│ ╭─────────────╮       │ SENSOR EVIDENCE         │ ╔═══════════════════╗ │
│ │             │       │                         │ ║⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋║ │
│ │   41:18     │       │  ╱╲                     │ ║ SIMULATED DISPATCH║ │
│ │  REMAINING  │       │ ╱  ╲    ┄┄┄┄┄ 4.0g      │ ║⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋⟋║ │
│ ╰─────────────╯       │╱    ╲__/‾\___           │ ╟───────────────────╢ │
│                       │      │ T=0  peak 9.1g   │ ║ SIM-…-004417      ║ │
│ SEVERE      SMS       │  -8s  0  +4s            │ ║ Chengalpattu GH   ║ │
│                       │                         │ ║ 6.2 km            ║ │
│ 18:32:11 IST          ├─────────────────────────┤ ╚═══════════════════╝ │
│ 2 min ago             │ CONDITIONS AT IMPACT    │                       │
│                       │ Weather   Heavy rain    │ VICTIM DETAILS        │
│ NH-45, Guduvancheri   │ Visibility     400 m    │ Occupants          1  │
│ Chengalpattu, TN      │ Light          Night    │ Blood group       O+  │
│                       │ Traffic     Moderate    │ Conditions    Asthma  │
│ 12.91845 N            │ Segment risk  0.78 H    │ Language      ta-IN   │
│ 80.22456 E            │                         │                       │
│ ±8 m                  │ TOP RISK FACTORS        │ TIMELINE              │
│                       │ Night          +0.21    │ ● Detected  18:32:11  │
│ [ mini map ]          │ Heavy rain     +0.18    │ ● Confirmed 18:32:21  │
│                       │ Curvature      +0.14    │ ● Sent SMS  18:32:24  │
│                       │                         │ ● Received  18:32:29  │
│                       │ IMPACT MECHANICS        │ ◐ Dispatch  awaiting  │
│                       │ Peak          9.1 g     │                       │
│                       │ Delta-V   41.2 km/h     │                       │
│                       │ Direction     Front     │                       │
│                       │ Rollover         No     │                       │
│                       │ Still moving     No     │                       │
└───────────────────────┴─────────────────────────┴───────────────────────┘
```

| Column | Function | Reasoning |
|---|---|---|
| **Left — identity** | Who, where, how urgent | Golden Hour Dial at full 160 px is the first thing seen. Coordinates in Telemetry, large enough to read aloud over a radio |
| **Centre — evidence** | Why we believe this | Trace Sparkline (§7.6) is the top element. **Evidence precedes conclusions** — an operator who can see the crash pulse trusts the system; one shown only a severity label does not. Conditions and SHAP factors follow, all in Telemetry, right-aligned for column scanning |
| **Right — action and disclosure** | What happens next | The Simulation Seal sits at the top-right, the highest-attention corner after the dial. Victim details below (`highway-500` left border — this is protected data). Timeline last, as an audit record |

**Export** produces PDF and GeoJSON. **The Simulation Seal renders in the PDF**, at full fidelity — a printed incident report must not be able to launder a mock into an official-looking record.

## 23. Risk Map (analyst view)

Distinct from Live Operations: no incident rail, full-width map, an analytical control panel, and the **Corridor mode** that makes the Segment Ribbon a full-scale tool.

| Element | Function | Specification |
|---|---|---|
| **Condition simulator** | The analyst's core tool | A left panel of sliders — rainfall, visibility, hour-of-day, traffic ratio. Moving them **re-scores the visible network live**, letting an official ask *"which stretches become Severe under heavy rain at 11 p.m.?"* This converts a static blackspot exercise into a scenario-planning instrument, and is the strongest argument the product can make to MoRTH |
| **Corridor mode** | Length-wise analysis | Draw or select a corridor → the map collapses to a full-width Segment Ribbon with a kilometre ruler above and a 24 h × 7 d heat-grid below. Every cell inspectable |
| **Comparison mode** | The thesis, proven | Split-screen: our live risk surface left, official blackspots right, synchronised pan/zoom. A `sodium-500` readout reports agreement rate and, critically, **segments we flag that the official list does not** — the product's entire predictive claim, quantified |
| **Top-N table** | Prioritisation | Sortable, exportable. Segment ID, road, district, current score, band, 3-year crash count, blackspot status, top factors. All Telemetry, tabular figures |

## 24. Analytics

Light theme by default. This view exists to be screenshotted into government presentations, so **every chart must be legible in greyscale and at 50% scale.**

| Panel | Content | Design notes |
|---|---|---|
| **Response performance** | Crash→ack latency distribution, p50/p95/p99 | Histogram, `sodium-500` bars, `bitumen-400` gridlines. p95 marked with a `flare-500` rule and Telemetry label |
| **Channel mix** | DATA vs SMS vs SOS over time | Stacked area. **SMS in `sodium-500` and always on top** — it's the differentiator and gets the visual position of honour |
| **Golden Hour compliance** | % of incidents acknowledged within 60/30/15 min | Three large Telemetry stats with sparklines. The headline number of the entire product |
| **Detection quality** | Cancel rate per 100 drive-hours, trend | With a target line at 2.0. Honest reporting of our own false positives builds the credibility the product needs |
| **Risk model performance** | PR-AUC, Brier, Precision@top-1%, calibration curve | For technical reviewers. Calibration plot with the diagonal reference in `ink-muted` |
| **Coverage** | Devices, km of network, districts | Choropleth by district |

All panels export as PNG and CSV. Chart colours come from the same tokens — **no chart-specific palette exists**, so a risk band is the same colour in a chart as on the map, every time.

## 25. Simulator Console

Demo-only, gated by role and an environment flag. In production builds the nav item is absent, not disabled.

| Control | Function | Appearance |
|---|---|---|
| **Inject crash** | Place a synthetic incident | Click the map, choose severity, channel (`DATA`/`SMS`), and device locale. Fires the full real pipeline |
| **Force SMS path** | The demo's decisive moment | A large toggle that blocks the data channel for a chosen device, forcing the SMS fallback live in front of the jury |
| **Gateway mode** | Prove resilience | `OK` / `SLOW 8s` / `TIMEOUT` / `REJECT`. Demonstrates that dispatch failure degrades visibly rather than silently |
| **Feed failure** | Prove P2 | Kill the weather or traffic feed and watch the Honesty Bar and the risk overlay degrade correctly |
| **Scenario playback** | Rehearsed demo | Runs a scripted sequence end-to-end, so the stage demo is deterministic |

The whole view carries a persistent `flare-500` header: **`SIMULATOR — synthetic data, clearly marked`**, and every injected record is permanently flagged `is_simulated = true` and rendered with the Simulation Seal everywhere it later appears.

---

# PART V — CROSS-CUTTING

## 26. State coverage

Every data surface specifies five states. Missing states are the most common cause of a polished design feeling broken in production.

| State | Treatment |
|---|---|
| **Loading** | Headlight Sweep skeletons (§8.4) matching final layout dimensions. **Never a spinner** — spinners give no shape information and make waits feel longer |
| **Empty (good)** | A calm, complete sentence with a Milestone glyph at 20% opacity: *"No incidents in the last 24 hours."* On a road-safety product, empty is the goal — never style it as a deficiency |
| **Empty (filtered)** | Names the filter and offers one-click clear |
| **Error** | Inline in the affected panel, never a global modal. States what failed, what still works, and a retry. `flare-500` |
| **Degraded** | `sodium-500` badge with **data age in Telemetry**, content still rendered. The most important state in this product (P2) |

## 27. Accessibility

| Requirement | Implementation |
|---|---|
| **WCAG 2.1 AA** across both surfaces; AAA on the crash screen | Contrast table §4.9 |
| **Colour never sole encoder** | Risk bands carry hue + pattern + letter + stroke weight (§4.7) |
| **Focus visible** | 2 px `sodium-500` ring, 2 px offset. Never `outline: none` |
| **Keyboard** | Full dashboard operation without a mouse. `J`/`K` traverse the incident rail, `Enter` opens, `A` acknowledges, `/` focuses search |
| **Screen readers** | TalkBack on the crash screen announces *"Crash detected. Alert sending in ten seconds. Double-tap anywhere to cancel."* — **the entire screen is one accessibility action** on that view, because a blind user must not have to locate a button under time pressure |
| **Live regions** | Incident rail is `aria-live="polite"`; the Golden Hour Dial announces at 30/15/5 min rather than continuously |
| **Reduced motion** | Suppresses ambient animation only; countdowns and colour states persist |
| **Touch targets** | 48 dp min; 96 dp for the cancel button |
| **Text scaling** | Both surfaces functional to 200%. The crash screen is tested at 200% specifically — it must not clip at any setting |

## 28. Design tokens

```css
:root {
  /* Bitumen */
  --bitumen-000:#0A0F0D; --bitumen-050:#0E1512; --bitumen-100:#141C18;
  --bitumen-200:#1B241F; --bitumen-300:#24302A; --bitumen-400:#33413A;
  --bitumen-500:#475A50;
  /* Paper */
  --paper-000:#FBFAF6; --paper-100:#F4F2EA; --paper-200:#EAE7DB;
  --paper-300:#DCD8C8; --paper-400:#C6C1AE;
  /* Sodium */
  --sodium-200:#FFE3B8; --sodium-300:#FFCC80; --sodium-400:#F5B14C;
  --sodium-500:#E8971C; --sodium-600:#C87C0D; --sodium-700:#94590A;
  /* Highway */
  --highway-300:#5FBF95; --highway-500:#1F6B4A;
  --highway-600:#175339; --highway-700:#0F3A28;
  /* Risk — semantic only */
  --risk-low:#3E8C74; --risk-mod:#D9A227;
  --risk-high:#D9622B; --risk-severe:#B4232F; --risk-none:#4A554E;
  /* Flare — failure and simulation only */
  --flare-500:#E03131; --flare-100:#FFE0E0;

  --font-display:"Fraunces",Georgia,serif;
  --font-ui:"Inter",system-ui,sans-serif;
  --font-telemetry:"IBM Plex Mono",ui-monospace,monospace;

  --radius-sm:4px; --radius-md:8px; --radius-lg:12px;
  --ease-standard:cubic-bezier(.2,0,0,1);
  --ease-emphasis:cubic-bezier(.3,0,0,1);
  --motion-fast:120ms; --motion-base:180ms; --motion-emphasis:280ms;
}

:root { /* light */
  --ground:var(--paper-000); --surface:var(--paper-100);
  --ink-primary:#141A16; --ink-secondary:#3E4740;
  --ink-muted:#6B7369; --ink-inverse:#FBFAF6; --border:var(--paper-400);
}
:root[data-theme="dark"] {
  --ground:var(--bitumen-050); --surface:var(--bitumen-100);
  --ink-primary:#F4F1EA; --ink-secondary:#C6C0B2;
  --ink-muted:#8E887A; --ink-inverse:#0E1512; --border:var(--bitumen-400);
}
```

Distributed as a single `tokens.json` (Style Dictionary) compiled to CSS custom properties for `web/`, a Compose `Theme.kt` for `android/`, and a Figma variable collection. **One source, three targets** — a token changed anywhere is changed everywhere.

## 29. Do / Don't

| ✕ Never | ✓ Instead |
|---|---|
| Default government blue | Sodium amber on bitumen (§3) |
| Red for the crash screen | Amber — hazard-light semantics (§5.1) |
| White text on amber (2.1:1) | `ink-inverse` near-black (6.6:1) |
| Pure `#FFFFFF` or `#000000` | Warm `paper-000` / green-shifted `bitumen-000` |
| Colour as the only encoder | Hue + pattern + letter + stroke weight |
| Traffic-light risk ramp | Sage → amber → burnt orange → vermilion (§4.7) |
| Generic teardrop map pins | Milestone Markers (§7.1) |
| Skeleton shimmer | Headlight Sweep (§8.4) |
| Spinners | Shaped skeletons |
| Glassmorphism / blur panels | Solid surfaces stepped by colour |
| Bounce, spring, overshoot | Single-direction easing |
| Emoji in product UI | Phosphor + 9 custom domain glyphs |
| Weights below 400 | 400 minimum, 500/600 for emphasis |
| Flags for language selection | Language name in its own script |
| Animating the crash screen in | `motion-instant` — appears fully formed |
| A modal to dismiss the crash screen | One button, one volume key |
| Batching permission requests | One Consent Card per permission |
| State Emblem / ministry logos | Own Milestone mark until authorised (§20) |
| Hiding degraded state | Named badge + data age (P2) |
| Simulation disclosed in a footnote | Simulation Seal on every affected element (§7.5) |

---

## 30. Open design questions

| # | Question | Needed by |
|---|---|---|
| D1 | Fraunces has no Indic coverage; Noto Serif Devanagari/Tamil/Telugu/Bengali is the pairing. Does the weight and contrast match hold up at Display sizes in all four scripts? **Needs a printed specimen review with native readers** | Before S5 localisation |
| D2 | Is 10 s the right cancel window? It is inherited from the PRD and untested. **A/B it in the pilot** — too short risks false dispatch, too long burns golden-hour minutes | Pilot |
| D3 | Should the crash screen's cancel button be positioned by handedness, or is fixed-centre safer under stress? | S2 usability test |
| D4 | Two-wheeler riders use handlebar mounts and gloves. Does the 96 dp target work with gloves, and is the screen visible in a helmet's peripheral vision? Ties to PRD Q7 | S3 |
| D5 | Does the Segment Ribbon survive a real 0.5 s driving glance, or does the Severe overlay alone carry the warning? **Needs a driving-simulator test, not a desk review** | S4 |
| D6 | Confirm the current GIGW version and its exact conformance requirements with NIC before any government pilot | Pre-pilot |
| D7 | Will an ops room accept a dark default, or do procurement/standard-issue displays force light-first? | Stakeholder review |

---

*End of document.*
