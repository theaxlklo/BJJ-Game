# v0.3a Gate C Reachability Note

This note is committed before the amended checker implementation.

Under the Gate-C baseline context:

```text
Top PRESSURE
Bottom ESCAPE
both Fresh
```

the current Mount entry route can activate Americana only from Strong or Locked.

After entry:

- Success advances the submission stage with zero free axis gain;
- Contested holds the stage with zero axis change;
- PRESSURE / ESCAPE normal-speed drift is positive for Top.

Therefore an active Americana track in **Loose or Stable is not reachable through the Gate-C baseline route**.

The amended Gate C consequently enumerates the reachable Mount anchors:

```text
Strong
Locked
```

for each of:

```text
Threat
Control
Finish
```

This does not assert that Americana cannot persist through other positional contexts in a future multi-position model. It only keeps the current Mount-v0.3a proof scoped to states reachable from its implemented entry route and baseline behavior.
