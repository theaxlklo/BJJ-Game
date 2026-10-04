# Stamina Recovery Policy Amendment — Starting Evidence

## Status

STARTING EVIDENCE RECORDED BEFORE FLAG SPLITTING OR RECOVERY-POLICY IMPLEMENTATION.

Frozen amendment DoD:

```text
dcc5984afbf2f575548be5511bd39f807dbf7f82
```

Base main:

```text
b2299a1037b709d2d4a9893c615e4af5b55b4cfa
```

No settlement flag has been split.

No recovery-initiation mode has been implemented.

No shadow-stalling observer has been implemented.

No stalling-ON candidate matrix has been run.

## Exact Surface E configuration

The checker reused the exact existing Surface E configuration:

```text
100 matches
base seed 42
Top PRESSURE / FIXED
Bottom ESCAPE / RECOVER
initiator requested MEDIUM
Bottom responder INFORMED
response commitment RECOGNITION / trusts reads
v0.2 setup on
v0.3 submissions on
v0.4a commitment semantics on
v0.4b Recognition on
interval 5 s
clock 300 s
starting axis +1.50
starting stamina 100/100
```

Two existing settlement conditions were measured:

```text
LEGACY
  enable_stamina_settlement_rules=False

BOTH
  enable_stamina_settlement_rules=True
```

## Checker-owned result

GitHub Actions run #911, Python 3.13 semantic checker:

### LEGACY

```text
Bottom defensive spend=10,821
  responder commitment spend=9,076
  hold spend=1,745

Bottom own-attack commitment spend=6,091
Bottom own attacks=2,516
Bottom RESETs=29

Bottom behavior recovery=8,658
Bottom behavior spend=938
```

### BOTH settlement rules

```text
Bottom defensive spend=3,872
  responder commitment spend=3,872
  hold spend=0

Bottom own-attack commitment spend=11,994
Bottom own attacks=2,387
Bottom RESETs=18

Bottom behavior recovery=7,950
Bottom behavior spend=990
```

## Required starting evidence

The amendment froze:

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

Checker result:

```text
EXACT MATCH
```

Gate A starting evidence is therefore satisfied.

## Immediate interpretation

The new review hypothesis is quantitatively reproduced:

```text
defensive drain falls:
10,821 -> 3,872
change = -6,949

own-attack commitment spend rises:
6,091 -> 11,994
change = +5,903

Bottom own attacks fall only modestly:
2,516 -> 2,387
change = -129

RESETs fall:
29 -> 18
```

Rule 1 / Rule 2 therefore free substantial Bottom stamina from defense, but the existing CURRENT initiation policy spends much of the newly available budget on Bottom's own MEDIUM attacks.

This is starting evidence only.

It does not yet prove which settlement rule causes which outcome, and it does not select RESET or LOW as a recovery policy.

## Verification

Run #911 Python 3.13 at the evidence checkpoint:

```text
320 tests PASS
semantic checker PASS
legacy entry point PASS

expected digest:
3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2

actual digest:
3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2
```

The checker printed the starting-evidence values directly; tests pin the four required values for LEGACY and BOTH.

## Chronology boundary

This document is committed before:

1. Rule-1 / Rule-2 flag splitting;
2. isolated settlement attribution;
3. RESET_WHILE_EXHAUSTED;
4. LOW_WHILE_EXHAUSTED;
5. shadow v0.3b observation;
6. real stalling-ON candidate runs.

The next authorized implementation step is the independent settlement-flag split.
