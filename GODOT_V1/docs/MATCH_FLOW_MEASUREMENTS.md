<!-- Generated, deterministic. Regenerate with:
  godot-bjj --headless --path GODOT_V1 --script res://tests/measure_match_flow.gd
and keep the lines from '# Match-flow measurement' to the line before '== PERFORMANCE'. SHA-256 of that body: 94eaa489d9074d48a3945cbbba3659ab38bdd566e60dd2248489909261a39dea -->

# Match-flow measurement (B1e) — evidence only, not a balance claim

maximum windows per game: 80 (the 300 s clock at a 5 s interval ends a game after at most 60 windows); seeds: 30 (Mount/full-flow populations), 20 (Half Guard populations);
real Mount entries into Half Guard used by population B: 5 distinct plans

## Population A — Mount-only policies (an entered Half Guard is then played with passes only)
POPULATION. Rows are named scripted policies; `seeded_legal` and `seeded` are reproducible uniform random walks over LEGAL options, not intelligent or balanced players. Deterministic cells use one game.

**Summary by policy** (all cells with the same policy pooled; percentages are of games)
| policy | games | ended by a tap | ended by the clock | halted at an unsupported exit | entered Half Guard | still active after the maximum windows | windows mean | exchanges mean | feints accepted | feints that bit | feints effective (grade >= Success) | feints punished (grade <= Failure) | fallbacks | games with a 10+ window no-progress streak | final axis mean | lowest / highest axis mean | unsupported-exit destinations (games) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| pass_only | 2 | 0 (0%) | 2 (100%) | 0 (0%) | 0 (0%) | 0 | 59.0 | 0.0 | 0 | - | - | - | 0 | 2 (100%) | +4.00 | +2.00 / +4.00 | - |
| top_direct | 62 | 0 (0%) | 62 (100%) | 0 (0%) | 0 (0%) | 0 | 59.0 | 30.0 | 0 | - | - | - | 0 | 3 (5%) | +3.68 | +2.24 / +4.00 | - |
| top_finish | 62 | 51 (82%) | 11 (18%) | 0 (0%) | 0 (0%) | 0 | 26.4 | 13.7 | 0 | - | - | - | 0 | 4 (6%) | +3.97 | +2.26 / +4.00 | - |
| bottom_escape | 62 | 0 (0%) | 62 (100%) | 0 (0%) | 14 (23%) | 0 | 59.0 | 25.1 | 0 | - | - | - | 0 | 24 (39%) | +2.37 | +0.97 / +3.98 | - |
| bottom_trap_roll | 62 | 0 (0%) | 62 (100%) | 0 (0%) | 0 (0%) | 0 | 59.0 | 26.0 | 0 | - | - | - | 0 | 14 (23%) | +2.82 | +1.50 / +4.00 | - |
| seeded_legal | 120 | 36 (30%) | 82 (68%) | 2 (2%) | 18 (15%) | 0 | 53.3 | 31.1 | 0 | - | - | - | 0 | 27 (22%) | +2.89 | +1.03 / +3.81 | mount:Open Guard 2 |

**Outcomes (games per terminal class)** — `halt_*` is an unsupported-destination boundary, not a result
| cell | games | halt_mount:Open Guard | tap_mount | timeout_half_guard | timeout_mount |
|---|---|---|---|---|---|
| pass_only / first_available / MEDIUM | 1 | 0 | 0 | 0 | 1 |
| pass_only / first_available / HIGH | 1 | 0 | 0 | 0 | 1 |
| top_direct / first_available / MEDIUM | 1 | 0 | 0 | 0 | 1 |
| top_direct / first_available / HIGH | 1 | 0 | 0 | 0 | 1 |
| top_direct / seeded / MEDIUM | 30 | 0 | 0 | 0 | 30 |
| top_direct / seeded / HIGH | 30 | 0 | 0 | 0 | 30 |
| top_finish / first_available / MEDIUM | 1 | 0 | 1 | 0 | 0 |
| top_finish / first_available / HIGH | 1 | 0 | 1 | 0 | 0 |
| top_finish / seeded / MEDIUM | 30 | 0 | 28 | 0 | 2 |
| top_finish / seeded / HIGH | 30 | 0 | 21 | 0 | 9 |
| bottom_escape / first_available / MEDIUM | 1 | 0 | 0 | 1 | 0 |
| bottom_escape / first_available / HIGH | 1 | 0 | 0 | 1 | 0 |
| bottom_escape / seeded / MEDIUM | 30 | 0 | 0 | 6 | 24 |
| bottom_escape / seeded / HIGH | 30 | 0 | 0 | 6 | 24 |
| bottom_trap_roll / first_available / MEDIUM | 1 | 0 | 0 | 0 | 1 |
| bottom_trap_roll / first_available / HIGH | 1 | 0 | 0 | 0 | 1 |
| bottom_trap_roll / seeded / MEDIUM | 30 | 0 | 0 | 0 | 30 |
| bottom_trap_roll / seeded / HIGH | 30 | 0 | 0 | 0 | 30 |
| seeded_legal / first_available / MEDIUM | 30 | 0 | 17 | 5 | 8 |
| seeded_legal / first_available / HIGH | 30 | 2 | 13 | 7 | 8 |
| seeded_legal / seeded / MEDIUM | 30 | 0 | 3 | 2 | 25 |
| seeded_legal / seeded / HIGH | 30 | 0 | 3 | 4 | 23 |

**Time, entry and position time** (means over the cell's games; seconds are simulated clock seconds)
| cell | windows mean (min-max) | seconds mean | entered Half Guard | mean entry window | Mount windows mean | Half Guard windows mean | exchanges mean | passes mean | D3-B holds mean | longest pass streak max | longest idle streak max |
|---|---|---|---|---|---|---|---|---|---|---|---|
| pass_only / first_available / MEDIUM | 59.0 (59-59) | 300.0 | 0/1 | - | 59.0 | 0.0 | 0.0 | 59.0 | 0.0 | 59 | 59 |
| pass_only / first_available / HIGH | 59.0 (59-59) | 300.0 | 0/1 | - | 59.0 | 0.0 | 0.0 | 59.0 | 0.0 | 59 | 59 |
| top_direct / first_available / MEDIUM | 59.0 (59-59) | 300.0 | 0/1 | - | 59.0 | 0.0 | 30.0 | 29.0 | 0.0 | 1 | 1 |
| top_direct / first_available / HIGH | 59.0 (59-59) | 300.0 | 0/1 | - | 59.0 | 0.0 | 30.0 | 29.0 | 0.0 | 1 | 1 |
| top_direct / seeded / MEDIUM | 59.0 (59-59) | 300.0 | 0/30 | - | 59.0 | 0.0 | 30.0 | 29.0 | 0.0 | 1 | 1 |
| top_direct / seeded / HIGH | 59.0 (59-59) | 300.0 | 0/30 | - | 59.0 | 0.0 | 30.0 | 29.0 | 0.0 | 1 | 1 |
| top_finish / first_available / MEDIUM | 41.0 (41-41) | 205.0 | 0/1 | - | 41.0 | 0.0 | 21.0 | 20.0 | 0.0 | 1 | 1 |
| top_finish / first_available / HIGH | 23.0 (23-23) | 115.0 | 0/1 | - | 23.0 | 0.0 | 12.0 | 11.0 | 0.0 | 1 | 1 |
| top_finish / seeded / MEDIUM | 23.5 (11-59) | 117.7 | 0/30 | - | 23.5 | 0.0 | 12.2 | 11.2 | 0.0 | 1 | 1 |
| top_finish / seeded / HIGH | 29.0 (11-59) | 146.5 | 0/30 | - | 29.0 | 0.0 | 15.0 | 14.0 | 0.0 | 1 | 1 |
| bottom_escape / first_available / MEDIUM | 59.0 (59-59) | 300.0 | 1/1 | 32.0 | 32.0 | 27.0 | 16.0 | 43.0 | 0.0 | 27 | 27 |
| bottom_escape / first_available / HIGH | 59.0 (59-59) | 300.0 | 1/1 | 32.0 | 32.0 | 27.0 | 16.0 | 43.0 | 0.0 | 27 | 27 |
| bottom_escape / seeded / MEDIUM | 59.0 (59-59) | 300.0 | 6/30 | 46.3 | 56.5 | 2.5 | 25.4 | 31.2 | 2.4 | 15 | 15 |
| bottom_escape / seeded / HIGH | 59.0 (59-59) | 300.0 | 6/30 | 46.3 | 56.5 | 2.5 | 25.4 | 31.2 | 2.4 | 15 | 15 |
| bottom_trap_roll / first_available / MEDIUM | 59.0 (59-59) | 300.0 | 0/1 | - | 59.0 | 0.0 | 26.0 | 30.0 | 3.0 | 1 | 7 |
| bottom_trap_roll / first_available / HIGH | 59.0 (59-59) | 300.0 | 0/1 | - | 59.0 | 0.0 | 26.0 | 30.0 | 3.0 | 1 | 7 |
| bottom_trap_roll / seeded / MEDIUM | 59.0 (59-59) | 300.0 | 0/30 | - | 59.0 | 0.0 | 26.0 | 30.0 | 3.0 | 1 | 7 |
| bottom_trap_roll / seeded / HIGH | 59.0 (59-59) | 300.0 | 0/30 | - | 59.0 | 0.0 | 26.0 | 30.0 | 3.0 | 1 | 7 |
| seeded_legal / first_available / MEDIUM | 50.3 (27-59) | 253.8 | 5/30 | 8.8 | 42.0 | 8.4 | 28.2 | 20.7 | 1.4 | 57 | 57 |
| seeded_legal / first_available / HIGH | 48.3 (12-59) | 243.8 | 7/30 | 12.9 | 37.5 | 10.8 | 24.3 | 21.8 | 2.2 | 57 | 57 |
| seeded_legal / seeded / MEDIUM | 57.1 (37-59) | 290.2 | 2/30 | 46.0 | 56.3 | 0.9 | 37.0 | 17.5 | 2.7 | 15 | 15 |
| seeded_legal / seeded / HIGH | 57.4 (23-59) | 291.5 | 4/30 | 46.0 | 55.7 | 1.7 | 35.1 | 17.8 | 4.5 | 23 | 23 |

**Stamina, exhaustion and commitment downgrades** (means; `downgrades` counts exchanges whose requested commitment was funded lower, either fighter)
| cell | min stamina top (mean) | min stamina bottom (mean) | games with an exhausted fighter | exhausted windows top+bottom (mean) | downgrades (mean) | windows where any stamina rose: Mount / Half Guard (total) |
|---|---|---|---|---|---|---|
| pass_only / first_available / MEDIUM | 41.0 | 41.0 | 0/1 | 0.0 | 0.0 | 0 / 0 |
| pass_only / first_available / HIGH | 41.0 | 41.0 | 0/1 | 0.0 | 0.0 | 0 / 0 |
| top_direct / first_available / MEDIUM | 0.0 | 14.0 | 1/1 | 63.0 | 19.0 | 19 / 0 |
| top_direct / first_available / HIGH | 0.0 | 25.0 | 1/1 | 62.0 | 23.0 | 13 / 0 |
| top_direct / seeded / MEDIUM | 0.0 | 13.2 | 30/30 | 64.6 | 19.0 | 582 / 0 |
| top_direct / seeded / HIGH | 0.0 | 25.0 | 30/30 | 62.0 | 23.0 | 390 / 0 |
| top_finish / first_available / MEDIUM | 0.0 | 14.0 | 1/1 | 38.0 | 10.0 | 13 / 0 |
| top_finish / first_available / HIGH | 0.0 | 28.0 | 1/1 | 12.0 | 5.0 | 0 / 0 |
| top_finish / seeded / MEDIUM | 14.0 | 18.3 | 21/30 | 14.5 | 2.7 | 146 / 0 |
| top_finish / seeded / HIGH | 8.1 | 36.1 | 16/30 | 22.8 | 8.5 | 132 / 0 |
| bottom_escape / first_available / MEDIUM | 0.0 | 19.0 | 1/1 | 82.0 | 5.0 | 7 / 0 |
| bottom_escape / first_available / HIGH | 0.0 | 19.0 | 1/1 | 82.0 | 5.0 | 7 / 0 |
| bottom_escape / seeded / MEDIUM | 0.0 | 19.0 | 30/30 | 75.7 | 14.4 | 609 / 0 |
| bottom_escape / seeded / HIGH | 0.0 | 19.0 | 30/30 | 75.7 | 14.4 | 609 / 0 |
| bottom_trap_roll / first_available / MEDIUM | 0.0 | 19.0 | 1/1 | 76.0 | 15.0 | 22 / 0 |
| bottom_trap_roll / first_available / HIGH | 0.0 | 19.0 | 1/1 | 76.0 | 15.0 | 22 / 0 |
| bottom_trap_roll / seeded / MEDIUM | 0.0 | 19.0 | 30/30 | 76.0 | 15.0 | 660 / 0 |
| bottom_trap_roll / seeded / HIGH | 0.0 | 19.0 | 30/30 | 76.0 | 15.0 | 660 / 0 |
| seeded_legal / first_available / MEDIUM | 10.9 | 24.2 | 26/30 | 56.1 | 18.2 | 517 / 0 |
| seeded_legal / first_available / HIGH | 10.2 | 28.2 | 26/30 | 52.8 | 16.6 | 448 / 0 |
| seeded_legal / seeded / MEDIUM | 0.0 | 15.3 | 30/30 | 79.0 | 25.7 | 743 / 0 |
| seeded_legal / seeded / HIGH | 0.0 | 19.4 | 30/30 | 79.3 | 26.6 | 774 / 0 |

**Feints and the published LOW fallback** (totals over the cell's games; `effective` = final grade >= Success, `punished` = final grade <= Failure)
| cell | feint attempts | refused (by code) | accepted | bit | not bit | effective | neutral | punished | exits by a feint | exits capped (LOW) | fallbacks | undercommitment +1 | fallback modifier mismatches |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| (no feint or fallback in this population) | | | | | | | | | | | | | |

**Positional trajectory** (one comparable axis, positive = Top advantage: Mount `axis`, Half Guard `axis_tenths / 10`; means over games)
| cell | final axis (mean) | lowest axis reached (mean) | highest axis reached (mean) |
|---|---|---|---|
| pass_only / first_available / MEDIUM | +4.00 | +2.00 | +4.00 |
| pass_only / first_available / HIGH | +4.00 | +2.00 | +4.00 |
| top_direct / first_available / MEDIUM | +4.00 | +3.00 | +4.00 |
| top_direct / first_available / HIGH | +4.00 | +3.00 | +4.00 |
| top_direct / seeded / MEDIUM | +3.67 | +2.03 | +4.00 |
| top_direct / seeded / HIGH | +3.67 | +2.40 | +4.00 |
| top_finish / first_available / MEDIUM | +4.00 | +3.00 | +4.00 |
| top_finish / first_available / HIGH | +4.00 | +4.00 | +4.00 |
| top_finish / seeded / MEDIUM | +3.97 | +2.03 | +4.00 |
| top_finish / seeded / HIGH | +3.97 | +2.40 | +4.00 |
| bottom_escape / first_available / MEDIUM | +0.50 | +0.50 | +3.25 |
| bottom_escape / first_available / HIGH | +0.50 | +0.50 | +3.25 |
| bottom_escape / seeded / MEDIUM | +2.43 | +0.98 | +4.00 |
| bottom_escape / seeded / HIGH | +2.43 | +0.98 | +4.00 |
| bottom_trap_roll / first_available / MEDIUM | +3.75 | +2.00 | +4.00 |
| bottom_trap_roll / first_available / HIGH | +3.75 | +2.00 | +4.00 |
| bottom_trap_roll / seeded / MEDIUM | +2.79 | +1.48 | +4.00 |
| bottom_trap_roll / seeded / HIGH | +2.79 | +1.48 | +4.00 |
| seeded_legal / first_available / MEDIUM | +3.04 | +0.96 | +3.62 |
| seeded_legal / first_available / HIGH | +2.50 | +0.81 | +3.62 |
| seeded_legal / seeded / MEDIUM | +3.07 | +1.34 | +4.00 |
| seeded_legal / seeded / HIGH | +2.95 | +1.01 | +4.00 |

**No-progress sequences** (a window that leaves the positional fingerprint unchanged: Mount axis, band, setup tiers and submission stage; Half Guard axis, band and both readiness tiers)
| cell | longest no-progress streak (max) | mean | games with a streak of 10+ windows | policy errors | transitions checked | continuity violations |
|---|---|---|---|---|---|---|
| pass_only / first_available / MEDIUM | 54 | 54.0 | 1/1 | 0 | 0 | 0 |
| pass_only / first_available / HIGH | 54 | 54.0 | 1/1 | 0 | 0 | 0 |
| top_direct / first_available / MEDIUM | 29 | 29.0 | 1/1 | 0 | 0 | 0 |
| top_direct / first_available / HIGH | 13 | 13.0 | 1/1 | 0 | 0 | 0 |
| top_direct / seeded / MEDIUM | 9 | 4.9 | 0/30 | 0 | 0 | 0 |
| top_direct / seeded / HIGH | 11 | 4.5 | 1/30 | 0 | 0 | 0 |
| top_finish / first_available / MEDIUM | 29 | 29.0 | 1/1 | 0 | 0 | 0 |
| top_finish / first_available / HIGH | 13 | 13.0 | 1/1 | 0 | 0 | 0 |
| top_finish / seeded / MEDIUM | 11 | 4.6 | 1/30 | 0 | 0 | 0 |
| top_finish / seeded / HIGH | 11 | 3.5 | 1/30 | 0 | 0 | 0 |
| bottom_escape / first_available / MEDIUM | 27 | 27.0 | 1/1 | 0 | 1 | 0 |
| bottom_escape / first_available / HIGH | 27 | 27.0 | 1/1 | 0 | 1 | 0 |
| bottom_escape / seeded / MEDIUM | 15 | 8.8 | 11/30 | 0 | 6 | 0 |
| bottom_escape / seeded / HIGH | 15 | 8.8 | 11/30 | 0 | 6 | 0 |
| bottom_trap_roll / first_available / MEDIUM | 21 | 21.0 | 1/1 | 0 | 0 | 0 |
| bottom_trap_roll / first_available / HIGH | 21 | 21.0 | 1/1 | 0 | 0 | 0 |
| bottom_trap_roll / seeded / MEDIUM | 17 | 8.1 | 6/30 | 0 | 0 | 0 |
| bottom_trap_roll / seeded / HIGH | 17 | 8.1 | 6/30 | 0 | 0 | 0 |
| seeded_legal / first_available / MEDIUM | 57 | 11.9 | 6/30 | 0 | 5 | 0 |
| seeded_legal / first_available / HIGH | 57 | 13.9 | 8/30 | 0 | 7 | 0 |
| seeded_legal / seeded / MEDIUM | 18 | 7.2 | 8/30 | 0 | 2 | 0 |
| seeded_legal / seeded / HIGH | 23 | 7.6 | 5/30 | 0 | 4 | 0 |

## Population B — Half Guard from real Mount entries (5 entries x attackers x defenders x commitments)
POPULATION. Each entry is a REAL Mount escape taken through the graph (different stamina, interval and rule set); the Half Guard play starts at that real entry.

**Summary by policy** (all cells with the same policy pooled; percentages are of games)
| policy | games | ended by a tap | ended by the clock | halted at an unsupported exit | entered Half Guard | still active after the maximum windows | windows mean | exchanges mean | feints accepted | feints that bit | feints effective (grade >= Success) | feints punished (grade <= Failure) | fallbacks | games with a 10+ window no-progress streak | final axis mean | lowest / highest axis mean | unsupported-exit destinations (games) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| pass vs bite | 10 | 0 (0%) | 10 (100%) | 0 (0%) | 10 (100%) | 0 | 59.0 | 0.0 | 0 | - | - | - | 0 | 10 (100%) | +0.50 | +0.50 / +0.50 | - |
| pass vs call | 10 | 0 (0%) | 10 (100%) | 0 (0%) | 10 (100%) | 0 | 59.0 | 0.0 | 0 | - | - | - | 0 | 10 (100%) | +0.50 | +0.50 / +0.50 | - |
| pass vs balanced | 10 | 0 (0%) | 10 (100%) | 0 (0%) | 10 (100%) | 0 | 59.0 | 0.0 | 0 | - | - | - | 0 | 10 (100%) | +0.50 | +0.50 / +0.50 | - |
| pass vs fallback | 10 | 0 (0%) | 10 (100%) | 0 (0%) | 10 (100%) | 0 | 59.0 | 0.0 | 0 | - | - | - | 0 | 10 (100%) | +0.50 | +0.50 / +0.50 | - |
| pass vs seeded | 200 | 0 (0%) | 200 (100%) | 0 (0%) | 200 (100%) | 0 | 59.0 | 0.0 | 0 | - | - | - | 0 | 200 (100%) | +0.50 | +0.50 / +0.50 | - |
| direct_cycle vs bite | 10 | 0 (0%) | 2 (20%) | 8 (80%) | 10 (100%) | 0 | 16.6 | 16.6 | 0 | - | - | - | 0 | 2 (20%) | -0.80 | -2.30 / +2.10 | half_guard:Closed Guard 1, half_guard:Open Guard 3, half_guard:Side Control 4 |
| direct_cycle vs call | 10 | 0 (0%) | 2 (20%) | 8 (80%) | 10 (100%) | 0 | 15.3 | 15.3 | 0 | - | - | - | 0 | 2 (20%) | +1.40 | -0.15 / +3.35 | half_guard:Closed Guard 1, half_guard:Side Control 7 |
| direct_cycle vs balanced | 10 | 0 (0%) | 2 (20%) | 8 (80%) | 10 (100%) | 0 | 15.3 | 15.3 | 0 | - | - | - | 0 | 2 (20%) | +1.40 | -0.15 / +3.35 | half_guard:Closed Guard 1, half_guard:Side Control 7 |
| direct_cycle vs fallback | 10 | 0 (0%) | 4 (40%) | 6 (60%) | 10 (100%) | 0 | 28.2 | 28.2 | 0 | - | - | - | 282 | 0 (0%) | +0.60 | -0.30 / +3.10 | half_guard:Closed Guard 2, half_guard:Side Control 4 |
| direct_cycle vs seeded | 200 | 0 (0%) | 0 (0%) | 200 (100%) | 200 (100%) | 0 | 8.7 | 8.7 | 0 | - | - | - | 0 | 0 (0%) | +1.26 | -0.92 / +2.82 | half_guard:Closed Guard 40, half_guard:Open Guard 29, half_guard:Side Control 131 |
| feint_when_eligible vs bite | 10 | 0 (0%) | 4 (40%) | 6 (60%) | 10 (100%) | 0 | 27.2 | 27.2 | 34 | 34 (100%) | 34 (100%) | 0 (0%) | 0 | 1 (10%) | -1.80 | -2.65 / +2.95 | half_guard:Closed Guard 5, half_guard:Open Guard 1 |
| feint_when_eligible vs call | 10 | 0 (0%) | 7 (70%) | 3 (30%) | 10 (100%) | 0 | 43.0 | 43.0 | 39 | 0 (0%) | 6 (15%) | 28 (72%) | 0 | 7 (70%) | +4.00 | -2.00 / +4.00 | half_guard:Side Control 3 |
| feint_when_eligible vs balanced | 10 | 0 (0%) | 7 (70%) | 3 (30%) | 10 (100%) | 0 | 43.0 | 43.0 | 39 | 0 (0%) | 7 (18%) | 28 (72%) | 0 | 7 (70%) | +3.20 | -2.25 / +3.65 | half_guard:Side Control 3 |
| feint_when_eligible vs fallback | 10 | 0 (0%) | 7 (70%) | 3 (30%) | 10 (100%) | 0 | 42.9 | 42.9 | 26 | 0 (0%) | 24 (92%) | 0 (0%) | 429 | 7 (70%) | +3.20 | +0.35 / +3.85 | half_guard:Closed Guard 1, half_guard:Side Control 2 |
| feint_when_eligible vs seeded | 200 | 0 (0%) | 65 (32%) | 135 (68%) | 200 (100%) | 0 | 22.2 | 22.2 | 707 | 202 (29%) | 384 (54%) | 201 (28%) | 0 | 7 (4%) | +0.89 | -0.98 / +2.83 | half_guard:Closed Guard 52, half_guard:Open Guard 7, half_guard:Side Control 76 |
| prep_oriented vs bite | 10 | 0 (0%) | 2 (20%) | 8 (80%) | 10 (100%) | 0 | 17.6 | 17.6 | 0 | - | - | - | 0 | 0 (0%) | -0.10 | -1.60 / +1.90 | half_guard:Closed Guard 4, half_guard:Side Control 4 |
| prep_oriented vs call | 10 | 0 (0%) | 0 (0%) | 10 (100%) | 10 (100%) | 0 | 8.2 | 8.2 | 0 | - | - | - | 0 | 0 (0%) | -3.70 | -3.70 / +0.40 | half_guard:Closed Guard 4, half_guard:Open Guard 6 |
| prep_oriented vs balanced | 10 | 0 (0%) | 2 (20%) | 8 (80%) | 10 (100%) | 0 | 17.0 | 17.0 | 0 | - | - | - | 0 | 2 (20%) | -0.75 | -2.50 / +1.25 | half_guard:Closed Guard 2, half_guard:Open Guard 2, half_guard:Side Control 4 |
| prep_oriented vs fallback | 10 | 0 (0%) | 0 (0%) | 10 (100%) | 10 (100%) | 0 | 5.4 | 5.4 | 0 | - | - | - | 54 | 0 (0%) | -2.45 | -2.90 / +0.75 | half_guard:Closed Guard 8, half_guard:Side Control 2 |
| prep_oriented vs seeded | 200 | 0 (0%) | 0 (0%) | 200 (100%) | 200 (100%) | 0 | 6.8 | 6.8 | 0 | - | - | - | 0 | 0 (0%) | +1.89 | -0.14 / +3.12 | half_guard:Closed Guard 42, half_guard:Open Guard 9, half_guard:Side Control 149 |
| seeded_legal vs bite | 200 | 0 (0%) | 58 (29%) | 142 (71%) | 200 (100%) | 0 | 25.4 | 17.0 | 94 | 94 (100%) | 94 (100%) | 0 (0%) | 0 | 16 (8%) | +0.20 | -1.97 / +2.58 | half_guard:Closed Guard 30, half_guard:Open Guard 20, half_guard:Side Control 92 |
| seeded_legal vs call | 200 | 0 (0%) | 56 (28%) | 144 (72%) | 200 (100%) | 0 | 25.2 | 16.8 | 71 | 0 (0%) | 14 (20%) | 54 (76%) | 0 | 21 (10%) | -0.14 | -2.05 / +2.28 | half_guard:Closed Guard 30, half_guard:Open Guard 33, half_guard:Side Control 81 |
| seeded_legal vs balanced | 200 | 0 (0%) | 65 (32%) | 135 (68%) | 200 (100%) | 0 | 27.0 | 18.1 | 80 | 0 (0%) | 20 (25%) | 48 (60%) | 0 | 22 (11%) | +0.09 | -1.98 / +2.40 | half_guard:Closed Guard 34, half_guard:Open Guard 17, half_guard:Side Control 84 |
| seeded_legal vs fallback | 200 | 0 (0%) | 14 (7%) | 186 (93%) | 200 (100%) | 0 | 15.2 | 9.8 | 97 | 0 (0%) | 90 (93%) | 3 (3%) | 1958 | 9 (4%) | +0.64 | -1.14 / +2.84 | half_guard:Closed Guard 63, half_guard:Open Guard 18, half_guard:Side Control 105 |
| seeded_legal vs seeded | 200 | 0 (0%) | 5 (2%) | 195 (98%) | 200 (100%) | 0 | 12.8 | 8.6 | 148 | 42 (28%) | 82 (55%) | 46 (31%) | 0 | 0 (0%) | +2.17 | -0.27 / +3.40 | half_guard:Closed Guard 33, half_guard:Open Guard 10, half_guard:Side Control 152 |

**Outcomes (games per terminal class)** — `halt_*` is an unsupported-destination boundary, not a result
| cell | games | halt_half_guard:Closed Guard | halt_half_guard:Open Guard | halt_half_guard:Side Control | timeout_half_guard |
|---|---|---|---|---|---|
| entry 0 / pass / bite / MEDIUM | 1 | 0 | 0 | 0 | 1 |
| entry 0 / pass / bite / HIGH | 1 | 0 | 0 | 0 | 1 |
| entry 0 / pass / call / MEDIUM | 1 | 0 | 0 | 0 | 1 |
| entry 0 / pass / call / HIGH | 1 | 0 | 0 | 0 | 1 |
| entry 0 / pass / balanced / MEDIUM | 1 | 0 | 0 | 0 | 1 |
| entry 0 / pass / balanced / HIGH | 1 | 0 | 0 | 0 | 1 |
| entry 0 / pass / fallback / MEDIUM | 1 | 0 | 0 | 0 | 1 |
| entry 0 / pass / fallback / HIGH | 1 | 0 | 0 | 0 | 1 |
| entry 0 / pass / seeded / MEDIUM | 20 | 0 | 0 | 0 | 20 |
| entry 0 / pass / seeded / HIGH | 20 | 0 | 0 | 0 | 20 |
| entry 0 / direct_cycle / bite / MEDIUM | 1 | 0 | 0 | 0 | 1 |
| entry 0 / direct_cycle / bite / HIGH | 1 | 0 | 1 | 0 | 0 |
| entry 0 / direct_cycle / call / MEDIUM | 1 | 0 | 0 | 0 | 1 |
| entry 0 / direct_cycle / call / HIGH | 1 | 0 | 0 | 1 | 0 |
| entry 0 / direct_cycle / balanced / MEDIUM | 1 | 0 | 0 | 0 | 1 |
| entry 0 / direct_cycle / balanced / HIGH | 1 | 0 | 0 | 1 | 0 |
| entry 0 / direct_cycle / fallback / MEDIUM | 1 | 0 | 0 | 0 | 1 |
| entry 0 / direct_cycle / fallback / HIGH | 1 | 0 | 0 | 0 | 1 |
| entry 0 / direct_cycle / seeded / MEDIUM | 20 | 4 | 5 | 11 | 0 |
| entry 0 / direct_cycle / seeded / HIGH | 20 | 6 | 3 | 11 | 0 |
| entry 0 / feint_when_eligible / bite / MEDIUM | 1 | 1 | 0 | 0 | 0 |
| entry 0 / feint_when_eligible / bite / HIGH | 1 | 1 | 0 | 0 | 0 |
| entry 0 / feint_when_eligible / call / MEDIUM | 1 | 0 | 0 | 0 | 1 |
| entry 0 / feint_when_eligible / call / HIGH | 1 | 0 | 0 | 0 | 1 |
| entry 0 / feint_when_eligible / balanced / MEDIUM | 1 | 0 | 0 | 0 | 1 |
| entry 0 / feint_when_eligible / balanced / HIGH | 1 | 0 | 0 | 0 | 1 |
| entry 0 / feint_when_eligible / fallback / MEDIUM | 1 | 0 | 0 | 0 | 1 |
| entry 0 / feint_when_eligible / fallback / HIGH | 1 | 0 | 0 | 0 | 1 |
| entry 0 / feint_when_eligible / seeded / MEDIUM | 20 | 6 | 0 | 6 | 8 |
| entry 0 / feint_when_eligible / seeded / HIGH | 20 | 6 | 0 | 5 | 9 |
| entry 0 / prep_oriented / bite / MEDIUM | 1 | 0 | 0 | 0 | 1 |
| entry 0 / prep_oriented / bite / HIGH | 1 | 1 | 0 | 0 | 0 |
| entry 0 / prep_oriented / call / MEDIUM | 1 | 0 | 1 | 0 | 0 |
| entry 0 / prep_oriented / call / HIGH | 1 | 1 | 0 | 0 | 0 |
| entry 0 / prep_oriented / balanced / MEDIUM | 1 | 0 | 0 | 0 | 1 |
| entry 0 / prep_oriented / balanced / HIGH | 1 | 1 | 0 | 0 | 0 |
| entry 0 / prep_oriented / fallback / MEDIUM | 1 | 1 | 0 | 0 | 0 |
| entry 0 / prep_oriented / fallback / HIGH | 1 | 1 | 0 | 0 | 0 |
| entry 0 / prep_oriented / seeded / MEDIUM | 20 | 4 | 1 | 15 | 0 |
| entry 0 / prep_oriented / seeded / HIGH | 20 | 3 | 1 | 16 | 0 |
| entry 0 / seeded_legal / bite / MEDIUM | 20 | 0 | 3 | 2 | 15 |
| entry 0 / seeded_legal / bite / HIGH | 20 | 2 | 6 | 3 | 9 |
| entry 0 / seeded_legal / call / MEDIUM | 20 | 0 | 4 | 0 | 16 |
| entry 0 / seeded_legal / call / HIGH | 20 | 5 | 4 | 6 | 5 |
| entry 0 / seeded_legal / balanced / MEDIUM | 20 | 0 | 1 | 0 | 19 |
| entry 0 / seeded_legal / balanced / HIGH | 20 | 2 | 7 | 5 | 6 |
| entry 0 / seeded_legal / fallback / MEDIUM | 20 | 8 | 2 | 9 | 1 |
| entry 0 / seeded_legal / fallback / HIGH | 20 | 9 | 3 | 5 | 3 |
| entry 0 / seeded_legal / seeded / MEDIUM | 20 | 3 | 0 | 16 | 1 |
| entry 0 / seeded_legal / seeded / HIGH | 20 | 3 | 2 | 14 | 1 |
| entry 1 / pass / bite / MEDIUM | 1 | 0 | 0 | 0 | 1 |
| entry 1 / pass / bite / HIGH | 1 | 0 | 0 | 0 | 1 |
| entry 1 / pass / call / MEDIUM | 1 | 0 | 0 | 0 | 1 |
| entry 1 / pass / call / HIGH | 1 | 0 | 0 | 0 | 1 |
| entry 1 / pass / balanced / MEDIUM | 1 | 0 | 0 | 0 | 1 |
| entry 1 / pass / balanced / HIGH | 1 | 0 | 0 | 0 | 1 |
| entry 1 / pass / fallback / MEDIUM | 1 | 0 | 0 | 0 | 1 |
| entry 1 / pass / fallback / HIGH | 1 | 0 | 0 | 0 | 1 |
| entry 1 / pass / seeded / MEDIUM | 20 | 0 | 0 | 0 | 20 |
| entry 1 / pass / seeded / HIGH | 20 | 0 | 0 | 0 | 20 |
| entry 1 / direct_cycle / bite / MEDIUM | 1 | 0 | 0 | 1 | 0 |
| entry 1 / direct_cycle / bite / HIGH | 1 | 0 | 0 | 1 | 0 |
| entry 1 / direct_cycle / call / MEDIUM | 1 | 0 | 0 | 1 | 0 |
| entry 1 / direct_cycle / call / HIGH | 1 | 0 | 0 | 1 | 0 |
| entry 1 / direct_cycle / balanced / MEDIUM | 1 | 0 | 0 | 1 | 0 |
| entry 1 / direct_cycle / balanced / HIGH | 1 | 0 | 0 | 1 | 0 |
| entry 1 / direct_cycle / fallback / MEDIUM | 1 | 0 | 0 | 1 | 0 |
| entry 1 / direct_cycle / fallback / HIGH | 1 | 0 | 0 | 1 | 0 |
| entry 1 / direct_cycle / seeded / MEDIUM | 20 | 0 | 0 | 20 | 0 |
| entry 1 / direct_cycle / seeded / HIGH | 20 | 3 | 0 | 17 | 0 |
| entry 1 / feint_when_eligible / bite / MEDIUM | 1 | 0 | 1 | 0 | 0 |
| entry 1 / feint_when_eligible / bite / HIGH | 1 | 0 | 0 | 0 | 1 |
| entry 1 / feint_when_eligible / call / MEDIUM | 1 | 0 | 0 | 0 | 1 |
| entry 1 / feint_when_eligible / call / HIGH | 1 | 0 | 0 | 1 | 0 |
| entry 1 / feint_when_eligible / balanced / MEDIUM | 1 | 0 | 0 | 0 | 1 |
| entry 1 / feint_when_eligible / balanced / HIGH | 1 | 0 | 0 | 1 | 0 |
| entry 1 / feint_when_eligible / fallback / MEDIUM | 1 | 0 | 0 | 0 | 1 |
| entry 1 / feint_when_eligible / fallback / HIGH | 1 | 0 | 0 | 0 | 1 |
| entry 1 / feint_when_eligible / seeded / MEDIUM | 20 | 4 | 1 | 7 | 8 |
| entry 1 / feint_when_eligible / seeded / HIGH | 20 | 4 | 0 | 6 | 10 |
| entry 1 / prep_oriented / bite / MEDIUM | 1 | 0 | 0 | 1 | 0 |
| entry 1 / prep_oriented / bite / HIGH | 1 | 0 | 0 | 1 | 0 |
| entry 1 / prep_oriented / call / MEDIUM | 1 | 0 | 1 | 0 | 0 |
| entry 1 / prep_oriented / call / HIGH | 1 | 1 | 0 | 0 | 0 |
| entry 1 / prep_oriented / balanced / MEDIUM | 1 | 0 | 0 | 1 | 0 |
| entry 1 / prep_oriented / balanced / HIGH | 1 | 0 | 0 | 1 | 0 |
| entry 1 / prep_oriented / fallback / MEDIUM | 1 | 1 | 0 | 0 | 0 |
| entry 1 / prep_oriented / fallback / HIGH | 1 | 1 | 0 | 0 | 0 |
| entry 1 / prep_oriented / seeded / MEDIUM | 20 | 3 | 0 | 17 | 0 |
| entry 1 / prep_oriented / seeded / HIGH | 20 | 2 | 1 | 17 | 0 |
| entry 1 / seeded_legal / bite / MEDIUM | 20 | 0 | 0 | 20 | 0 |
| entry 1 / seeded_legal / bite / HIGH | 20 | 0 | 0 | 18 | 2 |
| entry 1 / seeded_legal / call / MEDIUM | 20 | 0 | 2 | 15 | 3 |
| entry 1 / seeded_legal / call / HIGH | 20 | 0 | 3 | 15 | 2 |
| entry 1 / seeded_legal / balanced / MEDIUM | 20 | 0 | 0 | 18 | 2 |
| entry 1 / seeded_legal / balanced / HIGH | 20 | 0 | 1 | 16 | 3 |
| entry 1 / seeded_legal / fallback / MEDIUM | 20 | 3 | 0 | 17 | 0 |
| entry 1 / seeded_legal / fallback / HIGH | 20 | 3 | 1 | 16 | 0 |
| entry 1 / seeded_legal / seeded / MEDIUM | 20 | 1 | 0 | 19 | 0 |
| entry 1 / seeded_legal / seeded / HIGH | 20 | 1 | 1 | 17 | 1 |
| entry 2 / pass / bite / MEDIUM | 1 | 0 | 0 | 0 | 1 |
| entry 2 / pass / bite / HIGH | 1 | 0 | 0 | 0 | 1 |
| entry 2 / pass / call / MEDIUM | 1 | 0 | 0 | 0 | 1 |
| entry 2 / pass / call / HIGH | 1 | 0 | 0 | 0 | 1 |
| entry 2 / pass / balanced / MEDIUM | 1 | 0 | 0 | 0 | 1 |
| entry 2 / pass / balanced / HIGH | 1 | 0 | 0 | 0 | 1 |
| entry 2 / pass / fallback / MEDIUM | 1 | 0 | 0 | 0 | 1 |
| entry 2 / pass / fallback / HIGH | 1 | 0 | 0 | 0 | 1 |
| entry 2 / pass / seeded / MEDIUM | 20 | 0 | 0 | 0 | 20 |
| entry 2 / pass / seeded / HIGH | 20 | 0 | 0 | 0 | 20 |
| entry 2 / direct_cycle / bite / MEDIUM | 1 | 0 | 0 | 1 | 0 |
| entry 2 / direct_cycle / bite / HIGH | 1 | 0 | 0 | 1 | 0 |
| entry 2 / direct_cycle / call / MEDIUM | 1 | 0 | 0 | 1 | 0 |
| entry 2 / direct_cycle / call / HIGH | 1 | 0 | 0 | 1 | 0 |
| entry 2 / direct_cycle / balanced / MEDIUM | 1 | 0 | 0 | 1 | 0 |
| entry 2 / direct_cycle / balanced / HIGH | 1 | 0 | 0 | 1 | 0 |
| entry 2 / direct_cycle / fallback / MEDIUM | 1 | 0 | 0 | 1 | 0 |
| entry 2 / direct_cycle / fallback / HIGH | 1 | 0 | 0 | 1 | 0 |
| entry 2 / direct_cycle / seeded / MEDIUM | 20 | 0 | 0 | 20 | 0 |
| entry 2 / direct_cycle / seeded / HIGH | 20 | 0 | 0 | 20 | 0 |
| entry 2 / feint_when_eligible / bite / MEDIUM | 1 | 0 | 0 | 0 | 1 |
| entry 2 / feint_when_eligible / bite / HIGH | 1 | 0 | 0 | 0 | 1 |
| entry 2 / feint_when_eligible / call / MEDIUM | 1 | 0 | 0 | 1 | 0 |
| entry 2 / feint_when_eligible / call / HIGH | 1 | 0 | 0 | 1 | 0 |
| entry 2 / feint_when_eligible / balanced / MEDIUM | 1 | 0 | 0 | 1 | 0 |
| entry 2 / feint_when_eligible / balanced / HIGH | 1 | 0 | 0 | 1 | 0 |
| entry 2 / feint_when_eligible / fallback / MEDIUM | 1 | 0 | 0 | 1 | 0 |
| entry 2 / feint_when_eligible / fallback / HIGH | 1 | 0 | 0 | 1 | 0 |
| entry 2 / feint_when_eligible / seeded / MEDIUM | 20 | 0 | 0 | 19 | 1 |
| entry 2 / feint_when_eligible / seeded / HIGH | 20 | 0 | 0 | 19 | 1 |
| entry 2 / prep_oriented / bite / MEDIUM | 1 | 0 | 0 | 1 | 0 |
| entry 2 / prep_oriented / bite / HIGH | 1 | 0 | 0 | 1 | 0 |
| entry 2 / prep_oriented / call / MEDIUM | 1 | 0 | 1 | 0 | 0 |
| entry 2 / prep_oriented / call / HIGH | 1 | 0 | 1 | 0 | 0 |
| entry 2 / prep_oriented / balanced / MEDIUM | 1 | 0 | 0 | 1 | 0 |
| entry 2 / prep_oriented / balanced / HIGH | 1 | 0 | 0 | 1 | 0 |
| entry 2 / prep_oriented / fallback / MEDIUM | 1 | 0 | 0 | 1 | 0 |
| entry 2 / prep_oriented / fallback / HIGH | 1 | 0 | 0 | 1 | 0 |
| entry 2 / prep_oriented / seeded / MEDIUM | 20 | 0 | 0 | 20 | 0 |
| entry 2 / prep_oriented / seeded / HIGH | 20 | 0 | 0 | 20 | 0 |
| entry 2 / seeded_legal / bite / MEDIUM | 20 | 0 | 0 | 20 | 0 |
| entry 2 / seeded_legal / bite / HIGH | 20 | 0 | 0 | 20 | 0 |
| entry 2 / seeded_legal / call / MEDIUM | 20 | 0 | 0 | 20 | 0 |
| entry 2 / seeded_legal / call / HIGH | 20 | 0 | 0 | 20 | 0 |
| entry 2 / seeded_legal / balanced / MEDIUM | 20 | 0 | 0 | 20 | 0 |
| entry 2 / seeded_legal / balanced / HIGH | 20 | 0 | 0 | 20 | 0 |
| entry 2 / seeded_legal / fallback / MEDIUM | 20 | 0 | 0 | 20 | 0 |
| entry 2 / seeded_legal / fallback / HIGH | 20 | 0 | 0 | 20 | 0 |
| entry 2 / seeded_legal / seeded / MEDIUM | 20 | 0 | 0 | 20 | 0 |
| entry 2 / seeded_legal / seeded / HIGH | 20 | 0 | 0 | 20 | 0 |
| entry 3 / pass / bite / MEDIUM | 1 | 0 | 0 | 0 | 1 |
| entry 3 / pass / bite / HIGH | 1 | 0 | 0 | 0 | 1 |
| entry 3 / pass / call / MEDIUM | 1 | 0 | 0 | 0 | 1 |
| entry 3 / pass / call / HIGH | 1 | 0 | 0 | 0 | 1 |
| entry 3 / pass / balanced / MEDIUM | 1 | 0 | 0 | 0 | 1 |
| entry 3 / pass / balanced / HIGH | 1 | 0 | 0 | 0 | 1 |
| entry 3 / pass / fallback / MEDIUM | 1 | 0 | 0 | 0 | 1 |
| entry 3 / pass / fallback / HIGH | 1 | 0 | 0 | 0 | 1 |
| entry 3 / pass / seeded / MEDIUM | 20 | 0 | 0 | 0 | 20 |
| entry 3 / pass / seeded / HIGH | 20 | 0 | 0 | 0 | 20 |
| entry 3 / direct_cycle / bite / MEDIUM | 1 | 0 | 1 | 0 | 0 |
| entry 3 / direct_cycle / bite / HIGH | 1 | 1 | 0 | 0 | 0 |
| entry 3 / direct_cycle / call / MEDIUM | 1 | 1 | 0 | 0 | 0 |
| entry 3 / direct_cycle / call / HIGH | 1 | 0 | 0 | 1 | 0 |
| entry 3 / direct_cycle / balanced / MEDIUM | 1 | 1 | 0 | 0 | 0 |
| entry 3 / direct_cycle / balanced / HIGH | 1 | 0 | 0 | 1 | 0 |
| entry 3 / direct_cycle / fallback / MEDIUM | 1 | 1 | 0 | 0 | 0 |
| entry 3 / direct_cycle / fallback / HIGH | 1 | 1 | 0 | 0 | 0 |
| entry 3 / direct_cycle / seeded / MEDIUM | 20 | 10 | 6 | 4 | 0 |
| entry 3 / direct_cycle / seeded / HIGH | 20 | 11 | 4 | 5 | 0 |
| entry 3 / feint_when_eligible / bite / MEDIUM | 1 | 1 | 0 | 0 | 0 |
| entry 3 / feint_when_eligible / bite / HIGH | 1 | 1 | 0 | 0 | 0 |
| entry 3 / feint_when_eligible / call / MEDIUM | 1 | 0 | 0 | 0 | 1 |
| entry 3 / feint_when_eligible / call / HIGH | 1 | 0 | 0 | 0 | 1 |
| entry 3 / feint_when_eligible / balanced / MEDIUM | 1 | 0 | 0 | 0 | 1 |
| entry 3 / feint_when_eligible / balanced / HIGH | 1 | 0 | 0 | 0 | 1 |
| entry 3 / feint_when_eligible / fallback / MEDIUM | 1 | 0 | 0 | 0 | 1 |
| entry 3 / feint_when_eligible / fallback / HIGH | 1 | 1 | 0 | 0 | 0 |
| entry 3 / feint_when_eligible / seeded / MEDIUM | 20 | 12 | 4 | 3 | 1 |
| entry 3 / feint_when_eligible / seeded / HIGH | 20 | 11 | 2 | 3 | 4 |
| entry 3 / prep_oriented / bite / MEDIUM | 1 | 1 | 0 | 0 | 0 |
| entry 3 / prep_oriented / bite / HIGH | 1 | 1 | 0 | 0 | 0 |
| entry 3 / prep_oriented / call / MEDIUM | 1 | 0 | 1 | 0 | 0 |
| entry 3 / prep_oriented / call / HIGH | 1 | 1 | 0 | 0 | 0 |
| entry 3 / prep_oriented / balanced / MEDIUM | 1 | 1 | 0 | 0 | 0 |
| entry 3 / prep_oriented / balanced / HIGH | 1 | 0 | 1 | 0 | 0 |
| entry 3 / prep_oriented / fallback / MEDIUM | 1 | 1 | 0 | 0 | 0 |
| entry 3 / prep_oriented / fallback / HIGH | 1 | 1 | 0 | 0 | 0 |
| entry 3 / prep_oriented / seeded / MEDIUM | 20 | 13 | 0 | 7 | 0 |
| entry 3 / prep_oriented / seeded / HIGH | 20 | 10 | 1 | 9 | 0 |
| entry 3 / seeded_legal / bite / MEDIUM | 20 | 12 | 6 | 2 | 0 |
| entry 3 / seeded_legal / bite / HIGH | 20 | 16 | 2 | 2 | 0 |
| entry 3 / seeded_legal / call / MEDIUM | 20 | 13 | 6 | 0 | 1 |
| entry 3 / seeded_legal / call / HIGH | 20 | 12 | 5 | 2 | 1 |
| entry 3 / seeded_legal / balanced / MEDIUM | 20 | 15 | 4 | 0 | 1 |
| entry 3 / seeded_legal / balanced / HIGH | 20 | 16 | 1 | 2 | 1 |
| entry 3 / seeded_legal / fallback / MEDIUM | 20 | 14 | 0 | 6 | 0 |
| entry 3 / seeded_legal / fallback / HIGH | 20 | 16 | 1 | 3 | 0 |
| entry 3 / seeded_legal / seeded / MEDIUM | 20 | 10 | 2 | 8 | 0 |
| entry 3 / seeded_legal / seeded / HIGH | 20 | 11 | 0 | 9 | 0 |
| entry 4 / pass / bite / MEDIUM | 1 | 0 | 0 | 0 | 1 |
| entry 4 / pass / bite / HIGH | 1 | 0 | 0 | 0 | 1 |
| entry 4 / pass / call / MEDIUM | 1 | 0 | 0 | 0 | 1 |
| entry 4 / pass / call / HIGH | 1 | 0 | 0 | 0 | 1 |
| entry 4 / pass / balanced / MEDIUM | 1 | 0 | 0 | 0 | 1 |
| entry 4 / pass / balanced / HIGH | 1 | 0 | 0 | 0 | 1 |
| entry 4 / pass / fallback / MEDIUM | 1 | 0 | 0 | 0 | 1 |
| entry 4 / pass / fallback / HIGH | 1 | 0 | 0 | 0 | 1 |
| entry 4 / pass / seeded / MEDIUM | 20 | 0 | 0 | 0 | 20 |
| entry 4 / pass / seeded / HIGH | 20 | 0 | 0 | 0 | 20 |
| entry 4 / direct_cycle / bite / MEDIUM | 1 | 0 | 0 | 0 | 1 |
| entry 4 / direct_cycle / bite / HIGH | 1 | 0 | 1 | 0 | 0 |
| entry 4 / direct_cycle / call / MEDIUM | 1 | 0 | 0 | 0 | 1 |
| entry 4 / direct_cycle / call / HIGH | 1 | 0 | 0 | 1 | 0 |
| entry 4 / direct_cycle / balanced / MEDIUM | 1 | 0 | 0 | 0 | 1 |
| entry 4 / direct_cycle / balanced / HIGH | 1 | 0 | 0 | 1 | 0 |
| entry 4 / direct_cycle / fallback / MEDIUM | 1 | 0 | 0 | 0 | 1 |
| entry 4 / direct_cycle / fallback / HIGH | 1 | 0 | 0 | 0 | 1 |
| entry 4 / direct_cycle / seeded / MEDIUM | 20 | 1 | 7 | 12 | 0 |
| entry 4 / direct_cycle / seeded / HIGH | 20 | 5 | 4 | 11 | 0 |
| entry 4 / feint_when_eligible / bite / MEDIUM | 1 | 1 | 0 | 0 | 0 |
| entry 4 / feint_when_eligible / bite / HIGH | 1 | 0 | 0 | 0 | 1 |
| entry 4 / feint_when_eligible / call / MEDIUM | 1 | 0 | 0 | 0 | 1 |
| entry 4 / feint_when_eligible / call / HIGH | 1 | 0 | 0 | 0 | 1 |
| entry 4 / feint_when_eligible / balanced / MEDIUM | 1 | 0 | 0 | 0 | 1 |
| entry 4 / feint_when_eligible / balanced / HIGH | 1 | 0 | 0 | 0 | 1 |
| entry 4 / feint_when_eligible / fallback / MEDIUM | 1 | 0 | 0 | 0 | 1 |
| entry 4 / feint_when_eligible / fallback / HIGH | 1 | 0 | 0 | 0 | 1 |
| entry 4 / feint_when_eligible / seeded / MEDIUM | 20 | 5 | 0 | 5 | 10 |
| entry 4 / feint_when_eligible / seeded / HIGH | 20 | 4 | 0 | 3 | 13 |
| entry 4 / prep_oriented / bite / MEDIUM | 1 | 0 | 0 | 0 | 1 |
| entry 4 / prep_oriented / bite / HIGH | 1 | 1 | 0 | 0 | 0 |
| entry 4 / prep_oriented / call / MEDIUM | 1 | 0 | 1 | 0 | 0 |
| entry 4 / prep_oriented / call / HIGH | 1 | 1 | 0 | 0 | 0 |
| entry 4 / prep_oriented / balanced / MEDIUM | 1 | 0 | 0 | 0 | 1 |
| entry 4 / prep_oriented / balanced / HIGH | 1 | 0 | 1 | 0 | 0 |
| entry 4 / prep_oriented / fallback / MEDIUM | 1 | 1 | 0 | 0 | 0 |
| entry 4 / prep_oriented / fallback / HIGH | 1 | 1 | 0 | 0 | 0 |
| entry 4 / prep_oriented / seeded / MEDIUM | 20 | 3 | 1 | 16 | 0 |
| entry 4 / prep_oriented / seeded / HIGH | 20 | 4 | 4 | 12 | 0 |
| entry 4 / seeded_legal / bite / MEDIUM | 20 | 0 | 0 | 2 | 18 |
| entry 4 / seeded_legal / bite / HIGH | 20 | 0 | 3 | 3 | 14 |
| entry 4 / seeded_legal / call / MEDIUM | 20 | 0 | 4 | 0 | 16 |
| entry 4 / seeded_legal / call / HIGH | 20 | 0 | 5 | 3 | 12 |
| entry 4 / seeded_legal / balanced / MEDIUM | 20 | 0 | 0 | 0 | 20 |
| entry 4 / seeded_legal / balanced / HIGH | 20 | 1 | 3 | 3 | 13 |
| entry 4 / seeded_legal / fallback / MEDIUM | 20 | 4 | 4 | 6 | 6 |
| entry 4 / seeded_legal / fallback / HIGH | 20 | 6 | 7 | 3 | 4 |
| entry 4 / seeded_legal / seeded / MEDIUM | 20 | 2 | 1 | 15 | 2 |
| entry 4 / seeded_legal / seeded / HIGH | 20 | 2 | 4 | 14 | 0 |

**Time, entry and position time** (means over the cell's games; seconds are simulated clock seconds)
| cell | windows mean (min-max) | seconds mean | entered Half Guard | mean entry window | Mount windows mean | Half Guard windows mean | exchanges mean | passes mean | D3-B holds mean | longest pass streak max | longest idle streak max |
|---|---|---|---|---|---|---|---|---|---|---|---|
| entry 0 / pass / bite / MEDIUM | 59.0 (59-59) | 300.0 | 1/1 | 0.0 | 0.0 | 59.0 | 0.0 | 59.0 | 0.0 | 59 | 59 |
| entry 0 / pass / bite / HIGH | 59.0 (59-59) | 300.0 | 1/1 | 0.0 | 0.0 | 59.0 | 0.0 | 59.0 | 0.0 | 59 | 59 |
| entry 0 / pass / call / MEDIUM | 59.0 (59-59) | 300.0 | 1/1 | 0.0 | 0.0 | 59.0 | 0.0 | 59.0 | 0.0 | 59 | 59 |
| entry 0 / pass / call / HIGH | 59.0 (59-59) | 300.0 | 1/1 | 0.0 | 0.0 | 59.0 | 0.0 | 59.0 | 0.0 | 59 | 59 |
| entry 0 / pass / balanced / MEDIUM | 59.0 (59-59) | 300.0 | 1/1 | 0.0 | 0.0 | 59.0 | 0.0 | 59.0 | 0.0 | 59 | 59 |
| entry 0 / pass / balanced / HIGH | 59.0 (59-59) | 300.0 | 1/1 | 0.0 | 0.0 | 59.0 | 0.0 | 59.0 | 0.0 | 59 | 59 |
| entry 0 / pass / fallback / MEDIUM | 59.0 (59-59) | 300.0 | 1/1 | 0.0 | 0.0 | 59.0 | 0.0 | 59.0 | 0.0 | 59 | 59 |
| entry 0 / pass / fallback / HIGH | 59.0 (59-59) | 300.0 | 1/1 | 0.0 | 0.0 | 59.0 | 0.0 | 59.0 | 0.0 | 59 | 59 |
| entry 0 / pass / seeded / MEDIUM | 59.0 (59-59) | 300.0 | 20/20 | 0.0 | 0.0 | 59.0 | 0.0 | 59.0 | 0.0 | 59 | 59 |
| entry 0 / pass / seeded / HIGH | 59.0 (59-59) | 300.0 | 20/20 | 0.0 | 0.0 | 59.0 | 0.0 | 59.0 | 0.0 | 59 | 59 |
| entry 0 / direct_cycle / bite / MEDIUM | 59.0 (59-59) | 300.0 | 1/1 | 0.0 | 0.0 | 59.0 | 59.0 | 0.0 | 0.0 | 0 | 0 |
| entry 0 / direct_cycle / bite / HIGH | 6.0 (6-6) | 30.0 | 1/1 | 0.0 | 0.0 | 6.0 | 6.0 | 0.0 | 0.0 | 0 | 0 |
| entry 0 / direct_cycle / call / MEDIUM | 59.0 (59-59) | 300.0 | 1/1 | 0.0 | 0.0 | 59.0 | 59.0 | 0.0 | 0.0 | 0 | 0 |
| entry 0 / direct_cycle / call / HIGH | 3.0 (3-3) | 15.0 | 1/1 | 0.0 | 0.0 | 3.0 | 3.0 | 0.0 | 0.0 | 0 | 0 |
| entry 0 / direct_cycle / balanced / MEDIUM | 59.0 (59-59) | 300.0 | 1/1 | 0.0 | 0.0 | 59.0 | 59.0 | 0.0 | 0.0 | 0 | 0 |
| entry 0 / direct_cycle / balanced / HIGH | 3.0 (3-3) | 15.0 | 1/1 | 0.0 | 0.0 | 3.0 | 3.0 | 0.0 | 0.0 | 0 | 0 |
| entry 0 / direct_cycle / fallback / MEDIUM | 59.0 (59-59) | 300.0 | 1/1 | 0.0 | 0.0 | 59.0 | 59.0 | 0.0 | 0.0 | 0 | 0 |
| entry 0 / direct_cycle / fallback / HIGH | 59.0 (59-59) | 300.0 | 1/1 | 0.0 | 0.0 | 59.0 | 59.0 | 0.0 | 0.0 | 0 | 0 |
| entry 0 / direct_cycle / seeded / MEDIUM | 8.4 (3-16) | 42.2 | 20/20 | 0.0 | 0.0 | 8.4 | 8.4 | 0.0 | 0.0 | 0 | 0 |
| entry 0 / direct_cycle / seeded / HIGH | 12.3 (2-45) | 61.8 | 20/20 | 0.0 | 0.0 | 12.3 | 12.3 | 0.0 | 0.0 | 0 | 0 |
| entry 0 / feint_when_eligible / bite / MEDIUM | 6.0 (6-6) | 30.0 | 1/1 | 0.0 | 0.0 | 6.0 | 6.0 | 0.0 | 0.0 | 0 | 0 |
| entry 0 / feint_when_eligible / bite / HIGH | 6.0 (6-6) | 30.0 | 1/1 | 0.0 | 0.0 | 6.0 | 6.0 | 0.0 | 0.0 | 0 | 0 |
| entry 0 / feint_when_eligible / call / MEDIUM | 59.0 (59-59) | 300.0 | 1/1 | 0.0 | 0.0 | 59.0 | 59.0 | 0.0 | 0.0 | 0 | 0 |
| entry 0 / feint_when_eligible / call / HIGH | 59.0 (59-59) | 300.0 | 1/1 | 0.0 | 0.0 | 59.0 | 59.0 | 0.0 | 0.0 | 0 | 0 |
| entry 0 / feint_when_eligible / balanced / MEDIUM | 59.0 (59-59) | 300.0 | 1/1 | 0.0 | 0.0 | 59.0 | 59.0 | 0.0 | 0.0 | 0 | 0 |
| entry 0 / feint_when_eligible / balanced / HIGH | 59.0 (59-59) | 300.0 | 1/1 | 0.0 | 0.0 | 59.0 | 59.0 | 0.0 | 0.0 | 0 | 0 |
| entry 0 / feint_when_eligible / fallback / MEDIUM | 59.0 (59-59) | 300.0 | 1/1 | 0.0 | 0.0 | 59.0 | 59.0 | 0.0 | 0.0 | 0 | 0 |
| entry 0 / feint_when_eligible / fallback / HIGH | 59.0 (59-59) | 300.0 | 1/1 | 0.0 | 0.0 | 59.0 | 59.0 | 0.0 | 0.0 | 0 | 0 |
| entry 0 / feint_when_eligible / seeded / MEDIUM | 26.3 (2-59) | 133.5 | 20/20 | 0.0 | 0.0 | 26.3 | 26.3 | 0.0 | 0.0 | 0 | 0 |
| entry 0 / feint_when_eligible / seeded / HIGH | 28.8 (2-59) | 146.2 | 20/20 | 0.0 | 0.0 | 28.8 | 28.8 | 0.0 | 0.0 | 0 | 0 |
| entry 0 / prep_oriented / bite / MEDIUM | 59.0 (59-59) | 300.0 | 1/1 | 0.0 | 0.0 | 59.0 | 59.0 | 0.0 | 0.0 | 0 | 0 |
| entry 0 / prep_oriented / bite / HIGH | 10.0 (10-10) | 50.0 | 1/1 | 0.0 | 0.0 | 10.0 | 10.0 | 0.0 | 0.0 | 0 | 0 |
| entry 0 / prep_oriented / call / MEDIUM | 4.0 (4-4) | 20.0 | 1/1 | 0.0 | 0.0 | 4.0 | 4.0 | 0.0 | 0.0 | 0 | 0 |
| entry 0 / prep_oriented / call / HIGH | 4.0 (4-4) | 20.0 | 1/1 | 0.0 | 0.0 | 4.0 | 4.0 | 0.0 | 0.0 | 0 | 0 |
| entry 0 / prep_oriented / balanced / MEDIUM | 59.0 (59-59) | 300.0 | 1/1 | 0.0 | 0.0 | 59.0 | 59.0 | 0.0 | 0.0 | 0 | 0 |
| entry 0 / prep_oriented / balanced / HIGH | 8.0 (8-8) | 40.0 | 1/1 | 0.0 | 0.0 | 8.0 | 8.0 | 0.0 | 0.0 | 0 | 0 |
| entry 0 / prep_oriented / fallback / MEDIUM | 8.0 (8-8) | 40.0 | 1/1 | 0.0 | 0.0 | 8.0 | 8.0 | 0.0 | 0.0 | 0 | 0 |
| entry 0 / prep_oriented / fallback / HIGH | 4.0 (4-4) | 20.0 | 1/1 | 0.0 | 0.0 | 4.0 | 4.0 | 0.0 | 0.0 | 0 | 0 |
| entry 0 / prep_oriented / seeded / MEDIUM | 8.8 (3-29) | 44.2 | 20/20 | 0.0 | 0.0 | 8.8 | 8.8 | 0.0 | 0.0 | 0 | 0 |
| entry 0 / prep_oriented / seeded / HIGH | 8.3 (3-41) | 41.5 | 20/20 | 0.0 | 0.0 | 8.3 | 8.3 | 0.0 | 0.0 | 0 | 0 |
| entry 0 / seeded_legal / bite / MEDIUM | 48.2 (7-59) | 245.0 | 20/20 | 0.0 | 0.0 | 48.2 | 32.9 | 15.3 | 0.0 | 5 | 5 |
| entry 0 / seeded_legal / bite / HIGH | 32.8 (6-59) | 166.2 | 20/20 | 0.0 | 0.0 | 32.8 | 22.1 | 10.7 | 0.0 | 5 | 5 |
| entry 0 / seeded_legal / call / MEDIUM | 49.7 (12-59) | 252.5 | 20/20 | 0.0 | 0.0 | 49.7 | 34.0 | 15.7 | 0.0 | 4 | 4 |
| entry 0 / seeded_legal / call / HIGH | 24.8 (3-59) | 125.0 | 20/20 | 0.0 | 0.0 | 24.8 | 15.8 | 8.9 | 0.0 | 4 | 4 |
| entry 0 / seeded_legal / balanced / MEDIUM | 57.0 (20-59) | 290.0 | 20/20 | 0.0 | 0.0 | 57.0 | 39.4 | 17.6 | 0.0 | 5 | 5 |
| entry 0 / seeded_legal / balanced / HIGH | 26.8 (3-59) | 135.2 | 20/20 | 0.0 | 0.0 | 26.8 | 17.1 | 9.7 | 0.0 | 5 | 5 |
| entry 0 / seeded_legal / fallback / MEDIUM | 18.0 (3-59) | 90.2 | 20/20 | 0.0 | 0.0 | 18.0 | 11.7 | 6.3 | 0.0 | 5 | 5 |
| entry 0 / seeded_legal / fallback / HIGH | 19.6 (3-59) | 98.8 | 20/20 | 0.0 | 0.0 | 19.6 | 12.5 | 7.1 | 0.0 | 5 | 5 |
| entry 0 / seeded_legal / seeded / MEDIUM | 14.2 (3-59) | 71.5 | 20/20 | 0.0 | 0.0 | 14.2 | 9.8 | 4.4 | 0.0 | 4 | 4 |
| entry 0 / seeded_legal / seeded / HIGH | 13.2 (3-59) | 66.5 | 20/20 | 0.0 | 0.0 | 13.2 | 8.9 | 4.3 | 0.0 | 4 | 4 |
| entry 1 / pass / bite / MEDIUM | 59.0 (59-59) | 300.0 | 1/1 | 0.0 | 0.0 | 59.0 | 0.0 | 59.0 | 0.0 | 59 | 59 |
| entry 1 / pass / bite / HIGH | 59.0 (59-59) | 300.0 | 1/1 | 0.0 | 0.0 | 59.0 | 0.0 | 59.0 | 0.0 | 59 | 59 |
| entry 1 / pass / call / MEDIUM | 59.0 (59-59) | 300.0 | 1/1 | 0.0 | 0.0 | 59.0 | 0.0 | 59.0 | 0.0 | 59 | 59 |
| entry 1 / pass / call / HIGH | 59.0 (59-59) | 300.0 | 1/1 | 0.0 | 0.0 | 59.0 | 0.0 | 59.0 | 0.0 | 59 | 59 |
| entry 1 / pass / balanced / MEDIUM | 59.0 (59-59) | 300.0 | 1/1 | 0.0 | 0.0 | 59.0 | 0.0 | 59.0 | 0.0 | 59 | 59 |
| entry 1 / pass / balanced / HIGH | 59.0 (59-59) | 300.0 | 1/1 | 0.0 | 0.0 | 59.0 | 0.0 | 59.0 | 0.0 | 59 | 59 |
| entry 1 / pass / fallback / MEDIUM | 59.0 (59-59) | 300.0 | 1/1 | 0.0 | 0.0 | 59.0 | 0.0 | 59.0 | 0.0 | 59 | 59 |
| entry 1 / pass / fallback / HIGH | 59.0 (59-59) | 300.0 | 1/1 | 0.0 | 0.0 | 59.0 | 0.0 | 59.0 | 0.0 | 59 | 59 |
| entry 1 / pass / seeded / MEDIUM | 59.0 (59-59) | 300.0 | 20/20 | 0.0 | 0.0 | 59.0 | 0.0 | 59.0 | 0.0 | 59 | 59 |
| entry 1 / pass / seeded / HIGH | 59.0 (59-59) | 300.0 | 20/20 | 0.0 | 0.0 | 59.0 | 0.0 | 59.0 | 0.0 | 59 | 59 |
| entry 1 / direct_cycle / bite / MEDIUM | 9.0 (9-9) | 45.0 | 1/1 | 0.0 | 0.0 | 9.0 | 9.0 | 0.0 | 0.0 | 0 | 0 |
| entry 1 / direct_cycle / bite / HIGH | 9.0 (9-9) | 45.0 | 1/1 | 0.0 | 0.0 | 9.0 | 9.0 | 0.0 | 0.0 | 0 | 0 |
| entry 1 / direct_cycle / call / MEDIUM | 9.0 (9-9) | 45.0 | 1/1 | 0.0 | 0.0 | 9.0 | 9.0 | 0.0 | 0.0 | 0 | 0 |
| entry 1 / direct_cycle / call / HIGH | 3.0 (3-3) | 15.0 | 1/1 | 0.0 | 0.0 | 3.0 | 3.0 | 0.0 | 0.0 | 0 | 0 |
| entry 1 / direct_cycle / balanced / MEDIUM | 9.0 (9-9) | 45.0 | 1/1 | 0.0 | 0.0 | 9.0 | 9.0 | 0.0 | 0.0 | 0 | 0 |
| entry 1 / direct_cycle / balanced / HIGH | 3.0 (3-3) | 15.0 | 1/1 | 0.0 | 0.0 | 3.0 | 3.0 | 0.0 | 0.0 | 0 | 0 |
| entry 1 / direct_cycle / fallback / MEDIUM | 9.0 (9-9) | 45.0 | 1/1 | 0.0 | 0.0 | 9.0 | 9.0 | 0.0 | 0.0 | 0 | 0 |
| entry 1 / direct_cycle / fallback / HIGH | 9.0 (9-9) | 45.0 | 1/1 | 0.0 | 0.0 | 9.0 | 9.0 | 0.0 | 0.0 | 0 | 0 |
| entry 1 / direct_cycle / seeded / MEDIUM | 9.0 (3-15) | 45.0 | 20/20 | 0.0 | 0.0 | 9.0 | 9.0 | 0.0 | 0.0 | 0 | 0 |
| entry 1 / direct_cycle / seeded / HIGH | 8.3 (2-27) | 41.8 | 20/20 | 0.0 | 0.0 | 8.3 | 8.3 | 0.0 | 0.0 | 0 | 0 |
| entry 1 / feint_when_eligible / bite / MEDIUM | 6.0 (6-6) | 30.0 | 1/1 | 0.0 | 0.0 | 6.0 | 6.0 | 0.0 | 0.0 | 0 | 0 |
| entry 1 / feint_when_eligible / bite / HIGH | 59.0 (59-59) | 300.0 | 1/1 | 0.0 | 0.0 | 59.0 | 59.0 | 0.0 | 0.0 | 0 | 0 |
| entry 1 / feint_when_eligible / call / MEDIUM | 59.0 (59-59) | 300.0 | 1/1 | 0.0 | 0.0 | 59.0 | 59.0 | 0.0 | 0.0 | 0 | 0 |
| entry 1 / feint_when_eligible / call / HIGH | 7.0 (7-7) | 35.0 | 1/1 | 0.0 | 0.0 | 7.0 | 7.0 | 0.0 | 0.0 | 0 | 0 |
| entry 1 / feint_when_eligible / balanced / MEDIUM | 59.0 (59-59) | 300.0 | 1/1 | 0.0 | 0.0 | 59.0 | 59.0 | 0.0 | 0.0 | 0 | 0 |
| entry 1 / feint_when_eligible / balanced / HIGH | 7.0 (7-7) | 35.0 | 1/1 | 0.0 | 0.0 | 7.0 | 7.0 | 0.0 | 0.0 | 0 | 0 |
| entry 1 / feint_when_eligible / fallback / MEDIUM | 59.0 (59-59) | 300.0 | 1/1 | 0.0 | 0.0 | 59.0 | 59.0 | 0.0 | 0.0 | 0 | 0 |
| entry 1 / feint_when_eligible / fallback / HIGH | 59.0 (59-59) | 300.0 | 1/1 | 0.0 | 0.0 | 59.0 | 59.0 | 0.0 | 0.0 | 0 | 0 |
| entry 1 / feint_when_eligible / seeded / MEDIUM | 26.1 (2-59) | 132.8 | 20/20 | 0.0 | 0.0 | 26.1 | 26.1 | 0.0 | 0.0 | 0 | 0 |
| entry 1 / feint_when_eligible / seeded / HIGH | 31.4 (2-59) | 159.5 | 20/20 | 0.0 | 0.0 | 31.4 | 31.4 | 0.0 | 0.0 | 0 | 0 |
| entry 1 / prep_oriented / bite / MEDIUM | 11.0 (11-11) | 55.0 | 1/1 | 0.0 | 0.0 | 11.0 | 11.0 | 0.0 | 0.0 | 0 | 0 |
| entry 1 / prep_oriented / bite / HIGH | 7.0 (7-7) | 35.0 | 1/1 | 0.0 | 0.0 | 7.0 | 7.0 | 0.0 | 0.0 | 0 | 0 |
| entry 1 / prep_oriented / call / MEDIUM | 4.0 (4-4) | 20.0 | 1/1 | 0.0 | 0.0 | 4.0 | 4.0 | 0.0 | 0.0 | 0 | 0 |
| entry 1 / prep_oriented / call / HIGH | 4.0 (4-4) | 20.0 | 1/1 | 0.0 | 0.0 | 4.0 | 4.0 | 0.0 | 0.0 | 0 | 0 |
| entry 1 / prep_oriented / balanced / MEDIUM | 11.0 (11-11) | 55.0 | 1/1 | 0.0 | 0.0 | 11.0 | 11.0 | 0.0 | 0.0 | 0 | 0 |
| entry 1 / prep_oriented / balanced / HIGH | 9.0 (9-9) | 45.0 | 1/1 | 0.0 | 0.0 | 9.0 | 9.0 | 0.0 | 0.0 | 0 | 0 |
| entry 1 / prep_oriented / fallback / MEDIUM | 8.0 (8-8) | 40.0 | 1/1 | 0.0 | 0.0 | 8.0 | 8.0 | 0.0 | 0.0 | 0 | 0 |
| entry 1 / prep_oriented / fallback / HIGH | 4.0 (4-4) | 20.0 | 1/1 | 0.0 | 0.0 | 4.0 | 4.0 | 0.0 | 0.0 | 0 | 0 |
| entry 1 / prep_oriented / seeded / MEDIUM | 6.0 (3-11) | 30.2 | 20/20 | 0.0 | 0.0 | 6.0 | 6.0 | 0.0 | 0.0 | 0 | 0 |
| entry 1 / prep_oriented / seeded / HIGH | 6.2 (3-19) | 30.8 | 20/20 | 0.0 | 0.0 | 6.2 | 6.2 | 0.0 | 0.0 | 0 | 0 |
| entry 1 / seeded_legal / bite / MEDIUM | 16.4 (7-33) | 82.0 | 20/20 | 0.0 | 0.0 | 16.4 | 10.4 | 6.0 | 0.0 | 4 | 4 |
| entry 1 / seeded_legal / bite / HIGH | 18.4 (7-59) | 92.5 | 20/20 | 0.0 | 0.0 | 18.4 | 11.7 | 6.8 | 0.0 | 4 | 4 |
| entry 1 / seeded_legal / call / MEDIUM | 23.8 (9-59) | 119.8 | 20/20 | 0.0 | 0.0 | 23.8 | 15.5 | 8.3 | 0.0 | 5 | 5 |
| entry 1 / seeded_legal / call / HIGH | 17.6 (3-59) | 88.2 | 20/20 | 0.0 | 0.0 | 17.6 | 11.2 | 6.4 | 0.0 | 4 | 4 |
| entry 1 / seeded_legal / balanced / MEDIUM | 20.4 (9-59) | 102.5 | 20/20 | 0.0 | 0.0 | 20.4 | 12.9 | 7.5 | 0.0 | 5 | 5 |
| entry 1 / seeded_legal / balanced / HIGH | 19.2 (3-59) | 97.0 | 20/20 | 0.0 | 0.0 | 19.2 | 12.6 | 6.7 | 0.0 | 4 | 4 |
| entry 1 / seeded_legal / fallback / MEDIUM | 12.6 (3-33) | 62.8 | 20/20 | 0.0 | 0.0 | 12.6 | 7.9 | 4.7 | 0.0 | 4 | 4 |
| entry 1 / seeded_legal / fallback / HIGH | 12.9 (3-59) | 64.5 | 20/20 | 0.0 | 0.0 | 12.9 | 8.1 | 4.8 | 0.0 | 4 | 4 |
| entry 1 / seeded_legal / seeded / MEDIUM | 11.4 (3-33) | 57.2 | 20/20 | 0.0 | 0.0 | 11.4 | 7.5 | 3.9 | 0.0 | 4 | 4 |
| entry 1 / seeded_legal / seeded / HIGH | 12.9 (3-59) | 64.8 | 20/20 | 0.0 | 0.0 | 12.9 | 8.8 | 4.1 | 0.0 | 4 | 4 |
| entry 2 / pass / bite / MEDIUM | 59.0 (59-59) | 300.0 | 1/1 | 0.0 | 0.0 | 59.0 | 0.0 | 59.0 | 0.0 | 59 | 59 |
| entry 2 / pass / bite / HIGH | 59.0 (59-59) | 300.0 | 1/1 | 0.0 | 0.0 | 59.0 | 0.0 | 59.0 | 0.0 | 59 | 59 |
| entry 2 / pass / call / MEDIUM | 59.0 (59-59) | 300.0 | 1/1 | 0.0 | 0.0 | 59.0 | 0.0 | 59.0 | 0.0 | 59 | 59 |
| entry 2 / pass / call / HIGH | 59.0 (59-59) | 300.0 | 1/1 | 0.0 | 0.0 | 59.0 | 0.0 | 59.0 | 0.0 | 59 | 59 |
| entry 2 / pass / balanced / MEDIUM | 59.0 (59-59) | 300.0 | 1/1 | 0.0 | 0.0 | 59.0 | 0.0 | 59.0 | 0.0 | 59 | 59 |
| entry 2 / pass / balanced / HIGH | 59.0 (59-59) | 300.0 | 1/1 | 0.0 | 0.0 | 59.0 | 0.0 | 59.0 | 0.0 | 59 | 59 |
| entry 2 / pass / fallback / MEDIUM | 59.0 (59-59) | 300.0 | 1/1 | 0.0 | 0.0 | 59.0 | 0.0 | 59.0 | 0.0 | 59 | 59 |
| entry 2 / pass / fallback / HIGH | 59.0 (59-59) | 300.0 | 1/1 | 0.0 | 0.0 | 59.0 | 0.0 | 59.0 | 0.0 | 59 | 59 |
| entry 2 / pass / seeded / MEDIUM | 59.0 (59-59) | 300.0 | 20/20 | 0.0 | 0.0 | 59.0 | 0.0 | 59.0 | 0.0 | 59 | 59 |
| entry 2 / pass / seeded / HIGH | 59.0 (59-59) | 300.0 | 20/20 | 0.0 | 0.0 | 59.0 | 0.0 | 59.0 | 0.0 | 59 | 59 |
| entry 2 / direct_cycle / bite / MEDIUM | 3.0 (3-3) | 15.0 | 1/1 | 0.0 | 0.0 | 3.0 | 3.0 | 0.0 | 0.0 | 0 | 0 |
| entry 2 / direct_cycle / bite / HIGH | 3.0 (3-3) | 15.0 | 1/1 | 0.0 | 0.0 | 3.0 | 3.0 | 0.0 | 0.0 | 0 | 0 |
| entry 2 / direct_cycle / call / MEDIUM | 3.0 (3-3) | 15.0 | 1/1 | 0.0 | 0.0 | 3.0 | 3.0 | 0.0 | 0.0 | 0 | 0 |
| entry 2 / direct_cycle / call / HIGH | 3.0 (3-3) | 15.0 | 1/1 | 0.0 | 0.0 | 3.0 | 3.0 | 0.0 | 0.0 | 0 | 0 |
| entry 2 / direct_cycle / balanced / MEDIUM | 3.0 (3-3) | 15.0 | 1/1 | 0.0 | 0.0 | 3.0 | 3.0 | 0.0 | 0.0 | 0 | 0 |
| entry 2 / direct_cycle / balanced / HIGH | 3.0 (3-3) | 15.0 | 1/1 | 0.0 | 0.0 | 3.0 | 3.0 | 0.0 | 0.0 | 0 | 0 |
| entry 2 / direct_cycle / fallback / MEDIUM | 3.0 (3-3) | 15.0 | 1/1 | 0.0 | 0.0 | 3.0 | 3.0 | 0.0 | 0.0 | 0 | 0 |
| entry 2 / direct_cycle / fallback / HIGH | 3.0 (3-3) | 15.0 | 1/1 | 0.0 | 0.0 | 3.0 | 3.0 | 0.0 | 0.0 | 0 | 0 |
| entry 2 / direct_cycle / seeded / MEDIUM | 4.5 (3-9) | 22.5 | 20/20 | 0.0 | 0.0 | 4.5 | 4.5 | 0.0 | 0.0 | 0 | 0 |
| entry 2 / direct_cycle / seeded / HIGH | 3.6 (3-9) | 18.0 | 20/20 | 0.0 | 0.0 | 3.6 | 3.6 | 0.0 | 0.0 | 0 | 0 |
| entry 2 / feint_when_eligible / bite / MEDIUM | 59.0 (59-59) | 300.0 | 1/1 | 0.0 | 0.0 | 59.0 | 59.0 | 0.0 | 0.0 | 0 | 0 |
| entry 2 / feint_when_eligible / bite / HIGH | 59.0 (59-59) | 300.0 | 1/1 | 0.0 | 0.0 | 59.0 | 59.0 | 0.0 | 0.0 | 0 | 0 |
| entry 2 / feint_when_eligible / call / MEDIUM | 5.0 (5-5) | 25.0 | 1/1 | 0.0 | 0.0 | 5.0 | 5.0 | 0.0 | 0.0 | 0 | 0 |
| entry 2 / feint_when_eligible / call / HIGH | 5.0 (5-5) | 25.0 | 1/1 | 0.0 | 0.0 | 5.0 | 5.0 | 0.0 | 0.0 | 0 | 0 |
| entry 2 / feint_when_eligible / balanced / MEDIUM | 5.0 (5-5) | 25.0 | 1/1 | 0.0 | 0.0 | 5.0 | 5.0 | 0.0 | 0.0 | 0 | 0 |
| entry 2 / feint_when_eligible / balanced / HIGH | 5.0 (5-5) | 25.0 | 1/1 | 0.0 | 0.0 | 5.0 | 5.0 | 0.0 | 0.0 | 0 | 0 |
| entry 2 / feint_when_eligible / fallback / MEDIUM | 3.0 (3-3) | 15.0 | 1/1 | 0.0 | 0.0 | 3.0 | 3.0 | 0.0 | 0.0 | 0 | 0 |
| entry 2 / feint_when_eligible / fallback / HIGH | 3.0 (3-3) | 15.0 | 1/1 | 0.0 | 0.0 | 3.0 | 3.0 | 0.0 | 0.0 | 0 | 0 |
| entry 2 / feint_when_eligible / seeded / MEDIUM | 6.4 (3-59) | 32.2 | 20/20 | 0.0 | 0.0 | 6.4 | 6.4 | 0.0 | 0.0 | 0 | 0 |
| entry 2 / feint_when_eligible / seeded / HIGH | 6.4 (3-59) | 32.2 | 20/20 | 0.0 | 0.0 | 6.4 | 6.4 | 0.0 | 0.0 | 0 | 0 |
| entry 2 / prep_oriented / bite / MEDIUM | 5.0 (5-5) | 25.0 | 1/1 | 0.0 | 0.0 | 5.0 | 5.0 | 0.0 | 0.0 | 0 | 0 |
| entry 2 / prep_oriented / bite / HIGH | 3.0 (3-3) | 15.0 | 1/1 | 0.0 | 0.0 | 3.0 | 3.0 | 0.0 | 0.0 | 0 | 0 |
| entry 2 / prep_oriented / call / MEDIUM | 30.0 (30-30) | 150.0 | 1/1 | 0.0 | 0.0 | 30.0 | 30.0 | 0.0 | 0.0 | 0 | 0 |
| entry 2 / prep_oriented / call / HIGH | 20.0 (20-20) | 100.0 | 1/1 | 0.0 | 0.0 | 20.0 | 20.0 | 0.0 | 0.0 | 0 | 0 |
| entry 2 / prep_oriented / balanced / MEDIUM | 5.0 (5-5) | 25.0 | 1/1 | 0.0 | 0.0 | 5.0 | 5.0 | 0.0 | 0.0 | 0 | 0 |
| entry 2 / prep_oriented / balanced / HIGH | 3.0 (3-3) | 15.0 | 1/1 | 0.0 | 0.0 | 3.0 | 3.0 | 0.0 | 0.0 | 0 | 0 |
| entry 2 / prep_oriented / fallback / MEDIUM | 3.0 (3-3) | 15.0 | 1/1 | 0.0 | 0.0 | 3.0 | 3.0 | 0.0 | 0.0 | 0 | 0 |
| entry 2 / prep_oriented / fallback / HIGH | 3.0 (3-3) | 15.0 | 1/1 | 0.0 | 0.0 | 3.0 | 3.0 | 0.0 | 0.0 | 0 | 0 |
| entry 2 / prep_oriented / seeded / MEDIUM | 4.3 (3-9) | 21.5 | 20/20 | 0.0 | 0.0 | 4.3 | 4.3 | 0.0 | 0.0 | 0 | 0 |
| entry 2 / prep_oriented / seeded / HIGH | 4.0 (3-11) | 20.0 | 20/20 | 0.0 | 0.0 | 4.0 | 4.0 | 0.0 | 0.0 | 0 | 0 |
| entry 2 / seeded_legal / bite / MEDIUM | 10.3 (3-33) | 51.5 | 20/20 | 0.0 | 0.0 | 10.3 | 6.5 | 3.9 | 0.0 | 4 | 4 |
| entry 2 / seeded_legal / bite / HIGH | 7.5 (3-17) | 37.5 | 20/20 | 0.0 | 0.0 | 7.5 | 4.9 | 2.6 | 0.0 | 4 | 4 |
| entry 2 / seeded_legal / call / MEDIUM | 11.0 (3-33) | 55.0 | 20/20 | 0.0 | 0.0 | 11.0 | 7.0 | 4.0 | 0.0 | 4 | 4 |
| entry 2 / seeded_legal / call / HIGH | 7.9 (3-17) | 39.5 | 20/20 | 0.0 | 0.0 | 7.9 | 5.2 | 2.8 | 0.0 | 4 | 4 |
| entry 2 / seeded_legal / balanced / MEDIUM | 10.2 (3-33) | 51.0 | 20/20 | 0.0 | 0.0 | 10.2 | 6.3 | 3.9 | 0.0 | 4 | 4 |
| entry 2 / seeded_legal / balanced / HIGH | 7.5 (3-17) | 37.5 | 20/20 | 0.0 | 0.0 | 7.5 | 4.9 | 2.6 | 0.0 | 4 | 4 |
| entry 2 / seeded_legal / fallback / MEDIUM | 9.0 (3-33) | 45.0 | 20/20 | 0.0 | 0.0 | 9.0 | 5.7 | 3.3 | 0.0 | 4 | 4 |
| entry 2 / seeded_legal / fallback / HIGH | 8.3 (3-33) | 41.5 | 20/20 | 0.0 | 0.0 | 8.3 | 5.2 | 3.1 | 0.0 | 4 | 4 |
| entry 2 / seeded_legal / seeded / MEDIUM | 8.9 (3-25) | 44.5 | 20/20 | 0.0 | 0.0 | 8.9 | 6.0 | 2.9 | 0.0 | 4 | 4 |
| entry 2 / seeded_legal / seeded / HIGH | 7.6 (3-17) | 38.0 | 20/20 | 0.0 | 0.0 | 7.6 | 5.1 | 2.5 | 0.0 | 4 | 4 |
| entry 3 / pass / bite / MEDIUM | 59.0 (59-59) | 300.0 | 1/1 | 0.0 | 0.0 | 59.0 | 0.0 | 59.0 | 0.0 | 59 | 59 |
| entry 3 / pass / bite / HIGH | 59.0 (59-59) | 300.0 | 1/1 | 0.0 | 0.0 | 59.0 | 0.0 | 59.0 | 0.0 | 59 | 59 |
| entry 3 / pass / call / MEDIUM | 59.0 (59-59) | 300.0 | 1/1 | 0.0 | 0.0 | 59.0 | 0.0 | 59.0 | 0.0 | 59 | 59 |
| entry 3 / pass / call / HIGH | 59.0 (59-59) | 300.0 | 1/1 | 0.0 | 0.0 | 59.0 | 0.0 | 59.0 | 0.0 | 59 | 59 |
| entry 3 / pass / balanced / MEDIUM | 59.0 (59-59) | 300.0 | 1/1 | 0.0 | 0.0 | 59.0 | 0.0 | 59.0 | 0.0 | 59 | 59 |
| entry 3 / pass / balanced / HIGH | 59.0 (59-59) | 300.0 | 1/1 | 0.0 | 0.0 | 59.0 | 0.0 | 59.0 | 0.0 | 59 | 59 |
| entry 3 / pass / fallback / MEDIUM | 59.0 (59-59) | 300.0 | 1/1 | 0.0 | 0.0 | 59.0 | 0.0 | 59.0 | 0.0 | 59 | 59 |
| entry 3 / pass / fallback / HIGH | 59.0 (59-59) | 300.0 | 1/1 | 0.0 | 0.0 | 59.0 | 0.0 | 59.0 | 0.0 | 59 | 59 |
| entry 3 / pass / seeded / MEDIUM | 59.0 (59-59) | 300.0 | 20/20 | 0.0 | 0.0 | 59.0 | 0.0 | 59.0 | 0.0 | 59 | 59 |
| entry 3 / pass / seeded / HIGH | 59.0 (59-59) | 300.0 | 20/20 | 0.0 | 0.0 | 59.0 | 0.0 | 59.0 | 0.0 | 59 | 59 |
| entry 3 / direct_cycle / bite / MEDIUM | 6.0 (6-6) | 30.0 | 1/1 | 0.0 | 0.0 | 6.0 | 6.0 | 0.0 | 0.0 | 0 | 0 |
| entry 3 / direct_cycle / bite / HIGH | 6.0 (6-6) | 30.0 | 1/1 | 0.0 | 0.0 | 6.0 | 6.0 | 0.0 | 0.0 | 0 | 0 |
| entry 3 / direct_cycle / call / MEDIUM | 8.0 (8-8) | 40.0 | 1/1 | 0.0 | 0.0 | 8.0 | 8.0 | 0.0 | 0.0 | 0 | 0 |
| entry 3 / direct_cycle / call / HIGH | 3.0 (3-3) | 15.0 | 1/1 | 0.0 | 0.0 | 3.0 | 3.0 | 0.0 | 0.0 | 0 | 0 |
| entry 3 / direct_cycle / balanced / MEDIUM | 8.0 (8-8) | 40.0 | 1/1 | 0.0 | 0.0 | 8.0 | 8.0 | 0.0 | 0.0 | 0 | 0 |
| entry 3 / direct_cycle / balanced / HIGH | 3.0 (3-3) | 15.0 | 1/1 | 0.0 | 0.0 | 3.0 | 3.0 | 0.0 | 0.0 | 0 | 0 |
| entry 3 / direct_cycle / fallback / MEDIUM | 12.0 (12-12) | 60.0 | 1/1 | 0.0 | 0.0 | 12.0 | 12.0 | 0.0 | 0.0 | 0 | 0 |
| entry 3 / direct_cycle / fallback / HIGH | 10.0 (10-10) | 50.0 | 1/1 | 0.0 | 0.0 | 10.0 | 10.0 | 0.0 | 0.0 | 0 | 0 |
| entry 3 / direct_cycle / seeded / MEDIUM | 7.5 (3-14) | 37.5 | 20/20 | 0.0 | 0.0 | 7.5 | 7.5 | 0.0 | 0.0 | 0 | 0 |
| entry 3 / direct_cycle / seeded / HIGH | 8.8 (2-33) | 43.8 | 20/20 | 0.0 | 0.0 | 8.8 | 8.8 | 0.0 | 0.0 | 0 | 0 |
| entry 3 / feint_when_eligible / bite / MEDIUM | 6.0 (6-6) | 30.0 | 1/1 | 0.0 | 0.0 | 6.0 | 6.0 | 0.0 | 0.0 | 0 | 0 |
| entry 3 / feint_when_eligible / bite / HIGH | 6.0 (6-6) | 30.0 | 1/1 | 0.0 | 0.0 | 6.0 | 6.0 | 0.0 | 0.0 | 0 | 0 |
| entry 3 / feint_when_eligible / call / MEDIUM | 59.0 (59-59) | 300.0 | 1/1 | 0.0 | 0.0 | 59.0 | 59.0 | 0.0 | 0.0 | 0 | 0 |
| entry 3 / feint_when_eligible / call / HIGH | 59.0 (59-59) | 300.0 | 1/1 | 0.0 | 0.0 | 59.0 | 59.0 | 0.0 | 0.0 | 0 | 0 |
| entry 3 / feint_when_eligible / balanced / MEDIUM | 59.0 (59-59) | 300.0 | 1/1 | 0.0 | 0.0 | 59.0 | 59.0 | 0.0 | 0.0 | 0 | 0 |
| entry 3 / feint_when_eligible / balanced / HIGH | 59.0 (59-59) | 300.0 | 1/1 | 0.0 | 0.0 | 59.0 | 59.0 | 0.0 | 0.0 | 0 | 0 |
| entry 3 / feint_when_eligible / fallback / MEDIUM | 59.0 (59-59) | 300.0 | 1/1 | 0.0 | 0.0 | 59.0 | 59.0 | 0.0 | 0.0 | 0 | 0 |
| entry 3 / feint_when_eligible / fallback / HIGH | 10.0 (10-10) | 50.0 | 1/1 | 0.0 | 0.0 | 10.0 | 10.0 | 0.0 | 0.0 | 0 | 0 |
| entry 3 / feint_when_eligible / seeded / MEDIUM | 9.5 (2-59) | 47.8 | 20/20 | 0.0 | 0.0 | 9.5 | 9.5 | 0.0 | 0.0 | 0 | 0 |
| entry 3 / feint_when_eligible / seeded / HIGH | 16.4 (2-59) | 82.8 | 20/20 | 0.0 | 0.0 | 16.4 | 16.4 | 0.0 | 0.0 | 0 | 0 |
| entry 3 / prep_oriented / bite / MEDIUM | 10.0 (10-10) | 50.0 | 1/1 | 0.0 | 0.0 | 10.0 | 10.0 | 0.0 | 0.0 | 0 | 0 |
| entry 3 / prep_oriented / bite / HIGH | 6.0 (6-6) | 30.0 | 1/1 | 0.0 | 0.0 | 6.0 | 6.0 | 0.0 | 0.0 | 0 | 0 |
| entry 3 / prep_oriented / call / MEDIUM | 4.0 (4-4) | 20.0 | 1/1 | 0.0 | 0.0 | 4.0 | 4.0 | 0.0 | 0.0 | 0 | 0 |
| entry 3 / prep_oriented / call / HIGH | 4.0 (4-4) | 20.0 | 1/1 | 0.0 | 0.0 | 4.0 | 4.0 | 0.0 | 0.0 | 0 | 0 |
| entry 3 / prep_oriented / balanced / MEDIUM | 8.0 (8-8) | 40.0 | 1/1 | 0.0 | 0.0 | 8.0 | 8.0 | 0.0 | 0.0 | 0 | 0 |
| entry 3 / prep_oriented / balanced / HIGH | 4.0 (4-4) | 20.0 | 1/1 | 0.0 | 0.0 | 4.0 | 4.0 | 0.0 | 0.0 | 0 | 0 |
| entry 3 / prep_oriented / fallback / MEDIUM | 8.0 (8-8) | 40.0 | 1/1 | 0.0 | 0.0 | 8.0 | 8.0 | 0.0 | 0.0 | 0 | 0 |
| entry 3 / prep_oriented / fallback / HIGH | 4.0 (4-4) | 20.0 | 1/1 | 0.0 | 0.0 | 4.0 | 4.0 | 0.0 | 0.0 | 0 | 0 |
| entry 3 / prep_oriented / seeded / MEDIUM | 7.2 (3-16) | 35.8 | 20/20 | 0.0 | 0.0 | 7.2 | 7.2 | 0.0 | 0.0 | 0 | 0 |
| entry 3 / prep_oriented / seeded / HIGH | 6.0 (3-16) | 30.2 | 20/20 | 0.0 | 0.0 | 6.0 | 6.0 | 0.0 | 0.0 | 0 | 0 |
| entry 3 / seeded_legal / bite / MEDIUM | 12.1 (6-18) | 60.5 | 20/20 | 0.0 | 0.0 | 12.1 | 7.8 | 4.3 | 0.0 | 4 | 4 |
| entry 3 / seeded_legal / bite / HIGH | 11.1 (6-18) | 55.5 | 20/20 | 0.0 | 0.0 | 11.1 | 7.1 | 4.0 | 0.0 | 4 | 4 |
| entry 3 / seeded_legal / call / MEDIUM | 15.8 (8-59) | 79.5 | 20/20 | 0.0 | 0.0 | 15.8 | 10.2 | 5.6 | 0.0 | 4 | 4 |
| entry 3 / seeded_legal / call / HIGH | 12.9 (3-59) | 65.0 | 20/20 | 0.0 | 0.0 | 12.9 | 8.4 | 4.5 | 0.0 | 4 | 4 |
| entry 3 / seeded_legal / balanced / MEDIUM | 16.6 (8-59) | 83.5 | 20/20 | 0.0 | 0.0 | 16.6 | 10.9 | 5.8 | 0.0 | 4 | 4 |
| entry 3 / seeded_legal / balanced / HIGH | 12.6 (3-59) | 63.0 | 20/20 | 0.0 | 0.0 | 12.6 | 8.2 | 4.3 | 0.0 | 4 | 4 |
| entry 3 / seeded_legal / fallback / MEDIUM | 12.2 (3-24) | 61.0 | 20/20 | 0.0 | 0.0 | 12.2 | 7.7 | 4.5 | 0.0 | 5 | 5 |
| entry 3 / seeded_legal / fallback / HIGH | 11.8 (3-26) | 59.2 | 20/20 | 0.0 | 0.0 | 11.8 | 7.6 | 4.2 | 0.0 | 4 | 4 |
| entry 3 / seeded_legal / seeded / MEDIUM | 13.3 (3-32) | 66.5 | 20/20 | 0.0 | 0.0 | 13.3 | 8.6 | 4.7 | 0.0 | 4 | 4 |
| entry 3 / seeded_legal / seeded / HIGH | 12.3 (3-27) | 61.8 | 20/20 | 0.0 | 0.0 | 12.3 | 8.0 | 4.4 | 0.0 | 4 | 4 |
| entry 4 / pass / bite / MEDIUM | 59.0 (59-59) | 300.0 | 1/1 | 0.0 | 0.0 | 59.0 | 0.0 | 59.0 | 0.0 | 59 | 59 |
| entry 4 / pass / bite / HIGH | 59.0 (59-59) | 300.0 | 1/1 | 0.0 | 0.0 | 59.0 | 0.0 | 59.0 | 0.0 | 59 | 59 |
| entry 4 / pass / call / MEDIUM | 59.0 (59-59) | 300.0 | 1/1 | 0.0 | 0.0 | 59.0 | 0.0 | 59.0 | 0.0 | 59 | 59 |
| entry 4 / pass / call / HIGH | 59.0 (59-59) | 300.0 | 1/1 | 0.0 | 0.0 | 59.0 | 0.0 | 59.0 | 0.0 | 59 | 59 |
| entry 4 / pass / balanced / MEDIUM | 59.0 (59-59) | 300.0 | 1/1 | 0.0 | 0.0 | 59.0 | 0.0 | 59.0 | 0.0 | 59 | 59 |
| entry 4 / pass / balanced / HIGH | 59.0 (59-59) | 300.0 | 1/1 | 0.0 | 0.0 | 59.0 | 0.0 | 59.0 | 0.0 | 59 | 59 |
| entry 4 / pass / fallback / MEDIUM | 59.0 (59-59) | 300.0 | 1/1 | 0.0 | 0.0 | 59.0 | 0.0 | 59.0 | 0.0 | 59 | 59 |
| entry 4 / pass / fallback / HIGH | 59.0 (59-59) | 300.0 | 1/1 | 0.0 | 0.0 | 59.0 | 0.0 | 59.0 | 0.0 | 59 | 59 |
| entry 4 / pass / seeded / MEDIUM | 59.0 (59-59) | 300.0 | 20/20 | 0.0 | 0.0 | 59.0 | 0.0 | 59.0 | 0.0 | 59 | 59 |
| entry 4 / pass / seeded / HIGH | 59.0 (59-59) | 300.0 | 20/20 | 0.0 | 0.0 | 59.0 | 0.0 | 59.0 | 0.0 | 59 | 59 |
| entry 4 / direct_cycle / bite / MEDIUM | 59.0 (59-59) | 300.0 | 1/1 | 0.0 | 0.0 | 59.0 | 59.0 | 0.0 | 0.0 | 0 | 0 |
| entry 4 / direct_cycle / bite / HIGH | 6.0 (6-6) | 30.0 | 1/1 | 0.0 | 0.0 | 6.0 | 6.0 | 0.0 | 0.0 | 0 | 0 |
| entry 4 / direct_cycle / call / MEDIUM | 59.0 (59-59) | 300.0 | 1/1 | 0.0 | 0.0 | 59.0 | 59.0 | 0.0 | 0.0 | 0 | 0 |
| entry 4 / direct_cycle / call / HIGH | 3.0 (3-3) | 15.0 | 1/1 | 0.0 | 0.0 | 3.0 | 3.0 | 0.0 | 0.0 | 0 | 0 |
| entry 4 / direct_cycle / balanced / MEDIUM | 59.0 (59-59) | 300.0 | 1/1 | 0.0 | 0.0 | 59.0 | 59.0 | 0.0 | 0.0 | 0 | 0 |
| entry 4 / direct_cycle / balanced / HIGH | 3.0 (3-3) | 15.0 | 1/1 | 0.0 | 0.0 | 3.0 | 3.0 | 0.0 | 0.0 | 0 | 0 |
| entry 4 / direct_cycle / fallback / MEDIUM | 59.0 (59-59) | 300.0 | 1/1 | 0.0 | 0.0 | 59.0 | 59.0 | 0.0 | 0.0 | 0 | 0 |
| entry 4 / direct_cycle / fallback / HIGH | 59.0 (59-59) | 300.0 | 1/1 | 0.0 | 0.0 | 59.0 | 59.0 | 0.0 | 0.0 | 0 | 0 |
| entry 4 / direct_cycle / seeded / MEDIUM | 11.8 (3-28) | 59.0 | 20/20 | 0.0 | 0.0 | 11.8 | 11.8 | 0.0 | 0.0 | 0 | 0 |
| entry 4 / direct_cycle / seeded / HIGH | 12.8 (2-45) | 63.8 | 20/20 | 0.0 | 0.0 | 12.8 | 12.8 | 0.0 | 0.0 | 0 | 0 |
| entry 4 / feint_when_eligible / bite / MEDIUM | 6.0 (6-6) | 30.0 | 1/1 | 0.0 | 0.0 | 6.0 | 6.0 | 0.0 | 0.0 | 0 | 0 |
| entry 4 / feint_when_eligible / bite / HIGH | 59.0 (59-59) | 300.0 | 1/1 | 0.0 | 0.0 | 59.0 | 59.0 | 0.0 | 0.0 | 0 | 0 |
| entry 4 / feint_when_eligible / call / MEDIUM | 59.0 (59-59) | 300.0 | 1/1 | 0.0 | 0.0 | 59.0 | 59.0 | 0.0 | 0.0 | 0 | 0 |
| entry 4 / feint_when_eligible / call / HIGH | 59.0 (59-59) | 300.0 | 1/1 | 0.0 | 0.0 | 59.0 | 59.0 | 0.0 | 0.0 | 0 | 0 |
| entry 4 / feint_when_eligible / balanced / MEDIUM | 59.0 (59-59) | 300.0 | 1/1 | 0.0 | 0.0 | 59.0 | 59.0 | 0.0 | 0.0 | 0 | 0 |
| entry 4 / feint_when_eligible / balanced / HIGH | 59.0 (59-59) | 300.0 | 1/1 | 0.0 | 0.0 | 59.0 | 59.0 | 0.0 | 0.0 | 0 | 0 |
| entry 4 / feint_when_eligible / fallback / MEDIUM | 59.0 (59-59) | 300.0 | 1/1 | 0.0 | 0.0 | 59.0 | 59.0 | 0.0 | 0.0 | 0 | 0 |
| entry 4 / feint_when_eligible / fallback / HIGH | 59.0 (59-59) | 300.0 | 1/1 | 0.0 | 0.0 | 59.0 | 59.0 | 0.0 | 0.0 | 0 | 0 |
| entry 4 / feint_when_eligible / seeded / MEDIUM | 31.4 (2-59) | 159.8 | 20/20 | 0.0 | 0.0 | 31.4 | 31.4 | 0.0 | 0.0 | 0 | 0 |
| entry 4 / feint_when_eligible / seeded / HIGH | 39.4 (2-59) | 200.2 | 20/20 | 0.0 | 0.0 | 39.4 | 39.4 | 0.0 | 0.0 | 0 | 0 |
| entry 4 / prep_oriented / bite / MEDIUM | 59.0 (59-59) | 300.0 | 1/1 | 0.0 | 0.0 | 59.0 | 59.0 | 0.0 | 0.0 | 0 | 0 |
| entry 4 / prep_oriented / bite / HIGH | 6.0 (6-6) | 30.0 | 1/1 | 0.0 | 0.0 | 6.0 | 6.0 | 0.0 | 0.0 | 0 | 0 |
| entry 4 / prep_oriented / call / MEDIUM | 4.0 (4-4) | 20.0 | 1/1 | 0.0 | 0.0 | 4.0 | 4.0 | 0.0 | 0.0 | 0 | 0 |
| entry 4 / prep_oriented / call / HIGH | 4.0 (4-4) | 20.0 | 1/1 | 0.0 | 0.0 | 4.0 | 4.0 | 0.0 | 0.0 | 0 | 0 |
| entry 4 / prep_oriented / balanced / MEDIUM | 59.0 (59-59) | 300.0 | 1/1 | 0.0 | 0.0 | 59.0 | 59.0 | 0.0 | 0.0 | 0 | 0 |
| entry 4 / prep_oriented / balanced / HIGH | 4.0 (4-4) | 20.0 | 1/1 | 0.0 | 0.0 | 4.0 | 4.0 | 0.0 | 0.0 | 0 | 0 |
| entry 4 / prep_oriented / fallback / MEDIUM | 8.0 (8-8) | 40.0 | 1/1 | 0.0 | 0.0 | 8.0 | 8.0 | 0.0 | 0.0 | 0 | 0 |
| entry 4 / prep_oriented / fallback / HIGH | 4.0 (4-4) | 20.0 | 1/1 | 0.0 | 0.0 | 4.0 | 4.0 | 0.0 | 0.0 | 0 | 0 |
| entry 4 / prep_oriented / seeded / MEDIUM | 8.4 (3-32) | 42.0 | 20/20 | 0.0 | 0.0 | 8.4 | 8.4 | 0.0 | 0.0 | 0 | 0 |
| entry 4 / prep_oriented / seeded / HIGH | 8.5 (3-28) | 42.5 | 20/20 | 0.0 | 0.0 | 8.5 | 8.5 | 0.0 | 0.0 | 0 | 0 |
| entry 4 / seeded_legal / bite / MEDIUM | 53.9 (7-59) | 274.0 | 20/20 | 0.0 | 0.0 | 53.9 | 37.1 | 16.8 | 0.0 | 5 | 5 |
| entry 4 / seeded_legal / bite / HIGH | 43.5 (6-59) | 221.2 | 20/20 | 0.0 | 0.0 | 43.5 | 29.7 | 13.8 | 0.0 | 5 | 5 |
| entry 4 / seeded_legal / call / MEDIUM | 49.7 (12-59) | 252.5 | 20/20 | 0.0 | 0.0 | 49.7 | 34.0 | 15.7 | 0.0 | 4 | 4 |
| entry 4 / seeded_legal / call / HIGH | 38.8 (3-59) | 196.8 | 20/20 | 0.0 | 0.0 | 38.8 | 26.8 | 12.0 | 0.0 | 4 | 4 |
| entry 4 / seeded_legal / balanced / MEDIUM | 59.0 (59-59) | 300.0 | 20/20 | 0.0 | 0.0 | 59.0 | 40.9 | 18.1 | 0.0 | 5 | 5 |
| entry 4 / seeded_legal / balanced / HIGH | 41.1 (3-59) | 208.8 | 20/20 | 0.0 | 0.0 | 41.1 | 28.2 | 12.8 | 0.0 | 5 | 5 |
| entry 4 / seeded_legal / fallback / MEDIUM | 25.2 (3-59) | 127.5 | 20/20 | 0.0 | 0.0 | 25.2 | 16.8 | 8.4 | 0.0 | 5 | 5 |
| entry 4 / seeded_legal / fallback / HIGH | 22.6 (3-59) | 113.8 | 20/20 | 0.0 | 0.0 | 22.6 | 14.8 | 7.8 | 0.0 | 5 | 5 |
| entry 4 / seeded_legal / seeded / MEDIUM | 18.2 (3-59) | 91.8 | 20/20 | 0.0 | 0.0 | 18.2 | 12.7 | 5.6 | 0.0 | 4 | 4 |
| entry 4 / seeded_legal / seeded / HIGH | 15.5 (3-56) | 77.5 | 20/20 | 0.0 | 0.0 | 15.5 | 10.6 | 5.0 | 0.0 | 4 | 4 |

**Stamina, exhaustion and commitment downgrades** (means; `downgrades` counts exchanges whose requested commitment was funded lower, either fighter)
| cell | min stamina top (mean) | min stamina bottom (mean) | games with an exhausted fighter | exhausted windows top+bottom (mean) | downgrades (mean) | windows where any stamina rose: Mount / Half Guard (total) |
|---|---|---|---|---|---|---|
| entry 0 / pass / bite / MEDIUM | 93.0 | 93.0 | 0/1 | 0.0 | 0.0 | 0 / 0 |
| entry 0 / pass / bite / HIGH | 93.0 | 93.0 | 0/1 | 0.0 | 0.0 | 0 / 0 |
| entry 0 / pass / call / MEDIUM | 93.0 | 93.0 | 0/1 | 0.0 | 0.0 | 0 / 0 |
| entry 0 / pass / call / HIGH | 93.0 | 93.0 | 0/1 | 0.0 | 0.0 | 0 / 0 |
| entry 0 / pass / balanced / MEDIUM | 93.0 | 93.0 | 0/1 | 0.0 | 0.0 | 0 / 0 |
| entry 0 / pass / balanced / HIGH | 93.0 | 93.0 | 0/1 | 0.0 | 0.0 | 0 / 0 |
| entry 0 / pass / fallback / MEDIUM | 93.0 | 93.0 | 0/1 | 0.0 | 0.0 | 0 / 0 |
| entry 0 / pass / fallback / HIGH | 93.0 | 93.0 | 0/1 | 0.0 | 0.0 | 0 / 0 |
| entry 0 / pass / seeded / MEDIUM | 93.0 | 93.0 | 0/20 | 0.0 | 0.0 | 0 / 0 |
| entry 0 / pass / seeded / HIGH | 93.0 | 93.0 | 0/20 | 0.0 | 0.0 | 0 / 0 |
| entry 0 / direct_cycle / bite / MEDIUM | 2.0 | 2.0 | 1/1 | 98.0 | 92.0 | 0 / 0 |
| entry 0 / direct_cycle / bite / HIGH | 36.0 | 36.0 | 0/1 | 0.0 | 0.0 | 0 / 0 |
| entry 0 / direct_cycle / call / MEDIUM | 2.0 | 2.0 | 1/1 | 98.0 | 92.0 | 0 / 0 |
| entry 0 / direct_cycle / call / HIGH | 62.0 | 67.0 | 0/1 | 0.0 | 0.0 | 0 / 0 |
| entry 0 / direct_cycle / balanced / MEDIUM | 2.0 | 2.0 | 1/1 | 98.0 | 92.0 | 0 / 0 |
| entry 0 / direct_cycle / balanced / HIGH | 62.0 | 67.0 | 0/1 | 0.0 | 0.0 | 0 / 0 |
| entry 0 / direct_cycle / fallback / MEDIUM | 0.0 | 0.0 | 1/1 | 90.0 | 81.0 | 0 / 0 |
| entry 0 / direct_cycle / fallback / HIGH | 0.0 | 0.0 | 1/1 | 99.0 | 93.0 | 0 / 0 |
| entry 0 / direct_cycle / seeded / MEDIUM | 35.0 | 35.4 | 5/20 | 2.3 | 1.0 | 0 / 0 |
| entry 0 / direct_cycle / seeded / HIGH | 25.4 | 27.4 | 11/20 | 13.2 | 11.5 | 0 / 0 |
| entry 0 / feint_when_eligible / bite / MEDIUM | 48.0 | 42.0 | 0/1 | 0.0 | 0.0 | 0 / 0 |
| entry 0 / feint_when_eligible / bite / HIGH | 33.0 | 27.0 | 0/1 | 0.0 | 0.0 | 0 / 0 |
| entry 0 / feint_when_eligible / call / MEDIUM | 2.0 | 2.0 | 1/1 | 100.0 | 94.0 | 0 / 0 |
| entry 0 / feint_when_eligible / call / HIGH | 2.0 | 0.0 | 1/1 | 103.0 | 101.0 | 0 / 0 |
| entry 0 / feint_when_eligible / balanced / MEDIUM | 2.0 | 2.0 | 1/1 | 100.0 | 94.0 | 0 / 0 |
| entry 0 / feint_when_eligible / balanced / HIGH | 2.0 | 0.0 | 1/1 | 103.0 | 101.0 | 0 / 0 |
| entry 0 / feint_when_eligible / fallback / MEDIUM | 0.0 | 0.0 | 1/1 | 91.0 | 82.0 | 0 / 0 |
| entry 0 / feint_when_eligible / fallback / HIGH | 0.0 | 0.0 | 1/1 | 99.0 | 94.0 | 0 / 0 |
| entry 0 / feint_when_eligible / seeded / MEDIUM | 32.4 | 33.4 | 8/20 | 39.8 | 37.5 | 0 / 0 |
| entry 0 / feint_when_eligible / seeded / HIGH | 26.0 | 27.8 | 10/20 | 47.0 | 45.4 | 0 / 0 |
| entry 0 / prep_oriented / bite / MEDIUM | 2.0 | 2.0 | 1/1 | 98.0 | 92.0 | 0 / 0 |
| entry 0 / prep_oriented / bite / HIGH | 2.0 | 3.0 | 1/1 | 5.0 | 2.0 | 0 / 0 |
| entry 0 / prep_oriented / call / MEDIUM | 65.0 | 65.0 | 0/1 | 0.0 | 0.0 | 0 / 0 |
| entry 0 / prep_oriented / call / HIGH | 55.0 | 55.0 | 0/1 | 0.0 | 0.0 | 0 / 0 |
| entry 0 / prep_oriented / balanced / MEDIUM | 2.0 | 2.0 | 1/1 | 98.0 | 92.0 | 0 / 0 |
| entry 0 / prep_oriented / balanced / HIGH | 17.0 | 17.0 | 1/1 | 1.0 | 0.0 | 0 / 0 |
| entry 0 / prep_oriented / fallback / MEDIUM | 53.0 | 53.0 | 0/1 | 0.0 | 0.0 | 0 / 0 |
| entry 0 / prep_oriented / fallback / HIGH | 63.0 | 63.0 | 0/1 | 0.0 | 0.0 | 0 / 0 |
| entry 0 / prep_oriented / seeded / MEDIUM | 42.9 | 40.2 | 7/20 | 5.2 | 3.5 | 0 / 0 |
| entry 0 / prep_oriented / seeded / HIGH | 37.0 | 38.1 | 6/20 | 6.5 | 5.5 | 0 / 0 |
| entry 0 / seeded_legal / bite / MEDIUM | 7.2 | 7.5 | 18/20 | 66.8 | 41.9 | 0 / 0 |
| entry 0 / seeded_legal / bite / HIGH | 14.8 | 14.8 | 13/20 | 43.9 | 28.1 | 0 / 0 |
| entry 0 / seeded_legal / call / MEDIUM | 9.4 | 9.3 | 16/20 | 69.5 | 44.5 | 0 / 0 |
| entry 0 / seeded_legal / call / HIGH | 17.0 | 18.7 | 13/20 | 27.9 | 16.2 | 0 / 0 |
| entry 0 / seeded_legal / balanced / MEDIUM | 1.5 | 1.7 | 20/20 | 82.5 | 53.2 | 0 / 0 |
| entry 0 / seeded_legal / balanced / HIGH | 17.4 | 18.8 | 13/20 | 32.2 | 18.7 | 0 / 0 |
| entry 0 / seeded_legal / fallback / MEDIUM | 45.0 | 47.4 | 5/20 | 9.8 | 4.9 | 0 / 0 |
| entry 0 / seeded_legal / fallback / HIGH | 30.9 | 35.9 | 10/20 | 16.4 | 9.3 | 0 / 0 |
| entry 0 / seeded_legal / seeded / MEDIUM | 37.0 | 40.8 | 5/20 | 8.1 | 5.3 | 0 / 0 |
| entry 0 / seeded_legal / seeded / HIGH | 26.9 | 32.3 | 6/20 | 8.3 | 5.1 | 0 / 0 |
| entry 1 / pass / bite / MEDIUM | 93.0 | 53.0 | 0/1 | 0.0 | 0.0 | 0 / 0 |
| entry 1 / pass / bite / HIGH | 93.0 | 53.0 | 0/1 | 0.0 | 0.0 | 0 / 0 |
| entry 1 / pass / call / MEDIUM | 93.0 | 53.0 | 0/1 | 0.0 | 0.0 | 0 / 0 |
| entry 1 / pass / call / HIGH | 93.0 | 53.0 | 0/1 | 0.0 | 0.0 | 0 / 0 |
| entry 1 / pass / balanced / MEDIUM | 93.0 | 53.0 | 0/1 | 0.0 | 0.0 | 0 / 0 |
| entry 1 / pass / balanced / HIGH | 93.0 | 53.0 | 0/1 | 0.0 | 0.0 | 0 / 0 |
| entry 1 / pass / fallback / MEDIUM | 93.0 | 53.0 | 0/1 | 0.0 | 0.0 | 0 / 0 |
| entry 1 / pass / fallback / HIGH | 93.0 | 53.0 | 0/1 | 0.0 | 0.0 | 0 / 0 |
| entry 1 / pass / seeded / MEDIUM | 93.0 | 53.0 | 0/20 | 0.0 | 0.0 | 0 / 0 |
| entry 1 / pass / seeded / HIGH | 93.0 | 53.0 | 0/20 | 0.0 | 0.0 | 0 / 0 |
| entry 1 / direct_cycle / bite / MEDIUM | 30.0 | 1.0 | 1/1 | 5.0 | 2.0 | 0 / 0 |
| entry 1 / direct_cycle / bite / HIGH | 12.0 | 1.0 | 1/1 | 7.0 | 4.0 | 0 / 0 |
| entry 1 / direct_cycle / call / MEDIUM | 30.0 | 1.0 | 1/1 | 5.0 | 2.0 | 0 / 0 |
| entry 1 / direct_cycle / call / HIGH | 62.0 | 27.0 | 0/1 | 0.0 | 0.0 | 0 / 0 |
| entry 1 / direct_cycle / balanced / MEDIUM | 30.0 | 1.0 | 1/1 | 5.0 | 2.0 | 0 / 0 |
| entry 1 / direct_cycle / balanced / HIGH | 62.0 | 27.0 | 0/1 | 0.0 | 0.0 | 0 / 0 |
| entry 1 / direct_cycle / fallback / MEDIUM | 46.0 | 10.0 | 1/1 | 3.0 | 0.0 | 0 / 0 |
| entry 1 / direct_cycle / fallback / HIGH | 21.0 | 2.0 | 1/1 | 5.0 | 2.0 | 0 / 0 |
| entry 1 / direct_cycle / seeded / MEDIUM | 33.2 | 7.2 | 16/20 | 5.5 | 3.1 | 0 / 0 |
| entry 1 / direct_cycle / seeded / HIGH | 24.1 | 8.2 | 14/20 | 7.3 | 5.2 | 0 / 0 |
| entry 1 / feint_when_eligible / bite / MEDIUM | 48.0 | 2.0 | 1/1 | 2.0 | 0.0 | 0 / 0 |
| entry 1 / feint_when_eligible / bite / HIGH | 1.0 | 2.0 | 1/1 | 106.0 | 102.0 | 0 / 0 |
| entry 1 / feint_when_eligible / call / MEDIUM | 2.0 | 1.0 | 1/1 | 106.0 | 100.0 | 0 / 0 |
| entry 1 / feint_when_eligible / call / HIGH | 12.0 | 1.0 | 1/1 | 3.0 | 2.0 | 0 / 0 |
| entry 1 / feint_when_eligible / balanced / MEDIUM | 2.0 | 1.0 | 1/1 | 106.0 | 100.0 | 0 / 0 |
| entry 1 / feint_when_eligible / balanced / HIGH | 12.0 | 1.0 | 1/1 | 3.0 | 2.0 | 0 / 0 |
| entry 1 / feint_when_eligible / fallback / MEDIUM | 2.0 | 0.0 | 1/1 | 97.0 | 88.0 | 0 / 0 |
| entry 1 / feint_when_eligible / fallback / HIGH | 2.0 | 2.0 | 1/1 | 105.0 | 99.0 | 0 / 0 |
| entry 1 / feint_when_eligible / seeded / MEDIUM | 33.2 | 10.4 | 14/20 | 41.5 | 38.1 | 0 / 0 |
| entry 1 / feint_when_eligible / seeded / HIGH | 24.2 | 7.5 | 15/20 | 54.0 | 51.5 | 0 / 0 |
| entry 1 / prep_oriented / bite / MEDIUM | 23.0 | 1.0 | 1/1 | 7.0 | 4.0 | 0 / 0 |
| entry 1 / prep_oriented / bite / HIGH | 24.0 | 1.0 | 1/1 | 3.0 | 2.0 | 0 / 0 |
| entry 1 / prep_oriented / call / MEDIUM | 65.0 | 25.0 | 0/1 | 0.0 | 0.0 | 0 / 0 |
| entry 1 / prep_oriented / call / HIGH | 55.0 | 15.0 | 0/1 | 0.0 | 0.0 | 0 / 0 |
| entry 1 / prep_oriented / balanced / MEDIUM | 23.0 | 1.0 | 1/1 | 7.0 | 4.0 | 0 / 0 |
| entry 1 / prep_oriented / balanced / HIGH | 12.0 | 1.0 | 1/1 | 7.0 | 4.0 | 0 / 0 |
| entry 1 / prep_oriented / fallback / MEDIUM | 53.0 | 13.0 | 1/1 | 2.0 | 0.0 | 0 / 0 |
| entry 1 / prep_oriented / fallback / HIGH | 63.0 | 23.0 | 0/1 | 0.0 | 0.0 | 0 / 0 |
| entry 1 / prep_oriented / seeded / MEDIUM | 50.7 | 14.8 | 10/20 | 2.3 | 1.1 | 0 / 0 |
| entry 1 / prep_oriented / seeded / HIGH | 38.5 | 11.7 | 11/20 | 3.8 | 2.6 | 0 / 0 |
| entry 1 / seeded_legal / bite / MEDIUM | 29.3 | 3.4 | 19/20 | 10.8 | 3.7 | 0 / 0 |
| entry 1 / seeded_legal / bite / HIGH | 14.5 | 2.4 | 20/20 | 19.6 | 8.9 | 0 / 0 |
| entry 1 / seeded_legal / call / MEDIUM | 22.2 | 1.6 | 20/20 | 24.4 | 12.1 | 0 / 0 |
| entry 1 / seeded_legal / call / HIGH | 18.9 | 4.3 | 18/20 | 18.6 | 8.7 | 0 / 0 |
| entry 1 / seeded_legal / balanced / MEDIUM | 25.2 | 1.6 | 20/20 | 17.9 | 7.9 | 0 / 0 |
| entry 1 / seeded_legal / balanced / HIGH | 20.4 | 4.8 | 17/20 | 22.1 | 11.8 | 0 / 0 |
| entry 1 / seeded_legal / fallback / MEDIUM | 51.5 | 19.8 | 11/20 | 4.0 | 1.1 | 0 / 0 |
| entry 1 / seeded_legal / fallback / HIGH | 36.2 | 15.3 | 13/20 | 8.8 | 3.7 | 0 / 0 |
| entry 1 / seeded_legal / seeded / MEDIUM | 41.0 | 10.8 | 15/20 | 6.3 | 2.2 | 0 / 0 |
| entry 1 / seeded_legal / seeded / HIGH | 29.6 | 7.0 | 16/20 | 11.2 | 6.7 | 0 / 0 |
| entry 2 / pass / bite / MEDIUM | 93.0 | 17.0 | 1/1 | 59.0 | 0.0 | 0 / 0 |
| entry 2 / pass / bite / HIGH | 93.0 | 17.0 | 1/1 | 59.0 | 0.0 | 0 / 0 |
| entry 2 / pass / call / MEDIUM | 93.0 | 17.0 | 1/1 | 59.0 | 0.0 | 0 / 0 |
| entry 2 / pass / call / HIGH | 93.0 | 17.0 | 1/1 | 59.0 | 0.0 | 0 / 0 |
| entry 2 / pass / balanced / MEDIUM | 93.0 | 17.0 | 1/1 | 59.0 | 0.0 | 0 / 0 |
| entry 2 / pass / balanced / HIGH | 93.0 | 17.0 | 1/1 | 59.0 | 0.0 | 0 / 0 |
| entry 2 / pass / fallback / MEDIUM | 93.0 | 17.0 | 1/1 | 59.0 | 0.0 | 0 / 0 |
| entry 2 / pass / fallback / HIGH | 93.0 | 17.0 | 1/1 | 59.0 | 0.0 | 0 / 0 |
| entry 2 / pass / seeded / MEDIUM | 93.0 | 17.0 | 20/20 | 59.0 | 0.0 | 0 / 0 |
| entry 2 / pass / seeded / HIGH | 93.0 | 17.0 | 20/20 | 59.0 | 0.0 | 0 / 0 |
| entry 2 / direct_cycle / bite / MEDIUM | 72.0 | 0.0 | 1/1 | 3.0 | 1.0 | 0 / 0 |
| entry 2 / direct_cycle / bite / HIGH | 62.0 | 0.0 | 1/1 | 3.0 | 2.0 | 0 / 0 |
| entry 2 / direct_cycle / call / MEDIUM | 72.0 | 0.0 | 1/1 | 3.0 | 1.0 | 0 / 0 |
| entry 2 / direct_cycle / call / HIGH | 62.0 | 0.0 | 1/1 | 3.0 | 2.0 | 0 / 0 |
| entry 2 / direct_cycle / balanced / MEDIUM | 72.0 | 0.0 | 1/1 | 3.0 | 1.0 | 0 / 0 |
| entry 2 / direct_cycle / balanced / HIGH | 62.0 | 0.0 | 1/1 | 3.0 | 2.0 | 0 / 0 |
| entry 2 / direct_cycle / fallback / MEDIUM | 76.0 | 4.0 | 1/1 | 3.0 | 0.0 | 0 / 0 |
| entry 2 / direct_cycle / fallback / HIGH | 66.0 | 2.0 | 1/1 | 3.0 | 1.0 | 0 / 0 |
| entry 2 / direct_cycle / seeded / MEDIUM | 65.8 | 1.0 | 20/20 | 4.5 | 2.6 | 0 / 0 |
| entry 2 / direct_cycle / seeded / HIGH | 57.4 | 1.3 | 20/20 | 3.6 | 2.1 | 0 / 0 |
| entry 2 / feint_when_eligible / bite / MEDIUM | 0.0 | 0.0 | 1/1 | 101.0 | 95.0 | 0 / 0 |
| entry 2 / feint_when_eligible / bite / HIGH | 1.0 | 0.0 | 1/1 | 109.0 | 105.0 | 0 / 0 |
| entry 2 / feint_when_eligible / call / MEDIUM | 56.0 | 0.0 | 1/1 | 5.0 | 3.0 | 0 / 0 |
| entry 2 / feint_when_eligible / call / HIGH | 41.0 | 0.0 | 1/1 | 5.0 | 4.0 | 0 / 0 |
| entry 2 / feint_when_eligible / balanced / MEDIUM | 56.0 | 0.0 | 1/1 | 5.0 | 3.0 | 0 / 0 |
| entry 2 / feint_when_eligible / balanced / HIGH | 41.0 | 0.0 | 1/1 | 5.0 | 4.0 | 0 / 0 |
| entry 2 / feint_when_eligible / fallback / MEDIUM | 70.0 | 1.0 | 1/1 | 3.0 | 0.0 | 0 / 0 |
| entry 2 / feint_when_eligible / fallback / HIGH | 60.0 | 1.0 | 1/1 | 3.0 | 1.0 | 0 / 0 |
| entry 2 / feint_when_eligible / seeded / MEDIUM | 59.0 | 1.1 | 20/20 | 8.6 | 6.6 | 0 / 0 |
| entry 2 / feint_when_eligible / seeded / HIGH | 48.0 | 1.1 | 20/20 | 8.9 | 7.7 | 0 / 0 |
| entry 2 / prep_oriented / bite / MEDIUM | 65.0 | 0.0 | 1/1 | 5.0 | 3.0 | 0 / 0 |
| entry 2 / prep_oriented / bite / HIGH | 62.0 | 0.0 | 1/1 | 3.0 | 2.0 | 0 / 0 |
| entry 2 / prep_oriented / call / MEDIUM | 2.0 | 0.0 | 1/1 | 43.0 | 35.0 | 0 / 0 |
| entry 2 / prep_oriented / call / HIGH | 2.0 | 0.0 | 1/1 | 29.0 | 26.0 | 0 / 0 |
| entry 2 / prep_oriented / balanced / MEDIUM | 65.0 | 0.0 | 1/1 | 5.0 | 3.0 | 0 / 0 |
| entry 2 / prep_oriented / balanced / HIGH | 62.0 | 0.0 | 1/1 | 3.0 | 2.0 | 0 / 0 |
| entry 2 / prep_oriented / fallback / MEDIUM | 76.0 | 4.0 | 1/1 | 3.0 | 0.0 | 0 / 0 |
| entry 2 / prep_oriented / fallback / HIGH | 66.0 | 2.0 | 1/1 | 3.0 | 1.0 | 0 / 0 |
| entry 2 / prep_oriented / seeded / MEDIUM | 66.5 | 1.0 | 20/20 | 4.3 | 2.4 | 0 / 0 |
| entry 2 / prep_oriented / seeded / HIGH | 55.0 | 1.3 | 20/20 | 4.0 | 2.5 | 0 / 0 |
| entry 2 / seeded_legal / bite / MEDIUM | 57.5 | 0.0 | 20/20 | 10.3 | 4.5 | 0 / 0 |
| entry 2 / seeded_legal / bite / HIGH | 48.5 | 0.3 | 20/20 | 7.6 | 3.7 | 0 / 0 |
| entry 2 / seeded_legal / call / MEDIUM | 55.2 | 0.0 | 20/20 | 11.0 | 5.0 | 0 / 0 |
| entry 2 / seeded_legal / call / HIGH | 46.6 | 0.3 | 20/20 | 8.0 | 4.0 | 0 / 0 |
| entry 2 / seeded_legal / balanced / MEDIUM | 57.5 | 0.0 | 20/20 | 10.2 | 4.3 | 0 / 0 |
| entry 2 / seeded_legal / balanced / HIGH | 48.5 | 0.3 | 20/20 | 7.6 | 3.7 | 0 / 0 |
| entry 2 / seeded_legal / fallback / MEDIUM | 64.2 | 2.5 | 20/20 | 9.0 | 2.6 | 0 / 0 |
| entry 2 / seeded_legal / fallback / HIGH | 51.5 | 3.0 | 20/20 | 8.7 | 3.0 | 0 / 0 |
| entry 2 / seeded_legal / seeded / MEDIUM | 59.5 | 1.4 | 20/20 | 8.9 | 4.2 | 0 / 0 |
| entry 2 / seeded_legal / seeded / HIGH | 48.8 | 1.6 | 20/20 | 7.6 | 3.7 | 0 / 0 |
| entry 3 / pass / bite / MEDIUM | 53.0 | 93.0 | 0/1 | 0.0 | 0.0 | 0 / 0 |
| entry 3 / pass / bite / HIGH | 53.0 | 93.0 | 0/1 | 0.0 | 0.0 | 0 / 0 |
| entry 3 / pass / call / MEDIUM | 53.0 | 93.0 | 0/1 | 0.0 | 0.0 | 0 / 0 |
| entry 3 / pass / call / HIGH | 53.0 | 93.0 | 0/1 | 0.0 | 0.0 | 0 / 0 |
| entry 3 / pass / balanced / MEDIUM | 53.0 | 93.0 | 0/1 | 0.0 | 0.0 | 0 / 0 |
| entry 3 / pass / balanced / HIGH | 53.0 | 93.0 | 0/1 | 0.0 | 0.0 | 0 / 0 |
| entry 3 / pass / fallback / MEDIUM | 53.0 | 93.0 | 0/1 | 0.0 | 0.0 | 0 / 0 |
| entry 3 / pass / fallback / HIGH | 53.0 | 93.0 | 0/1 | 0.0 | 0.0 | 0 / 0 |
| entry 3 / pass / seeded / MEDIUM | 53.0 | 93.0 | 0/20 | 0.0 | 0.0 | 0 / 0 |
| entry 3 / pass / seeded / HIGH | 53.0 | 93.0 | 0/20 | 0.0 | 0.0 | 0 / 0 |
| entry 3 / direct_cycle / bite / MEDIUM | 11.0 | 51.0 | 1/1 | 2.0 | 0.0 | 0 / 0 |
| entry 3 / direct_cycle / bite / HIGH | 0.0 | 36.0 | 1/1 | 3.0 | 1.0 | 0 / 0 |
| entry 3 / direct_cycle / call / MEDIUM | 1.0 | 37.0 | 1/1 | 4.0 | 1.0 | 0 / 0 |
| entry 3 / direct_cycle / call / HIGH | 22.0 | 67.0 | 0/1 | 0.0 | 0.0 | 0 / 0 |
| entry 3 / direct_cycle / balanced / MEDIUM | 1.0 | 37.0 | 1/1 | 4.0 | 1.0 | 0 / 0 |
| entry 3 / direct_cycle / balanced / HIGH | 22.0 | 67.0 | 0/1 | 0.0 | 0.0 | 0 / 0 |
| entry 3 / direct_cycle / fallback / MEDIUM | 0.0 | 33.0 | 1/1 | 6.0 | 2.0 | 0 / 0 |
| entry 3 / direct_cycle / fallback / HIGH | 1.0 | 21.0 | 1/1 | 6.0 | 4.0 | 0 / 0 |
| entry 3 / direct_cycle / seeded / MEDIUM | 9.4 | 43.1 | 15/20 | 3.4 | 1.8 | 0 / 0 |
| entry 3 / direct_cycle / seeded / HIGH | 8.8 | 35.5 | 14/20 | 8.8 | 7.2 | 0 / 0 |
| entry 3 / feint_when_eligible / bite / MEDIUM | 8.0 | 42.0 | 1/1 | 2.0 | 0.0 | 0 / 0 |
| entry 3 / feint_when_eligible / bite / HIGH | 0.0 | 27.0 | 1/1 | 3.0 | 1.0 | 0 / 0 |
| entry 3 / feint_when_eligible / call / MEDIUM | 2.0 | 2.0 | 1/1 | 100.0 | 92.0 | 0 / 0 |
| entry 3 / feint_when_eligible / call / HIGH | 0.0 | 0.0 | 1/1 | 107.0 | 102.0 | 0 / 0 |
| entry 3 / feint_when_eligible / balanced / MEDIUM | 2.0 | 2.0 | 1/1 | 100.0 | 92.0 | 0 / 0 |
| entry 3 / feint_when_eligible / balanced / HIGH | 0.0 | 0.0 | 1/1 | 107.0 | 102.0 | 0 / 0 |
| entry 3 / feint_when_eligible / fallback / MEDIUM | 0.0 | 0.0 | 1/1 | 99.0 | 88.0 | 0 / 0 |
| entry 3 / feint_when_eligible / fallback / HIGH | 2.0 | 12.0 | 1/1 | 7.0 | 4.0 | 0 / 0 |
| entry 3 / feint_when_eligible / seeded / MEDIUM | 8.6 | 36.7 | 14/20 | 8.6 | 6.5 | 0 / 0 |
| entry 3 / feint_when_eligible / seeded / HIGH | 6.3 | 28.9 | 15/20 | 23.9 | 22.2 | 0 / 0 |
| entry 3 / prep_oriented / bite / MEDIUM | 1.0 | 30.0 | 1/1 | 6.0 | 3.0 | 0 / 0 |
| entry 3 / prep_oriented / bite / HIGH | 0.0 | 36.0 | 1/1 | 3.0 | 1.0 | 0 / 0 |
| entry 3 / prep_oriented / call / MEDIUM | 25.0 | 65.0 | 0/1 | 0.0 | 0.0 | 0 / 0 |
| entry 3 / prep_oriented / call / HIGH | 15.0 | 55.0 | 1/1 | 1.0 | 0.0 | 0 / 0 |
| entry 3 / prep_oriented / balanced / MEDIUM | 1.0 | 37.0 | 1/1 | 4.0 | 1.0 | 0 / 0 |
| entry 3 / prep_oriented / balanced / HIGH | 15.0 | 55.0 | 1/1 | 1.0 | 0.0 | 0 / 0 |
| entry 3 / prep_oriented / fallback / MEDIUM | 13.0 | 53.0 | 1/1 | 2.0 | 0.0 | 0 / 0 |
| entry 3 / prep_oriented / fallback / HIGH | 23.0 | 63.0 | 0/1 | 0.0 | 0.0 | 0 / 0 |
| entry 3 / prep_oriented / seeded / MEDIUM | 15.1 | 45.7 | 10/20 | 3.6 | 1.9 | 0 / 0 |
| entry 3 / prep_oriented / seeded / HIGH | 10.6 | 40.6 | 11/20 | 3.6 | 2.3 | 0 / 0 |
| entry 3 / seeded_legal / bite / MEDIUM | 5.1 | 39.2 | 19/20 | 6.1 | 1.3 | 0 / 0 |
| entry 3 / seeded_legal / bite / HIGH | 2.2 | 30.9 | 19/20 | 6.6 | 2.6 | 0 / 0 |
| entry 3 / seeded_legal / call / MEDIUM | 2.6 | 34.3 | 20/20 | 11.9 | 4.7 | 0 / 0 |
| entry 3 / seeded_legal / call / HIGH | 3.5 | 32.3 | 18/20 | 10.7 | 5.5 | 0 / 0 |
| entry 3 / seeded_legal / balanced / MEDIUM | 2.0 | 32.0 | 20/20 | 12.7 | 5.3 | 0 / 0 |
| entry 3 / seeded_legal / balanced / HIGH | 3.9 | 33.9 | 18/20 | 10.1 | 5.3 | 0 / 0 |
| entry 3 / seeded_legal / fallback / MEDIUM | 15.8 | 55.5 | 12/20 | 4.2 | 0.7 | 0 / 0 |
| entry 3 / seeded_legal / fallback / HIGH | 9.2 | 42.4 | 15/20 | 7.0 | 2.6 | 0 / 0 |
| entry 3 / seeded_legal / seeded / MEDIUM | 8.0 | 41.5 | 15/20 | 8.7 | 3.6 | 0 / 0 |
| entry 3 / seeded_legal / seeded / HIGH | 4.3 | 32.8 | 16/20 | 8.8 | 4.5 | 0 / 0 |
| entry 4 / pass / bite / MEDIUM | 53.0 | 53.0 | 0/1 | 0.0 | 0.0 | 0 / 0 |
| entry 4 / pass / bite / HIGH | 53.0 | 53.0 | 0/1 | 0.0 | 0.0 | 0 / 0 |
| entry 4 / pass / call / MEDIUM | 53.0 | 53.0 | 0/1 | 0.0 | 0.0 | 0 / 0 |
| entry 4 / pass / call / HIGH | 53.0 | 53.0 | 0/1 | 0.0 | 0.0 | 0 / 0 |
| entry 4 / pass / balanced / MEDIUM | 53.0 | 53.0 | 0/1 | 0.0 | 0.0 | 0 / 0 |
| entry 4 / pass / balanced / HIGH | 53.0 | 53.0 | 0/1 | 0.0 | 0.0 | 0 / 0 |
| entry 4 / pass / fallback / MEDIUM | 53.0 | 53.0 | 0/1 | 0.0 | 0.0 | 0 / 0 |
| entry 4 / pass / fallback / HIGH | 53.0 | 53.0 | 0/1 | 0.0 | 0.0 | 0 / 0 |
| entry 4 / pass / seeded / MEDIUM | 53.0 | 53.0 | 0/20 | 0.0 | 0.0 | 0 / 0 |
| entry 4 / pass / seeded / HIGH | 53.0 | 53.0 | 0/20 | 0.0 | 0.0 | 0 / 0 |
| entry 4 / direct_cycle / bite / MEDIUM | 1.0 | 1.0 | 1/1 | 110.0 | 104.0 | 0 / 0 |
| entry 4 / direct_cycle / bite / HIGH | 0.0 | 1.0 | 1/1 | 5.0 | 2.0 | 0 / 0 |
| entry 4 / direct_cycle / call / MEDIUM | 1.0 | 1.0 | 1/1 | 110.0 | 104.0 | 0 / 0 |
| entry 4 / direct_cycle / call / HIGH | 22.0 | 27.0 | 0/1 | 0.0 | 0.0 | 0 / 0 |
| entry 4 / direct_cycle / balanced / MEDIUM | 1.0 | 1.0 | 1/1 | 110.0 | 104.0 | 0 / 0 |
| entry 4 / direct_cycle / balanced / HIGH | 22.0 | 27.0 | 0/1 | 0.0 | 0.0 | 0 / 0 |
| entry 4 / direct_cycle / fallback / MEDIUM | 0.0 | 0.0 | 1/1 | 106.0 | 97.0 | 0 / 0 |
| entry 4 / direct_cycle / fallback / HIGH | 1.0 | 2.0 | 1/1 | 110.0 | 105.0 | 0 / 0 |
| entry 4 / direct_cycle / seeded / MEDIUM | 6.0 | 7.7 | 16/20 | 15.3 | 11.2 | 0 / 0 |
| entry 4 / direct_cycle / seeded / HIGH | 8.7 | 9.6 | 14/20 | 19.1 | 17.2 | 0 / 0 |
| entry 4 / feint_when_eligible / bite / MEDIUM | 8.0 | 2.0 | 1/1 | 4.0 | 0.0 | 0 / 0 |
| entry 4 / feint_when_eligible / bite / HIGH | 0.0 | 2.0 | 1/1 | 112.0 | 108.0 | 0 / 0 |
| entry 4 / feint_when_eligible / call / MEDIUM | 2.0 | 1.0 | 1/1 | 110.0 | 104.0 | 0 / 0 |
| entry 4 / feint_when_eligible / call / HIGH | 0.0 | 1.0 | 1/1 | 111.0 | 109.0 | 0 / 0 |
| entry 4 / feint_when_eligible / balanced / MEDIUM | 2.0 | 1.0 | 1/1 | 110.0 | 104.0 | 0 / 0 |
| entry 4 / feint_when_eligible / balanced / HIGH | 0.0 | 1.0 | 1/1 | 111.0 | 109.0 | 0 / 0 |
| entry 4 / feint_when_eligible / fallback / MEDIUM | 0.0 | 0.0 | 1/1 | 107.0 | 98.0 | 0 / 0 |
| entry 4 / feint_when_eligible / fallback / HIGH | 2.0 | 2.0 | 1/1 | 111.0 | 105.0 | 0 / 0 |
| entry 4 / feint_when_eligible / seeded / MEDIUM | 9.2 | 10.2 | 14/20 | 55.6 | 52.8 | 0 / 0 |
| entry 4 / feint_when_eligible / seeded / HIGH | 6.5 | 7.5 | 15/20 | 72.8 | 70.7 | 0 / 0 |
| entry 4 / prep_oriented / bite / MEDIUM | 1.0 | 1.0 | 1/1 | 110.0 | 104.0 | 0 / 0 |
| entry 4 / prep_oriented / bite / HIGH | 0.0 | 1.0 | 1/1 | 5.0 | 2.0 | 0 / 0 |
| entry 4 / prep_oriented / call / MEDIUM | 25.0 | 25.0 | 0/1 | 0.0 | 0.0 | 0 / 0 |
| entry 4 / prep_oriented / call / HIGH | 15.0 | 15.0 | 1/1 | 1.0 | 0.0 | 0 / 0 |
| entry 4 / prep_oriented / balanced / MEDIUM | 1.0 | 1.0 | 1/1 | 110.0 | 104.0 | 0 / 0 |
| entry 4 / prep_oriented / balanced / HIGH | 15.0 | 15.0 | 1/1 | 1.0 | 0.0 | 0 / 0 |
| entry 4 / prep_oriented / fallback / MEDIUM | 13.0 | 13.0 | 1/1 | 4.0 | 0.0 | 0 / 0 |
| entry 4 / prep_oriented / fallback / HIGH | 23.0 | 23.0 | 0/1 | 0.0 | 0.0 | 0 / 0 |
| entry 4 / prep_oriented / seeded / MEDIUM | 15.3 | 15.2 | 10/20 | 9.2 | 6.5 | 0 / 0 |
| entry 4 / prep_oriented / seeded / HIGH | 10.6 | 11.7 | 11/20 | 10.4 | 8.9 | 0 / 0 |
| entry 4 / seeded_legal / bite / MEDIUM | 2.6 | 3.1 | 19/20 | 95.4 | 60.8 | 0 / 0 |
| entry 4 / seeded_legal / bite / HIGH | 2.2 | 2.8 | 20/20 | 76.2 | 49.5 | 0 / 0 |
| entry 4 / seeded_legal / call / MEDIUM | 1.5 | 1.3 | 20/20 | 87.0 | 54.0 | 0 / 0 |
| entry 4 / seeded_legal / call / HIGH | 3.5 | 4.8 | 18/20 | 66.8 | 44.0 | 0 / 0 |
| entry 4 / seeded_legal / balanced / MEDIUM | 1.1 | 1.0 | 20/20 | 105.6 | 67.8 | 0 / 0 |
| entry 4 / seeded_legal / balanced / HIGH | 3.5 | 4.8 | 18/20 | 71.5 | 47.0 | 0 / 0 |
| entry 4 / seeded_legal / fallback / MEDIUM | 14.6 | 16.5 | 12/20 | 33.8 | 19.0 | 0 / 0 |
| entry 4 / seeded_legal / fallback / HIGH | 9.1 | 11.4 | 15/20 | 32.5 | 18.3 | 0 / 0 |
| entry 4 / seeded_legal / seeded / MEDIUM | 8.1 | 11.1 | 16/20 | 24.2 | 13.9 | 0 / 0 |
| entry 4 / seeded_legal / seeded / HIGH | 4.3 | 7.2 | 17/20 | 20.6 | 12.1 | 0 / 0 |

**Feints and the published LOW fallback** (totals over the cell's games; `effective` = final grade >= Success, `punished` = final grade <= Failure)
| cell | feint attempts | refused (by code) | accepted | bit | not bit | effective | neutral | punished | exits by a feint | exits capped (LOW) | fallbacks | undercommitment +1 | fallback modifier mismatches |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| entry 0 / direct_cycle / fallback / MEDIUM | 0 | - | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 59 | 18 | 0 |
| entry 0 / direct_cycle / fallback / HIGH | 0 | - | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 59 | 12 | 0 |
| entry 0 / feint_when_eligible / bite / MEDIUM | 6 | feint_not_eligible:2 | 4 | 4 | 0 | 4 | 0 | 0 | 1 | 0 | 0 | 0 | 0 |
| entry 0 / feint_when_eligible / bite / HIGH | 6 | feint_not_eligible:2 | 4 | 4 | 0 | 4 | 0 | 0 | 1 | 0 | 0 | 0 | 0 |
| entry 0 / feint_when_eligible / call / MEDIUM | 59 | feint_not_eligible:29, feint_requires_funding:24 | 6 | 0 | 6 | 0 | 0 | 6 | 0 | 0 | 0 | 0 | 0 |
| entry 0 / feint_when_eligible / call / HIGH | 59 | feint_not_eligible:28, feint_requires_funding:26 | 5 | 0 | 5 | 0 | 1 | 4 | 0 | 0 | 0 | 0 | 0 |
| entry 0 / feint_when_eligible / balanced / MEDIUM | 59 | feint_not_eligible:29, feint_requires_funding:24 | 6 | 0 | 6 | 0 | 0 | 6 | 0 | 0 | 0 | 0 | 0 |
| entry 0 / feint_when_eligible / balanced / HIGH | 59 | feint_not_eligible:29, feint_requires_funding:25 | 5 | 0 | 5 | 1 | 0 | 4 | 0 | 0 | 0 | 0 | 0 |
| entry 0 / feint_when_eligible / fallback / MEDIUM | 59 | feint_not_eligible:57 | 2 | 0 | 2 | 2 | 0 | 0 | 0 | 0 | 59 | 18 | 0 |
| entry 0 / feint_when_eligible / fallback / HIGH | 59 | feint_not_eligible:57 | 2 | 0 | 2 | 2 | 0 | 0 | 0 | 0 | 59 | 12 | 0 |
| entry 0 / feint_when_eligible / seeded / MEDIUM | 526 | feint_not_eligible:387, feint_requires_funding:54 | 85 | 26 | 59 | 36 | 28 | 21 | 12 | 0 | 0 | 0 | 0 |
| entry 0 / feint_when_eligible / seeded / HIGH | 576 | feint_not_eligible:449, feint_requires_funding:56 | 71 | 22 | 49 | 38 | 6 | 27 | 11 | 0 | 0 | 0 | 0 |
| entry 0 / prep_oriented / fallback / MEDIUM | 0 | - | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 0 |
| entry 0 / prep_oriented / fallback / HIGH | 0 | - | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 4 | 0 |
| entry 0 / seeded_legal / bite / MEDIUM | 95 | feint_not_eligible:84 | 11 | 11 | 0 | 11 | 0 | 0 | 2 | 0 | 0 | 0 | 0 |
| entry 0 / seeded_legal / bite / HIGH | 58 | feint_requires_funding:3, feint_not_eligible:43 | 12 | 12 | 0 | 12 | 0 | 0 | 4 | 0 | 0 | 0 | 0 |
| entry 0 / seeded_legal / call / MEDIUM | 91 | feint_not_eligible:84 | 7 | 0 | 7 | 0 | 0 | 7 | 0 | 0 | 0 | 0 | 0 |
| entry 0 / seeded_legal / call / HIGH | 41 | feint_not_eligible:33, feint_requires_funding:1 | 7 | 0 | 7 | 1 | 0 | 6 | 0 | 0 | 0 | 0 | 0 |
| entry 0 / seeded_legal / balanced / MEDIUM | 109 | feint_not_eligible:100 | 9 | 0 | 9 | 0 | 3 | 6 | 0 | 0 | 0 | 0 | 0 |
| entry 0 / seeded_legal / balanced / HIGH | 49 | feint_not_eligible:38, feint_requires_funding:1 | 10 | 0 | 10 | 4 | 0 | 6 | 2 | 0 | 0 | 0 | 0 |
| entry 0 / seeded_legal / fallback / MEDIUM | 36 | feint_not_eligible:22, feint_requires_funding:3 | 11 | 0 | 11 | 11 | 0 | 0 | 0 | 0 | 234 | 186 | 0 |
| entry 0 / seeded_legal / fallback / HIGH | 33 | feint_not_eligible:22, feint_requires_funding:1 | 10 | 0 | 10 | 10 | 0 | 0 | 1 | 0 | 250 | 162 | 0 |
| entry 0 / seeded_legal / seeded / MEDIUM | 36 | feint_not_eligible:12, feint_requires_funding:7 | 17 | 5 | 12 | 7 | 5 | 5 | 4 | 0 | 0 | 0 | 0 |
| entry 0 / seeded_legal / seeded / HIGH | 36 | feint_not_eligible:13, feint_requires_funding:7 | 16 | 5 | 11 | 9 | 2 | 5 | 4 | 0 | 0 | 0 | 0 |
| entry 1 / direct_cycle / fallback / MEDIUM | 0 | - | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 9 | 9 | 0 |
| entry 1 / direct_cycle / fallback / HIGH | 0 | - | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 9 | 8 | 0 |
| entry 1 / feint_when_eligible / bite / MEDIUM | 6 | feint_not_eligible:2 | 4 | 4 | 0 | 4 | 0 | 0 | 1 | 0 | 0 | 0 | 0 |
| entry 1 / feint_when_eligible / bite / HIGH | 59 | feint_not_eligible:56 | 3 | 3 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| entry 1 / feint_when_eligible / call / MEDIUM | 59 | feint_not_eligible:29, feint_requires_funding:24 | 6 | 0 | 6 | 0 | 4 | 2 | 0 | 0 | 0 | 0 | 0 |
| entry 1 / feint_when_eligible / call / HIGH | 7 | feint_not_eligible:3 | 4 | 0 | 4 | 2 | 0 | 2 | 1 | 0 | 0 | 0 | 0 |
| entry 1 / feint_when_eligible / balanced / MEDIUM | 59 | feint_not_eligible:29, feint_requires_funding:24 | 6 | 0 | 6 | 0 | 4 | 2 | 0 | 0 | 0 | 0 | 0 |
| entry 1 / feint_when_eligible / balanced / HIGH | 7 | feint_not_eligible:3 | 4 | 0 | 4 | 2 | 0 | 2 | 1 | 0 | 0 | 0 | 0 |
| entry 1 / feint_when_eligible / fallback / MEDIUM | 59 | feint_not_eligible:57 | 2 | 0 | 2 | 2 | 0 | 0 | 0 | 0 | 59 | 16 | 0 |
| entry 1 / feint_when_eligible / fallback / HIGH | 59 | feint_not_eligible:57 | 2 | 0 | 2 | 2 | 0 | 0 | 0 | 0 | 59 | 10 | 0 |
| entry 1 / feint_when_eligible / seeded / MEDIUM | 523 | feint_not_eligible:404, feint_requires_funding:46 | 73 | 21 | 52 | 30 | 22 | 21 | 12 | 0 | 0 | 0 | 0 |
| entry 1 / feint_when_eligible / seeded / HIGH | 628 | feint_requires_funding:51, feint_not_eligible:515 | 62 | 19 | 43 | 33 | 4 | 25 | 10 | 0 | 0 | 0 | 0 |
| entry 1 / prep_oriented / fallback / MEDIUM | 0 | - | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 0 |
| entry 1 / prep_oriented / fallback / HIGH | 0 | - | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 4 | 0 |
| entry 1 / seeded_legal / bite / MEDIUM | 29 | feint_not_eligible:17, feint_requires_funding:1 | 11 | 11 | 0 | 11 | 0 | 0 | 4 | 0 | 0 | 0 | 0 |
| entry 1 / seeded_legal / bite / HIGH | 36 | feint_not_eligible:28 | 8 | 8 | 0 | 8 | 0 | 0 | 3 | 0 | 0 | 0 | 0 |
| entry 1 / seeded_legal / call / MEDIUM | 40 | feint_not_eligible:25, feint_requires_funding:6 | 9 | 0 | 9 | 0 | 3 | 6 | 0 | 0 | 0 | 0 | 0 |
| entry 1 / seeded_legal / call / HIGH | 37 | feint_not_eligible:30, feint_requires_funding:1 | 6 | 0 | 6 | 1 | 0 | 5 | 1 | 0 | 0 | 0 | 0 |
| entry 1 / seeded_legal / balanced / MEDIUM | 39 | feint_not_eligible:26, feint_requires_funding:4 | 9 | 0 | 9 | 0 | 5 | 4 | 0 | 0 | 0 | 0 | 0 |
| entry 1 / seeded_legal / balanced / HIGH | 40 | feint_not_eligible:30, feint_requires_funding:2 | 8 | 0 | 8 | 4 | 0 | 4 | 3 | 0 | 0 | 0 | 0 |
| entry 1 / seeded_legal / fallback / MEDIUM | 25 | feint_not_eligible:11, feint_requires_funding:3 | 11 | 0 | 11 | 10 | 1 | 0 | 3 | 0 | 158 | 147 | 0 |
| entry 1 / seeded_legal / fallback / HIGH | 26 | feint_not_eligible:14, feint_requires_funding:2 | 10 | 0 | 10 | 10 | 0 | 0 | 3 | 1 | 162 | 129 | 0 |
| entry 1 / seeded_legal / seeded / MEDIUM | 28 | feint_not_eligible:9, feint_requires_funding:1 | 18 | 5 | 13 | 10 | 3 | 5 | 5 | 1 | 0 | 0 | 0 |
| entry 1 / seeded_legal / seeded / HIGH | 31 | feint_not_eligible:8, feint_requires_funding:8 | 15 | 5 | 10 | 10 | 1 | 4 | 6 | 0 | 0 | 0 | 0 |
| entry 2 / direct_cycle / fallback / MEDIUM | 0 | - | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 3 | 0 |
| entry 2 / direct_cycle / fallback / HIGH | 0 | - | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 3 | 0 |
| entry 2 / feint_when_eligible / bite / MEDIUM | 59 | feint_not_eligible:57 | 2 | 2 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| entry 2 / feint_when_eligible / bite / HIGH | 59 | feint_not_eligible:57 | 2 | 2 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| entry 2 / feint_when_eligible / call / MEDIUM | 5 | feint_not_eligible:2 | 3 | 0 | 3 | 2 | 0 | 1 | 1 | 0 | 0 | 0 | 0 |
| entry 2 / feint_when_eligible / call / HIGH | 5 | feint_not_eligible:2 | 3 | 0 | 3 | 2 | 0 | 1 | 1 | 0 | 0 | 0 | 0 |
| entry 2 / feint_when_eligible / balanced / MEDIUM | 5 | feint_not_eligible:2 | 3 | 0 | 3 | 2 | 0 | 1 | 1 | 0 | 0 | 0 | 0 |
| entry 2 / feint_when_eligible / balanced / HIGH | 5 | feint_not_eligible:2 | 3 | 0 | 3 | 2 | 0 | 1 | 1 | 0 | 0 | 0 | 0 |
| entry 2 / feint_when_eligible / fallback / MEDIUM | 3 | - | 3 | 0 | 3 | 2 | 1 | 0 | 1 | 0 | 3 | 3 | 0 |
| entry 2 / feint_when_eligible / fallback / HIGH | 3 | - | 3 | 0 | 3 | 2 | 1 | 0 | 1 | 0 | 3 | 3 | 0 |
| entry 2 / feint_when_eligible / seeded / MEDIUM | 128 | feint_requires_funding:25, feint_not_eligible:48 | 55 | 13 | 42 | 41 | 1 | 13 | 19 | 0 | 0 | 0 | 0 |
| entry 2 / feint_when_eligible / seeded / HIGH | 128 | feint_requires_funding:25, feint_not_eligible:48 | 55 | 13 | 42 | 41 | 1 | 13 | 19 | 0 | 0 | 0 | 0 |
| entry 2 / prep_oriented / fallback / MEDIUM | 0 | - | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 3 | 0 |
| entry 2 / prep_oriented / fallback / HIGH | 0 | - | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 3 | 0 |
| entry 2 / seeded_legal / bite / MEDIUM | 20 | feint_not_eligible:12, feint_requires_funding:1 | 7 | 7 | 0 | 7 | 0 | 0 | 3 | 0 | 0 | 0 | 0 |
| entry 2 / seeded_legal / bite / HIGH | 15 | feint_not_eligible:9, feint_requires_funding:1 | 5 | 5 | 0 | 5 | 0 | 0 | 2 | 0 | 0 | 0 | 0 |
| entry 2 / seeded_legal / call / MEDIUM | 23 | feint_not_eligible:14, feint_requires_funding:2 | 7 | 0 | 7 | 4 | 0 | 3 | 3 | 0 | 0 | 0 | 0 |
| entry 2 / seeded_legal / call / HIGH | 16 | feint_not_eligible:9, feint_requires_funding:1 | 6 | 0 | 6 | 3 | 0 | 3 | 3 | 0 | 0 | 0 | 0 |
| entry 2 / seeded_legal / balanced / MEDIUM | 20 | feint_not_eligible:13, feint_requires_funding:1 | 6 | 0 | 6 | 3 | 0 | 3 | 3 | 0 | 0 | 0 | 0 |
| entry 2 / seeded_legal / balanced / HIGH | 15 | feint_not_eligible:9, feint_requires_funding:1 | 5 | 0 | 5 | 2 | 0 | 3 | 2 | 0 | 0 | 0 | 0 |
| entry 2 / seeded_legal / fallback / MEDIUM | 19 | feint_not_eligible:11 | 8 | 0 | 8 | 7 | 0 | 1 | 4 | 0 | 114 | 90 | 0 |
| entry 2 / seeded_legal / fallback / HIGH | 17 | feint_not_eligible:8, feint_requires_funding:1 | 8 | 0 | 8 | 8 | 0 | 0 | 4 | 0 | 104 | 80 | 0 |
| entry 2 / seeded_legal / seeded / MEDIUM | 21 | feint_not_eligible:7, feint_requires_funding:3 | 11 | 2 | 9 | 8 | 0 | 3 | 5 | 0 | 0 | 0 | 0 |
| entry 2 / seeded_legal / seeded / HIGH | 19 | feint_not_eligible:7, feint_requires_funding:3 | 9 | 2 | 7 | 7 | 0 | 2 | 4 | 0 | 0 | 0 | 0 |
| entry 3 / direct_cycle / fallback / MEDIUM | 0 | - | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 12 | 11 | 0 |
| entry 3 / direct_cycle / fallback / HIGH | 0 | - | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 10 | 9 | 0 |
| entry 3 / feint_when_eligible / bite / MEDIUM | 6 | feint_not_eligible:2 | 4 | 4 | 0 | 4 | 0 | 0 | 1 | 0 | 0 | 0 | 0 |
| entry 3 / feint_when_eligible / bite / HIGH | 6 | feint_not_eligible:2 | 4 | 4 | 0 | 4 | 0 | 0 | 1 | 0 | 0 | 0 | 0 |
| entry 3 / feint_when_eligible / call / MEDIUM | 59 | feint_not_eligible:29, feint_requires_funding:27 | 3 | 0 | 3 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 |
| entry 3 / feint_when_eligible / call / HIGH | 59 | feint_not_eligible:29, feint_requires_funding:27 | 3 | 0 | 3 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 |
| entry 3 / feint_when_eligible / balanced / MEDIUM | 59 | feint_not_eligible:29, feint_requires_funding:27 | 3 | 0 | 3 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 |
| entry 3 / feint_when_eligible / balanced / HIGH | 59 | feint_not_eligible:29, feint_requires_funding:27 | 3 | 0 | 3 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 |
| entry 3 / feint_when_eligible / fallback / MEDIUM | 59 | feint_not_eligible:55 | 4 | 0 | 4 | 4 | 0 | 0 | 0 | 0 | 59 | 16 | 0 |
| entry 3 / feint_when_eligible / fallback / HIGH | 10 | feint_not_eligible:6 | 4 | 0 | 4 | 4 | 0 | 0 | 1 | 0 | 10 | 8 | 0 |
| entry 3 / feint_when_eligible / seeded / MEDIUM | 190 | feint_not_eligible:73, feint_requires_funding:22 | 95 | 26 | 69 | 52 | 27 | 16 | 19 | 0 | 0 | 0 | 0 |
| entry 3 / feint_when_eligible / seeded / HIGH | 327 | feint_not_eligible:223, feint_requires_funding:29 | 75 | 22 | 53 | 49 | 6 | 20 | 16 | 1 | 0 | 0 | 0 |
| entry 3 / prep_oriented / fallback / MEDIUM | 0 | - | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 0 |
| entry 3 / prep_oriented / fallback / HIGH | 0 | - | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 4 | 0 |
| entry 3 / seeded_legal / bite / MEDIUM | 21 | feint_not_eligible:9 | 12 | 12 | 0 | 12 | 0 | 0 | 5 | 0 | 0 | 0 | 0 |
| entry 3 / seeded_legal / bite / HIGH | 17 | feint_not_eligible:6, feint_requires_funding:1 | 10 | 10 | 0 | 10 | 0 | 0 | 4 | 0 | 0 | 0 | 0 |
| entry 3 / seeded_legal / call / MEDIUM | 26 | feint_not_eligible:18 | 8 | 0 | 8 | 1 | 0 | 7 | 1 | 0 | 0 | 0 | 0 |
| entry 3 / seeded_legal / call / HIGH | 22 | feint_not_eligible:14 | 8 | 0 | 8 | 3 | 0 | 5 | 3 | 0 | 0 | 0 | 0 |
| entry 3 / seeded_legal / balanced / MEDIUM | 29 | feint_not_eligible:20 | 9 | 0 | 9 | 1 | 2 | 6 | 1 | 0 | 0 | 0 | 0 |
| entry 3 / seeded_legal / balanced / HIGH | 22 | feint_not_eligible:12, feint_requires_funding:1 | 9 | 0 | 9 | 4 | 0 | 5 | 3 | 0 | 0 | 0 | 0 |
| entry 3 / seeded_legal / fallback / MEDIUM | 19 | feint_not_eligible:8 | 11 | 0 | 11 | 10 | 1 | 0 | 2 | 0 | 154 | 147 | 0 |
| entry 3 / seeded_legal / fallback / HIGH | 16 | feint_not_eligible:7 | 9 | 0 | 9 | 7 | 0 | 2 | 2 | 0 | 152 | 130 | 0 |
| entry 3 / seeded_legal / seeded / MEDIUM | 29 | feint_not_eligible:10, feint_requires_funding:1 | 18 | 5 | 13 | 9 | 3 | 6 | 4 | 0 | 0 | 0 | 0 |
| entry 3 / seeded_legal / seeded / HIGH | 32 | feint_not_eligible:13, feint_requires_funding:3 | 16 | 5 | 11 | 9 | 1 | 6 | 5 | 0 | 0 | 0 | 0 |
| entry 4 / direct_cycle / fallback / MEDIUM | 0 | - | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 59 | 10 | 0 |
| entry 4 / direct_cycle / fallback / HIGH | 0 | - | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 59 | 8 | 0 |
| entry 4 / feint_when_eligible / bite / MEDIUM | 6 | feint_not_eligible:2 | 4 | 4 | 0 | 4 | 0 | 0 | 1 | 0 | 0 | 0 | 0 |
| entry 4 / feint_when_eligible / bite / HIGH | 59 | feint_not_eligible:29, feint_requires_funding:27 | 3 | 3 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| entry 4 / feint_when_eligible / call / MEDIUM | 59 | feint_not_eligible:29, feint_requires_funding:27 | 3 | 0 | 3 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 |
| entry 4 / feint_when_eligible / call / HIGH | 59 | feint_not_eligible:29, feint_requires_funding:27 | 3 | 0 | 3 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 |
| entry 4 / feint_when_eligible / balanced / MEDIUM | 59 | feint_not_eligible:29, feint_requires_funding:27 | 3 | 0 | 3 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 |
| entry 4 / feint_when_eligible / balanced / HIGH | 59 | feint_not_eligible:29, feint_requires_funding:27 | 3 | 0 | 3 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 |
| entry 4 / feint_when_eligible / fallback / MEDIUM | 59 | feint_not_eligible:57 | 2 | 0 | 2 | 2 | 0 | 0 | 0 | 0 | 59 | 10 | 0 |
| entry 4 / feint_when_eligible / fallback / HIGH | 59 | feint_not_eligible:57 | 2 | 0 | 2 | 2 | 0 | 0 | 0 | 0 | 59 | 6 | 0 |
| entry 4 / feint_when_eligible / seeded / MEDIUM | 629 | feint_not_eligible:477, feint_requires_funding:78 | 74 | 21 | 53 | 32 | 21 | 21 | 10 | 0 | 0 | 0 | 0 |
| entry 4 / feint_when_eligible / seeded / HIGH | 788 | feint_requires_funding:175, feint_not_eligible:551 | 62 | 19 | 43 | 32 | 6 | 24 | 7 | 3 | 0 | 0 | 0 |
| entry 4 / prep_oriented / fallback / MEDIUM | 0 | - | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 0 |
| entry 4 / prep_oriented / fallback / HIGH | 0 | - | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 4 | 0 |
| entry 4 / seeded_legal / bite / MEDIUM | 104 | feint_not_eligible:88, feint_requires_funding:6 | 10 | 10 | 0 | 10 | 0 | 0 | 2 | 0 | 0 | 0 | 0 |
| entry 4 / seeded_legal / bite / HIGH | 81 | feint_requires_funding:17, feint_not_eligible:56 | 8 | 8 | 0 | 8 | 0 | 0 | 2 | 0 | 0 | 0 | 0 |
| entry 4 / seeded_legal / call / MEDIUM | 91 | feint_not_eligible:84 | 7 | 0 | 7 | 0 | 0 | 7 | 0 | 0 | 0 | 0 | 0 |
| entry 4 / seeded_legal / call / HIGH | 66 | feint_not_eligible:57, feint_requires_funding:3 | 6 | 0 | 6 | 1 | 0 | 5 | 1 | 0 | 0 | 0 | 0 |
| entry 4 / seeded_legal / balanced / MEDIUM | 111 | feint_not_eligible:99, feint_requires_funding:4 | 8 | 0 | 8 | 0 | 2 | 6 | 0 | 0 | 0 | 0 | 0 |
| entry 4 / seeded_legal / balanced / HIGH | 72 | feint_not_eligible:58, feint_requires_funding:7 | 7 | 0 | 7 | 2 | 0 | 5 | 1 | 0 | 0 | 0 | 0 |
| entry 4 / seeded_legal / fallback / MEDIUM | 47 | feint_not_eligible:35, feint_requires_funding:2 | 10 | 0 | 10 | 9 | 1 | 0 | 1 | 0 | 335 | 146 | 0 |
| entry 4 / seeded_legal / fallback / HIGH | 37 | feint_requires_funding:3, feint_not_eligible:25 | 9 | 0 | 9 | 8 | 1 | 0 | 2 | 0 | 295 | 123 | 0 |
| entry 4 / seeded_legal / seeded / MEDIUM | 44 | feint_not_eligible:15, feint_requires_funding:14 | 15 | 4 | 11 | 7 | 4 | 4 | 3 | 0 | 0 | 0 | 0 |
| entry 4 / seeded_legal / seeded / HIGH | 40 | feint_not_eligible:13, feint_requires_funding:14 | 13 | 4 | 9 | 6 | 1 | 6 | 2 | 0 | 0 | 0 | 0 |

**Positional trajectory** (one comparable axis, positive = Top advantage: Mount `axis`, Half Guard `axis_tenths / 10`; means over games)
| cell | final axis (mean) | lowest axis reached (mean) | highest axis reached (mean) |
|---|---|---|---|
| entry 0 / pass / bite / MEDIUM | +0.50 | +0.50 | +0.50 |
| entry 0 / pass / bite / HIGH | +0.50 | +0.50 | +0.50 |
| entry 0 / pass / call / MEDIUM | +0.50 | +0.50 | +0.50 |
| entry 0 / pass / call / HIGH | +0.50 | +0.50 | +0.50 |
| entry 0 / pass / balanced / MEDIUM | +0.50 | +0.50 | +0.50 |
| entry 0 / pass / balanced / HIGH | +0.50 | +0.50 | +0.50 |
| entry 0 / pass / fallback / MEDIUM | +0.50 | +0.50 | +0.50 |
| entry 0 / pass / fallback / HIGH | +0.50 | +0.50 | +0.50 |
| entry 0 / pass / seeded / MEDIUM | +0.50 | +0.50 | +0.50 |
| entry 0 / pass / seeded / HIGH | +0.50 | +0.50 | +0.50 |
| entry 0 / direct_cycle / bite / MEDIUM | -4.00 | -4.00 | +1.50 |
| entry 0 / direct_cycle / bite / HIGH | -3.50 | -3.50 | +0.50 |
| entry 0 / direct_cycle / call / MEDIUM | -4.00 | -4.00 | +2.50 |
| entry 0 / direct_cycle / call / HIGH | +3.50 | +1.50 | +3.50 |
| entry 0 / direct_cycle / balanced / MEDIUM | -4.00 | -4.00 | +2.50 |
| entry 0 / direct_cycle / balanced / HIGH | +3.50 | +1.50 | +3.50 |
| entry 0 / direct_cycle / fallback / MEDIUM | +0.50 | +0.50 | +2.50 |
| entry 0 / direct_cycle / fallback / HIGH | -2.50 | -2.50 | +2.50 |
| entry 0 / direct_cycle / seeded / MEDIUM | +0.42 | -1.55 | +2.48 |
| entry 0 / direct_cycle / seeded / HIGH | +0.47 | -1.50 | +2.38 |
| entry 0 / feint_when_eligible / bite / MEDIUM | -4.00 | -4.00 | +2.50 |
| entry 0 / feint_when_eligible / bite / HIGH | -4.00 | -4.00 | +2.50 |
| entry 0 / feint_when_eligible / call / MEDIUM | +4.00 | -3.50 | +4.00 |
| entry 0 / feint_when_eligible / call / HIGH | +4.00 | -1.50 | +4.00 |
| entry 0 / feint_when_eligible / balanced / MEDIUM | +4.00 | -3.50 | +4.00 |
| entry 0 / feint_when_eligible / balanced / HIGH | -4.00 | -4.00 | +0.50 |
| entry 0 / feint_when_eligible / fallback / MEDIUM | +4.00 | +0.50 | +4.00 |
| entry 0 / feint_when_eligible / fallback / HIGH | +4.00 | +0.50 | +4.00 |
| entry 0 / feint_when_eligible / seeded / MEDIUM | +0.62 | -1.32 | +2.58 |
| entry 0 / feint_when_eligible / seeded / HIGH | +0.68 | -1.20 | +2.73 |
| entry 0 / prep_oriented / bite / MEDIUM | -0.50 | -0.50 | +0.50 |
| entry 0 / prep_oriented / bite / HIGH | -4.00 | -4.00 | +0.50 |
| entry 0 / prep_oriented / call / MEDIUM | -3.50 | -3.50 | -0.50 |
| entry 0 / prep_oriented / call / HIGH | -4.00 | -4.00 | -0.50 |
| entry 0 / prep_oriented / balanced / MEDIUM | -4.00 | -4.00 | -0.50 |
| entry 0 / prep_oriented / balanced / HIGH | -4.00 | -4.00 | -0.50 |
| entry 0 / prep_oriented / fallback / MEDIUM | -4.00 | -4.00 | +0.50 |
| entry 0 / prep_oriented / fallback / HIGH | -4.00 | -4.00 | -0.50 |
| entry 0 / prep_oriented / seeded / MEDIUM | +1.85 | -0.40 | +3.00 |
| entry 0 / prep_oriented / seeded / HIGH | +2.30 | -0.53 | +3.20 |
| entry 0 / seeded_legal / bite / MEDIUM | -1.95 | -3.12 | +1.98 |
| entry 0 / seeded_legal / bite / HIGH | -1.62 | -2.83 | +1.98 |
| entry 0 / seeded_legal / call / MEDIUM | -2.52 | -3.30 | +1.48 |
| entry 0 / seeded_legal / call / HIGH | -1.02 | -2.30 | +1.88 |
| entry 0 / seeded_legal / balanced / MEDIUM | -2.25 | -3.15 | +1.80 |
| entry 0 / seeded_legal / balanced / HIGH | -1.38 | -2.40 | +1.73 |
| entry 0 / seeded_legal / fallback / MEDIUM | -0.03 | -1.68 | +2.65 |
| entry 0 / seeded_legal / fallback / HIGH | -0.70 | -2.05 | +2.40 |
| entry 0 / seeded_legal / seeded / MEDIUM | +2.45 | -0.30 | +3.45 |
| entry 0 / seeded_legal / seeded / HIGH | +1.73 | -0.35 | +3.35 |
| entry 1 / pass / bite / MEDIUM | +0.50 | +0.50 | +0.50 |
| entry 1 / pass / bite / HIGH | +0.50 | +0.50 | +0.50 |
| entry 1 / pass / call / MEDIUM | +0.50 | +0.50 | +0.50 |
| entry 1 / pass / call / HIGH | +0.50 | +0.50 | +0.50 |
| entry 1 / pass / balanced / MEDIUM | +0.50 | +0.50 | +0.50 |
| entry 1 / pass / balanced / HIGH | +0.50 | +0.50 | +0.50 |
| entry 1 / pass / fallback / MEDIUM | +0.50 | +0.50 | +0.50 |
| entry 1 / pass / fallback / HIGH | +0.50 | +0.50 | +0.50 |
| entry 1 / pass / seeded / MEDIUM | +0.50 | +0.50 | +0.50 |
| entry 1 / pass / seeded / HIGH | +0.50 | +0.50 | +0.50 |
| entry 1 / direct_cycle / bite / MEDIUM | +3.50 | -0.50 | +3.50 |
| entry 1 / direct_cycle / bite / HIGH | +3.50 | -1.50 | +3.50 |
| entry 1 / direct_cycle / call / MEDIUM | +4.00 | +0.50 | +4.00 |
| entry 1 / direct_cycle / call / HIGH | +3.50 | +1.50 | +3.50 |
| entry 1 / direct_cycle / balanced / MEDIUM | +4.00 | +0.50 | +4.00 |
| entry 1 / direct_cycle / balanced / HIGH | +3.50 | +1.50 | +3.50 |
| entry 1 / direct_cycle / fallback / MEDIUM | +4.00 | +0.50 | +4.00 |
| entry 1 / direct_cycle / fallback / HIGH | +4.00 | +1.50 | +4.00 |
| entry 1 / direct_cycle / seeded / MEDIUM | +3.90 | -0.75 | +3.90 |
| entry 1 / direct_cycle / seeded / HIGH | +2.80 | -0.53 | +3.15 |
| entry 1 / feint_when_eligible / bite / MEDIUM | -3.50 | -3.50 | +2.50 |
| entry 1 / feint_when_eligible / bite / HIGH | +3.00 | -2.50 | +4.00 |
| entry 1 / feint_when_eligible / call / MEDIUM | +4.00 | -1.50 | +4.00 |
| entry 1 / feint_when_eligible / call / HIGH | +4.00 | -0.50 | +4.00 |
| entry 1 / feint_when_eligible / balanced / MEDIUM | +4.00 | -1.50 | +4.00 |
| entry 1 / feint_when_eligible / balanced / HIGH | +4.00 | -0.50 | +4.00 |
| entry 1 / feint_when_eligible / fallback / MEDIUM | +4.00 | +0.50 | +4.00 |
| entry 1 / feint_when_eligible / fallback / HIGH | +4.00 | +0.50 | +4.00 |
| entry 1 / feint_when_eligible / seeded / MEDIUM | +1.30 | -0.78 | +2.70 |
| entry 1 / feint_when_eligible / seeded / HIGH | +1.73 | -0.70 | +2.95 |
| entry 1 / prep_oriented / bite / MEDIUM | +4.00 | -0.50 | +4.00 |
| entry 1 / prep_oriented / bite / HIGH | +4.00 | -0.50 | +4.00 |
| entry 1 / prep_oriented / call / MEDIUM | -3.50 | -3.50 | -0.50 |
| entry 1 / prep_oriented / call / HIGH | -4.00 | -4.00 | -0.50 |
| entry 1 / prep_oriented / balanced / MEDIUM | +4.00 | -1.50 | +4.00 |
| entry 1 / prep_oriented / balanced / HIGH | +3.50 | -2.50 | +3.50 |
| entry 1 / prep_oriented / fallback / MEDIUM | -4.00 | -4.00 | +0.50 |
| entry 1 / prep_oriented / fallback / HIGH | -4.00 | -4.00 | -0.50 |
| entry 1 / prep_oriented / seeded / MEDIUM | +2.67 | +0.03 | +3.20 |
| entry 1 / prep_oriented / seeded / HIGH | +2.80 | +0.07 | +3.30 |
| entry 1 / seeded_legal / bite / MEDIUM | +3.92 | -1.15 | +3.92 |
| entry 1 / seeded_legal / bite / HIGH | +3.55 | -0.88 | +3.95 |
| entry 1 / seeded_legal / call / MEDIUM | +2.67 | -1.62 | +3.35 |
| entry 1 / seeded_legal / call / HIGH | +2.35 | -1.02 | +3.27 |
| entry 1 / seeded_legal / balanced / MEDIUM | +3.90 | -1.25 | +3.95 |
| entry 1 / seeded_legal / balanced / HIGH | +2.70 | -0.97 | +3.42 |
| entry 1 / seeded_legal / fallback / MEDIUM | +2.65 | -0.55 | +3.25 |
| entry 1 / seeded_legal / fallback / HIGH | +2.27 | -0.88 | +3.15 |
| entry 1 / seeded_legal / seeded / MEDIUM | +3.58 | +0.03 | +3.70 |
| entry 1 / seeded_legal / seeded / HIGH | +3.12 | -0.03 | +3.70 |
| entry 2 / pass / bite / MEDIUM | +0.50 | +0.50 | +0.50 |
| entry 2 / pass / bite / HIGH | +0.50 | +0.50 | +0.50 |
| entry 2 / pass / call / MEDIUM | +0.50 | +0.50 | +0.50 |
| entry 2 / pass / call / HIGH | +0.50 | +0.50 | +0.50 |
| entry 2 / pass / balanced / MEDIUM | +0.50 | +0.50 | +0.50 |
| entry 2 / pass / balanced / HIGH | +0.50 | +0.50 | +0.50 |
| entry 2 / pass / fallback / MEDIUM | +0.50 | +0.50 | +0.50 |
| entry 2 / pass / fallback / HIGH | +0.50 | +0.50 | +0.50 |
| entry 2 / pass / seeded / MEDIUM | +0.50 | +0.50 | +0.50 |
| entry 2 / pass / seeded / HIGH | +0.50 | +0.50 | +0.50 |
| entry 2 / direct_cycle / bite / MEDIUM | +4.00 | +0.50 | +4.00 |
| entry 2 / direct_cycle / bite / HIGH | +4.00 | +1.50 | +4.00 |
| entry 2 / direct_cycle / call / MEDIUM | +4.00 | +1.50 | +4.00 |
| entry 2 / direct_cycle / call / HIGH | +4.00 | +2.50 | +4.00 |
| entry 2 / direct_cycle / balanced / MEDIUM | +4.00 | +1.50 | +4.00 |
| entry 2 / direct_cycle / balanced / HIGH | +4.00 | +2.50 | +4.00 |
| entry 2 / direct_cycle / fallback / MEDIUM | +4.00 | +2.50 | +4.00 |
| entry 2 / direct_cycle / fallback / HIGH | +4.00 | +2.50 | +4.00 |
| entry 2 / direct_cycle / seeded / MEDIUM | +3.88 | +1.45 | +3.88 |
| entry 2 / direct_cycle / seeded / HIGH | +3.90 | +1.85 | +3.90 |
| entry 2 / feint_when_eligible / bite / MEDIUM | +3.00 | +1.50 | +4.00 |
| entry 2 / feint_when_eligible / bite / HIGH | +3.00 | +1.50 | +4.00 |
| entry 2 / feint_when_eligible / call / MEDIUM | +4.00 | -0.50 | +4.00 |
| entry 2 / feint_when_eligible / call / HIGH | +4.00 | -0.50 | +4.00 |
| entry 2 / feint_when_eligible / balanced / MEDIUM | +4.00 | -0.50 | +4.00 |
| entry 2 / feint_when_eligible / balanced / HIGH | +4.00 | -0.50 | +4.00 |
| entry 2 / feint_when_eligible / fallback / MEDIUM | +4.00 | +2.50 | +4.00 |
| entry 2 / feint_when_eligible / fallback / HIGH | +4.00 | +2.50 | +4.00 |
| entry 2 / feint_when_eligible / seeded / MEDIUM | +3.65 | +1.18 | +3.90 |
| entry 2 / feint_when_eligible / seeded / HIGH | +3.62 | +1.23 | +3.88 |
| entry 2 / prep_oriented / bite / MEDIUM | +4.00 | +0.50 | +4.00 |
| entry 2 / prep_oriented / bite / HIGH | +4.00 | +1.50 | +4.00 |
| entry 2 / prep_oriented / call / MEDIUM | -3.00 | -3.00 | +4.00 |
| entry 2 / prep_oriented / call / HIGH | -4.00 | -4.00 | +4.00 |
| entry 2 / prep_oriented / balanced / MEDIUM | +4.00 | +0.50 | +4.00 |
| entry 2 / prep_oriented / balanced / HIGH | +4.00 | +1.50 | +4.00 |
| entry 2 / prep_oriented / fallback / MEDIUM | +3.50 | +1.50 | +3.50 |
| entry 2 / prep_oriented / fallback / HIGH | +4.00 | +1.50 | +4.00 |
| entry 2 / prep_oriented / seeded / MEDIUM | +3.92 | +1.75 | +3.92 |
| entry 2 / prep_oriented / seeded / HIGH | +4.00 | +1.90 | +4.00 |
| entry 2 / seeded_legal / bite / MEDIUM | +4.00 | +0.35 | +4.00 |
| entry 2 / seeded_legal / bite / HIGH | +3.92 | +0.85 | +3.92 |
| entry 2 / seeded_legal / call / MEDIUM | +3.95 | +0.15 | +3.95 |
| entry 2 / seeded_legal / call / HIGH | +3.88 | +0.60 | +3.88 |
| entry 2 / seeded_legal / balanced / MEDIUM | +3.92 | +0.20 | +3.92 |
| entry 2 / seeded_legal / balanced / HIGH | +3.88 | +0.65 | +3.88 |
| entry 2 / seeded_legal / fallback / MEDIUM | +3.90 | +1.35 | +3.90 |
| entry 2 / seeded_legal / fallback / HIGH | +3.92 | +1.40 | +3.92 |
| entry 2 / seeded_legal / seeded / MEDIUM | +3.90 | +1.25 | +3.90 |
| entry 2 / seeded_legal / seeded / HIGH | +3.92 | +1.30 | +3.92 |
| entry 3 / pass / bite / MEDIUM | +0.50 | +0.50 | +0.50 |
| entry 3 / pass / bite / HIGH | +0.50 | +0.50 | +0.50 |
| entry 3 / pass / call / MEDIUM | +0.50 | +0.50 | +0.50 |
| entry 3 / pass / call / HIGH | +0.50 | +0.50 | +0.50 |
| entry 3 / pass / balanced / MEDIUM | +0.50 | +0.50 | +0.50 |
| entry 3 / pass / balanced / HIGH | +0.50 | +0.50 | +0.50 |
| entry 3 / pass / fallback / MEDIUM | +0.50 | +0.50 | +0.50 |
| entry 3 / pass / fallback / HIGH | +0.50 | +0.50 | +0.50 |
| entry 3 / pass / seeded / MEDIUM | +0.50 | +0.50 | +0.50 |
| entry 3 / pass / seeded / HIGH | +0.50 | +0.50 | +0.50 |
| entry 3 / direct_cycle / bite / MEDIUM | -3.50 | -3.50 | +1.50 |
| entry 3 / direct_cycle / bite / HIGH | -4.00 | -4.00 | +0.50 |
| entry 3 / direct_cycle / call / MEDIUM | -4.00 | -4.00 | +2.50 |
| entry 3 / direct_cycle / call / HIGH | +3.50 | +1.50 | +3.50 |
| entry 3 / direct_cycle / balanced / MEDIUM | -4.00 | -4.00 | +2.50 |
| entry 3 / direct_cycle / balanced / HIGH | +3.50 | +1.50 | +3.50 |
| entry 3 / direct_cycle / fallback / MEDIUM | -4.00 | -4.00 | +2.50 |
| entry 3 / direct_cycle / fallback / HIGH | -4.00 | -4.00 | +2.50 |
| entry 3 / direct_cycle / seeded / MEDIUM | -2.15 | -2.65 | +2.05 |
| entry 3 / direct_cycle / seeded / HIGH | -1.90 | -2.65 | +1.60 |
| entry 3 / feint_when_eligible / bite / MEDIUM | -4.00 | -4.00 | +2.50 |
| entry 3 / feint_when_eligible / bite / HIGH | -4.00 | -4.00 | +2.50 |
| entry 3 / feint_when_eligible / call / MEDIUM | +4.00 | -4.00 | +4.00 |
| entry 3 / feint_when_eligible / call / HIGH | +4.00 | -4.00 | +4.00 |
| entry 3 / feint_when_eligible / balanced / MEDIUM | +4.00 | -4.00 | +4.00 |
| entry 3 / feint_when_eligible / balanced / HIGH | +4.00 | -4.00 | +4.00 |
| entry 3 / feint_when_eligible / fallback / MEDIUM | +4.00 | -0.50 | +4.00 |
| entry 3 / feint_when_eligible / fallback / HIGH | -4.00 | -4.00 | +2.50 |
| entry 3 / feint_when_eligible / seeded / MEDIUM | -2.60 | -2.92 | +1.80 |
| entry 3 / feint_when_eligible / seeded / HIGH | -1.68 | -2.55 | +2.10 |
| entry 3 / prep_oriented / bite / MEDIUM | -4.00 | -4.00 | +0.50 |
| entry 3 / prep_oriented / bite / HIGH | -4.00 | -4.00 | +0.50 |
| entry 3 / prep_oriented / call / MEDIUM | -3.50 | -3.50 | -0.50 |
| entry 3 / prep_oriented / call / HIGH | -4.00 | -4.00 | -0.50 |
| entry 3 / prep_oriented / balanced / MEDIUM | -4.00 | -4.00 | -0.50 |
| entry 3 / prep_oriented / balanced / HIGH | -3.50 | -3.50 | -0.50 |
| entry 3 / prep_oriented / fallback / MEDIUM | -4.00 | -4.00 | +0.50 |
| entry 3 / prep_oriented / fallback / HIGH | -4.00 | -4.00 | -0.50 |
| entry 3 / prep_oriented / seeded / MEDIUM | -1.25 | -2.00 | +2.30 |
| entry 3 / prep_oriented / seeded / HIGH | -0.40 | -1.18 | +2.40 |
| entry 3 / seeded_legal / bite / MEDIUM | -3.08 | -3.42 | +1.38 |
| entry 3 / seeded_legal / bite / HIGH | -3.17 | -3.55 | +1.18 |
| entry 3 / seeded_legal / call / MEDIUM | -3.85 | -3.95 | +0.97 |
| entry 3 / seeded_legal / call / HIGH | -2.77 | -3.20 | +1.18 |
| entry 3 / seeded_legal / balanced / MEDIUM | -3.85 | -3.95 | +0.97 |
| entry 3 / seeded_legal / balanced / HIGH | -2.75 | -3.17 | +1.12 |
| entry 3 / seeded_legal / fallback / MEDIUM | -1.50 | -2.10 | +2.40 |
| entry 3 / seeded_legal / fallback / HIGH | -2.75 | -3.02 | +1.90 |
| entry 3 / seeded_legal / seeded / MEDIUM | -0.70 | -1.88 | +2.55 |
| entry 3 / seeded_legal / seeded / HIGH | -0.30 | -1.68 | +2.80 |
| entry 4 / pass / bite / MEDIUM | +0.50 | +0.50 | +0.50 |
| entry 4 / pass / bite / HIGH | +0.50 | +0.50 | +0.50 |
| entry 4 / pass / call / MEDIUM | +0.50 | +0.50 | +0.50 |
| entry 4 / pass / call / HIGH | +0.50 | +0.50 | +0.50 |
| entry 4 / pass / balanced / MEDIUM | +0.50 | +0.50 | +0.50 |
| entry 4 / pass / balanced / HIGH | +0.50 | +0.50 | +0.50 |
| entry 4 / pass / fallback / MEDIUM | +0.50 | +0.50 | +0.50 |
| entry 4 / pass / fallback / HIGH | +0.50 | +0.50 | +0.50 |
| entry 4 / pass / seeded / MEDIUM | +0.50 | +0.50 | +0.50 |
| entry 4 / pass / seeded / HIGH | +0.50 | +0.50 | +0.50 |
| entry 4 / direct_cycle / bite / MEDIUM | -4.00 | -4.00 | +1.50 |
| entry 4 / direct_cycle / bite / HIGH | -4.00 | -4.00 | +0.50 |
| entry 4 / direct_cycle / call / MEDIUM | -4.00 | -4.00 | +2.50 |
| entry 4 / direct_cycle / call / HIGH | +3.50 | +1.50 | +3.50 |
| entry 4 / direct_cycle / balanced / MEDIUM | -4.00 | -4.00 | +2.50 |
| entry 4 / direct_cycle / balanced / HIGH | +3.50 | +1.50 | +3.50 |
| entry 4 / direct_cycle / fallback / MEDIUM | +0.50 | +0.50 | +2.50 |
| entry 4 / direct_cycle / fallback / HIGH | -0.50 | -0.50 | +2.50 |
| entry 4 / direct_cycle / seeded / MEDIUM | +0.78 | -1.55 | +2.67 |
| entry 4 / direct_cycle / seeded / HIGH | +0.50 | -1.27 | +2.17 |
| entry 4 / feint_when_eligible / bite / MEDIUM | -4.00 | -4.00 | +2.50 |
| entry 4 / feint_when_eligible / bite / HIGH | -3.50 | -3.50 | +2.50 |
| entry 4 / feint_when_eligible / call / MEDIUM | +4.00 | -1.50 | +4.00 |
| entry 4 / feint_when_eligible / call / HIGH | +4.00 | -2.50 | +4.00 |
| entry 4 / feint_when_eligible / balanced / MEDIUM | +4.00 | -1.50 | +4.00 |
| entry 4 / feint_when_eligible / balanced / HIGH | +4.00 | -2.50 | +4.00 |
| entry 4 / feint_when_eligible / fallback / MEDIUM | +4.00 | +0.50 | +4.00 |
| entry 4 / feint_when_eligible / fallback / HIGH | +4.00 | +0.50 | +4.00 |
| entry 4 / feint_when_eligible / seeded / MEDIUM | +0.72 | -1.25 | +2.70 |
| entry 4 / feint_when_eligible / seeded / HIGH | +0.88 | -1.48 | +2.92 |
| entry 4 / prep_oriented / bite / MEDIUM | -0.50 | -0.50 | +0.50 |
| entry 4 / prep_oriented / bite / HIGH | -4.00 | -4.00 | +0.50 |
| entry 4 / prep_oriented / call / MEDIUM | -3.50 | -3.50 | -0.50 |
| entry 4 / prep_oriented / call / HIGH | -4.00 | -4.00 | -0.50 |
| entry 4 / prep_oriented / balanced / MEDIUM | -4.00 | -4.00 | -0.50 |
| entry 4 / prep_oriented / balanced / HIGH | -3.50 | -3.50 | -0.50 |
| entry 4 / prep_oriented / fallback / MEDIUM | -4.00 | -4.00 | +0.50 |
| entry 4 / prep_oriented / fallback / HIGH | -4.00 | -4.00 | -0.50 |
| entry 4 / prep_oriented / seeded / MEDIUM | +2.23 | -0.25 | +3.08 |
| entry 4 / prep_oriented / seeded / HIGH | +0.75 | -0.78 | +2.80 |
| entry 4 / seeded_legal / bite / MEDIUM | -1.90 | -3.12 | +1.85 |
| entry 4 / seeded_legal / bite / HIGH | -1.68 | -2.80 | +1.70 |
| entry 4 / seeded_legal / call / MEDIUM | -2.62 | -3.35 | +1.27 |
| entry 4 / seeded_legal / call / HIGH | -1.45 | -2.52 | +1.60 |
| entry 4 / seeded_legal / balanced / MEDIUM | -2.25 | -3.30 | +1.50 |
| entry 4 / seeded_legal / balanced / HIGH | -1.05 | -2.45 | +1.73 |
| entry 4 / seeded_legal / fallback / MEDIUM | +0.12 | -1.43 | +2.70 |
| entry 4 / seeded_legal / fallback / HIGH | -1.52 | -2.45 | +2.10 |
| entry 4 / seeded_legal / seeded / MEDIUM | +2.35 | -0.45 | +3.42 |
| entry 4 / seeded_legal / seeded / HIGH | +1.62 | -0.55 | +3.23 |

**No-progress sequences** (a window that leaves the positional fingerprint unchanged: Mount axis, band, setup tiers and submission stage; Half Guard axis, band and both readiness tiers)
| cell | longest no-progress streak (max) | mean | games with a streak of 10+ windows | policy errors | transitions checked | continuity violations |
|---|---|---|---|---|---|---|
| entry 0 / pass / bite / MEDIUM | 59 | 59.0 | 1/1 | 0 | 0 | 0 |
| entry 0 / pass / bite / HIGH | 59 | 59.0 | 1/1 | 0 | 0 | 0 |
| entry 0 / pass / call / MEDIUM | 59 | 59.0 | 1/1 | 0 | 0 | 0 |
| entry 0 / pass / call / HIGH | 59 | 59.0 | 1/1 | 0 | 0 | 0 |
| entry 0 / pass / balanced / MEDIUM | 59 | 59.0 | 1/1 | 0 | 0 | 0 |
| entry 0 / pass / balanced / HIGH | 59 | 59.0 | 1/1 | 0 | 0 | 0 |
| entry 0 / pass / fallback / MEDIUM | 59 | 59.0 | 1/1 | 0 | 0 | 0 |
| entry 0 / pass / fallback / HIGH | 59 | 59.0 | 1/1 | 0 | 0 | 0 |
| entry 0 / pass / seeded / MEDIUM | 59 | 59.0 | 20/20 | 0 | 0 | 0 |
| entry 0 / pass / seeded / HIGH | 59 | 59.0 | 20/20 | 0 | 0 | 0 |
| entry 0 / direct_cycle / bite / MEDIUM | 46 | 46.0 | 1/1 | 0 | 0 | 0 |
| entry 0 / direct_cycle / bite / HIGH | 0 | 0.0 | 0/1 | 0 | 0 | 0 |
| entry 0 / direct_cycle / call / MEDIUM | 42 | 42.0 | 1/1 | 0 | 0 | 0 |
| entry 0 / direct_cycle / call / HIGH | 0 | 0.0 | 0/1 | 0 | 0 | 0 |
| entry 0 / direct_cycle / balanced / MEDIUM | 42 | 42.0 | 1/1 | 0 | 0 | 0 |
| entry 0 / direct_cycle / balanced / HIGH | 0 | 0.0 | 0/1 | 0 | 0 | 0 |
| entry 0 / direct_cycle / fallback / MEDIUM | 3 | 3.0 | 0/1 | 0 | 0 | 0 |
| entry 0 / direct_cycle / fallback / HIGH | 3 | 3.0 | 0/1 | 0 | 0 | 0 |
| entry 0 / direct_cycle / seeded / MEDIUM | 5 | 1.8 | 0/20 | 0 | 0 | 0 |
| entry 0 / direct_cycle / seeded / HIGH | 3 | 1.1 | 0/20 | 0 | 0 | 0 |
| entry 0 / feint_when_eligible / bite / MEDIUM | 0 | 0.0 | 0/1 | 0 | 0 | 0 |
| entry 0 / feint_when_eligible / bite / HIGH | 0 | 0.0 | 0/1 | 0 | 0 | 0 |
| entry 0 / feint_when_eligible / call / MEDIUM | 38 | 38.0 | 1/1 | 0 | 0 | 0 |
| entry 0 / feint_when_eligible / call / HIGH | 43 | 43.0 | 1/1 | 0 | 0 | 0 |
| entry 0 / feint_when_eligible / balanced / MEDIUM | 38 | 38.0 | 1/1 | 0 | 0 | 0 |
| entry 0 / feint_when_eligible / balanced / HIGH | 46 | 46.0 | 1/1 | 0 | 0 | 0 |
| entry 0 / feint_when_eligible / fallback / MEDIUM | 44 | 44.0 | 1/1 | 0 | 0 | 0 |
| entry 0 / feint_when_eligible / fallback / HIGH | 48 | 48.0 | 1/1 | 0 | 0 | 0 |
| entry 0 / feint_when_eligible / seeded / MEDIUM | 11 | 3.5 | 1/20 | 0 | 0 | 0 |
| entry 0 / feint_when_eligible / seeded / HIGH | 11 | 3.1 | 1/20 | 0 | 0 | 0 |
| entry 0 / prep_oriented / bite / MEDIUM | 0 | 0.0 | 0/1 | 0 | 0 | 0 |
| entry 0 / prep_oriented / bite / HIGH | 0 | 0.0 | 0/1 | 0 | 0 | 0 |
| entry 0 / prep_oriented / call / MEDIUM | 0 | 0.0 | 0/1 | 0 | 0 | 0 |
| entry 0 / prep_oriented / call / HIGH | 0 | 0.0 | 0/1 | 0 | 0 | 0 |
| entry 0 / prep_oriented / balanced / MEDIUM | 50 | 50.0 | 1/1 | 0 | 0 | 0 |
| entry 0 / prep_oriented / balanced / HIGH | 0 | 0.0 | 0/1 | 0 | 0 | 0 |
| entry 0 / prep_oriented / fallback / MEDIUM | 1 | 1.0 | 0/1 | 0 | 0 | 0 |
| entry 0 / prep_oriented / fallback / HIGH | 0 | 0.0 | 0/1 | 0 | 0 | 0 |
| entry 0 / prep_oriented / seeded / MEDIUM | 4 | 1.3 | 0/20 | 0 | 0 | 0 |
| entry 0 / prep_oriented / seeded / HIGH | 1 | 0.6 | 0/20 | 0 | 0 | 0 |
| entry 0 / seeded_legal / bite / MEDIUM | 12 | 6.5 | 2/20 | 0 | 0 | 0 |
| entry 0 / seeded_legal / bite / HIGH | 16 | 5.4 | 4/20 | 0 | 0 | 0 |
| entry 0 / seeded_legal / call / MEDIUM | 16 | 7.5 | 4/20 | 0 | 0 | 0 |
| entry 0 / seeded_legal / call / HIGH | 16 | 4.8 | 3/20 | 0 | 0 | 0 |
| entry 0 / seeded_legal / balanced / MEDIUM | 16 | 7.6 | 4/20 | 0 | 0 | 0 |
| entry 0 / seeded_legal / balanced / HIGH | 16 | 4.5 | 3/20 | 0 | 0 | 0 |
| entry 0 / seeded_legal / fallback / MEDIUM | 7 | 3.5 | 0/20 | 0 | 0 | 0 |
| entry 0 / seeded_legal / fallback / HIGH | 13 | 3.5 | 1/20 | 0 | 0 | 0 |
| entry 0 / seeded_legal / seeded / MEDIUM | 7 | 3.0 | 0/20 | 0 | 0 | 0 |
| entry 0 / seeded_legal / seeded / HIGH | 5 | 2.8 | 0/20 | 0 | 0 | 0 |
| entry 1 / pass / bite / MEDIUM | 59 | 59.0 | 1/1 | 0 | 0 | 0 |
| entry 1 / pass / bite / HIGH | 59 | 59.0 | 1/1 | 0 | 0 | 0 |
| entry 1 / pass / call / MEDIUM | 59 | 59.0 | 1/1 | 0 | 0 | 0 |
| entry 1 / pass / call / HIGH | 59 | 59.0 | 1/1 | 0 | 0 | 0 |
| entry 1 / pass / balanced / MEDIUM | 59 | 59.0 | 1/1 | 0 | 0 | 0 |
| entry 1 / pass / balanced / HIGH | 59 | 59.0 | 1/1 | 0 | 0 | 0 |
| entry 1 / pass / fallback / MEDIUM | 59 | 59.0 | 1/1 | 0 | 0 | 0 |
| entry 1 / pass / fallback / HIGH | 59 | 59.0 | 1/1 | 0 | 0 | 0 |
| entry 1 / pass / seeded / MEDIUM | 59 | 59.0 | 20/20 | 0 | 0 | 0 |
| entry 1 / pass / seeded / HIGH | 59 | 59.0 | 20/20 | 0 | 0 | 0 |
| entry 1 / direct_cycle / bite / MEDIUM | 2 | 2.0 | 0/1 | 0 | 0 | 0 |
| entry 1 / direct_cycle / bite / HIGH | 1 | 1.0 | 0/1 | 0 | 0 | 0 |
| entry 1 / direct_cycle / call / MEDIUM | 2 | 2.0 | 0/1 | 0 | 0 | 0 |
| entry 1 / direct_cycle / call / HIGH | 0 | 0.0 | 0/1 | 0 | 0 | 0 |
| entry 1 / direct_cycle / balanced / MEDIUM | 2 | 2.0 | 0/1 | 0 | 0 | 0 |
| entry 1 / direct_cycle / balanced / HIGH | 0 | 0.0 | 0/1 | 0 | 0 | 0 |
| entry 1 / direct_cycle / fallback / MEDIUM | 1 | 1.0 | 0/1 | 0 | 0 | 0 |
| entry 1 / direct_cycle / fallback / HIGH | 2 | 2.0 | 0/1 | 0 | 0 | 0 |
| entry 1 / direct_cycle / seeded / MEDIUM | 4 | 1.9 | 0/20 | 0 | 0 | 0 |
| entry 1 / direct_cycle / seeded / HIGH | 4 | 1.6 | 0/20 | 0 | 0 | 0 |
| entry 1 / feint_when_eligible / bite / MEDIUM | 1 | 1.0 | 0/1 | 0 | 0 | 0 |
| entry 1 / feint_when_eligible / bite / HIGH | 1 | 1.0 | 0/1 | 0 | 0 | 0 |
| entry 1 / feint_when_eligible / call / MEDIUM | 47 | 47.0 | 1/1 | 0 | 0 | 0 |
| entry 1 / feint_when_eligible / call / HIGH | 0 | 0.0 | 0/1 | 0 | 0 | 0 |
| entry 1 / feint_when_eligible / balanced / MEDIUM | 47 | 47.0 | 1/1 | 0 | 0 | 0 |
| entry 1 / feint_when_eligible / balanced / HIGH | 0 | 0.0 | 0/1 | 0 | 0 | 0 |
| entry 1 / feint_when_eligible / fallback / MEDIUM | 52 | 52.0 | 1/1 | 0 | 0 | 0 |
| entry 1 / feint_when_eligible / fallback / HIGH | 53 | 53.0 | 1/1 | 0 | 0 | 0 |
| entry 1 / feint_when_eligible / seeded / MEDIUM | 12 | 3.9 | 2/20 | 0 | 0 | 0 |
| entry 1 / feint_when_eligible / seeded / HIGH | 10 | 3.6 | 1/20 | 0 | 0 | 0 |
| entry 1 / prep_oriented / bite / MEDIUM | 1 | 1.0 | 0/1 | 0 | 0 | 0 |
| entry 1 / prep_oriented / bite / HIGH | 0 | 0.0 | 0/1 | 0 | 0 | 0 |
| entry 1 / prep_oriented / call / MEDIUM | 0 | 0.0 | 0/1 | 0 | 0 | 0 |
| entry 1 / prep_oriented / call / HIGH | 0 | 0.0 | 0/1 | 0 | 0 | 0 |
| entry 1 / prep_oriented / balanced / MEDIUM | 2 | 2.0 | 0/1 | 0 | 0 | 0 |
| entry 1 / prep_oriented / balanced / HIGH | 1 | 1.0 | 0/1 | 0 | 0 | 0 |
| entry 1 / prep_oriented / fallback / MEDIUM | 1 | 1.0 | 0/1 | 0 | 0 | 0 |
| entry 1 / prep_oriented / fallback / HIGH | 0 | 0.0 | 0/1 | 0 | 0 | 0 |
| entry 1 / prep_oriented / seeded / MEDIUM | 3 | 1.0 | 0/20 | 0 | 0 | 0 |
| entry 1 / prep_oriented / seeded / HIGH | 3 | 0.6 | 0/20 | 0 | 0 | 0 |
| entry 1 / seeded_legal / bite / MEDIUM | 11 | 3.6 | 1/20 | 0 | 0 | 0 |
| entry 1 / seeded_legal / bite / HIGH | 10 | 3.2 | 1/20 | 0 | 0 | 0 |
| entry 1 / seeded_legal / call / MEDIUM | 13 | 5.1 | 4/20 | 0 | 0 | 0 |
| entry 1 / seeded_legal / call / HIGH | 10 | 3.5 | 1/20 | 0 | 0 | 0 |
| entry 1 / seeded_legal / balanced / MEDIUM | 15 | 4.7 | 3/20 | 0 | 0 | 0 |
| entry 1 / seeded_legal / balanced / HIGH | 30 | 4.4 | 2/20 | 0 | 0 | 0 |
| entry 1 / seeded_legal / fallback / MEDIUM | 7 | 3.2 | 0/20 | 0 | 0 | 0 |
| entry 1 / seeded_legal / fallback / HIGH | 8 | 2.8 | 0/20 | 0 | 0 | 0 |
| entry 1 / seeded_legal / seeded / MEDIUM | 9 | 3.0 | 0/20 | 0 | 0 | 0 |
| entry 1 / seeded_legal / seeded / HIGH | 6 | 2.8 | 0/20 | 0 | 0 | 0 |
| entry 2 / pass / bite / MEDIUM | 59 | 59.0 | 1/1 | 0 | 0 | 0 |
| entry 2 / pass / bite / HIGH | 59 | 59.0 | 1/1 | 0 | 0 | 0 |
| entry 2 / pass / call / MEDIUM | 59 | 59.0 | 1/1 | 0 | 0 | 0 |
| entry 2 / pass / call / HIGH | 59 | 59.0 | 1/1 | 0 | 0 | 0 |
| entry 2 / pass / balanced / MEDIUM | 59 | 59.0 | 1/1 | 0 | 0 | 0 |
| entry 2 / pass / balanced / HIGH | 59 | 59.0 | 1/1 | 0 | 0 | 0 |
| entry 2 / pass / fallback / MEDIUM | 59 | 59.0 | 1/1 | 0 | 0 | 0 |
| entry 2 / pass / fallback / HIGH | 59 | 59.0 | 1/1 | 0 | 0 | 0 |
| entry 2 / pass / seeded / MEDIUM | 59 | 59.0 | 20/20 | 0 | 0 | 0 |
| entry 2 / pass / seeded / HIGH | 59 | 59.0 | 20/20 | 0 | 0 | 0 |
| entry 2 / direct_cycle / bite / MEDIUM | 1 | 1.0 | 0/1 | 0 | 0 | 0 |
| entry 2 / direct_cycle / bite / HIGH | 0 | 0.0 | 0/1 | 0 | 0 | 0 |
| entry 2 / direct_cycle / call / MEDIUM | 0 | 0.0 | 0/1 | 0 | 0 | 0 |
| entry 2 / direct_cycle / call / HIGH | 1 | 1.0 | 0/1 | 0 | 0 | 0 |
| entry 2 / direct_cycle / balanced / MEDIUM | 0 | 0.0 | 0/1 | 0 | 0 | 0 |
| entry 2 / direct_cycle / balanced / HIGH | 1 | 1.0 | 0/1 | 0 | 0 | 0 |
| entry 2 / direct_cycle / fallback / MEDIUM | 1 | 1.0 | 0/1 | 0 | 0 | 0 |
| entry 2 / direct_cycle / fallback / HIGH | 0 | 0.0 | 0/1 | 0 | 0 | 0 |
| entry 2 / direct_cycle / seeded / MEDIUM | 2 | 1.0 | 0/20 | 0 | 0 | 0 |
| entry 2 / direct_cycle / seeded / HIGH | 2 | 0.8 | 0/20 | 0 | 0 | 0 |
| entry 2 / feint_when_eligible / bite / MEDIUM | 21 | 21.0 | 1/1 | 0 | 0 | 0 |
| entry 2 / feint_when_eligible / bite / HIGH | 5 | 5.0 | 0/1 | 0 | 0 | 0 |
| entry 2 / feint_when_eligible / call / MEDIUM | 0 | 0.0 | 0/1 | 0 | 0 | 0 |
| entry 2 / feint_when_eligible / call / HIGH | 0 | 0.0 | 0/1 | 0 | 0 | 0 |
| entry 2 / feint_when_eligible / balanced / MEDIUM | 0 | 0.0 | 0/1 | 0 | 0 | 0 |
| entry 2 / feint_when_eligible / balanced / HIGH | 0 | 0.0 | 0/1 | 0 | 0 | 0 |
| entry 2 / feint_when_eligible / fallback / MEDIUM | 1 | 1.0 | 0/1 | 0 | 0 | 0 |
| entry 2 / feint_when_eligible / fallback / HIGH | 1 | 1.0 | 0/1 | 0 | 0 | 0 |
| entry 2 / feint_when_eligible / seeded / MEDIUM | 2 | 0.4 | 0/20 | 0 | 0 | 0 |
| entry 2 / feint_when_eligible / seeded / HIGH | 2 | 0.5 | 0/20 | 0 | 0 | 0 |
| entry 2 / prep_oriented / bite / MEDIUM | 1 | 1.0 | 0/1 | 0 | 0 | 0 |
| entry 2 / prep_oriented / bite / HIGH | 0 | 0.0 | 0/1 | 0 | 0 | 0 |
| entry 2 / prep_oriented / call / MEDIUM | 5 | 5.0 | 0/1 | 0 | 0 | 0 |
| entry 2 / prep_oriented / call / HIGH | 0 | 0.0 | 0/1 | 0 | 0 | 0 |
| entry 2 / prep_oriented / balanced / MEDIUM | 1 | 1.0 | 0/1 | 0 | 0 | 0 |
| entry 2 / prep_oriented / balanced / HIGH | 0 | 0.0 | 0/1 | 0 | 0 | 0 |
| entry 2 / prep_oriented / fallback / MEDIUM | 1 | 1.0 | 0/1 | 0 | 0 | 0 |
| entry 2 / prep_oriented / fallback / HIGH | 0 | 0.0 | 0/1 | 0 | 0 | 0 |
| entry 2 / prep_oriented / seeded / MEDIUM | 2 | 0.5 | 0/20 | 0 | 0 | 0 |
| entry 2 / prep_oriented / seeded / HIGH | 1 | 0.2 | 0/20 | 0 | 0 | 0 |
| entry 2 / seeded_legal / bite / MEDIUM | 6 | 2.9 | 0/20 | 0 | 0 | 0 |
| entry 2 / seeded_legal / bite / HIGH | 5 | 2.1 | 0/20 | 0 | 0 | 0 |
| entry 2 / seeded_legal / call / MEDIUM | 6 | 2.8 | 0/20 | 0 | 0 | 0 |
| entry 2 / seeded_legal / call / HIGH | 5 | 2.3 | 0/20 | 0 | 0 | 0 |
| entry 2 / seeded_legal / balanced / MEDIUM | 6 | 2.6 | 0/20 | 0 | 0 | 0 |
| entry 2 / seeded_legal / balanced / HIGH | 5 | 2.1 | 0/20 | 0 | 0 | 0 |
| entry 2 / seeded_legal / fallback / MEDIUM | 11 | 3.1 | 1/20 | 0 | 0 | 0 |
| entry 2 / seeded_legal / fallback / HIGH | 11 | 2.8 | 1/20 | 0 | 0 | 0 |
| entry 2 / seeded_legal / seeded / MEDIUM | 7 | 2.8 | 0/20 | 0 | 0 | 0 |
| entry 2 / seeded_legal / seeded / HIGH | 6 | 2.5 | 0/20 | 0 | 0 | 0 |
| entry 3 / pass / bite / MEDIUM | 59 | 59.0 | 1/1 | 0 | 0 | 0 |
| entry 3 / pass / bite / HIGH | 59 | 59.0 | 1/1 | 0 | 0 | 0 |
| entry 3 / pass / call / MEDIUM | 59 | 59.0 | 1/1 | 0 | 0 | 0 |
| entry 3 / pass / call / HIGH | 59 | 59.0 | 1/1 | 0 | 0 | 0 |
| entry 3 / pass / balanced / MEDIUM | 59 | 59.0 | 1/1 | 0 | 0 | 0 |
| entry 3 / pass / balanced / HIGH | 59 | 59.0 | 1/1 | 0 | 0 | 0 |
| entry 3 / pass / fallback / MEDIUM | 59 | 59.0 | 1/1 | 0 | 0 | 0 |
| entry 3 / pass / fallback / HIGH | 59 | 59.0 | 1/1 | 0 | 0 | 0 |
| entry 3 / pass / seeded / MEDIUM | 59 | 59.0 | 20/20 | 0 | 0 | 0 |
| entry 3 / pass / seeded / HIGH | 59 | 59.0 | 20/20 | 0 | 0 | 0 |
| entry 3 / direct_cycle / bite / MEDIUM | 1 | 1.0 | 0/1 | 0 | 0 | 0 |
| entry 3 / direct_cycle / bite / HIGH | 0 | 0.0 | 0/1 | 0 | 0 | 0 |
| entry 3 / direct_cycle / call / MEDIUM | 1 | 1.0 | 0/1 | 0 | 0 | 0 |
| entry 3 / direct_cycle / call / HIGH | 0 | 0.0 | 0/1 | 0 | 0 | 0 |
| entry 3 / direct_cycle / balanced / MEDIUM | 1 | 1.0 | 0/1 | 0 | 0 | 0 |
| entry 3 / direct_cycle / balanced / HIGH | 0 | 0.0 | 0/1 | 0 | 0 | 0 |
| entry 3 / direct_cycle / fallback / MEDIUM | 1 | 1.0 | 0/1 | 0 | 0 | 0 |
| entry 3 / direct_cycle / fallback / HIGH | 0 | 0.0 | 0/1 | 0 | 0 | 0 |
| entry 3 / direct_cycle / seeded / MEDIUM | 3 | 1.1 | 0/20 | 0 | 0 | 0 |
| entry 3 / direct_cycle / seeded / HIGH | 5 | 1.1 | 0/20 | 0 | 0 | 0 |
| entry 3 / feint_when_eligible / bite / MEDIUM | 1 | 1.0 | 0/1 | 0 | 0 | 0 |
| entry 3 / feint_when_eligible / bite / HIGH | 0 | 0.0 | 0/1 | 0 | 0 | 0 |
| entry 3 / feint_when_eligible / call / MEDIUM | 33 | 33.0 | 1/1 | 0 | 0 | 0 |
| entry 3 / feint_when_eligible / call / HIGH | 42 | 42.0 | 1/1 | 0 | 0 | 0 |
| entry 3 / feint_when_eligible / balanced / MEDIUM | 33 | 33.0 | 1/1 | 0 | 0 | 0 |
| entry 3 / feint_when_eligible / balanced / HIGH | 42 | 42.0 | 1/1 | 0 | 0 | 0 |
| entry 3 / feint_when_eligible / fallback / MEDIUM | 29 | 29.0 | 1/1 | 0 | 0 | 0 |
| entry 3 / feint_when_eligible / fallback / HIGH | 1 | 1.0 | 0/1 | 0 | 0 | 0 |
| entry 3 / feint_when_eligible / seeded / MEDIUM | 5 | 1.6 | 0/20 | 0 | 0 | 0 |
| entry 3 / feint_when_eligible / seeded / HIGH | 8 | 1.4 | 0/20 | 0 | 0 | 0 |
| entry 3 / prep_oriented / bite / MEDIUM | 1 | 1.0 | 0/1 | 0 | 0 | 0 |
| entry 3 / prep_oriented / bite / HIGH | 0 | 0.0 | 0/1 | 0 | 0 | 0 |
| entry 3 / prep_oriented / call / MEDIUM | 0 | 0.0 | 0/1 | 0 | 0 | 0 |
| entry 3 / prep_oriented / call / HIGH | 0 | 0.0 | 0/1 | 0 | 0 | 0 |
| entry 3 / prep_oriented / balanced / MEDIUM | 1 | 1.0 | 0/1 | 0 | 0 | 0 |
| entry 3 / prep_oriented / balanced / HIGH | 0 | 0.0 | 0/1 | 0 | 0 | 0 |
| entry 3 / prep_oriented / fallback / MEDIUM | 1 | 1.0 | 0/1 | 0 | 0 | 0 |
| entry 3 / prep_oriented / fallback / HIGH | 0 | 0.0 | 0/1 | 0 | 0 | 0 |
| entry 3 / prep_oriented / seeded / MEDIUM | 3 | 1.1 | 0/20 | 0 | 0 | 0 |
| entry 3 / prep_oriented / seeded / HIGH | 2 | 0.5 | 0/20 | 0 | 0 | 0 |
| entry 3 / seeded_legal / bite / MEDIUM | 9 | 2.8 | 0/20 | 0 | 0 | 0 |
| entry 3 / seeded_legal / bite / HIGH | 4 | 2.2 | 0/20 | 0 | 0 | 0 |
| entry 3 / seeded_legal / call / MEDIUM | 9 | 3.4 | 0/20 | 0 | 0 | 0 |
| entry 3 / seeded_legal / call / HIGH | 7 | 2.8 | 0/20 | 0 | 0 | 0 |
| entry 3 / seeded_legal / balanced / MEDIUM | 9 | 3.2 | 0/20 | 0 | 0 | 0 |
| entry 3 / seeded_legal / balanced / HIGH | 5 | 2.2 | 0/20 | 0 | 0 | 0 |
| entry 3 / seeded_legal / fallback / MEDIUM | 6 | 3.0 | 0/20 | 0 | 0 | 0 |
| entry 3 / seeded_legal / fallback / HIGH | 7 | 2.4 | 0/20 | 0 | 0 | 0 |
| entry 3 / seeded_legal / seeded / MEDIUM | 8 | 3.2 | 0/20 | 0 | 0 | 0 |
| entry 3 / seeded_legal / seeded / HIGH | 7 | 3.0 | 0/20 | 0 | 0 | 0 |
| entry 4 / pass / bite / MEDIUM | 59 | 59.0 | 1/1 | 0 | 0 | 0 |
| entry 4 / pass / bite / HIGH | 59 | 59.0 | 1/1 | 0 | 0 | 0 |
| entry 4 / pass / call / MEDIUM | 59 | 59.0 | 1/1 | 0 | 0 | 0 |
| entry 4 / pass / call / HIGH | 59 | 59.0 | 1/1 | 0 | 0 | 0 |
| entry 4 / pass / balanced / MEDIUM | 59 | 59.0 | 1/1 | 0 | 0 | 0 |
| entry 4 / pass / balanced / HIGH | 59 | 59.0 | 1/1 | 0 | 0 | 0 |
| entry 4 / pass / fallback / MEDIUM | 59 | 59.0 | 1/1 | 0 | 0 | 0 |
| entry 4 / pass / fallback / HIGH | 59 | 59.0 | 1/1 | 0 | 0 | 0 |
| entry 4 / pass / seeded / MEDIUM | 59 | 59.0 | 20/20 | 0 | 0 | 0 |
| entry 4 / pass / seeded / HIGH | 59 | 59.0 | 20/20 | 0 | 0 | 0 |
| entry 4 / direct_cycle / bite / MEDIUM | 46 | 46.0 | 1/1 | 0 | 0 | 0 |
| entry 4 / direct_cycle / bite / HIGH | 0 | 0.0 | 0/1 | 0 | 0 | 0 |
| entry 4 / direct_cycle / call / MEDIUM | 42 | 42.0 | 1/1 | 0 | 0 | 0 |
| entry 4 / direct_cycle / call / HIGH | 0 | 0.0 | 0/1 | 0 | 0 | 0 |
| entry 4 / direct_cycle / balanced / MEDIUM | 42 | 42.0 | 1/1 | 0 | 0 | 0 |
| entry 4 / direct_cycle / balanced / HIGH | 0 | 0.0 | 0/1 | 0 | 0 | 0 |
| entry 4 / direct_cycle / fallback / MEDIUM | 3 | 3.0 | 0/1 | 0 | 0 | 0 |
| entry 4 / direct_cycle / fallback / HIGH | 3 | 3.0 | 0/1 | 0 | 0 | 0 |
| entry 4 / direct_cycle / seeded / MEDIUM | 6 | 2.2 | 0/20 | 0 | 0 | 0 |
| entry 4 / direct_cycle / seeded / HIGH | 5 | 1.7 | 0/20 | 0 | 0 | 0 |
| entry 4 / feint_when_eligible / bite / MEDIUM | 0 | 0.0 | 0/1 | 0 | 0 | 0 |
| entry 4 / feint_when_eligible / bite / HIGH | 0 | 0.0 | 0/1 | 0 | 0 | 0 |
| entry 4 / feint_when_eligible / call / MEDIUM | 46 | 46.0 | 1/1 | 0 | 0 | 0 |
| entry 4 / feint_when_eligible / call / HIGH | 46 | 46.0 | 1/1 | 0 | 0 | 0 |
| entry 4 / feint_when_eligible / balanced / MEDIUM | 46 | 46.0 | 1/1 | 0 | 0 | 0 |
| entry 4 / feint_when_eligible / balanced / HIGH | 46 | 46.0 | 1/1 | 0 | 0 | 0 |
| entry 4 / feint_when_eligible / fallback / MEDIUM | 52 | 52.0 | 1/1 | 0 | 0 | 0 |
| entry 4 / feint_when_eligible / fallback / HIGH | 49 | 49.0 | 1/1 | 0 | 0 | 0 |
| entry 4 / feint_when_eligible / seeded / MEDIUM | 10 | 3.6 | 1/20 | 0 | 0 | 0 |
| entry 4 / feint_when_eligible / seeded / HIGH | 11 | 3.9 | 1/20 | 0 | 0 | 0 |
| entry 4 / prep_oriented / bite / MEDIUM | 0 | 0.0 | 0/1 | 0 | 0 | 0 |
| entry 4 / prep_oriented / bite / HIGH | 0 | 0.0 | 0/1 | 0 | 0 | 0 |
| entry 4 / prep_oriented / call / MEDIUM | 0 | 0.0 | 0/1 | 0 | 0 | 0 |
| entry 4 / prep_oriented / call / HIGH | 0 | 0.0 | 0/1 | 0 | 0 | 0 |
| entry 4 / prep_oriented / balanced / MEDIUM | 50 | 50.0 | 1/1 | 0 | 0 | 0 |
| entry 4 / prep_oriented / balanced / HIGH | 0 | 0.0 | 0/1 | 0 | 0 | 0 |
| entry 4 / prep_oriented / fallback / MEDIUM | 1 | 1.0 | 0/1 | 0 | 0 | 0 |
| entry 4 / prep_oriented / fallback / HIGH | 0 | 0.0 | 0/1 | 0 | 0 | 0 |
| entry 4 / prep_oriented / seeded / MEDIUM | 2 | 1.0 | 0/20 | 0 | 0 | 0 |
| entry 4 / prep_oriented / seeded / HIGH | 2 | 0.5 | 0/20 | 0 | 0 | 0 |
| entry 4 / seeded_legal / bite / MEDIUM | 12 | 7.0 | 3/20 | 0 | 0 | 0 |
| entry 4 / seeded_legal / bite / HIGH | 16 | 6.8 | 5/20 | 0 | 0 | 0 |
| entry 4 / seeded_legal / call / MEDIUM | 16 | 7.5 | 4/20 | 0 | 0 | 0 |
| entry 4 / seeded_legal / call / HIGH | 16 | 7.0 | 5/20 | 0 | 0 | 0 |
| entry 4 / seeded_legal / balanced / MEDIUM | 36 | 9.2 | 4/20 | 0 | 0 | 0 |
| entry 4 / seeded_legal / balanced / HIGH | 16 | 7.2 | 6/20 | 0 | 0 | 0 |
| entry 4 / seeded_legal / fallback / MEDIUM | 28 | 6.6 | 4/20 | 0 | 0 | 0 |
| entry 4 / seeded_legal / fallback / HIGH | 15 | 4.3 | 2/20 | 0 | 0 | 0 |
| entry 4 / seeded_legal / seeded / MEDIUM | 7 | 3.2 | 0/20 | 0 | 0 | 0 |
| entry 4 / seeded_legal / seeded / HIGH | 5 | 2.9 | 0/20 | 0 | 0 | 0 |

## Population C — bounded combinations: a Mount policy, then a Half Guard attacker against a named defender (MEDIUM commitments)
POPULATION. The Half Guard phase only occurs for games whose Mount policy really reaches a Half Guard exit.

**Summary by policy** (all cells with the same policy pooled; percentages are of games)
| policy | games | ended by a tap | ended by the clock | halted at an unsupported exit | entered Half Guard | still active after the maximum windows | windows mean | exchanges mean | feints accepted | feints that bit | feints effective (grade >= Success) | feints punished (grade <= Failure) | fallbacks | games with a 10+ window no-progress streak | final axis mean | lowest / highest axis mean | unsupported-exit destinations (games) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| pass_only -> feint_when_eligible vs bite | 1 | 0 (0%) | 1 (100%) | 0 (0%) | 0 (0%) | 0 | 59.0 | 0.0 | 0 | - | - | - | 0 | 1 (100%) | +4.00 | +2.00 / +4.00 | - |
| pass_only -> feint_when_eligible vs call | 1 | 0 (0%) | 1 (100%) | 0 (0%) | 0 (0%) | 0 | 59.0 | 0.0 | 0 | - | - | - | 0 | 1 (100%) | +4.00 | +2.00 / +4.00 | - |
| pass_only -> feint_when_eligible vs fallback | 1 | 0 (0%) | 1 (100%) | 0 (0%) | 0 (0%) | 0 | 59.0 | 0.0 | 0 | - | - | - | 0 | 1 (100%) | +4.00 | +2.00 / +4.00 | - |
| pass_only -> prep_oriented vs bite | 1 | 0 (0%) | 1 (100%) | 0 (0%) | 0 (0%) | 0 | 59.0 | 0.0 | 0 | - | - | - | 0 | 1 (100%) | +4.00 | +2.00 / +4.00 | - |
| pass_only -> prep_oriented vs call | 1 | 0 (0%) | 1 (100%) | 0 (0%) | 0 (0%) | 0 | 59.0 | 0.0 | 0 | - | - | - | 0 | 1 (100%) | +4.00 | +2.00 / +4.00 | - |
| pass_only -> prep_oriented vs fallback | 1 | 0 (0%) | 1 (100%) | 0 (0%) | 0 (0%) | 0 | 59.0 | 0.0 | 0 | - | - | - | 0 | 1 (100%) | +4.00 | +2.00 / +4.00 | - |
| top_direct -> feint_when_eligible vs bite | 1 | 0 (0%) | 1 (100%) | 0 (0%) | 0 (0%) | 0 | 59.0 | 30.0 | 0 | - | - | - | 0 | 1 (100%) | +4.00 | +3.00 / +4.00 | - |
| top_direct -> feint_when_eligible vs call | 1 | 0 (0%) | 1 (100%) | 0 (0%) | 0 (0%) | 0 | 59.0 | 30.0 | 0 | - | - | - | 0 | 1 (100%) | +4.00 | +3.00 / +4.00 | - |
| top_direct -> feint_when_eligible vs fallback | 1 | 0 (0%) | 1 (100%) | 0 (0%) | 0 (0%) | 0 | 59.0 | 30.0 | 0 | - | - | - | 0 | 1 (100%) | +4.00 | +3.00 / +4.00 | - |
| top_direct -> prep_oriented vs bite | 1 | 0 (0%) | 1 (100%) | 0 (0%) | 0 (0%) | 0 | 59.0 | 30.0 | 0 | - | - | - | 0 | 1 (100%) | +4.00 | +3.00 / +4.00 | - |
| top_direct -> prep_oriented vs call | 1 | 0 (0%) | 1 (100%) | 0 (0%) | 0 (0%) | 0 | 59.0 | 30.0 | 0 | - | - | - | 0 | 1 (100%) | +4.00 | +3.00 / +4.00 | - |
| top_direct -> prep_oriented vs fallback | 1 | 0 (0%) | 1 (100%) | 0 (0%) | 0 (0%) | 0 | 59.0 | 30.0 | 0 | - | - | - | 0 | 1 (100%) | +4.00 | +3.00 / +4.00 | - |
| bottom_escape -> feint_when_eligible vs bite | 1 | 0 (0%) | 0 (0%) | 1 (100%) | 1 (100%) | 0 | 36.0 | 20.0 | 2 | 2 (100%) | 2 (100%) | 0 (0%) | 0 | 0 (0%) | -4.00 | -4.00 / +3.25 | half_guard:Closed Guard 1 |
| bottom_escape -> feint_when_eligible vs call | 1 | 0 (0%) | 1 (100%) | 0 (0%) | 1 (100%) | 0 | 59.0 | 43.0 | 2 | 0 (0%) | 0 (0%) | 0 (0%) | 0 | 1 (100%) | +4.00 | +0.50 / +4.00 | - |
| bottom_escape -> feint_when_eligible vs fallback | 1 | 0 (0%) | 1 (100%) | 0 (0%) | 1 (100%) | 0 | 59.0 | 43.0 | 0 | - | - | - | 27 | 1 (100%) | +4.00 | +0.50 / +4.00 | - |
| bottom_escape -> prep_oriented vs bite | 1 | 0 (0%) | 1 (100%) | 0 (0%) | 1 (100%) | 0 | 59.0 | 43.0 | 0 | - | - | - | 0 | 0 (0%) | -4.00 | -4.00 / +3.25 | - |
| bottom_escape -> prep_oriented vs call | 1 | 0 (0%) | 0 (0%) | 1 (100%) | 1 (100%) | 0 | 36.0 | 20.0 | 0 | - | - | - | 0 | 0 (0%) | -4.00 | -4.00 / +3.25 | half_guard:Closed Guard 1 |
| bottom_escape -> prep_oriented vs fallback | 1 | 0 (0%) | 0 (0%) | 1 (100%) | 1 (100%) | 0 | 36.0 | 20.0 | 0 | - | - | - | 4 | 0 (0%) | -4.00 | -4.00 / +3.25 | half_guard:Closed Guard 1 |
| bottom_trap_roll -> feint_when_eligible vs bite | 1 | 0 (0%) | 1 (100%) | 0 (0%) | 0 (0%) | 0 | 59.0 | 26.0 | 0 | - | - | - | 0 | 1 (100%) | +3.75 | +2.00 / +4.00 | - |
| bottom_trap_roll -> feint_when_eligible vs call | 1 | 0 (0%) | 1 (100%) | 0 (0%) | 0 (0%) | 0 | 59.0 | 26.0 | 0 | - | - | - | 0 | 1 (100%) | +3.75 | +2.00 / +4.00 | - |
| bottom_trap_roll -> feint_when_eligible vs fallback | 1 | 0 (0%) | 1 (100%) | 0 (0%) | 0 (0%) | 0 | 59.0 | 26.0 | 0 | - | - | - | 0 | 1 (100%) | +3.75 | +2.00 / +4.00 | - |
| bottom_trap_roll -> prep_oriented vs bite | 1 | 0 (0%) | 1 (100%) | 0 (0%) | 0 (0%) | 0 | 59.0 | 26.0 | 0 | - | - | - | 0 | 1 (100%) | +3.75 | +2.00 / +4.00 | - |
| bottom_trap_roll -> prep_oriented vs call | 1 | 0 (0%) | 1 (100%) | 0 (0%) | 0 (0%) | 0 | 59.0 | 26.0 | 0 | - | - | - | 0 | 1 (100%) | +3.75 | +2.00 / +4.00 | - |
| bottom_trap_roll -> prep_oriented vs fallback | 1 | 0 (0%) | 1 (100%) | 0 (0%) | 0 (0%) | 0 | 59.0 | 26.0 | 0 | - | - | - | 0 | 1 (100%) | +3.75 | +2.00 / +4.00 | - |
| seeded_legal -> feint_when_eligible vs bite | 30 | 17 (57%) | 8 (27%) | 5 (17%) | 5 (17%) | 0 | 42.9 | 29.1 | 18 | 18 (100%) | 18 (100%) | 0 (0%) | 0 | 1 (3%) | +2.29 | +0.21 / +3.80 | half_guard:Closed Guard 5 |
| seeded_legal -> feint_when_eligible vs call | 30 | 17 (57%) | 13 (43%) | 0 (0%) | 5 (17%) | 0 | 50.3 | 36.5 | 22 | 0 (0%) | 0 (0%) | 20 (91%) | 0 | 6 (20%) | +3.62 | +0.42 / +4.00 | - |
| seeded_legal -> feint_when_eligible vs fallback | 30 | 17 (57%) | 13 (43%) | 0 (0%) | 5 (17%) | 0 | 50.3 | 36.5 | 8 | 0 (0%) | 8 (100%) | 0 (0%) | 251 | 6 (20%) | +3.62 | +0.96 / +4.00 | - |
| seeded_legal -> prep_oriented vs bite | 30 | 17 (57%) | 13 (43%) | 0 (0%) | 5 (17%) | 0 | 50.3 | 36.5 | 0 | - | - | - | 0 | 1 (3%) | +2.76 | +0.68 / +3.62 | - |
| seeded_legal -> prep_oriented vs call | 30 | 17 (57%) | 8 (27%) | 5 (17%) | 5 (17%) | 0 | 42.6 | 28.8 | 0 | - | - | - | 0 | 1 (3%) | +2.36 | +0.28 / +3.62 | half_guard:Closed Guard 1, half_guard:Open Guard 4 |
| seeded_legal -> prep_oriented vs fallback | 30 | 17 (57%) | 8 (27%) | 5 (17%) | 5 (17%) | 0 | 43.2 | 29.4 | 0 | - | - | - | 36 | 1 (3%) | +2.29 | +0.21 / +3.62 | half_guard:Closed Guard 5 |

**Outcomes (games per terminal class)** — `halt_*` is an unsupported-destination boundary, not a result
| cell | games | halt_half_guard:Closed Guard | halt_half_guard:Open Guard | tap_mount | timeout_half_guard | timeout_mount |
|---|---|---|---|---|---|---|
| pass_only -> feint_when_eligible / bite | 1 | 0 | 0 | 0 | 0 | 1 |
| pass_only -> feint_when_eligible / call | 1 | 0 | 0 | 0 | 0 | 1 |
| pass_only -> feint_when_eligible / fallback | 1 | 0 | 0 | 0 | 0 | 1 |
| pass_only -> prep_oriented / bite | 1 | 0 | 0 | 0 | 0 | 1 |
| pass_only -> prep_oriented / call | 1 | 0 | 0 | 0 | 0 | 1 |
| pass_only -> prep_oriented / fallback | 1 | 0 | 0 | 0 | 0 | 1 |
| top_direct -> feint_when_eligible / bite | 1 | 0 | 0 | 0 | 0 | 1 |
| top_direct -> feint_when_eligible / call | 1 | 0 | 0 | 0 | 0 | 1 |
| top_direct -> feint_when_eligible / fallback | 1 | 0 | 0 | 0 | 0 | 1 |
| top_direct -> prep_oriented / bite | 1 | 0 | 0 | 0 | 0 | 1 |
| top_direct -> prep_oriented / call | 1 | 0 | 0 | 0 | 0 | 1 |
| top_direct -> prep_oriented / fallback | 1 | 0 | 0 | 0 | 0 | 1 |
| bottom_escape -> feint_when_eligible / bite | 1 | 1 | 0 | 0 | 0 | 0 |
| bottom_escape -> feint_when_eligible / call | 1 | 0 | 0 | 0 | 1 | 0 |
| bottom_escape -> feint_when_eligible / fallback | 1 | 0 | 0 | 0 | 1 | 0 |
| bottom_escape -> prep_oriented / bite | 1 | 0 | 0 | 0 | 1 | 0 |
| bottom_escape -> prep_oriented / call | 1 | 1 | 0 | 0 | 0 | 0 |
| bottom_escape -> prep_oriented / fallback | 1 | 1 | 0 | 0 | 0 | 0 |
| bottom_trap_roll -> feint_when_eligible / bite | 1 | 0 | 0 | 0 | 0 | 1 |
| bottom_trap_roll -> feint_when_eligible / call | 1 | 0 | 0 | 0 | 0 | 1 |
| bottom_trap_roll -> feint_when_eligible / fallback | 1 | 0 | 0 | 0 | 0 | 1 |
| bottom_trap_roll -> prep_oriented / bite | 1 | 0 | 0 | 0 | 0 | 1 |
| bottom_trap_roll -> prep_oriented / call | 1 | 0 | 0 | 0 | 0 | 1 |
| bottom_trap_roll -> prep_oriented / fallback | 1 | 0 | 0 | 0 | 0 | 1 |
| seeded_legal -> feint_when_eligible / bite | 30 | 5 | 0 | 17 | 0 | 8 |
| seeded_legal -> feint_when_eligible / call | 30 | 0 | 0 | 17 | 5 | 8 |
| seeded_legal -> feint_when_eligible / fallback | 30 | 0 | 0 | 17 | 5 | 8 |
| seeded_legal -> prep_oriented / bite | 30 | 0 | 0 | 17 | 5 | 8 |
| seeded_legal -> prep_oriented / call | 30 | 1 | 4 | 17 | 0 | 8 |
| seeded_legal -> prep_oriented / fallback | 30 | 5 | 0 | 17 | 0 | 8 |

**Time, entry and position time** (means over the cell's games; seconds are simulated clock seconds)
| cell | windows mean (min-max) | seconds mean | entered Half Guard | mean entry window | Mount windows mean | Half Guard windows mean | exchanges mean | passes mean | D3-B holds mean | longest pass streak max | longest idle streak max |
|---|---|---|---|---|---|---|---|---|---|---|---|
| pass_only -> feint_when_eligible / bite | 59.0 (59-59) | 300.0 | 0/1 | - | 59.0 | 0.0 | 0.0 | 59.0 | 0.0 | 59 | 59 |
| pass_only -> feint_when_eligible / call | 59.0 (59-59) | 300.0 | 0/1 | - | 59.0 | 0.0 | 0.0 | 59.0 | 0.0 | 59 | 59 |
| pass_only -> feint_when_eligible / fallback | 59.0 (59-59) | 300.0 | 0/1 | - | 59.0 | 0.0 | 0.0 | 59.0 | 0.0 | 59 | 59 |
| pass_only -> prep_oriented / bite | 59.0 (59-59) | 300.0 | 0/1 | - | 59.0 | 0.0 | 0.0 | 59.0 | 0.0 | 59 | 59 |
| pass_only -> prep_oriented / call | 59.0 (59-59) | 300.0 | 0/1 | - | 59.0 | 0.0 | 0.0 | 59.0 | 0.0 | 59 | 59 |
| pass_only -> prep_oriented / fallback | 59.0 (59-59) | 300.0 | 0/1 | - | 59.0 | 0.0 | 0.0 | 59.0 | 0.0 | 59 | 59 |
| top_direct -> feint_when_eligible / bite | 59.0 (59-59) | 300.0 | 0/1 | - | 59.0 | 0.0 | 30.0 | 29.0 | 0.0 | 1 | 1 |
| top_direct -> feint_when_eligible / call | 59.0 (59-59) | 300.0 | 0/1 | - | 59.0 | 0.0 | 30.0 | 29.0 | 0.0 | 1 | 1 |
| top_direct -> feint_when_eligible / fallback | 59.0 (59-59) | 300.0 | 0/1 | - | 59.0 | 0.0 | 30.0 | 29.0 | 0.0 | 1 | 1 |
| top_direct -> prep_oriented / bite | 59.0 (59-59) | 300.0 | 0/1 | - | 59.0 | 0.0 | 30.0 | 29.0 | 0.0 | 1 | 1 |
| top_direct -> prep_oriented / call | 59.0 (59-59) | 300.0 | 0/1 | - | 59.0 | 0.0 | 30.0 | 29.0 | 0.0 | 1 | 1 |
| top_direct -> prep_oriented / fallback | 59.0 (59-59) | 300.0 | 0/1 | - | 59.0 | 0.0 | 30.0 | 29.0 | 0.0 | 1 | 1 |
| bottom_escape -> feint_when_eligible / bite | 36.0 (36-36) | 180.0 | 1/1 | 32.0 | 32.0 | 4.0 | 20.0 | 16.0 | 0.0 | 1 | 1 |
| bottom_escape -> feint_when_eligible / call | 59.0 (59-59) | 300.0 | 1/1 | 32.0 | 32.0 | 27.0 | 43.0 | 16.0 | 0.0 | 1 | 1 |
| bottom_escape -> feint_when_eligible / fallback | 59.0 (59-59) | 300.0 | 1/1 | 32.0 | 32.0 | 27.0 | 43.0 | 16.0 | 0.0 | 1 | 1 |
| bottom_escape -> prep_oriented / bite | 59.0 (59-59) | 300.0 | 1/1 | 32.0 | 32.0 | 27.0 | 43.0 | 16.0 | 0.0 | 1 | 1 |
| bottom_escape -> prep_oriented / call | 36.0 (36-36) | 180.0 | 1/1 | 32.0 | 32.0 | 4.0 | 20.0 | 16.0 | 0.0 | 1 | 1 |
| bottom_escape -> prep_oriented / fallback | 36.0 (36-36) | 180.0 | 1/1 | 32.0 | 32.0 | 4.0 | 20.0 | 16.0 | 0.0 | 1 | 1 |
| bottom_trap_roll -> feint_when_eligible / bite | 59.0 (59-59) | 300.0 | 0/1 | - | 59.0 | 0.0 | 26.0 | 30.0 | 3.0 | 1 | 7 |
| bottom_trap_roll -> feint_when_eligible / call | 59.0 (59-59) | 300.0 | 0/1 | - | 59.0 | 0.0 | 26.0 | 30.0 | 3.0 | 1 | 7 |
| bottom_trap_roll -> feint_when_eligible / fallback | 59.0 (59-59) | 300.0 | 0/1 | - | 59.0 | 0.0 | 26.0 | 30.0 | 3.0 | 1 | 7 |
| bottom_trap_roll -> prep_oriented / bite | 59.0 (59-59) | 300.0 | 0/1 | - | 59.0 | 0.0 | 26.0 | 30.0 | 3.0 | 1 | 7 |
| bottom_trap_roll -> prep_oriented / call | 59.0 (59-59) | 300.0 | 0/1 | - | 59.0 | 0.0 | 26.0 | 30.0 | 3.0 | 1 | 7 |
| bottom_trap_roll -> prep_oriented / fallback | 59.0 (59-59) | 300.0 | 0/1 | - | 59.0 | 0.0 | 26.0 | 30.0 | 3.0 | 1 | 7 |
| seeded_legal -> feint_when_eligible / bite | 42.9 (8-59) | 215.8 | 5/30 | 8.8 | 42.0 | 0.9 | 29.1 | 12.4 | 1.4 | 5 | 5 |
| seeded_legal -> feint_when_eligible / call | 50.3 (27-59) | 253.8 | 5/30 | 8.8 | 42.0 | 8.4 | 36.5 | 12.4 | 1.4 | 5 | 5 |
| seeded_legal -> feint_when_eligible / fallback | 50.3 (27-59) | 253.8 | 5/30 | 8.8 | 42.0 | 8.4 | 36.5 | 12.4 | 1.4 | 5 | 5 |
| seeded_legal -> prep_oriented / bite | 50.3 (27-59) | 253.8 | 5/30 | 8.8 | 42.0 | 8.4 | 36.5 | 12.4 | 1.4 | 5 | 5 |
| seeded_legal -> prep_oriented / call | 42.6 (6-59) | 214.5 | 5/30 | 8.8 | 42.0 | 0.7 | 28.8 | 12.4 | 1.4 | 5 | 5 |
| seeded_legal -> prep_oriented / fallback | 43.2 (10-59) | 217.2 | 5/30 | 8.8 | 42.0 | 1.2 | 29.4 | 12.4 | 1.4 | 5 | 5 |

**Stamina, exhaustion and commitment downgrades** (means; `downgrades` counts exchanges whose requested commitment was funded lower, either fighter)
| cell | min stamina top (mean) | min stamina bottom (mean) | games with an exhausted fighter | exhausted windows top+bottom (mean) | downgrades (mean) | windows where any stamina rose: Mount / Half Guard (total) |
|---|---|---|---|---|---|---|
| pass_only -> feint_when_eligible / bite | 41.0 | 41.0 | 0/1 | 0.0 | 0.0 | 0 / 0 |
| pass_only -> feint_when_eligible / call | 41.0 | 41.0 | 0/1 | 0.0 | 0.0 | 0 / 0 |
| pass_only -> feint_when_eligible / fallback | 41.0 | 41.0 | 0/1 | 0.0 | 0.0 | 0 / 0 |
| pass_only -> prep_oriented / bite | 41.0 | 41.0 | 0/1 | 0.0 | 0.0 | 0 / 0 |
| pass_only -> prep_oriented / call | 41.0 | 41.0 | 0/1 | 0.0 | 0.0 | 0 / 0 |
| pass_only -> prep_oriented / fallback | 41.0 | 41.0 | 0/1 | 0.0 | 0.0 | 0 / 0 |
| top_direct -> feint_when_eligible / bite | 0.0 | 14.0 | 1/1 | 63.0 | 19.0 | 19 / 0 |
| top_direct -> feint_when_eligible / call | 0.0 | 14.0 | 1/1 | 63.0 | 19.0 | 19 / 0 |
| top_direct -> feint_when_eligible / fallback | 0.0 | 14.0 | 1/1 | 63.0 | 19.0 | 19 / 0 |
| top_direct -> prep_oriented / bite | 0.0 | 14.0 | 1/1 | 63.0 | 19.0 | 19 / 0 |
| top_direct -> prep_oriented / call | 0.0 | 14.0 | 1/1 | 63.0 | 19.0 | 19 / 0 |
| top_direct -> prep_oriented / fallback | 0.0 | 14.0 | 1/1 | 63.0 | 19.0 | 19 / 0 |
| bottom_escape -> feint_when_eligible / bite | 0.0 | 6.0 | 1/1 | 36.0 | 9.0 | 7 / 0 |
| bottom_escape -> feint_when_eligible / call | 0.0 | 0.0 | 1/1 | 82.0 | 55.0 | 7 / 0 |
| bottom_escape -> feint_when_eligible / fallback | 0.0 | 2.0 | 1/1 | 82.0 | 52.0 | 7 / 0 |
| bottom_escape -> prep_oriented / bite | 0.0 | 2.0 | 1/1 | 82.0 | 53.0 | 7 / 0 |
| bottom_escape -> prep_oriented / call | 0.0 | 12.0 | 1/1 | 36.0 | 9.0 | 7 / 0 |
| bottom_escape -> prep_oriented / fallback | 0.0 | 12.0 | 1/1 | 36.0 | 9.0 | 7 / 0 |
| bottom_trap_roll -> feint_when_eligible / bite | 0.0 | 19.0 | 1/1 | 76.0 | 15.0 | 22 / 0 |
| bottom_trap_roll -> feint_when_eligible / call | 0.0 | 19.0 | 1/1 | 76.0 | 15.0 | 22 / 0 |
| bottom_trap_roll -> feint_when_eligible / fallback | 0.0 | 19.0 | 1/1 | 76.0 | 15.0 | 22 / 0 |
| bottom_trap_roll -> prep_oriented / bite | 0.0 | 19.0 | 1/1 | 76.0 | 15.0 | 22 / 0 |
| bottom_trap_roll -> prep_oriented / call | 0.0 | 19.0 | 1/1 | 76.0 | 15.0 | 22 / 0 |
| bottom_trap_roll -> prep_oriented / fallback | 0.0 | 19.0 | 1/1 | 76.0 | 15.0 | 22 / 0 |
| seeded_legal -> feint_when_eligible / bite | 4.9 | 17.0 | 26/30 | 54.7 | 18.3 | 517 / 0 |
| seeded_legal -> feint_when_eligible / call | 0.0 | 13.0 | 30/30 | 69.1 | 32.1 | 517 / 0 |
| seeded_legal -> feint_when_eligible / fallback | 0.2 | 13.1 | 30/30 | 68.2 | 30.6 | 517 / 0 |
| seeded_legal -> prep_oriented / bite | 0.1 | 13.0 | 30/30 | 68.8 | 31.7 | 517 / 0 |
| seeded_legal -> prep_oriented / call | 7.2 | 20.3 | 26/30 | 54.7 | 18.3 | 517 / 0 |
| seeded_legal -> prep_oriented / fallback | 5.6 | 18.7 | 26/30 | 54.7 | 18.3 | 517 / 0 |

**Feints and the published LOW fallback** (totals over the cell's games; `effective` = final grade >= Success, `punished` = final grade <= Failure)
| cell | feint attempts | refused (by code) | accepted | bit | not bit | effective | neutral | punished | exits by a feint | exits capped (LOW) | fallbacks | undercommitment +1 | fallback modifier mismatches |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| bottom_escape -> feint_when_eligible / bite | 4 | feint_requires_funding:1, feint_not_eligible:1 | 2 | 2 | 0 | 2 | 0 | 0 | 1 | 0 | 0 | 0 | 0 |
| bottom_escape -> feint_when_eligible / call | 27 | feint_requires_funding:14, feint_not_eligible:11 | 2 | 0 | 2 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 |
| bottom_escape -> feint_when_eligible / fallback | 27 | feint_requires_funding:14, feint_not_eligible:13 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 27 | 4 | 0 |
| bottom_escape -> prep_oriented / fallback | 0 | - | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 2 | 0 |
| seeded_legal -> feint_when_eligible / bite | 28 | feint_not_eligible:9, feint_requires_funding:1 | 18 | 18 | 0 | 18 | 0 | 0 | 5 | 0 | 0 | 0 | 0 |
| seeded_legal -> feint_when_eligible / call | 251 | feint_not_eligible:121, feint_requires_funding:108 | 22 | 0 | 22 | 0 | 2 | 20 | 0 | 0 | 0 | 0 | 0 |
| seeded_legal -> feint_when_eligible / fallback | 251 | feint_not_eligible:230, feint_requires_funding:13 | 8 | 0 | 8 | 8 | 0 | 0 | 0 | 0 | 251 | 66 | 0 |
| seeded_legal -> prep_oriented / fallback | 0 | - | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 36 | 34 | 0 |

**Positional trajectory** (one comparable axis, positive = Top advantage: Mount `axis`, Half Guard `axis_tenths / 10`; means over games)
| cell | final axis (mean) | lowest axis reached (mean) | highest axis reached (mean) |
|---|---|---|---|
| pass_only -> feint_when_eligible / bite | +4.00 | +2.00 | +4.00 |
| pass_only -> feint_when_eligible / call | +4.00 | +2.00 | +4.00 |
| pass_only -> feint_when_eligible / fallback | +4.00 | +2.00 | +4.00 |
| pass_only -> prep_oriented / bite | +4.00 | +2.00 | +4.00 |
| pass_only -> prep_oriented / call | +4.00 | +2.00 | +4.00 |
| pass_only -> prep_oriented / fallback | +4.00 | +2.00 | +4.00 |
| top_direct -> feint_when_eligible / bite | +4.00 | +3.00 | +4.00 |
| top_direct -> feint_when_eligible / call | +4.00 | +3.00 | +4.00 |
| top_direct -> feint_when_eligible / fallback | +4.00 | +3.00 | +4.00 |
| top_direct -> prep_oriented / bite | +4.00 | +3.00 | +4.00 |
| top_direct -> prep_oriented / call | +4.00 | +3.00 | +4.00 |
| top_direct -> prep_oriented / fallback | +4.00 | +3.00 | +4.00 |
| bottom_escape -> feint_when_eligible / bite | -4.00 | -4.00 | +3.25 |
| bottom_escape -> feint_when_eligible / call | +4.00 | +0.50 | +4.00 |
| bottom_escape -> feint_when_eligible / fallback | +4.00 | +0.50 | +4.00 |
| bottom_escape -> prep_oriented / bite | -4.00 | -4.00 | +3.25 |
| bottom_escape -> prep_oriented / call | -4.00 | -4.00 | +3.25 |
| bottom_escape -> prep_oriented / fallback | -4.00 | -4.00 | +3.25 |
| bottom_trap_roll -> feint_when_eligible / bite | +3.75 | +2.00 | +4.00 |
| bottom_trap_roll -> feint_when_eligible / call | +3.75 | +2.00 | +4.00 |
| bottom_trap_roll -> feint_when_eligible / fallback | +3.75 | +2.00 | +4.00 |
| bottom_trap_roll -> prep_oriented / bite | +3.75 | +2.00 | +4.00 |
| bottom_trap_roll -> prep_oriented / call | +3.75 | +2.00 | +4.00 |
| bottom_trap_roll -> prep_oriented / fallback | +3.75 | +2.00 | +4.00 |
| seeded_legal -> feint_when_eligible / bite | +2.29 | +0.21 | +3.80 |
| seeded_legal -> feint_when_eligible / call | +3.62 | +0.42 | +4.00 |
| seeded_legal -> feint_when_eligible / fallback | +3.62 | +0.96 | +4.00 |
| seeded_legal -> prep_oriented / bite | +2.76 | +0.68 | +3.62 |
| seeded_legal -> prep_oriented / call | +2.36 | +0.28 | +3.62 |
| seeded_legal -> prep_oriented / fallback | +2.29 | +0.21 | +3.62 |

**No-progress sequences** (a window that leaves the positional fingerprint unchanged: Mount axis, band, setup tiers and submission stage; Half Guard axis, band and both readiness tiers)
| cell | longest no-progress streak (max) | mean | games with a streak of 10+ windows | policy errors | transitions checked | continuity violations |
|---|---|---|---|---|---|---|
| pass_only -> feint_when_eligible / bite | 54 | 54.0 | 1/1 | 0 | 0 | 0 |
| pass_only -> feint_when_eligible / call | 54 | 54.0 | 1/1 | 0 | 0 | 0 |
| pass_only -> feint_when_eligible / fallback | 54 | 54.0 | 1/1 | 0 | 0 | 0 |
| pass_only -> prep_oriented / bite | 54 | 54.0 | 1/1 | 0 | 0 | 0 |
| pass_only -> prep_oriented / call | 54 | 54.0 | 1/1 | 0 | 0 | 0 |
| pass_only -> prep_oriented / fallback | 54 | 54.0 | 1/1 | 0 | 0 | 0 |
| top_direct -> feint_when_eligible / bite | 29 | 29.0 | 1/1 | 0 | 0 | 0 |
| top_direct -> feint_when_eligible / call | 29 | 29.0 | 1/1 | 0 | 0 | 0 |
| top_direct -> feint_when_eligible / fallback | 29 | 29.0 | 1/1 | 0 | 0 | 0 |
| top_direct -> prep_oriented / bite | 29 | 29.0 | 1/1 | 0 | 0 | 0 |
| top_direct -> prep_oriented / call | 29 | 29.0 | 1/1 | 0 | 0 | 0 |
| top_direct -> prep_oriented / fallback | 29 | 29.0 | 1/1 | 0 | 0 | 0 |
| bottom_escape -> feint_when_eligible / bite | 0 | 0.0 | 0/1 | 0 | 1 | 0 |
| bottom_escape -> feint_when_eligible / call | 17 | 17.0 | 1/1 | 0 | 1 | 0 |
| bottom_escape -> feint_when_eligible / fallback | 13 | 13.0 | 1/1 | 0 | 1 | 0 |
| bottom_escape -> prep_oriented / bite | 1 | 1.0 | 0/1 | 0 | 1 | 0 |
| bottom_escape -> prep_oriented / call | 0 | 0.0 | 0/1 | 0 | 1 | 0 |
| bottom_escape -> prep_oriented / fallback | 0 | 0.0 | 0/1 | 0 | 1 | 0 |
| bottom_trap_roll -> feint_when_eligible / bite | 21 | 21.0 | 1/1 | 0 | 0 | 0 |
| bottom_trap_roll -> feint_when_eligible / call | 21 | 21.0 | 1/1 | 0 | 0 | 0 |
| bottom_trap_roll -> feint_when_eligible / fallback | 21 | 21.0 | 1/1 | 0 | 0 | 0 |
| bottom_trap_roll -> prep_oriented / bite | 21 | 21.0 | 1/1 | 0 | 0 | 0 |
| bottom_trap_roll -> prep_oriented / call | 21 | 21.0 | 1/1 | 0 | 0 | 0 |
| bottom_trap_roll -> prep_oriented / fallback | 21 | 21.0 | 1/1 | 0 | 0 | 0 |
| seeded_legal -> feint_when_eligible / bite | 11 | 3.8 | 1/30 | 0 | 5 | 0 |
| seeded_legal -> feint_when_eligible / call | 38 | 9.1 | 6/30 | 0 | 5 | 0 |
| seeded_legal -> feint_when_eligible / fallback | 44 | 9.8 | 6/30 | 0 | 5 | 0 |
| seeded_legal -> prep_oriented / bite | 11 | 3.8 | 1/30 | 0 | 5 | 0 |
| seeded_legal -> prep_oriented / call | 11 | 3.8 | 1/30 | 0 | 5 | 0 |
| seeded_legal -> prep_oriented / fallback | 11 | 3.9 | 1/30 | 0 | 5 | 0 |

## Determinism and replay (STRUCTURAL)
games: 2534; windows driven: 74490; population trace digest (first run) 15c3e0493ca264d7bca2f402e174a462112bc956bd02ece8c939db82f18e74e9; (second run) 15c3e0493ca264d7bca2f402e174a462112bc956bd02ece8c939db82f18e74e9; replay IDENTICAL
policy errors (a refused command the harness did not intend; any non-zero value is a harness defect): 0

## Structural totals over every game above (STRUCTURAL; each must hold for the report to be valid)
Mount -> Half Guard transitions checked for identity, stamina, latch, meter, clock and window continuity: 68; violations: 0
Half Guard windows in which any stamina rose (Half Guard v0 has no recovery rule): 0
published-fallback exchanges: 3041; undercommitment +1 applied: 1693; expected from the funded commitments alone: 1693; any other modifier difference: 0
(measured, not an invariant) Mount windows where any stamina rose: 9763; Mount D3-B HOLD windows: 930; games ended by a tap: 189, by a clock end: 907, halted at an unsupported exit: 1438

