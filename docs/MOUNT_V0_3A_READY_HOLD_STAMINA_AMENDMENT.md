# v0.3a Design Amendment — Ready-Americana Stalemate Hold Cost

## Reason

The active-stage hold-cost experiment could not influence informed Gate B because informed Bottom never allowed Threat to start.

The repeated informed sequence was:

```text
rebuild Ready Americana
-> Bottom chooses Turn-In
-> final grade Contested
-> setup consumed
-> Threat not entered
-> repeat
```

So a stamina cost attached only to Threat/Control/Finish Contested holds never fired.

## Narrow extension

When v0.3 submissions are enabled, the Ready-Americana Contested stalemate is part of the same submission-pressure hold economy as an active-stage Contested hold.

Charge the responder the existing LOW cost:

```text
3 stamina
```

when all of these are true:

```text
enable_v03_submissions == True
action == Ready Americana target
target_was_ready == True
final grade == Contested
```

This cost is post-resolution.

The current response uses the responder stamina band sampled before the cost; crossing into Exhausted changes only later exchanges.

## v0.2 compatibility

The same Ready-Americana exchange under:

```text
enable_v02_setup=True
enable_v03_submissions=False
```

remains response-cost free.

Therefore the extension does not change ordinary v0.2 Ready stamina semantics.

## Shared observability

Ready and active-stage Contested costs use the same submission-hold history fields:

- responder side;
- requested cost;
- charged cost;
- shortfall.

The history records the actual hold event regardless of whether it occurred at Ready isolation or an active Threat/Control/Finish stage.

## No other changes

This amendment does not alter:

- response weights;
- raw grades;
- setup progression;
- commitment costs;
- behavior stamina;
- exhaustion thresholds;
- Gate-B threshold;
- active-stage legality;
- Contested/Failure semantics.

If informed Gate B still fails after this extension, record the result before changing setup or stamina further.
