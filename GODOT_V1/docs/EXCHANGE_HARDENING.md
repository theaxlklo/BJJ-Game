# Exchange contract hardening

The negative-first regression run demonstrated both review findings: a blank
result returned success and dereferenced null funding during serialization; the
numeric comparator lacked finite-value admission. Nine new native assertions
cover blank-result safety, NaN and both infinities on either side of comparison,
and an equal finite axis.

`ok()` now requires the mandatory historical records as well as an empty error.
Exchange admission checks its explicit validation error before filling those
records. Incomplete serialization returns `incomplete_exchange_result`.
The parity comparator rejects every nonfinite numeric value before tolerance
comparison; the existing 1e-10 axis tolerance is unchanged.

No Python reference, gameplay rule, fixture expectation or predecessor history
was changed. This PR depends on CI PR #23 and therefore preserves the complete
#17 → #18 → #22 → #23 stack. See its Actions run for current qualification.
