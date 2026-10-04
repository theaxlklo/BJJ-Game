# Stamina Recovery Policy Amendment — Definition of Done

## Status

**FROZEN FOR USER REVIEW — HARD STOP.**

This document starts the amendment that follows stamina-settlement PR #8.

It does **not** authorize implementation.

No flag split, diagnostic collector change, recovery-initiation policy, or gameplay/policy change may be implemented until the user reviews this committed DoD and explicitly authorizes implementation.

## Base and branch

Merged PR #8 main:

```text
b2299a1037b709d2d4a9893c615e4af5b55b4cfa
```

Branch:

```text
review/stamina-recovery-policy-amendment-dod
```

Frozen Mount enumerate digest remains:

```text
3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2
```

Authoritative prior evidence:

```text
docs/STAMINA_ECONOMY_RULE_PRECHANGE_EVIDENCE.md
docs/STAMINA_ECONOMY_RULE_POSTCHANGE_MEASUREMENT.md
```

---

# Why this amendment exists

PR #8 established two separate facts:

1. **Rule 1 worked locally.**
   An initiator whose true effective commitment is UNFUNDED no longer extracts responder stamina through response commitment or hold settlement.

2. **Gate D remained OPEN.**
   Surface E still produced zero Bottom Exhausted-latch clears and zero CONSERVE -> ESCAPE returns, even though mutual-zero time fell sharply.

Independent post-PR review found the missing accounting explanation:

```text
Surface E Bottom stamina                 before rules    after rules

spent defending
(response commitment + hold)                 10,821          3,872

spent on Bottom's own attacks                 6,091         11,994

Bottom own attacks                            2,516          2,387

Bottom RESETs across 100 matches                 29             18
```

These figures are **review-provided starting evidence**.

They are not yet checker-owned evidence.

The interpretation to test is:

```text
Rule 1 removes most defensive drain
-> RECOVER / CONSERVE generates usable stamina
-> EscapeFirstInitiatorPolicy continues initiating at requested MEDIUM
-> Bottom spends recovered stamina on its own attacks
-> Bottom still cannot accumulate to the >=35 Exhausted-latch clear threshold
```

That points to a **policy-layer recovery problem**, not a new stamina-number problem.

PR #8 also produced:

```text
public-MATCH matches reaching Threat:
78 -> 0
```

But Rule 1 and Rule 2 were enabled by one shared flag, so that collapse is only attributed to Rule 2 by reasoning, not by an isolated measurement.

This amendment therefore has two jobs:

1. isolate Rule 1 and Rule 2 experimentally with separate flags;
2. test recovery-aware **initiation policy** while Exhausted without changing stamina rules.

It does not preselect a winning recovery-initiation policy.

---

# Scope principle

The next correction must answer:

```text
Where does recovered Bottom stamina go,
and which policy-layer intervention—if any—lets it accumulate?
```

It must **not** answer that question by changing:

- LOW / MEDIUM / HIGH costs;
- behavior recovery rate;
- behavior spend rate;
- Exhausted entry threshold;
- >=35 latch-clear threshold;
- Rule 1 semantics;
- Rule 2 semantics;
- Recognition probabilities;
- matchup grades;
- submission transition grades;
- setup mechanics;
- stalling rules.

The amendment is about **attribution and policy**, not stamina tuning.

---

# Required implementation chronology after authorization

If and only if the user authorizes this DoD:

```text
1. add read-only Surface-E stamina-destination counters only
2. reproduce the four review-provided before/after figures
3. commit that starting evidence
4. if any figure does not reproduce, STOP before flag or policy changes
5. split Rule 1 and Rule 2 into independent opt-in flags
6. prove legacy-off and both-on equivalence
7. measure NONE / Rule1-only / Rule2-only / BOTH
8. add batch-only recovery-initiation candidate modes
9. measure CURRENT / RESET-WHILE-EXHAUSTED / LOW-WHILE-EXHAUSTED
10. run all gates and predictions
11. record first untuned measurement
12. open/update PR
13. HARD STOP for user review
14. no merge without explicit authorization
```

No step may be skipped because a later result appears obvious.

---

# Phase 1 — reproduce the new starting evidence

## Exact Surface E

Use the existing Surface E configuration exactly:

```text
matches=100
base seed=42
Top behavior=PRESSURE
Bottom baseline behavior=ESCAPE
Bottom behavior mode=RECOVER
initiator requested commitment=MEDIUM
Bottom responder=INFORMED
response commitment policy=RECOGNITION / trusts reads
v0.2 setup=enabled
v0.3 submissions=enabled
v0.4a commitment semantics=enabled
v0.4b Recognition=enabled
interval=5
clock=300
starting axis=+1.50
starting stamina=100/100
```

Two settlement conditions:

```text
LEGACY:
  Rule 1 off
  Rule 2 off

BOTH:
  Rule 1 on
  Rule 2 on
```

## Required counters

For Bottom report:

- behavior recovery;
- behavior spend;
- initiator commitment spend on Bottom's own attacks;
- Bottom own initiated-action count;
- responder commitment spend;
- provisional/supplemental hold spend;
- combined defensive spend = response + hold;
- RESET count;
- time in State 1 / State 2 / State 3;
- final stamina median;
- latch clears;
- CONSERVE -> ESCAPE switches.

## Required starting-evidence reproduction

Before any flag split or recovery-policy change, the checker must reproduce:

```text
LEGACY:

Bottom defensive spend=10,821
Bottom own-attack commitment spend=6,091
Bottom own attacks=2,516
Bottom RESETs=29

BOTH:

Bottom defensive spend=3,872
Bottom own-attack commitment spend=11,994
Bottom own attacks=2,387
Bottom RESETs=18
```

If any value differs:

```text
STOP
-> record the disagreement
-> do not split flags
-> do not add recovery-initiation candidates
-> review the accounting definition
```

The exact split between responder commitment and hold must also be printed even though no new frozen value is declared here.

---

# Phase 2 — separate Rule 1 and Rule 2 flags

PR #8 currently exposes one umbrella:

```text
enable_stamina_settlement_rules
```

This amendment adds two explicit opt-in capabilities:

```text
enable_unfunded_responder_cost_waiver
enable_supplemental_hold_settlement
```

Names may differ slightly in code if needed for consistency, but the two capabilities must remain semantically separate and plainly named.

## Compatibility requirement

The existing umbrella remains valid for historical replay:

```text
enable_stamina_settlement_rules=True
-> effective Rule 1=True
-> effective Rule 2=True
```

The new explicit flags default to false.

Effective rule activation:

```text
Rule 1 effective
= umbrella OR explicit Rule-1 flag

Rule 2 effective
= umbrella OR explicit Rule-2 flag
```

Therefore:

```text
all flags false
-> exact pre-PR8 behavior

umbrella true
-> exact PR8 BOTH behavior

umbrella false + Rule1 true + Rule2 false
-> Rule1-only

umbrella false + Rule1 false + Rule2 true
-> Rule2-only

umbrella false + Rule1 true + Rule2 true
-> exact PR8 BOTH behavior
```

No default behavior changes.

## Rule semantics do not change

Rule 1 remains:

```text
initiator true effective commitment == UNFUNDED
-> responder commitment charged=0
-> supplemental hold charged=0
```

Rule 2 remains:

```text
for a funded initiator hold:
supplemental hold request
= max(0, 3 - responder commitment stamina charged)
```

This phase changes only **activation granularity**, not either rule.

---

# Phase 3 — isolated settlement matrix

Run exact matched seeds for:

```text
A public MATCH
B trusts reads
E trusts reads + Bottom RECOVER
```

under four settlement modes:

```text
NONE
RULE1_ONLY
RULE2_ONLY
BOTH
```

This produces a 3 x 4 matrix.

## Required metrics per cell

Report:

- Tap;
- escapes;
- timeouts;
- matches reaching Threat;
- Threat entries;
- Control entries;
- Finish entries;
- final Top/Bottom stamina median;
- Bottom defensive spend;
- Bottom own-attack spend;
- Bottom own-attack count;
- Bottom RESET count;
- Bottom behavior recovery;
- Bottom latch clears;
- Bottom CONSERVE -> ESCAPE switches;
- State 1 / 2 / 3 shares.

For hold settlement also report:

- hold exchanges;
- nominal hold burden;
- amount covered by response;
- supplemental requested;
- supplemental charged.

For Rule 1 also report:

- true-UNFUNDED initiator exchanges;
- responder spend on those exchanges.

---

# Phase 4 — recovery-aware initiation candidates

The existing batch policy separates:

```text
behavior selection
from
initiation selection
```

Today:

```text
Bottom RECOVER mode + Exhausted
-> behavior becomes CONSERVE
-> EscapeFirstInitiatorPolicy still chooses attacks normally
-> requested initiator commitment remains MEDIUM
```

This amendment adds **batch-policy diagnostic modes only**.

They are not selected as the game default in this slice.

## RecoveryInitiationMode.CURRENT

Existing behavior.

While Bottom is Exhausted:

```text
behavior=CONSERVE
initiation policy=normal EscapeFirst
requested commitment=MEDIUM
```

This is the control.

## RecoveryInitiationMode.RESET_WHILE_EXHAUSTED

Applies only when all are true:

```text
side == Bottom
Bottom behavior mode == RECOVER
Bottom stamina band == Exhausted
Bottom is the current initiator
```

Then:

```text
do not choose an attack
use the existing RESET path
```

No new reset mechanic is invented.

Existing reset/stalling/setup semantics remain authoritative.

As soon as the Exhausted latch clears:

```text
behavior returns to ESCAPE
normal EscapeFirst initiation resumes
requested commitment returns to baseline MEDIUM
```

## RecoveryInitiationMode.LOW_WHILE_EXHAUSTED

Under the same trigger:

```text
EscapeFirst still chooses the same legal action
but Bottom requests LOW instead of MEDIUM
```

No action is hidden or removed.

Existing funding downgrade applies normally.

Existing requested-LOW semantics apply normally.

When the latch clears:

```text
requested initiator commitment returns to baseline MEDIUM
```

## No automatic winner

This amendment does **not** automatically promote RESET or LOW to the default policy.

The purpose is to measure the tradeoff:

```text
CURRENT
vs
RESET while Exhausted
vs
LOW while Exhausted
```

Selection, if any, is a later review decision.

---

# Setup-policy interaction that must be visible

The current setup-policy debt may interact with recovery:

```text
Bridge can build setup through exchanges that are not clean wins
```

Therefore every recovery-initiation mode must report while Bottom is Exhausted:

- Bridge attempts;
- setup-builder attempts;
- setup advances/builds;
- completed setup builds;
- Ready transitions created by Bottom;
- escapes attributable after those setup builds;
- RESETs that forgo an otherwise legal setup-building opportunity.

Do not change setup advancement in this amendment.

The measurement must reveal whether LOW_WHILE_EXHAUSTED preserves recovery only by continuing to exploit setup-building debt, or whether RESET sacrifices meaningful escape construction.

---

# Frozen gates

## Gate A — new starting evidence is checker-owned

PASS requires exact reproduction of:

```text
LEGACY:
defensive spend=10,821
own-attack spend=6,091
own attacks=2,516
RESETs=29

BOTH:
defensive spend=3,872
own-attack spend=11,994
own attacks=2,387
RESETs=18
```

All values must be structured and testable.

This evidence must be committed before flag splitting or recovery-policy implementation.

---

## Gate B — separate flags preserve old and BOTH behavior

PASS requires:

```text
all flags false
== historical legacy behavior

umbrella true
== explicit Rule1+Rule2 true

Rule1-only does not activate Rule2
Rule2-only does not activate Rule1
```

For exact matched deterministic probes and the A/B/E batch surfaces:

- legacy/off signatures must match pre-PR8 historical values;
- BOTH via umbrella and BOTH via explicit flags must be identical.

No old result may silently migrate to a different activation mode.

---

## Gate C — Rule 1 isolated attribution

On RULE1_ONLY:

PASS requires its local invariant:

```text
true-UNFUNDED initiator exchange
-> responder commitment charged=0
-> hold charged=0
```

Report whether Rule 1 alone changes:

- public-MATCH Threat reach;
- trust-read Threat reach;
- Surface-E Bottom defensive spend;
- Surface-E own-attack spend;
- Surface-E latch clears.

There is no outcome threshold beyond the local Rule-1 invariant.

---

## Gate D — Rule 2 isolated attribution

On RULE2_ONLY:

PASS requires its local invariant:

```text
funded response commitment covers the first 3 points of hold burden
additive double-charge cases=0
```

Report public-MATCH:

```text
matches reaching Threat
Threat entries
Control
Finish
Tap
```

The key attribution question is observational:

```text
Does Rule 2 alone reproduce most or all of the 78 -> 0 public-MATCH Threat collapse?
```

Do not change Rule 2 in this slice based on the answer.

A bad attribution result is evidence for the next review, not authorization to tune.

---

## Gate E — current recovery blocker is reproduced

On Surface E with BOTH settlement rules and RecoveryInitiationMode.CURRENT:

PASS requires the checker to reproduce the qualitative blocker:

```text
defensive spend is much lower than legacy
own-attack spend is higher than legacy
latch clears=0
CONSERVE -> ESCAPE=0
```

The exact starting values are already pinned by Gate A.

Also report:

```text
own-attack spend / behavior recovery
defensive spend / behavior recovery
(total defensive + own-attack spend) / behavior recovery
```

This makes the recovery budget explicit.

---

## Gate F — recovery-initiation candidates are measured without stamina tuning

Run Surface E with BOTH settlement rules under:

```text
CURRENT
RESET_WHILE_EXHAUSTED
LOW_WHILE_EXHAUSTED
```

PASS for the **measurement gate** requires all three replay deterministically and all required counters are populated.

Separately report whether each candidate produces:

```text
>=1 Bottom Exhausted-latch clear
>=1 CONSERVE -> ESCAPE switch
>=1 State2 -> State1 exit
```

Those are outcome observations.

If neither candidate produces any latch clear:

```text
recovery-policy outcome = OPEN
-> no tuning
-> new design amendment required
```

If one or both candidates do clear the latch, that does **not** automatically select them as default.

---

## Gate G — no stamina or settlement rule changed

PASS requires unchanged:

```text
LOW=3
MEDIUM=7
HIGH=12

CONSERVE recovery rate
PRESSURE / ESCAPE / CONSERVE behavior spend rules
Exhausted entry threshold
>=35 latch-clear threshold

Rule 1 semantics
Rule 2 semantics
UNFUNDED equality
Recognition probabilities and RNG
matchup matrix / digest
submission progression
hold nominal amount=3
```

Only:

- flag granularity;
- read-only diagnostics;
- batch recovery-initiation policy modes

may change.

---

## Gate H — default behavior remains unchanged

With all new explicit flags/modes at defaults:

```text
game/batch behavior must equal merged main b2299a1
```

Specifically:

- shared settlement umbrella remains off by default;
- explicit Rule-1 flag off;
- explicit Rule-2 flag off;
- recovery-initiation mode CURRENT;
- no default match result changes.

Earlier frozen gates must still run on their historical paths.

---

## Gate I — checker and review boundary

The checker must print structured sections for:

1. Gate-A starting evidence;
2. four-mode settlement attribution matrix;
3. Rule-1 isolated invariants;
4. Rule-2 isolated hold settlement;
5. public-MATCH Threat attribution;
6. Surface-E recovery budget;
7. CURRENT / RESET / LOW recovery-initiation comparison;
8. setup-policy interaction counters;
9. latch-clear outcomes;
10. frozen digest.

A design outcome may be OPEN while checker execution still PASSes.

No prose-only evidence is sufficient.

---

# Predeclared predictions

These predictions are frozen **before any flag split or candidate-policy prototype**.

They are not pass targets unless a gate separately says so.

## P1 — Rule 1 isolation

Prediction:

```text
Rule1-only eliminates UNFUNDED-attack defender drain
without reproducing the full public-MATCH Threat collapse
```

Reason:

Rule 1 changes settlement only on UNFUNDED initiator exchanges and does not remove the funded-response hold burden that previously supported Threat reach.

If this prediction is wrong, record it.

---

## P2 — Rule 2 attribution

Prediction:

```text
Rule2-only causes most of the public-MATCH Threat-reach loss
seen under BOTH
```

The strength of the effect is unknown.

A full 78 -> 0 collapse is possible but not predeclared as required.

---

## P3 — BOTH replay

Prediction:

```text
explicit Rule1+Rule2
reproduces PR #8 BOTH results exactly
```

This one is a compatibility invariant, not merely observational.

---

## P4 — CURRENT recovery budget

Prediction:

```text
with BOTH + CURRENT,
Bottom's defensive spend stays greatly reduced,
but own-attack commitment spend consumes most newly available recovery
and latch clears remain 0
```

This is the causal hypothesis supplied by the new review evidence.

---

## P5 — RESET while Exhausted

Prediction:

```text
RESET_WHILE_EXHAUSTED sharply reduces Bottom own-attack stamina spend,
raises RESET count,
and gives the strongest chance of accumulating to >=35
```

Possible cost:

```text
fewer setup-building attempts / fewer immediate escape opportunities
```

No exact latch-clear count is predicted.

---

## P6 — LOW while Exhausted

Prediction:

```text
LOW_WHILE_EXHAUSTED reduces Bottom own-attack stamina spend relative to CURRENT
while preserving more setup/escape activity than RESET
```

It may or may not be sufficient to clear the Exhausted latch.

No exact outcome is predicted.

---

# Explicit non-goals

Do not in this amendment:

- change stamina costs;
- increase CONSERVE recovery;
- lower the 35-point clear threshold;
- change Exhausted entry;
- alter Rule 1;
- alter Rule 2;
- restore old additive hold charging;
- modify Recognition;
- tune Gate-B thresholds;
- change matchup grades;
- change setup progression;
- change stalling consequences;
- change submission stages;
- choose RESET or LOW as the permanent/default game policy.

---

# Review consequence

The likely review decisions after implementation are intentionally left open:

```text
1. keep Rule 1?
2. keep / amend / remove Rule 2?
3. should recovery-aware initiation exist?
4. if yes, RESET, LOW, or something else?
5. does setup-policy debt need its own slice before choosing?
```

This amendment gathers the evidence needed to answer those questions.

It does not answer them in advance.

---

# HARD STOP

This commit authorizes **nothing beyond design review**.

Do not:

- add the new counters;
- split the settlement flags;
- implement Rule1-only / Rule2-only modes;
- implement RESET_WHILE_EXHAUSTED;
- implement LOW_WHILE_EXHAUSTED;
- run candidate-policy experiments;
- change any stamina or policy rule;

until the user explicitly authorizes implementation after reviewing this committed DoD.

The next valid action is:

```text
STOP
-> present committed DoD
-> user review
-> explicit implementation authorization
```
