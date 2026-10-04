# Stamina Economy Rule Change — Pre-Change Defender-Drain Evidence

## Status

PRE-CHANGE BASELINE RECORDED.

This document was committed **before Rule 1 or Rule 2 implementation**.

Frozen rule-change DoD under review/authorization lineage:

```text
7a992f6ea5ae8eaa4ab9c36606d1d25788868c06
```

No stamina-settlement mechanic has been changed in this evidence commit.

## Why this checkpoint exists

The rule-change DoD required the checker to reproduce the independently reviewed claim that free / UNFUNDED attacks drain recovered defender stamina before any mechanic edit.

The checker now owns two separate selectors:

```text
exact-zero:
  initiator pre-exchange stamina == 0

true-UNFUNDED:
  initiator true effective commitment == UNFUNDED
```

For each selector it reports:

- exchange count;
- response commitment stamina charged;
- provisional hold stamina charged;
- total responder stamina charged;
- stamina-state split;
- action-ID split;
- submission vs non-submission split;
- responder behavior recovery;
- drain/recovery share where recovery is nonzero.

## Surface E — independent causal figure reproduced exactly

Surface:

```text
E trusts reads + Bottom RECOVER
100 matches
base seed 42
Top PRESSURE / FIXED
Bottom ESCAPE / RECOVER
Recognition trust-read responder
```

For **Top exact-zero attacks**:

```text
exchange count=1,949

Bottom response commitment charged=5,010
Bottom provisional hold charged=1,192

total Bottom stamina charged=6,202

Bottom behavior recovery=8,658

6,202 / 8,658 = 0.7163
                 = 71.63%
```

All 6,202 points occur while the exchange is classified:

```text
MUTUALLY_EXHAUSTED_NOT_BOTH_ZERO
```

Action split:

```text
Americana Arm Isolation:       914
Americana Submission Finish: 4,391
High Mount Climb:              897
```

Submission / non-submission responder drain:

```text
submission=5,305
non-submission=897
```

This reproduces the independently reviewed **6,202 / 8,658 ≈ 72%** causal figure exactly.

### Semantic UNFUNDED comparison

For Top true-UNFUNDED attacks, including 1-2 stamina initiators as well as zero:

```text
exchange count=2,001

response charged=5,154
hold charged=1,265
total charged=6,419

Bottom recovery=8,658
drain/recovery=74.14%
```

This confirms why the rule trigger is semantic UNFUNDED rather than raw zero alone.

## Surface B — accounting-label discrepancy resolved

The reviewed rule-change DoD stated:

```text
Surface B Bottom spend caused by Top zero-stamina attacks=95
```

The structured checker shows that wording was too narrow.

### Top exact-zero attacks -> Bottom defender drain

```text
Top exact-zero exchanges=1,878

Bottom response commitment charged=24
Bottom hold charged=5
Bottom total charged=29
```

### Bottom exact-zero attacks -> Top defender drain

```text
Bottom exact-zero exchanges=1,874

Top response commitment charged=66
Top hold charged=0
Top total charged=66
```

### Combined Surface-B exact-zero defender drain

```text
29 + 66 = 95
```

Therefore the independently reviewed `95` is reproduced by the checker as:

> **combined responder stamina charged on Surface B by exact-zero initiators in both directions**

It is **not** reproduced as Top-zero -> Bottom-only drain.

This is an accounting-label correction, not a gameplay change.

### Surface-B semantic UNFUNDED drain

Top true-UNFUNDED -> Bottom:

```text
response=75
hold=34
total=109
```

Bottom true-UNFUNDED -> Top:

```text
response=93
hold=0
total=93
```

Combined:

```text
202
```

## Checker run evidence

GitHub Actions run #872, Python 3.13 semantic checker, printed:

```text
Surface B exact-zero Top:
  response/hold/total=24/5/29

Surface B exact-zero Bottom:
  response/hold/total=66/0/66

Surface E exact-zero Top:
  exchanges=1949
  response/hold/total=5010/1192/6202
  responder behavior recovery=8658
  drain/recovery=0.7163

Surface E true-UNFUNDED Top:
  exchanges=2001
  response/hold/total=5154/1265/6419
  responder behavior recovery=8658
  drain/recovery=0.7414

STATUS: PASS
```

The same run preserved the frozen matchup digest:

```text
3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2
```

## Process consequence

The central Surface-E causal evidence is fully reproduced.

However, the Surface-B `95` label in the reviewed DoD is inaccurate.

Because the DoD explicitly said to stop on an accounting disagreement before mechanics, Rule 1 and Rule 2 remain **unimplemented** at this checkpoint.

The DoD must be clarified so its baseline says:

```text
Surface B exact-zero combined defender drain=95
  Top -> Bottom=29
  Bottom -> Top=66
```

After that clarification is reviewed/authorized, implementation may proceed from this frozen pre-change evidence.
