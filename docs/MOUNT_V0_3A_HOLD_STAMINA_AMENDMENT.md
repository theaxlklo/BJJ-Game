# v0.3a Design Amendment — Submission Hold Stamina and Informed Gate B

## Evidence motivating this amendment

The Option-A submission semantics fixed the perfect-response lock:

- active Americana stages inherit the Ready isolation response set;
- Tight Elbows stays illegal while isolation holds;
- Contested holds the stage;
- Failure or worse breaks the track and costs -1.00 axis;
- an Exhausted informed defender can be submitted.

But a full-match informed-responder probe found:

```text
random PRESSURE / ESCAPE:
  Tap 98/100

informed PRESSURE / ESCAPE:
  Tap 0/100
  Threat reached 0

informed PRESSURE / PROTECT:
  Tap 0/100
  Threat reached 0

informed PRESSURE / CONSERVE:
  Tap 0/100
  Bottom escapes 100/100

informed HOLD or CONSERVE / ESCAPE:
  Tap 0/100
  Bottom escapes approximately 100/100
```

The isolated Gate-E state (Top Fresh / Bottom Exhausted) exists mathematically, but normal full-match stamina flow does not create it reliably because attacking costs stamina and responding costs zero.

That is the unresolved v0.2b response-cost debt showing up in the first submission system.

## Narrow v0.3a response-cost rule

Only one response now has a direct stamina cost:

> Holding an active Americana submission stage at final grade Contested costs the responder the existing LOW action cost.

The cost is not a new number. It is defined as:

```text
DEFAULT_STAMINA_COST_POLICY.cost(Commitment.LOW) = 3
```

Scope:

```text
action == Americana Submission Finish
final grade == Contested
-> responder pays 3 stamina
```

No other response receives a direct stamina cost in v0.3a.

In particular:

- Ready-Americana entry defense has no direct response cost;
- Failure / Strong Failure that breaks the submission track has no added direct response cost;
- ordinary Mount positional responses still cost zero;
- Bottom escape responses still cost zero.

This resolves only the evidence-backed submission-hold case and does not generalize response stamina across v0.2.

## Timing rule

Both stamina bands are sampled **before** the current exchange costs are paid, preserving the v0.2b exhaustion contract.

Order:

```text
1. sample initiator stamina band
2. sample responder stamina band
3. compute exhaustion modifiers
4. resolve exchange
5. charge initiator action cost
6. if active submission result is Contested, charge responder hold cost 3
7. apply state changes
```

Therefore a responder who crosses into Exhausted by paying the hold cost becomes Exhausted only for later exchanges. The current exchange is never retroactively upgraded for Top.

If the responder has fewer than 3 stamina points, `spend_up_to(3)` charges the available amount and records the shortfall. A zero-stamina responder can still physically choose the response; its Exhausted band already affects resolution.

## Observability

The modern history/check surface must record submission-hold responder stamina charges separately from initiator action stamina.

At minimum report:

- requested hold cost;
- charged hold cost;
- shortfall;
- responder side.

This is not folded into the initiator's commitment history.

## Full-match informed responder

The checker gains a deterministic full-match informed-Bottom mode.

When Top initiates an action, Bottom:

1. sees the selected Top action, consistent with the current established-position v0.2 ordering;
2. enumerates the action's legal responses;
3. resolves every response non-mutating with the real current state, including:
   - Ready final-grade override when applicable;
   - initiator exhaustion modifier;
   - responder exhaustion modifier;
   - active submission-stage semantics;
4. selects the legal response producing the **lowest final grade for Top**;
5. ties break by the existing legal-response order.

When Bottom initiates, Top continues to use the ordinary seeded random response mix. The probe is specifically an informed Bottom defender, not an omniscient two-sided solver.

Everything else remains the same as the normal batch:

- seeds;
- clock;
- drift;
- action policy;
- setup;
- submission state;
- stamina;
- behavior recovery;
- commitment.

## Gate B amendment — competent defender means informed defender

The phrase behind Gate B has always been:

> A fresh, competent defender under dominant Top survives most attempts rather than being submitted automatically.

The random response mix does not represent that phrase once Recognition does not yet exist.

Gate B therefore uses the informed-Bottom standard batch.

The numerical target remains unchanged:

```text
0% < informed Tap rate < 50%
```

No threshold is moved.

The existing random response batch is retained and printed as a **non-gating contrast**.

Gate B must report both:

```text
informed Tap rate = gating
random Tap rate = observational contrast
```

This is a measurement correction to align "competent defender" with the actual responder model, not a numerical tuning change.

## Random-response evidence remains useful

The random mix still answers a different question:

> What happens when the responder samples from the frozen response prior rather than choosing the best recognized defense?

It remains useful for future Recognition/information-layer design and should not be deleted.

## Setup-policy debt remains separate

The informed probe also showed that High Mount Climb can keep gaining Americana setup progress while losing the positional exchange because generic setup progression is broader than result success.

That remains explicit debt.

This amendment does **not** change setup progression, response weights, raw matchup grades, commitment costs, or Gate-5 semantics.

Measure the hold-cost effect first. If Gate B still fails, record that result before revisiting setup progression.
