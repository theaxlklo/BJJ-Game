# Mount v0 — Final Playtest Tuning Decision

## Status

**Accepted final Mount v0 tuning decision after logged playtesting.**

This document is a narrow evidence-driven override to the frozen v9 specification and the revised naming lock. It does **not** reopen the Mount v0 architecture.

It supersedes only the Elbow-Knee Escape destination rule that previously mapped every `Strong Success` directly to `Open Guard`.

All other v9 and naming-lock rules remain unchanged.

---

## Evidence that triggered the change

The prototype was played through eight logged pre-tune sessions, including the targeted Section 58 cases and several ordinary decision chains. The critical reproducible case was:

```text
Starting / decision state: Stable Mount at +1.80
Bottom action: Elbow-Knee Escape
Top response: Hand Post and Base
Final grade: Strong Success
Old destination: Open Guard
```

Under the old grade-only branch rule, the same direct jump to Open Guard remained reachable from Stable Mount all the way through `+2.10`.

The checker correctly exposed the old reachability ranges:

```text
Half Guard: +0.10..+1.10
Open Guard: +0.10..+2.10
```

This made Half Guard unavailable as an escape destination from much of Stable Mount, while a sufficiently good Elbow-Knee result could jump directly from solid Stable Mount to Open Guard.

That is a poor match for the positional progression represented by the action. Common instruction for the elbow-knee / elbow escape treats knee insertion and half-guard recovery as a natural first checkpoint, with fuller guard recovery requiring continued work. A particularly strong escape from an already Loose Mount can still justify recovering Open Guard immediately.

---

## Final Elbow-Knee Exit Map

The escape threshold itself is unchanged:

```text
Final grade is Success or Strong Success
AND
proposed axis <= +0.10
→ Mount breaks
```

The destination is now selected by **final grade plus the visible band before the action**:

```text
Final grade = Success
→ Half Guard
```

```text
Final grade = Strong Success
AND visible band before action = Loose
→ Open Guard
```

```text
Final grade = Strong Success
AND visible band before action = Stable
→ Half Guard
```

Strong/Locked Mount cannot produce a successful Elbow-Knee exit under the current positional modifiers and threshold math, so no additional branch is needed for those bands.

The branch still does **not** use numerical overshoot. The player-visible band is the contextual constraint.

---

## Why this rule

The final rule preserves all three useful distinctions:

1. `Success` remains meaningful and reliably represents a partial guard recovery to Half Guard.
2. `Strong Success` remains better than `Success` when Mount is already Loose, producing Open Guard.
3. A solid Stable Mount no longer skips the intermediate guard-recovery checkpoint solely because the responder chose the wrong tactical answer.

This makes the destination reflect both **quality of execution** and **quality of the position being escaped**, using state the player can already see.

---

## Post-tune checker ranges

After the change:

```text
Elbow-Knee Escape — Top PRESSURE/HOLD

Half Guard:
  overall +0.10..+2.10
  Loose  +0.10..+1.10 via Wide Mount Base / Success
  Stable +0.81..+2.10 via Hand Post and Base or Wide Mount Base

Open Guard:
  overall +0.10..+1.19
  Loose only, via Hand Post and Base / Strong Success
```

Both branches remain reachable.

Trap-and-Roll behavior is unchanged:

```text
PRESSURE: Reversal reachable through +2.10
HOLD:     Reversal reachable through +1.10
```

---

## Regression confirmation

Two post-tune replay logs verify the branch split directly:

```text
Stable +1.80
Elbow-Knee Escape vs Hand Post and Base
Strong Success
→ Half Guard
```

```text
Loose +0.60
Elbow-Knee Escape vs Hand Post and Base
Strong Success
→ Open Guard
```

See `docs/playtest/09-post-tune-solid-stable-half-guard.txt` and `docs/playtest/10-post-tune-loose-open-guard.txt`.

---

## Final freeze

This is the last Mount v0 mechanics tuning change before v0.1.

Mount v0 is now considered **implementation complete and playtest-frozen** unless a future regression reveals an actual correctness bug.

The next design/implementation phase is:

> **Mount v0.1 — stamina, commitment, CONSERVE, and the STABILIZE distinction.**

## BJJ reference basis

The tuning decision is consistent with common instructional sequencing for the elbow-knee / elbow escape:

- Marcelo Garcia's MGInAction mount-escape lesson describes using the elbow-and-knee wedge to turn to **Half Guard**, then continuing the guard recovery from there: https://www.mginaction.com/VideoDetails.aspx?VideoId=29702
- Peter Mettler's elbow-escape instructional describes the progression from **Half Guard to Closed Guard**, supporting Half Guard as a normal intermediate checkpoint rather than treating full/open guard recovery as automatic from a solid Mount: https://www.youtube.com/watch?v=WMEqsjfYGqc

These references support the positional interpretation; they do not determine the game's numeric tuning by themselves.
