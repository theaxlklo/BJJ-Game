# v0.4b Recognition — Commitment Read Question

## Status

FUTURE DESIGN NOTE — NOT A DEFINITION OF DONE.

Do not implement Recognition from this note.

When the v0.4b Recognition Definition of Done is drafted, it must explicitly answer the question below before implementation begins.

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

## Change-control reminder

When v0.4b is started:

```text
draft/freeze v0.4b DoD
-> include this question and chosen semantics
-> commit
-> STOP FOR REVIEW
-> explicit authorization
-> implementation
```

No v0.4b mechanic is authorized by this note.
