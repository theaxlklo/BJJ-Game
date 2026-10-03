# BJJ Mount v0 Prototype

A dependency-free implementation of the frozen **Mount v0** rules for the tactical BJJ roguelike.

Sources of truth included under `docs/`:

- `BJJ_Game_Concept_Current_Recap_v9_CODE_READY_FREEZE.md`
- `Mount_v0_Canonical_BJJ_Technique_Naming_Lock_REVISED.md`
- `Mount_v0_Final_Playtest_Tuning.md` — final evidence-driven Elbow-Knee branch override after logged playtesting

The implementation also includes the final coding cleanups agreed after the revised naming lock:

- `Tight-Elbow Arm Defense` keeps its name; its meaning is compact elbows that defend the High Mount climb and Americana isolation while leaving the head/shoulder line open to Crossface Pressure.
- `--enumerate` reports `NEVER-BEST (hedge response)` for `Turn-In Recovery` and `Wide Mount Base`; this is informational, not an error.
- name normalization replaces `+` and `&` as characters before separator normalization, and `Repummel` is accepted as an alias.

## What is implemented

- 12 canonical action/response entities with stable IDs and aliases
- corrected 18-entry deterministic BJJ matchup matrix
- result-grade ladder and initiator-relative axis direction
- behavior drift with 1-second ticks
- drift clamp to `+0.10..+4.00`
- `PRESSURE`, `HOLD`, `ESCAPE`, `PROTECT`
- HOLD and PROTECT behavior modifiers
- visible-band positional modifiers
- full hysteresis, including multi-band jumps
- Bridge special rule
- failure clamp
- Elbow-Knee Escape → band-constrained Half Guard/Open Guard Exit Map
- Trap-and-Roll Escape → Reversal Exit Map
- partial final intervals with real start/end clock values
- alternating Top/Bottom v0 initiative scaffold
- command-line hot-seat play
- full decision/drift logging and run summary
- `--enumerate` exhaustive checker
- perfect-response-lock diagnostic
- never-best hedge-response diagnostic
- automated branch-reachability and naming-invariant checks
- full Section 58 branch-range reporting by visible band and Top behavior
- Trap-and-Roll/HOLD reachability comparison
- persistent `--log PATH` text-session logging
- exact hot-seat input capture in text logs, including blank/invalid entries
- cancellation summaries on `Ctrl+C` / `Ctrl+D`, marked `CANCELLED`
- readable short-name histories in run summaries

## Run without installing

Primary OOP entry point:

```bash
PYTHONPATH=src python -m bjj_game --check
PYTHONPATH=src python -m bjj_game --enumerate
PYTHONPATH=src python -m bjj_game
PYTHONPATH=src python -m bjj_game --log logs/session-001.txt
```

Targeted run:

```bash
PYTHONPATH=src python -m bjj_game --axis 0.50 --clock 0:30 --interval 7 --log logs/session-001.txt
```

Blind hot-seat playtest mode:

```bash
PYTHONPATH=src python -m bjj_game --blind --log logs/blind-session.txt
```

Solo seeded blind playtest mode:

```bash
PYTHONPATH=src python -m bjj_game \
  --blind \
  --blind-responder random \
  --seed 42 \
  --log logs/blind-seed-42.txt
```

For clean behavior experiments, either side can be fixed for the entire session:

```bash
PYTHONPATH=src python -m bjj_game \
  --blind \
  --blind-responder random \
  --seed 42 \
  --top-behavior PRESSURE \
  --bottom-behavior ESCAPE \
  --log logs/pressure-vs-escape-seed-42.txt
```

Supported fixed values:

```text
--top-behavior PRESSURE|HOLD|CONSERVE
--bottom-behavior ESCAPE|PROTECT|CONSERVE
```

A fixed side is not re-prompted between windows. The other side stays interactive when only one behavior flag is supplied.

In `--blind`, the responder locks a response before the initiator chooses an action or RESET. Human mode hides the typed response with `getpass`. Random mode uses a deterministic seeded policy and reveals/logs the selected response only after the initiator commits, so one person can run genuinely blind sessions.

Current fixed random-response mixes:

```text
Bottom responding to Top:
Frame : Tight Elbows = 4 : 3
Turn-In = 0

Top responding to Bottom:
Wide Base : Hip Follow = 2 : 1
Post = 0
```

The seed and every random draw/response are written to the session log for replay. This changes input order only; resolution mechanics are unchanged. The legacy `mount_v0` path rejects blind-testing flags.

Legacy compatibility remains available during migration:

```bash
PYTHONPATH=src python -m mount_v0 --check
PYTHONPATH=src python -m mount_v0 --enumerate
PYTHONPATH=src python -m mount_v0
```

## Install editable

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
bjj-game --check
bjj-game --enumerate
bjj-game
```

`mount-v0` remains installed as a legacy alias.

## Test

No third-party test runner is required:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

CI runs the full suite and both semantic-check entry points on Python 3.11 and 3.13.

## Mount v0.1a — stamina telemetry

The first v0.1 slice is now present as **state only**. Every `Competitor` owns an independent `StaminaPool`; the CLI can start Top and Bottom at any value from 0–100 and reports the observational band.

```bash
PYTHONPATH=src python -m bjj_game \
  --top-stamina 75 \
  --bottom-stamina 25
```

Current bands are observational quartiles:

```text
76–100  Fresh
51–75   Working
26–50   Tired
0–25    Exhausted
```

**Stamina has no mechanical effect in v0.1a.** It does not change grades, drift, axis movement, clamps, exits, or action availability.

The exact frozen v0 `--enumerate` output is protected by SHA-256 regression test:

```text
3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2
```

See `docs/MOUNT_V0_1A_STAMINA.md`.

## Mount v0.1b — commitment + stamina costs

The primary `bjj_game` flow now wraps each initiated action in an `ActionAttempt` with explicit commitment:

```text
LOW       3 stamina requested
MEDIUM    7 stamina requested
HIGH     12 stamina requested
```

These are prototype cost values. Commitment changes stamina cost only in v0.1b; LOW/MEDIUM/HIGH do **not** change the frozen Mount grade or axis resolution yet.

`MountMatch.attempt()` charges the initiator and records `before / requested / charged / shortfall / after`. If the fighter cannot fully pay, the remaining stamina is charged, shortfall is logged, and the action still resolves normally. Recovery and exhaustion consequences come later.

The legacy `mount_v0` CLI keeps the old prompt sequence and calls cost-free `decide()`.

See `docs/MOUNT_V0_1B_COMMITMENT.md`.
## Mount v0.1c — behavior stamina + CONSERVE

The normal-speed behavior layer now has a stamina economy:

```text
PRESSURE   -1 / 5s
ESCAPE     -1 / 5s
HOLD        0 / 5s
PROTECT     0 / 5s
CONSERVE   +2 / 5s
```

`CONSERVE` projects onto HOLD/PROTECT for positional drift but does **not** inherit their special resolution modifier. Five 1-second windows equal one 5-second window through fixed-point carry.

Standard play defaults commitment to `MEDIUM` because LOW still strictly dominates while commitment has no outcome effect. Use `--commitment LOW|MEDIUM|HIGH` for targeted tests.

Underfunded commitment downgrades to the highest fully payable level; at zero stamina it becomes `UNFUNDED`, preventing future HIGH effects from being free.

See `docs/MOUNT_V0_1C_CONSERVE.md`.
## Mount v0.1e — exhaustion consequence

v0.1e established the exhaustion consequence before the stamina layer was closed. The former standalone v0.1d STABILIZE step has since been retired into v0.2.

Minimal rule:

```text
Initiator starts the action Exhausted
→ final initiated-action grade -1
```

Exhaustion now has 25/35 hysteresis: enter at <=25, but once exhausted you must recover to >=35 before the penalty clears. The band is read before the action's commitment cost is paid. If the current action pushes the fighter into Exhausted, the penalty begins on their next initiation.

`bjj_game --check` now reports projected time to Exhausted and zero stamina for LOW/MEDIUM/HIGH under active PRESSURE/ESCAPE, plus exhausted escape reachability and the v0.2 responder-stamina debt. The current costs are intentionally left unchanged until playtests produce evidence.

Behavior-stamina logs always include fixed-point carry so partial recovery/spend across behavior changes is visible.

The modern v0.1 flow also offers **RESET / NO ACTION**. It yields the current attack window with no action cost or immediate axis change, allowing CONSERVE to recover from Exhausted instead of forcing another paid technique every 10 seconds. Repeated RESET is explicitly tracked as a future stalling-system debt.

`StaminaPool.current` is read-only; supported mutation routes all refresh the 25/35 exhaustion latch. Latched displays explain the recovery threshold, e.g. `30/100 (Exhausted — recovers at 35)`.

See `docs/MOUNT_V0_1E_EXHAUSTION.md`.

### Mount v0.1 validation conclusion

Mount v0.1 stamina is **validated and closed for Mount v0**.

Batch and low-stamina stress tests show two important limits of the current scaffold:

- rational v0.1 escape-first play from 100 stamina rarely spent enough for exhaustion to become binding;
- v0.2 setup chains create enough paid action volume for stamina to matter;
- v0.2b now makes responder exhaustion mechanical as well: an Exhausted responder defends one grade worse.

The forced-attack pacing projection is therefore a **stress case**, not expected rational-play pacing. Do not retune the prototype 3/7/12 action costs or CONSERVE's +2/5s recovery merely to make v0 consume more stamina.

The remaining pressure is expected to come from later systems:

```text
v0.2 setup / Ready / triggered initiative / information legality
→ more reasons and opportunities to initiate

v0.3 submissions
→ productive Top attacks and stamina spending from Strong / Locked
```

The former standalone v0.1d STABILIZE step is retired; STABILIZE will be reconsidered inside v0.2 alongside initiative/setup behavior.

v0.2 completion is defined by seven measurable debt gates in `docs/MOUNT_V0_2_DEFINITION_OF_DONE.md`. Modern `bjj_game --check` prints the current status of all seven gates so completion is measured against the original debts rather than code volume.

## Mount v0.2a — minimal Setup / Ready

The first v0.2 slice is implemented behind an opt-in batch flag. It adds discrete setup state without changing the frozen Mount-v0 grades:

```text
None → Partial → Ready
```

Two initial chains exist:

```text
Bridge attempt / forced base reaction
→ builds Trap-and-Roll setup

High Mount Climb attempt / forced defensive structure
→ builds Americana Arm Isolation setup
```

Trap-and-Roll and Americana Isolation are setup-dependent in the v0.2 path: they are unavailable until Ready. A designated builder advances setup even when the defender wins that local exchange, so a perfect responder cannot freeze setup forever by repeating the same counter. A Ready target narrows the legal response set and is consumed when used.

Ready also has a defender-balance invariant: the best legal response in every reachable fresh Ready state is exactly Contested. Wide Mount Base is the Trap-and-Roll stalemate response; Turn-In Recovery is the Americana stalemate response. These are v0.2 Ready rules and do not modify the frozen 18-entry matrix.

A setup builder also gets no progress when its entire positional result is absorbed at the +4.00 Mount cap. Partial movement into the cap can still progress setup; an already-capped exchange that stays at +4.00 cannot.

The established-position order in setup-enabled batches is now:

```text
initiator locks action
→ legal Ready-aware responses are derived
→ responder chooses
→ resolution
```

Run the v0.2a batch path with:

```bash
PYTHONPATH=src python -m bjj_game \
  --batch 100 \
  --seed 42 \
  --v02-setup \
  --top-behavior PRESSURE \
  --bottom-behavior ESCAPE
```

At the reviewed v0.2b baseline before submission finishes existed, the checker measured:

```text
Gate 1  PASS      every reachable Ready state's best legal defense is Contested
Gate 2  DEFERRED  to v0.3 while Locked has no submission-finish action
Gate 3  PASS      258 isolated exchanges change when only responder stamina changes
Gate 4  PASS      Bridge contributes to completed Trap-and-Roll chains
Gate 5  OPEN      0.610 meaningful Top follow-ups/match
                  threshold 1.000; margin -0.390
Gate 6  ACCEPTED  fresh HOLD lockout retained, but fixed no-recovery probe escapes 76/100
Gate 7  OPEN
```

No setup decay, setup disruption, commitment acceleration, exhaustion/setup interaction, RESET progress cost, STABILIZE, or submission finish is added in v0.2a.

See `docs/MOUNT_V0_2A_SETUP_READY.md`.

## Mount v0.2b — responder exhaustion

Responder stamina now matters mechanically:

```text
Exhausted initiator  → -1 grade
Exhausted responder  → +1 grade for initiator
both Exhausted       → modifiers cancel
```

Both stamina bands use the existing 25/35 exhaustion latch and are read before the initiator's action cost is paid. Responding still has no direct stamina cost.

The scripted batch policy uses the same net modifier as actual resolution.

Measured v0.2 evidence:

```text
Gate 3  PASS
fresh-vs-Exhausted responder outcome differences: 258

Gate 6  ACCEPTED
static routes: PRESSURE:1 / HOLD:0 / CONSERVE:1
dynamic no-recovery escapes/100: PRESSURE:0 / HOLD:76 / CONSERVE:35
```

A fresh HOLD Top may still completely shut down an already-Exhausted Bottom. That behavior is retained under Gate 6 path B because actual setup-driven play gives Bottom a measured route out once Top becomes Exhausted too.

See `docs/MOUNT_V0_2B_RESPONDER_EXHAUSTION.md`.

## Mount v0.3a — minimal Americana submission track

v0.3a adds one modern-only Americana submission path around the frozen Mount-v0 matrix:

```text
Ready Americana -> Threat -> Control -> Finish -> Tap
```

Mount is only the currently implemented **entry context**. The Americana isolation/submission-control graph is intentionally separate so future Side Control, Knee-on-Belly, Guard, and other positions can feed the same submission logic through their own access rules.

Current isolation legality:

```text
legal while Americana isolation holds:
  Forearm Frame
  Turn-In Recovery

illegal until isolation is broken/rebuilt:
  Tight Elbows
```

Submission-stage result semantics:

```text
Success / Strong Success -> advance
Contested                -> hold current stage; no axis loss
Failure / Strong Failure -> break track; axis -1.00 toward Bottom
```

A fresh informed Turn-In is therefore a stalemate. An Exhausted defender's same Turn-In becomes Success for Top, so the isolated Gate-E path can finish.

The responder policy preserves ordinary response mass under contextual legality:

```text
ordinary Bottom mix: Frame=4 / Tight Elbows=3 / Turn-In=0
isolated Americana:  Frame=4 / Turn-In=3
```

No response weight is invented.

### Current Gate-B model

"Competent defender" is measured with an **informed Bottom responder** that chooses the legal response giving Top the lowest real final grade. The frozen random mix remains a non-gating contrast.

The numerical criterion is unchanged:

```text
0% < informed Tap rate < 50%
```

At the v0.3a closure point, Gate B was **DEFERRED** because the model had neither response-side commitment nor a Recognition/information mechanic.

The checker carries two live expiry signals:

```text
response_commitment_present
recognition_present
```

v0.4a now supplies real response commitment, so the automatic deferral has expired:

```text
response_commitment_present=True
recognition_present=False
informed Tap=0/100
-> Gate B OPEN
```

The numerical criterion remains unchanged at `0% < informed Tap < 50%`. v0.4a closes the deferral mechanism, not Gate B itself.

### Provisional submission-hold stamina rule

v0.3a retains the existing LOW cost of 3, charged after resolution for a Contested Americana hold at either:

- Ready Americana, when v0.3 submissions are enabled; or
- active Threat / Control / Finish.

The identical Ready exchange under v0.2-only remains response-cost free.

The value is explicitly **provisional**. Its measured contribution is submission access:

```text
without hold cost:
  informed Threat=0/100

with LOW=3:
  informed Threat=78/100
```

It does not solve full-match conversion:

```text
informed PRESSURE / ESCAPE:
  Tap=0/100
  Threat=78
  Control=0
  Finish=0
  final stamina median=0/0

random PRESSURE / ESCAPE contrast:
  Tap=99/100
```

The reason is now explicit. At MEDIUM commitment Top pays 7 per initiated action, while the defender pays 3 per Contested submission hold. Sustained pressure exhausts both fighters; then:

```text
Exhausted initiator -1
Exhausted responder +1
net = 0
```

Turn-In becomes Contested again.

The future defender-effort/information slice must create a principled asymmetry through one of two paths:

- **uneven costs:** a defender maintaining the submission stalemate drains differently from the attacker forcing it; or
- **uneven exhaustion effects:** mutual exhaustion stops canceling specifically for submission exchanges.

The project will not increase the cost post-hoc merely until Gate B passes.

Original v0.3a closure state:

```text
Gate A PASS
Gate B DEFERRED
Gate C PASS
Gate D PASS
Gate E PASS
```

Current state after v0.4a capability expiry:

```text
Gate A PASS
Gate B OPEN
Gate C PASS
Gate D PASS
Gate E PASS
```

Gate C proves fresh informed defense holds rather than wins outright. Gate E proves Fresh Top can finish an already-Exhausted informed Bottom.

The setup-policy debt also remains explicit in `--check`. Under informed PRESSURE / PROTECT, Top can repeatedly build setup while failing to convert it:

```text
V0.3a SETUP-POLICY DEBT: builder progress is ranked above axis loss; informed PROTECT builds=1768, Threat entries=0.
```

This is observed debt, not tuned in v0.3a.

At the v0.3a closure point, the v0.2 Gate-2 deferral had intentionally expired to:

```text
Gate 2 OPEN
```

because a real submission-finish route existed while the historical repeated-RESET probe still timed out at Locked.

v0.3b now closes that debt with executable one-sided stalling evidence; see the next section.

The setup/policy debt also remains explicit: Top can repeatedly rebuild Americana setup even when informed defense prevents conversion. This is observed, not tuned in v0.3a.

See:

- `docs/MOUNT_V0_3A_DEFINITION_OF_DONE.md`
- `docs/MOUNT_V0_3A_STALEMATE_AMENDMENT.md`
- `docs/MOUNT_V0_3A_OPTION_A_MEASUREMENT.md`
- `docs/MOUNT_V0_3A_HOLD_STAMINA_AMENDMENT.md`
- `docs/MOUNT_V0_3A_ACTIVE_HOLD_COST_MEASUREMENT.md`
- `docs/MOUNT_V0_3A_READY_HOLD_STAMINA_AMENDMENT.md`
- `docs/MOUNT_V0_3A_LOW3_HOLD_COST_MEASUREMENT.md`
- `docs/MOUNT_V0_3A_GATE_B_DEFERRAL.md`

## Mount v0.3b — stalling / progress enforcement

v0.3b distinguishes **engagement** from successful advancement.

A legal progress-capable attempt counts as engagement even when the opponent stops it. A legal defensive response to that attempt also counts as engagement.

Each player owns an independent 20-second simulated-time advancement clock.

The escalation ladder is:

```text
offense 1 -> persistent Warning
offense 2 -> one visible-band penalty / boundary free initiative
offense 3+ -> directional escalation
```

For offense 3+:

```text
Top offender:
  use min(+1.50, current one-band target)
  or Bottom free initiative at Loose

Bottom offender:
  never use canonical +1.50 reset
  use one-band movement toward Top
  or Top free initiative at Locked
```

This preserves the frozen rule that stalling consequences always benefit the non-stalling player and prevents later escalation from becoming weaker than offense 2.

### Gate F — direction and escalation strength

The executable invariant sweeps both offender sides across every 0.1-axis state compatible with each persisted hysteresis band:

```text
cases=98
backward effects=0
weaker later effects=0
boundary mismatches=0
Bottom-lowering cases=0
classic both-RESET Bottom-lowering=0
```

```text
v0.3b Gate F PASS
```

### Gate A — timing-independent simulated-time measurement

The fixed sweep remains:

```text
intervals: 5s, 7s
match lengths: 240..300s in 5s increments
26 cases
```

After the first canonical Position Reset, every case must satisfy:

```text
Locked time share < 0.50
longest uninterrupted Locked dwell < 20s
```

Decision-window share is diagnostic only.

Current result:

```text
failing cases=0/26

max post-reset Locked time share=0.393
max post-reset decision-window share=0.500
max post-reset Locked dwell=11s
```

The previous exact `0.500` failures were caused by sampling decision windows at 7-second intervals. The strict `<0.50` threshold was not changed; the occupancy unit was corrected to simulated time so it matches the dwell metric, the stamina remainder model, and the 20-second stalling clock.

Current gate state:

```text
v0.2 Gate 2 PASS

v0.3b Gate A PASS
v0.3b Gate B PASS
v0.3b Gate C PASS
v0.3b Gate D PASS
v0.3b Gate E PASS
v0.3b Gate F PASS
```

### Normal-play guard

```text
V0.3b NORMAL-PLAY GUARD [PASS]

random:
  warnings=0/0
  penalties=0/0
  Position Resets=0/0

informed:
  warnings=0/0
  penalties=0/0
  Position Resets=0/0
```

### Stall versus active Bottom

The non-gating observation remains:

```text
Top RESETs every Top initiation
Bottom uses normal escape-first policy
normal random response mix
100 matches

timeouts=100
escapes=0
warnings=100
one-band penalties=100
Position Resets=800
```

v0 still does not define whether `TIMEOUT — Mount retained` is a win, draw, or loss. That belongs to the later scoring/points ruleset layer.

At the v0.3b closure point, v0.3a Gate B remained **DEFERRED** because v0.3b itself added neither expiry capability.

v0.4a now legitimately supplies response commitment:

```text
v03b_response_commitment_present=False
global response_commitment_present=True
recognition_present=False
v0.3a Gate B=OPEN
```

The historical v0.3b guard remains PASS because v0.3b itself still does not introduce commitment or Recognition.

See:

- `docs/MOUNT_V0_3B_DEFINITION_OF_DONE.md`
- `docs/MOUNT_V0_3B_STALLING_CADENCE.md`
- `docs/MOUNT_V0_3B_CADENCE_TIMING_CLARIFICATION.md`
- `docs/MOUNT_V0_3B_GATE_A_PROBE_CLARIFICATION.md`
- `docs/MOUNT_V0_3B_FULL_MATCH_STALLING_FAILURE.md`
- `docs/MOUNT_V0_3B_POSITION_RESET_ESCALATION.md`
- `docs/MOUNT_V0_3B_GATE_A_STEADY_STATE_AMENDMENT.md`
- `docs/MOUNT_V0_3B_GATE_A_STEADY_STATE_WINDOW_CLARIFICATION.md`
- `docs/MOUNT_V0_3B_POST_RESET_STEADY_STATE_MEASUREMENT.md` — superseded window-share result
- `docs/MOUNT_V0_3B_DIRECTIONAL_ESCALATION_INVARIANT.md`
- `docs/MOUNT_V0_3B_GATE_A_TIME_SHARE_CORRECTION.md`
- `docs/MOUNT_V0_3B_DIRECTIONAL_TIME_SHARE_FINAL_MEASUREMENT.md`

## Mount v0.4a — commitment semantics

v0.4a gives LOW / MEDIUM / HIGH tactical meaning for both initiated actions and responses while preserving the frozen raw Mount matrix.

Costs remain:

```text
LOW     3
MEDIUM  7
HIGH   12
```

Effective commitment remains governed by affordability:

```text
requested
-> highest fully payable requested-or-lower level
-> UNFUNDED below LOW
```

Current exchange semantics:

```text
MEDIUM:
  identity

HIGH:
  Failure -> Strong Failure
  Success -> Strong Success

LOW / UNFUNDED:
  Strong Failure -> Failure
  Strong Success -> Success

under-committed responder:
  initiator +1 grade
```

The grade order is explicitly sequential:

```text
pre-cost exhaustion
-> initiator commitment magnitude
-> response under-commitment
-> final resolution
```

Intermediate Strong Failure / Strong Success clamps are preserved. An independent audit found and fixed a bug where the first implementation summed modifiers and could lose those intermediate clamps. Regression coverage now includes the real clamp case plus exhaustive Grade × exhaustion × initiator-effective-commitment × responder-effective-commitment order checks.

Response commitment is public in v0.4a. Hidden/imperfect commitment recognition remains deferred.

The approved feint-intent amendment separates requested intent from funded capability:

```text
requested LOW
-> feint intent
-> active-stage cap applies

requested MEDIUM/HIGH
-> continuation intent
-> funding downgrade to effective LOW / UNFUNDED does not create a feint
```

Effective commitment still controls grade magnitude, stamina cost, funding, and response under-commitment comparison.

A requested-LOW Ready Americana may still create Threat. Once the Americana track is active, requested LOW cannot advance Threat -> Control, Control -> Finish, or Finish -> Tap, including when the LOW request itself is UNFUNDED.

A requested-LOW feint-capped active submission attempt does not reset the attacker's stalling clock, while the defender still receives defensive-engagement credit. A requested MEDIUM/HIGH attack uses normal progress-capable-route engagement even if funding downgrades its effective commitment.

### v0.4a gates

```text
A PASS — feature-off compatibility / MEDIUM identity
B PASS — v0.2 Gate 7 closes
C PASS — no selectable commitment globally dominates
D PASS — matched commitment preserves fresh Contested stalemates
E PASS — requested-LOW feint-intent cap
F PASS — response under-commitment only helps attacker
G PASS — genuine automatic Gate-B expiry
H PASS — requested-intent feints cannot dodge stalling clock
I PASS — affordability controls tactical credit
```

Audited key evidence:

```text
MEDIUM identity cases=1152
mismatches=0

higher-commitment advantage states=172
v0.2 Gate 7 PASS

dominance states=864
responder commitment LOW/MEDIUM/HIGH included
dominating pairs=none

matched-stalemate cases=360
breaks=0
active-Americana cases=72

under-commitment comparisons=864
regressions=0
strict attacker improvements=646
```

The v0.3a Gate-B deferral now auto-expires from a real runtime capability:

```text
response_commitment_present=True
recognition_present=False

informed MATCH defender:
  Tap=0/100
  Threat=78
  Control=0
  Finish=0
  stage attempts=2028

v0.3a Gate B OPEN
```

The unchanged Gate-B range is active:

```text
0% < informed Tap < 50%
```

Public perfect commitment matching does not solve the competent-defender lock; Recognition/information remains later work.

Post-amendment diagnostics:

```text
FIXED_MEDIUM response commitment:
  Tap=99/100
  Reached Finish=99/100
  Top / Bottom median stamina=0.0 / 0.0
  requested-LOW feint caps=0
  funding-downgrade successful active-stage attempts=191
  funding-downgrade feint caps=0

RANDOM response commitment:
  Tap=94/100
  Reached Finish=95/100
  Top / Bottom median stamina=0.0 / 0.0
  requested-LOW feint caps=0
  funding-downgrade successful active-stage attempts=156
  funding-downgrade feint caps=0
```

The historical pre-amendment RANDOM contrast was `Tap=25/100`. These batch results are observations, not tuning targets. RANDOM response commitment uses equal LOW / MEDIUM / HIGH weighting only as a diagnostic; it is not gameplay policy.

The existing provisional Americana hold cost remains separate from response commitment. An isolated MEDIUM/MEDIUM Contested hold charges:

```text
response commitment=7
provisional hold=3
Bottom 100 -> 90
```

SETUP-POLICY DEBT remains unchanged.

Audited verification:

```text
270 tests PASS on Python 3.11 and 3.13
modern semantic checker PASS
legacy checker PASS

frozen digest:
3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2
```

See:

- `docs/MOUNT_V0_4A_COMMITMENT_SEMANTICS_DEFINITION_OF_DONE.md`
- `docs/MOUNT_V0_4A_FIRST_MEASUREMENT.md` — historical/superseded for closure
- `docs/MOUNT_V0_4A_INDEPENDENT_AUDIT_AMENDMENT.md`
- `docs/MOUNT_V0_4A_AUDITED_FINAL_MEASUREMENT.md` — historical pre-feint-intent amendment closure
- `docs/MOUNT_V0_4A_FEINT_INTENT_FUNDING_AMENDMENT.md`
- `docs/MOUNT_V0_4A_FEINT_INTENT_PRECHANGE_MEASUREMENT.md`
- `docs/MOUNT_V0_4A_FEINT_INTENT_POST_AMENDMENT_MEASUREMENT.md`
- `docs/V0_4B_RECOGNITION_COMMITMENT_QUESTION.md` — future design note, not a DoD

## Known v0 limitation

The responder sees the exact initiated action and has unrestricted access to every response. Every action therefore has a Failure-or-worse best counter. `--enumerate` reports:

```text
PERFECT-RESPONSE LOCK: PRESENT
Classification: KNOWN V0 SCAFFOLDING LIMITATION
```

The matrix is intentionally **not** distorted to fix this. v0.2 setup/Ready/initiative legality is the planned layer that can restrict which responses are actually available or tactically valid.

For v0.1 playtests, `bjj_game --blind` can remove the full-information response advantage without changing the matrix: the responder commits before the initiated action is shown. `--blind-responder random --seed N` makes that usable in solo sessions. This is a testing mode, not the final v0.2 information model.

Bridge remains a known v0 setup limitation: in the raw matrix Trap-and-Roll is at least as good against every response and has the stronger Hip Follow result plus an escape branch. Bridge is being left intact for v0.2 setup/Ready work rather than receiving an ad-hoc stamina discount.

### Adaptive recovery behavior policy

Fixed behaviors are useful controls, but they do not model how CONSERVE is meant to be used tactically. Batch mode now supports an adaptive recovery policy:

```bash
PYTHONPATH=src python -m bjj_game \
  --batch 1000 \
  --initiator-policy escape-first \
  --seed 42 \
  --top-behavior HOLD \
  --bottom-behavior PROTECT \
  --bottom-behavior-policy recover
```

Behavior-policy flags are batch-only:

```text
--top-behavior-policy fixed|recover
--bottom-behavior-policy fixed|recover
```

`fixed` keeps the supplied baseline behavior for the whole match.

`recover` means:

```text
not Exhausted
→ use baseline behavior

latched Exhausted
→ switch to CONSERVE

recover to >=35 and clear the latch
→ return to baseline
```

The baseline is still supplied by `--top-behavior` or `--bottom-behavior`. For example, `--bottom-behavior PROTECT --bottom-behavior-policy recover` means PROTECT normally and CONSERVE only during actual Exhausted recovery.

Batch summaries now include behavior-window counts and switch counts, so a result can show whether CONSERVE was actually exercised instead of inferring it from final stamina alone.

## Batch behavior experiments

For repeatable statistics instead of one seed at a time:

```bash
PYTHONPATH=src python -m bjj_game \
  --batch 1000 \
  --initiator-policy escape-first \
  --seed 42 \
  --top-behavior HOLD \
  --bottom-behavior CONSERVE
```

Batch mode is non-interactive. It automatically uses the fixed seeded random-response mix; do not combine it with `--blind`.

Each match uses:

```text
match 0 → seed 42
match 1 → seed 43
match 2 → seed 44
...
```

Using the same base seed and match count across two behavior conditions therefore pairs comparable response streams.

The official `escape-first` initiator policy is deliberately lexicographic:

```text
at the exact current axis/band/stamina state
→ if any action can escape, choose the highest exact escape probability
→ with --v02-setup: otherwise build an unready setup only when its Ready target would have positive tactical value
→ otherwise require BOTH raw attacker-axis > 0 and realized attacker-axis > 0
→ among those positional attacks, choose the highest realized expectation
→ otherwise RESET
```

It includes current behavior, positional, exhaustion, floor, and cap effects. Escape is a lexicographic priority rather than a numeric bonus, so there is no hidden terminal-value conversion. Positional attacks must stay favorable both before and after clamping, which filters cap-only/floor-only gains. The policy does **not** assign a numeric value to Half Guard, Open Guard, Reversal, stamina, or time; it is a reproducible test rule, not an optimal-opponent model.

Batch output reports outcome frequencies, mean/median final stamina, mean final axis, RESET counts, and action counts by side.

With a fresh responder, Open Guard remains unreachable under the fixed positive-weight response mix because Hand Post and Base has zero weight. Responder exhaustion changes that reachability: Wide Mount Base can be degraded enough for Elbow-Knee to reach Strong Success, so Open Guard can occur in exhausted-responder batch play.

`bjj_game --check` reports fresh and Exhausted responder Exit Map reachability separately so this distinction remains visible.

Fixed-behavior batches measure extreme conditions such as HOLD-vs-CONSERVE or HOLD-vs-PROTECT. They do not answer whether short bursts of CONSERVE are useful; adaptive human sessions are still required for that question.

### Per-band blind-mix diagnostics

`bjj_game --check` reports every action against the fixed random-response mix by visible band using two separate signals:

- **raw attacker-axis** — expected grade-derived axis delta from the initiator's perspective after behavior and positional grade modifiers, before floor/cap handling.
- **realized-axis** — min..max expected actual attacker-favorable axis movement across the legal 0.01 axis grid after floor/cap handling; escape crossings use the resolver's crossing axis.
- **escape** — the min..max escape probability across the same legal axis grid.

MEDIUM's 7-stamina action cost is printed separately. The checker never converts stamina or an escape into axis points and never emits a combined utility score.

The baseline for these lines is Top PRESSURE / Bottom ESCAPE with no exhaustion penalty. The realized range matters at the edges. For example, Top's raw Loose values are negative, but the Mount-floor clamp limits failures, so Americana can have positive realized-axis expectation within Loose. At Locked, the reverse can happen: upside is capped at +4.00 while failures still lose position, making realized expectation worse than the raw grade average.

## Final Elbow-Knee playtest tune

Eight logged pre-tune sessions plus two post-tune regression replays resolved the final Section 58 question. Mount v0 now uses the visible band as a branch constraint after the escape threshold is reached:

```text
Success → Half Guard
Strong Success from Loose → Open Guard
Strong Success from Stable → Half Guard
```

`--enumerate` reports the resulting ranges:

```text
Elbow-Knee Escape → Half Guard: +0.10..+2.10
Elbow-Knee Escape → Open Guard: +0.10..+1.19 (Loose only)
Trap-and-Roll → Reversal with PRESSURE: +0.10..+2.10
Trap-and-Roll → Reversal with HOLD: +0.10..+1.10
```

The numerical overshoot still does not choose the branch; the final grade plus the already-visible band does. See `docs/Mount_v0_Final_Playtest_Tuning.md` and `docs/PLAYTEST_REPORT.md`.

## Object-oriented architecture

The frozen Mount v0 mechanics now run through the `bjj_game` object model. The historical `mount_v0` package remains as a compatibility facade so the original v0 regression suite and command line continue to work unchanged.

Core responsibilities are separated deliberately:

- `Competitor` owns grappler identity and current behavior now; v0.1 stamina/commitment and later belt/style/injury/run state attach here through composition.
- `MountMatch` owns mutable match state: competitors, clock, current position, initiative, history and exit state.
- `MountPosition` owns the Mount positional state; future positions can implement the same `Position` abstraction.
- `MountAxis` is the only persisted Mount-control state writer. It always stays inside `+0.10..+4.00`; escape overshoot is stored separately on `MountPosition`.
- `MountRuleSet` owns frozen Mount thresholds, drift rates, positional modifiers and Exit Map policy. Technique-specific behavior sensitivities and special-clamp metadata live in the catalog.
- `TechniqueCatalog` owns canonical technique/response definitions and lookup indexes.
- `MatchupTable` owns the 18 hand-authored deterministic BJJ grades.
- `MountResolutionEngine` resolves drift and exchanges without owning mutable match state. Its rule set, catalog and matchup table are explicit constructor-injected dataclass fields; `default()` wires production v0 dependencies.
- `diagnostics` and `interfaces` are separated from the domain/engine so future UI layers do not need to rewrite grappling mechanics.

The design favors composition over deep inheritance. Techniques, behaviors, belts, styles and future stamina/commitment are data/state attached to domain objects rather than subclass trees. The CLI uses competitor-owned behavior; method behavior arguments remain only for frozen v0 API compatibility.

Primary entry point:

```bash
PYTHONPATH=src python -m bjj_game --check
PYTHONPATH=src python -m bjj_game --enumerate
PYTHONPATH=src python -m bjj_game
```

The legacy commands remain supported:

```bash
PYTHONPATH=src python -m mount_v0 --check
```

### Refactor safety gate

The architecture-hardening pass changed architecture only, not Mount v0 mechanics. The original 44 tests still pass unchanged, 13 architecture tests now cover real dependency injection, data-driven special rules, competitor-owned behavior, and legal persisted-axis state; `--enumerate` remains byte-identical to the pre-hardening build.

## Blunder playtests

Sessions 11 and 12 in `docs/playtest/` show what happens when one player picks a bad move: a Bottom blunder that jumps Top from Stable to Locked, and a Top blunder that is clamped at Loose and then punished with Open Guard. `tests/test_blunder_replays.py` replays both. See the "Blunder sessions" section of `docs/PLAYTEST_REPORT.md`.

## Session logging and cancellation

Interactive `--log` sessions record both game output and the exact text entered at each prompt. This includes numeric menu choices, aliases, invalid entries, and blank Enter presses. The tee delegates terminal TTY/file-descriptor behavior to the real stdout so normal terminal input behavior is preserved.

If an interactive run is interrupted with `Ctrl+C` or reaches EOF (`Ctrl+D` on a terminal), Mount v0 prints and logs a partial run summary before exiting with status 130. The summary is explicitly marked:

```text
Run status: CANCELLED
Exit reason: CANCELLED
```

Elapsed simulated time, current axis/band, histories, initiation counts, clamps, and threshold state are preserved up to the interruption point.
