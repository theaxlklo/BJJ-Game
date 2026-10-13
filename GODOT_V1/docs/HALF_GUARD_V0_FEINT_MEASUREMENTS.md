# Half Guard v0 feint measurements (B1h)

**Evidence only. Nothing here is a balance qualification, a gate, or a claim that the prototype numbers are right.** The numbers are produced by `GODOT_V1/tests/measure_half_guard_feints.py` from the independent Python oracle (`tests/oracles/half_guard_v0.py`, written from `HALF_GUARD_V0_RULES.md` section 13). The typed Godot engine reproduces the oracle exactly (`test_half_guard_feint_reference.gd`: 6,664 fixture rows, 0 mismatches), so they describe the engine too. The script is deterministic (no clock, no `random`; a fixed LCG drives the seeded populations) and its output was byte-identical across two runs. It is **not** wired into CI.

Two categories are kept apart on purpose. **STRUCTURAL** results are exact facts about the rules (grade tables, funding arithmetic, forced searches, reachability within a stated depth). **POPULATION** results count what a *stated policy* does over seeded games; they say nothing about whether the game is fair or fun.

## Reading guide: what the measurements show

* **A feint is not a grade upgrade over the best direct attack against the same response** (section 2: in 0 of 108 eligible cells does the feint strictly beat both direct options against the same response). Its value is *information*: the defender chooses a response from the apparent technique. Against a defender who always answers the apparent technique with its best counter (the bite), the feint gains +2 where the direct apparent technique gets −1 (section 3).
* **A defender who calls the bluff holds the attacker down.** Against the best counter to the real technique the feint falls to −2 (MEDIUM). For FP-1 the balanced defender (Knee Shield) holds both modes to ≤ 0. For FP-2 the balanced defender at MEDIUM (Hip Pressure) holds both to ≤ 0, but a **HIGH** FP-2 feint still gets +1 against Hip Pressure (section 3): the proposal's neutral-state counterplay rule was written at MEDIUM; whether that residue matters is a balance question.
* **Repeated called feints are self-defeating.** Driven through the oracle, an attacker that feints at every window against a defender that always calls ends with 0 stamina after 10 feints, the axis pinned at the far end against the attacker (−40 for the Top's FP-1, +40 for the Bottom's FP-2) and no exit (section 4). Against a defender that always bites the attacker exits in 2 windows with 80 stamina left.
* **Stamina:** a MEDIUM feint (10) latches the attacker in 8 attacks while the defender is still at 44; a LOW feint takes 13 (section 4). The surcharge makes the attacker the faster drainer at every tier.
* **Preparation matters through eligibility and readiness:** at tier None the feint does not exist (0 cells); at Ready the feint equals the better direct option in 16 of 27 cells instead of 9 (section 2).
* **Exits:** within 5 windows, over every attacker action, feint and commitment, feints reach no exit earlier than direct play (Side Control 3, Open Guard 4, Closed Guard 2). Feints change *which defender policies* concede exits, not the structural earliest window. In the seeded populations (section 6) the share of games that end in an exit stays between about 88% and 99% in every cell, so feints change **which** exit happens rather than whether one does: against an always-biting defender Side Control falls from 368 to 156 of 500 games while Closed Guard rises from 95 to 279 when the attacker feints whenever eligible; against an always-calling defender only 6 of 500 games end in an exit made by a feint. **A feint guarantees no exit.**

## Measured tables

## 1. One-exchange final grades (STRUCTURAL)

**Top: crossface -> knee_slice (bite = underhook_fight, call = knee_shield), defender answers MEDIUM, attacker at 100 stamina, neutral axis**
| tiers (own/other) | attacker commitment | defender response | direct apparent | direct real | feint | feint exits? |
| Partial/1         | LOW                 | hip_frame         | 1               | 1           | 0     | -            |
| Partial/1         | LOW                 | underhook_fight   | -1              | 1           | 1     | -            |
| Partial/1         | LOW                 | knee_shield       | 0               | -1          | -1    | -            |
| Partial/1         | MEDIUM              | hip_frame         | 1               | 1           | 0     | -            |
| Partial/1         | MEDIUM              | underhook_fight   | -1              | 2           | 2     | -            |
| Partial/1         | MEDIUM              | knee_shield       | 0               | -2          | -2    | -            |
| Partial/1         | HIGH                | hip_frame         | 2               | 2           | 1     | -            |
| Partial/1         | HIGH                | underhook_fight   | -1              | 2           | 2     | -            |
| Partial/1         | HIGH                | knee_shield       | 1               | -1          | -1    | -            |
| Ready/1           | LOW                 | hip_frame         | 1               | 1           | 1     | -            |
| Ready/1           | LOW                 | underhook_fight   | -1              | 1           | 1     | -            |
| Ready/1           | LOW                 | knee_shield       | 0               | -1          | -1    | -            |
| Ready/1           | MEDIUM              | hip_frame         | 1               | 2           | 1     | -            |
| Ready/1           | MEDIUM              | underhook_fight   | -1              | 2           | 2     | -            |
| Ready/1           | MEDIUM              | knee_shield       | 0               | -1          | -2    | -            |
| Ready/1           | HIGH                | hip_frame         | 2               | 2           | 2     | -            |
| Ready/1           | HIGH                | underhook_fight   | -1              | 2           | 2     | -            |
| Ready/1           | HIGH                | knee_shield       | 1               | -1          | -1    | -            |

**Bottom: underhook -> recover_guard (bite = head_control, call = knee_pin), defender answers MEDIUM, attacker at 100 stamina, neutral axis**
| tiers (own/other) | attacker commitment | defender response | direct apparent | direct real | feint | feint exits? |
| Partial/1         | LOW                 | head_control      | -1              | 1           | 1     | -            |
| Partial/1         | LOW                 | hip_pressure      | 0               | 1           | 0     | -            |
| Partial/1         | LOW                 | knee_pin          | 1               | -1          | -1    | -            |
| Partial/1         | MEDIUM              | head_control      | -1              | 2           | 2     | -            |
| Partial/1         | MEDIUM              | hip_pressure      | 0               | 1           | 0     | -            |
| Partial/1         | MEDIUM              | knee_pin          | 1               | -2          | -2    | -            |
| Partial/1         | HIGH                | head_control      | -1              | 2           | 2     | -            |
| Partial/1         | HIGH                | hip_pressure      | 1               | 2           | 1     | -            |
| Partial/1         | HIGH                | knee_pin          | 2               | -1          | -1    | -            |
| Ready/1           | LOW                 | head_control      | -1              | 1           | 1     | -            |
| Ready/1           | LOW                 | hip_pressure      | 0               | 1           | 1     | -            |
| Ready/1           | LOW                 | knee_pin          | 1               | -1          | -1    | -            |
| Ready/1           | MEDIUM              | head_control      | -1              | 2           | 2     | -            |
| Ready/1           | MEDIUM              | hip_pressure      | 0               | 2           | 1     | -            |
| Ready/1           | MEDIUM              | knee_pin          | 1               | -1          | -2    | -            |
| Ready/1           | HIGH                | head_control      | -1              | 2           | 2     | -            |
| Ready/1           | HIGH                | hip_pressure      | 1               | 2           | 2     | -            |
| Ready/1           | HIGH                | knee_pin          | 2               | -1          | -1    | -            |

## 2. Does preparation create feint opportunities? (STRUCTURAL; 27 cells per row)
| pair                       | own tier            | cells (response x commitment x defender commitment) | feint strictly beats BOTH direct options | feint equals the better direct option | feint strictly worse than the better direct option |
| crossface -> knee_slice    | None (not eligible) | 0                                                   | 0                                        | 0                                     | 0                                                  |
| crossface -> knee_slice    | Partial             | 27                                                  | 0                                        | 9                                     | 18                                                 |
| crossface -> knee_slice    | Ready               | 27                                                  | 0                                        | 16                                    | 11                                                 |
| underhook -> recover_guard | None (not eligible) | 0                                                   | 0                                        | 0                                     | 0                                                  |
| underhook -> recover_guard | Partial             | 27                                                  | 0                                        | 9                                     | 18                                                 |
| underhook -> recover_guard | Ready               | 27                                                  | 0                                        | 16                                    | 11                                                 |

## 3. Defender policies at the neutral state (STRUCTURAL)
| pair                       | defender policy                                      | response        | direct apparent | feint (MEDIUM/MEDIUM) | feint (HIGH/MEDIUM) | attacker's worst case across {direct apparent, feint} |
| crossface -> knee_slice    | fixed best counter to the APPARENT technique (bites) | underhook_fight | -1              | 2                     | 2                   | 2                                                     |
| crossface -> knee_slice    | calls the bluff (best counter to the REAL technique) | knee_shield     | 0               | -2                    | -1                  | 0                                                     |
| crossface -> knee_slice    | balanced (minimises the attacker's worst case)       | knee_shield     | 0               | -2                    | -1                  | 0                                                     |
| crossface -> knee_slice    | timeout fallback (published, LOW)                    | hip_frame       | 2               | 1                     | 1                   | 2                                                     |
| underhook -> recover_guard | fixed best counter to the APPARENT technique (bites) | head_control    | -1              | 2                     | 2                   | 2                                                     |
| underhook -> recover_guard | calls the bluff (best counter to the REAL technique) | knee_pin        | 1               | -2                    | -1                  | 1                                                     |
| underhook -> recover_guard | balanced (minimises the attacker's worst case)       | hip_pressure    | 0               | 0                     | 1                   | 0                                                     |
| underhook -> recover_guard | timeout fallback (published, LOW)                    | hip_pressure    | 1               | 1                     | 1                   | 1                                                     |

## 4. Attacker stamina depletion (STRUCTURAL arithmetic)
| attack            | cost per attack | attacks until the attacker is latched (<= 25) from 100 | attacker stamina then | defender stamina then (answers MEDIUM) |
| direct MEDIUM     | 7               | 11                                                     | 23                    | 23                                     |
| direct HIGH       | 12              | 7                                                      | 16                    | 51                                     |
| feint LOW (+3)    | 6               | 13                                                     | 22                    | 9                                      |
| feint MEDIUM (+3) | 10              | 8                                                      | 20                    | 44                                     |
| feint HIGH (+3)   | 15              | 5                                                      | 25                    | 65                                     |

### Repeated feints driven through the oracle (STRUCTURAL sequence)
* top feinting crossface -> knee_slice every window, defender always calls (best counter to the real technique): 10 feints, final axis -40, attacker stamina 0, defender stamina 30, exit 'none'; exchanges (response, final grade, axis): [('knee_shield', -2, -15), ('knee_shield', -1, -25), ('knee_shield', -1, -35), ('knee_shield', -1, -40), ('knee_shield', -1, -40), ('knee_shield', -1, -40)]
* top feinting crossface -> knee_slice every window, defender always bites: 2 feints, final axis +40, attacker stamina 80, defender stamina 86, exit 'Side Control'; exchanges (response, final grade, axis): [('underhook_fight', 2, 25), ('underhook_fight', 2, 40), ('EXIT Side Control', 40)]
* bottom feinting underhook -> recover_guard every window, defender always calls (best counter to the real technique): 10 feints, final axis +40, attacker stamina 0, defender stamina 30, exit 'none'; exchanges (response, final grade, axis): [('knee_pin', -2, 25), ('knee_pin', -1, 35), ('knee_pin', -1, 40), ('knee_pin', -1, 40), ('knee_pin', -1, 40), ('knee_pin', -1, 40)]
* bottom feinting underhook -> recover_guard every window, defender always bites: 2 feints, final axis -35, attacker stamina 80, defender stamina 86, exit 'Closed Guard'; exchanges (response, final grade, axis): [('head_control', 2, -15), ('head_control', 2, -35), ('EXIT Closed Guard', -35)]

## 5. Earliest exit windows over every attacker choice and commitment (STRUCTURAL breadth-first search over every attacker action, feint and commitment, 5 windows (the state space grows too fast for more), defender answers MEDIUM)
| attacker options | defender                   | earliest window to Side Control | to Open Guard | to Closed Guard |
| direct only      | cooperative (any response) | 3                               | 4             | 2               |
| direct only      | always the bite response   | 3                               | 4             | 2               |
| direct only      | always the call response   | 3                               | 4             | 4               |
| direct + feint   | cooperative (any response) | 3                               | 4             | 2               |
| direct + feint   | always the bite response   | 3                               | 4             | 2               |
| direct + feint   | always the call response   | 3                               | 4             | 4               |

## 6. Seeded policy populations (POPULATION evidence; 500 games x 60 windows per cell)
| attacker                             | defender                            | games | Side Control | Open Guard | Closed Guard | timeout (60 windows) | accepted feints | exits ended by a feint |
| direct only                          | random response                     | 500   | 286          | 102        | 102          | 10                   | 0               | 0                      |
| direct only                          | always bites                        | 500   | 368          | 34         | 95           | 3                    | 0               | 0                      |
| direct only                          | always calls                        | 500   | 237          | 191        | 24           | 48                   | 0               | 0                      |
| direct only                          | published fallback (LOW) every time | 500   | 159          | 92         | 209          | 40                   | 0               | 0                      |
| feints 50% of the time when eligible | random response                     | 500   | 281          | 105        | 100          | 14                   | 562             | 65                     |
| feints 50% of the time when eligible | always bites                        | 500   | 284          | 49         | 164          | 3                    | 708             | 90                     |
| feints 50% of the time when eligible | always calls                        | 500   | 279          | 152        | 16           | 53                   | 354             | 5                      |
| feints 50% of the time when eligible | published fallback (LOW) every time | 500   | 137          | 111        | 203          | 49                   | 537             | 61                     |
| feints whenever eligible             | random response                     | 500   | 286          | 94         | 112          | 8                    | 1045            | 112                    |
| feints whenever eligible             | always bites                        | 500   | 156          | 63         | 279          | 2                    | 1250            | 175                    |
| feints whenever eligible             | always calls                        | 500   | 301          | 135        | 11           | 53                   | 606             | 6                      |
| feints whenever eligible             | published fallback (LOW) every time | 500   | 110          | 154        | 175          | 61                   | 1058            | 102                    |

## What these measurements do not establish

No claim about balance, enjoyment, human behavior, the right value of the surcharge, or the right bite value. The populations are uniform-random attackers against four fixed defender policies, not strategic players. The breadth-first search covers 5 windows because the state space grows too fast beyond that (a 6-window search took about three minutes). The Hip Frame / Hip Pressure fallback consequences shown here are the existing undercommitment mechanics only.
