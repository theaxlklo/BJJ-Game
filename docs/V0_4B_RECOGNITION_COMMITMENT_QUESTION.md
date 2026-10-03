# v0.4b Recognition — Commitment Read Question

## Status

HISTORICAL DESIGN QUESTION — RESOLVED BY THE FROZEN v0.4b DEFINITION OF DONE.

This note was written before v0.4b began. The question below is now answered by:

`docs/MOUNT_V0_4B_RECOGNITION_DEFINITION_OF_DONE.md`

The frozen decision is **Model C**: the defender receives separate noisy reads of requested intent and effective capability. This file remains as the design trail; it is no longer implementation guidance by itself.

## Required design question

v0.4a now gives requested and effective commitment different meanings:

```text
requested commitment
-> declared/selected intent
-> LOW is the feint-intent signal

effective commitment
-> funded capability after stamina affordability
-> controls grade magnitude, cost, mismatch, and funded tactical credit
```

Recognition must therefore define **what information the defender reads**.

At minimum the v0.4b DoD must choose and justify one of these models, or define another explicit model:

```text
A. defender recognizes requested commitment / intent

B. defender recognizes effective commitment / capability

C. defender receives separate noisy signals for requested intent
   and effective capability

D. defender observes one directly and infers the other
```

The DoD must also specify when the read happens relative to:

```text
requested selection
-> pre-cost stamina state
-> affordability downgrade
-> response commitment selection
-> exchange resolution
```

## Why this cannot remain implicit

Examples that must be addressed deliberately:

```text
requested LOW, fully funded
-> intentional feint with real LOW capability

requested MEDIUM, effective LOW
-> continuation intent, reduced capability

requested HIGH, effective UNFUNDED
-> strong continuation intent, effectively no funded commitment
```

A defender might plausibly read intent from behavior while also sensing reduced force from fatigue. Those are different signals after the v0.4a feint-intent amendment.

Recognition must not silently collapse them back into one field.

## Resolution

The frozen v0.4b DoD chose:

```text
requested intent      -> separate noisy d6 read
effective capability  -> separate noisy d6 read
```

The reads occur after initiator affordability is known and before defender response-commitment selection / legal-response choice.

The implementation authority comes from the frozen DoD plus the user's explicit authorization to implement v0.4b, not from this historical note.
