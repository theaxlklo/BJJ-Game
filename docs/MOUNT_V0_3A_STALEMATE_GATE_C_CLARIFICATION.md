# v0.3a Stalemate Amendment Clarification — Gate C Behavior Context

This clarification is committed before the mechanics change.

The stalemate amendment says a fresh defender's best legal submission-stage response should be exactly Contested. That invariant refers to the **baseline v0.3a stage context** used for the submission mechanics proof:

```text
Top PRESSURE
Bottom ESCAPE
Top Fresh
Bottom Fresh
```

It does **not** require every strategic Bottom behavior to produce Contested.

In particular, the intended behavior interaction remains:

```text
Bottom ESCAPE + Turn-In
    -> Contested
    -> hold stage

Bottom PROTECT + Turn-In
    -> behavior modifier -1
    -> Failure
    -> break track + axis -1.00

Bottom ESCAPE + Exhausted responder + Turn-In
    -> responder exhaustion +1 for Top
    -> Success
    -> advance stage
```

Therefore Gate C enumerates every stage and Mount-band anchor under fresh `PRESSURE / ESCAPE` and requires the informed best legal defense to be exactly Contested.

The separate behavior sweep remains responsible for showing how PROTECT and CONSERVE change aggregate outcomes.

Gate E likewise uses `PRESSURE / ESCAPE` while changing only Bottom's stamina band to Exhausted.
