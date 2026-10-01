# Mount v0 — Logged Playtest Report

## Scope

Eight pre-tune hot-seat logs were run against the final v0 implementation, followed by two post-tune regression replays.

The purpose was not to rebalance the whole matrix. It was to answer the remaining Elbow-Knee branch question and confirm that HOLD/PRESSURE could be felt in actual run flow.

## Pre-tune sessions

| Log | Scenario | Outcome / observation |
|---|---|---|
| 01 | Stable +1.80, HOLD/PROTECT, Elbow-Knee vs Post | Strong Success jumped directly to **Open Guard** from Stable Mount. This was the tuning concern. |
| 02 | Loose +0.60, Elbow-Knee vs Wide Base | Success → **Half Guard**. Clean partial guard recovery. |
| 03 | Loose +0.60, Elbow-Knee vs Post | Strong Success → **Open Guard**. This distinction felt structurally appropriate for a Loose Mount. |
| 04 | Stable +1.50, HOLD, Trap-and-Roll vs Hip Follow | HOLD downgraded Strong Success to Success; axis moved to +0.50 but Mount did **not** break. |
| 05 | Same exchange under PRESSURE | No HOLD downgrade; Strong Success crossed the threshold → **Reversal**. |
| 06 | Default 5:00 chain, mixed PRESSURE/HOLD | Axis progressed Stable → Loose; Elbow-Knee ultimately escaped to Open Guard from Loose. |
| 07 | Default 5:00, strong Top start then HOLD/ESCAPE erosion | Locked → Strong → Stable → Loose; repeated Trap-and-Roll eventually produced **Reversal**. |
| 08 | Default 5:00, Bridge + Elbow chain | Bridge stayed non-escape-capable; later Elbow-Knee hit exactly +0.10 and exited to **Half Guard**. |

## What the sessions established

- HOLD is mechanically noticeable rather than cosmetic. Session 04 vs 05 demonstrates the same Trap-and-Roll matchup producing no escape under HOLD and Reversal under PRESSURE.
- The axis can move through the whole control spectrum without violating hysteresis or clamp rules.
- Bridge behaves correctly as disruption rather than a completed escape.
- The exact +0.10 escape threshold behaves correctly in live CLI flow.
- The Elbow-Knee branch distinction is meaningful from Loose Mount.
- The old direct Stable → Open Guard branch was the one result that remained structurally questionable.

## Final decision

Adopt the visible-band constraint documented in `Mount_v0_Final_Playtest_Tuning.md`:

```text
Success → Half Guard
Strong Success from Loose → Open Guard
Strong Success from Stable → Half Guard
```

## Post-tune replay

The same targeted cases were replayed after implementation:

- Stable +1.80 + Strong Success now ends in **Half Guard**.
- Loose +0.60 + Strong Success still ends in **Open Guard**.

No other v0 rule was changed.

## Blunder sessions

Two more logged sessions test the opposite case: one player picks the wrong move and the opponent ends up far ahead. No rules were changed. Both sessions are replayed in `tests/test_blunder_replays.py`.

| Log | Scenario | Outcome / observation |
|---|---|---|
| 11 | Stable +1.60, Top HOLD. Bottom tries Trap-and-Roll into Hand Post and Base | Strong Failure moves the axis +2.00 in one exchange: **Stable → Strong → Locked** (+3.60). Bottom's best reply later (Elbow-Knee vs Post, raw Strong Success) is downgraded to Success at Locked and only reaches +3.00. Mount is held to the timeout. |
| 12 | Stable +2.00, Top PRESSURE. Top tries Americana into Tight-Elbow Arm Defense | Strong Failure would land at +0.00. The failure clamp holds Mount at **+0.10 Loose**. The next Bottom window, Elbow-Knee vs Post gets Strong Success from Loose, ending in **Open Guard**. |

### What the blunder sessions showed

- **Both blunders hurt a lot, in different ways.** A Bottom blunder makes things worse over several windows: it lifts Top into Strong/Locked, where every later Bottom action is downgraded one grade. A Top blunder doesn't end the match right away, because the failure clamp keeps Mount alive, but it leaves Top one exchange from losing the position, and Top's own actions are downgraded at Loose.
- **A blunder from Loose gives the opponent their best exit.** Since Open Guard can only come from Loose after the final tune, a Top blunder that drops to Loose is the only way to give up the better guard. That fits BJJ: a failed submission attempt is what lets someone recover full guard.
- **Top's good results are wasted at the cap.** In session 11, Crossface Pressure gets Strong Success at +4.00 and changes nothing. Top has no way to convert Locked into anything else in v0. Expected to change once submissions are added in v0.3; noted here as a pacing issue to watch.
- **Log clarity:** in session 11, the HOLD modifier is logged as `-1 grade` even though the grade was already at Strong Failure and couldn't go lower. The result is correct, but the log line looks like it did something. A future cleanup could log `-1 grade (no effect: already Strong Failure)`.
