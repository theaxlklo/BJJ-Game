# Half Guard v0 independent oracle (B1b checkpoint)

**Status: test-only. Nothing in the oracle is production code.** The typed GDScript engine (`GODOT_V1/scripts/positions/half_guard/`, see [HALF_GUARD_V0_ENGINE.md](HALF_GUARD_V0_ENGINE.md)) was written *after* the oracle and is replayed against its fixture. The oracle executes the rules of
[HALF_GUARD_V0_RULES.md](HALF_GUARD_V0_RULES.md) (the provisional v0 prototype baseline, C1 grades, decisions N-1 … N-11) so that the later typed GDScript
engine can be compared with a second, independently written implementation. It is not a balance claim.

## Files

| File | Purpose |
| --- | --- |
| `tests/oracles/half_guard_v0.py` | The oracle: stdlib-only executor (`validate_entry`, `HalfGuard`, `replay`, helpers) |
| `tests/oracles/half_guard_v0_scenarios.py` | Bounded, deterministic scenario families and structural searches (shared by tests and generator) |
| `tests/test_half_guard_oracle.py` | Focused unit tests (hand-computed literals, boundary grids, trajectories, frozen cross-checks, doc consistency) |
| `GODOT_V1/tests/generate_half_guard_reference.py` | Deterministic JSONL fixture generator for the later Godot parity suite (output git-ignored; **not wired into CI yet**) |
| `GODOT_V1/docs/HALF_GUARD_V0_RULES.md` | The canonical rules sheet the oracle is written from |

## Independence evidence

* The oracle imports only `copy`, `hashlib`, `json`, `math` (AST-checked); it never imports `bjj_game`, never constructs or runs a `MountMatch`, reads no file, uses no clock and no randomness (AST-checked).
* It was written from the rules sheet before any Half Guard GDScript existed, and no existing GDScript was translated. The engine was then written from the same sheet and compared with the oracle through the generated fixture (a mismatch is a bug in one of the two, never silently reconciled).
* The frozen Python reference is imported **only inside the unit tests** to compare position-independent helper semantics: stamina thresholds/bands/latch transitions (including capacities near 2^53), the cost policy, the exhaustion modifier, the magnitude and undercommitment helpers and `Grade.shift`.
* `RulesSheetConsistencyTests` parse the 15 raw-grade cells and the 8 hysteresis rules out of the rules sheet and compare them with the oracle tables, so the document cannot drift from the code unnoticed.
* The scenario module defines each helper, table and trajectory exactly once (an earlier draft carried shadowed duplicates). A development-time **mutation-sensitivity control** (disposable copies, not committed) confirmed that each of these single mutations is detected by the focused suite: C0 grade restored; defense None shift +2→+1; attack Ready shift +1→0; HIGH preservation ignoring payment; HIGH wearing like MEDIUM; a LOW response still wearing; Rule 1 waiver removed; no consumption on an exit; defense applied before attack (saturation order); pass line 30→35; a hysteresis threshold 12→13; undercommitment removed; initiative flipping on an exit.

## Running it

```
# focused oracle unit tests (development)
PYTHONPATH=src python -m unittest discover -s tests -p "test_half_guard_oracle.py"
# the fixture (git-ignored output); prints measured scenario / operation / comparison counts
python GODOT_V1/tests/generate_half_guard_reference.py [output.jsonl]
```

The tests are discovered by the same `unittest.defaultTestLoader.discover("tests")` loader and 6-way shard selection the Python CI job already uses (a test asserts discoverability). They need `PYTHONPATH=src` only for the frozen cross-checks; without it those tests are skipped and say so.
The full Python CLI and the historical Python matrix are **not** part of this checkpoint's iteration.

## Scenario families and measured counts

Counts are produced by running the code; they are never asserted from this document. Measured at the checkpoint commit: see the checkpoint report for the exact values and commands. The fixture families are `initial_band`, `band_update`, `entry`, `exchange_grid`, `break_grid` and `trajectory`:
the exchange grid is **exhaustive over the small structured space** (15 matchups × 9 readiness tier pairs × 9 commitment pairs) crossed with **11 stamina profiles chosen per rule class** (fresh, either side Exhausted, both Exhausted, MEDIUM-only, LOW-only and unfunded initiator, responder at the HIGH / MEDIUM-down / LOW-down / unfunded boundaries);
the break grid covers the six break matchups across 16 axis boundary values and every legal band, all 9 tier pairs and three initiator commitments; entries and trajectories are hand-designed.

## Known limitations

* The oracle covers direct techniques, preparation, defensive effort, entry, windows and replay only. Feints, the sealed-intent protocol, behaviors, recovery, Standing and contract-level addressing are out of scope.
* Runtime evidence is from the system Python used locally; Python 3.11 / 3.13 runtime evidence is CI-only. Syntax compatibility of every new file was checked with `ast.parse(..., feature_version=(3, 11))`, `(3, 13)` and `(3, 14)`.
* The fixture embeds full snapshots (large); the later Godot suite may prefer a compact encoding.
* Structural searches use fixed responder policies; they are reachability facts, not balance evidence.
