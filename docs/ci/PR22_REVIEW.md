# Read-only PR #22 review

Reviewed `83d2eb9d4d5f29249f1954ebf7b6b82661bac982` against PR #18 head
`9c4166cef43d367786bbb24b76bccef6624779ba`. No gameplay edits were made.

## Findings

1. **Medium, verification hardening; not a merge blocker for the bounded supported slice.**
   `GODOT_V1/tests/test_exchange_reference.gd:115` accepts NaN in an axis comparison:
   `absf(actual - expected) > epsilon` evaluates false for NaN. A headless probe calling
   `compare("review.result.axis_after", NAN, 1.5)` reported **1 check, 0 mismatches**.
   Incoming axes are explicitly checked for finiteness and bounded, so this finding
   does not demonstrate a runtime mismatch. Nevertheless the verifier should reject
   nonfinite actual/expected values explicitly and test NaN and both infinities.
   Correct this in the parity harness separately; CI routing does not alter it.

2. **Low, public result construction hardening; not a merge blocker.**
   `GODOT_V1/scripts/core/exchange_result.gd:152,172,178`: a newly constructed
   `BjjExchangeResult` reports `ok()` even though funding and outcome fields are null.
   Headless probe: `ok=true`, `funding-present=false`, `outcome-present=false`.
   Calling its serialization method before initialization can dereference null.
   The exchange entry point populates results before returning them; no supported
   exchange defect was observed. Prefer an initially invalid/uninitialized result
   or a factory that guarantees completeness. Address outside this CI change.

## Mechanics inspected

Validation precedes authoritative mutation. Both historical bands and the original
initiator are captured before charging. Requested/effective commitment and UNFUNDED
remain distinct; raw defaults do not adopt production flags. The v0.4a magnitude
transform precedes undercommitment, with sequential grade saturation and final
re-resolution. Position/setup/submission handling precedes initiator, responder,
and hold charges. Rule 1 waives both responder paths only for UNFUNDED initiators.
Production selects Rule 1 ON / Rule 2 OFF; supplemental hold credit remains an
explicit control. Contested finish and Ready isolation conditions are narrow.
Historical result serialization copies mutable collections. Approved terminal
rejection differences are documented and excluded from source-outcome equivalence.

No merge-blocking gameplay defect was found within the claimed slice. This is a
code review, not complete MountMatch or production recovery parity certification.
RECOVER, D3-B, clocks, Recognition and custom controllers remain outside the slice.

## Evidence verified

Final-head GitHub jobs and step conclusions are successful:

- [Python qualification](https://github.com/theaxlklo/BJJ-Game/actions/runs/37997418131):
  twelve shards, both verification jobs, both history jobs, aggregate gate.
- [Godot qualification](https://github.com/theaxlklo/BJJ-Game/actions/runs/37997418190):
  import, all predecessor suites, exchange suites, scene startup.

The generator invokes unchanged Python APIs. The source corpus and documented
report distinguish 14,631 scenarios, 14,780 operations, 8,851,698 scalar/structure
comparisons, 233 native assertions and four approved terminal-boundary operations.
These counts are not independent tests per field. This review inspected the corpus
construction and CI metadata; it did not obtain raw hosted logs for every field.
The routing PR reruns the unchanged qualification steps.
