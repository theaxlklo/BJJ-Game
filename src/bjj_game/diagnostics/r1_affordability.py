"""R1 observer-only characterization: response commitment / provisional-hold
hold-inclusive affordability (docs/R1_HOLD_INCLUSIVE_AFFORDABILITY_DOD.md).

No candidate mechanics are implemented. The observer wraps the informed Bottom
response chooser, delegates the real choice exactly once, and records what the
responder could know at decision time. Counterfactual lower commitments are
evaluated only through the non-mutating preview API. Not thread-safe: run this
standalone, never concurrently with gameplay.
"""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
from unittest.mock import patch

from ..domain.action import Commitment
from ..domain.model import Grade, Side
from ..interfaces import batch as batch_module
from ..interfaces.batch import BatchBehaviorMode, run_escape_first_batch
from ..interfaces.production_policy import GATE_G_STAMINA_RECOVERY_POLICY
from ..interfaces.recovery_policy import RecoveryInitiationMode
from ..positions.mount.catalog import (
    TOP_AMERICANA_ARM_ISOLATION,
    TOP_AMERICANA_SUBMISSION_FINISH,
)
from .d3b_promotion import canonical_kwargs
from .d3b_promotion_reference import canonical_surface_kwargs
from .stamina_economy import _surface_kwargs

_ORDER = (Commitment.LOW, Commitment.MEDIUM, Commitment.HIGH)
HOLD_NOMINAL = 3


def production_surfaces() -> dict[str, dict]:
    """Canonical production surfaces (every setting from the canonical policy)."""
    return {
        "A-PROD": canonical_surface_kwargs("A"),
        "B-PROD": canonical_surface_kwargs("B"),
        "E-PROD 42": canonical_kwargs(42, "OFF"),
        "E-PROD 142": canonical_kwargs(142, "OFF"),
    }


def attribution_ladder() -> dict[str, dict]:
    """Surface E, seed 42: where the historical 1,366 mismatch went."""
    e = _surface_kwargs("E trusts reads + Bottom RECOVER")
    return {
        "E pre-change (no settlement rules, CURRENT)": e,
        "E + LOW_WHILE_EXHAUSTED only (Rule 1 OFF)": {
            **e,
            "recovery_initiation_mode": RecoveryInitiationMode.LOW_WHILE_EXHAUSTED,
        },
        "E + Rule 1 only (CURRENT)": {
            **e,
            "enable_unfunded_responder_cost_waiver": True,
        },
        "E + Gate-G policy (Rule 1 + LOW)": {
            **e,
            **GATE_G_STAMINA_RECOVERY_POLICY.batch_settings(
                bottom_behavior_mode=BatchBehaviorMode.RECOVER
            ),
        },
        "E-PROD canonical (D3-B)": canonical_kwargs(42, "OFF"),
    }


def _hold_path(match, action_id: str) -> str | None:
    """Hold-eligible path known before the response choice, if any."""
    if action_id == TOP_AMERICANA_SUBMISSION_FINISH and match.submission_state.active:
        return "FINISH"
    if (
        action_id == TOP_AMERICANA_ARM_ISOLATION
        and match.enable_v03_submissions
        and action_id in match.setup_policy.target_action_ids
        and match.setup_state.is_ready(action_id)
    ):
        return "ARM_READY"
    return None


def observe_batch(**kwargs):
    """Return the unmodified BatchSummary plus ordered decision-time records."""
    original = batch_module._informed_bottom_response_id
    decisions: list[dict] = []

    def predicted_grade(match, action_id, response_id, response_commitment,
                        commitment, use_recognition, perceived):
        if use_recognition:
            return match.preview_attempt_resolution_from_effective(
                action_id=action_id,
                response_id=response_id,
                initiator_effective_commitment=perceived,
                response_commitment=response_commitment,
            ).final_grade
        return match.preview_attempt_resolution(
            action_id=action_id,
            response_id=response_id,
            commitment=commitment,
            response_commitment=response_commitment,
        ).final_grade

    def observed(match, *, action_id, commitment=Commitment.MEDIUM,
                 response_commitment=Commitment.MEDIUM, use_recognition=False,
                 perceived_effective_commitment=None):
        response_id = original(
            match,
            action_id=action_id,
            commitment=commitment,
            response_commitment=response_commitment,
            use_recognition=use_recognition,
            perceived_effective_commitment=perceived_effective_commitment,
        )
        record = dict(
            elapsed=match.elapsed_simulated_time,
            action_id=action_id,
            recognition=use_recognition,
            hold_path=_hold_path(match, action_id),
        )
        if record["hold_path"] is not None:
            costs = match.stamina_cost_policy
            stamina = match.bottom.stamina.current
            true_effective = costs.effective_commitment(
                requested=commitment,
                available_stamina=match.top.stamina.current,
            )
            perceived = (
                perceived_effective_commitment if use_recognition else true_effective
            )
            grade = predicted_grade(match, action_id, response_id,
                                    response_commitment, commitment,
                                    use_recognition, perceived)
            effective = costs.effective_commitment(
                requested=response_commitment, available_stamina=stamina
            )
            commitment_cost = costs.cost(effective) if effective is not None else 0
            perceived_funded = perceived is not None
            projected_hold = (
                HOLD_NOMINAL
                if grade is Grade.CONTESTED and perceived_funded
                else 0
            )
            known_reserve = HOLD_NOMINAL if perceived_funded else 0
            alternatives = []
            if commitment_cost + projected_hold > stamina and effective is not None:
                for lower in reversed(_ORDER[: _ORDER.index(effective)]):
                    lower_id = original(
                        match,
                        action_id=action_id,
                        commitment=commitment,
                        response_commitment=lower,
                        use_recognition=use_recognition,
                        perceived_effective_commitment=perceived_effective_commitment,
                    )
                    lower_grade = predicted_grade(match, action_id, lower_id,
                                                  lower, commitment,
                                                  use_recognition, perceived)
                    lower_hold = (
                        HOLD_NOMINAL
                        if lower_grade is Grade.CONTESTED and perceived_funded
                        else 0
                    )
                    alternatives.append(dict(
                        commitment=lower.value,
                        predicted_grade=lower_grade.display,
                        affordable=costs.cost(lower) + lower_hold <= stamina,
                        no_defensive_loss=lower_grade <= grade,
                    ))
            record.update(
                responder_stamina=stamina,
                response_requested=response_commitment.value,
                response_effective=effective.value if effective else "UNFUNDED",
                initiator_true_funded=true_effective is not None,
                initiator_perceived_funded=perceived_funded,
                predicted_grade=grade.display,
                predicted_contested=grade is Grade.CONTESTED,
                projected_burden=commitment_cost + projected_hold,
                known_reserve_burden=commitment_cost + known_reserve,
                alternatives=alternatives,
            )
        decisions.append(record)
        return response_id

    with patch.object(batch_module, "_informed_bottom_response_id", observed):
        summary = run_escape_first_batch(**{**kwargs, "measure_stamina_economy": True})
    return summary, decisions


def _join(summary, decisions):
    top_rows = [
        row for row in summary.stamina_economy.exchanges if row.initiator is Side.TOP
    ]
    if len(top_rows) != len(decisions):
        raise RuntimeError("decision/exchange alignment failed")
    for row, decision in zip(top_rows, decisions):
        if (row.action_id, row.elapsed_seconds) != (
            decision["action_id"], decision["elapsed"]
        ):
            raise RuntimeError("decision/exchange alignment failed")
    return list(zip(top_rows, decisions))


def characterize(summary, decisions) -> dict:
    exchanges = summary.stamina_economy.exchanges
    holds = [row for row in exchanges if row.submission_hold]
    joined = _join(summary, decisions)
    out: dict = dict(
        exchanges=len(exchanges),
        top_initiated=len(joined),
        bottom_initiated=len(exchanges) - len(joined),
        holds=len(holds),
        holds_outside_known_path=sum(
            row.submission_hold for row, d in joined if d["hold_path"] is None
        ),
        threat_matches=len({r.match_index for r in exchanges if r.transition_into_threat}),
        threat_entries=sum(r.transition_into_threat for r in exchanges),
        taps=sum(r.tapped for r in exchanges),
        rule1_waived_holds=sum(
            row.initiator_effective_commitment == "UNFUNDED" for row in holds
        ),
        funded_initiator_holds=sum(
            row.initiator_effective_commitment != "UNFUNDED" for row in holds
        ),
        additive_response_plus_hold=sum(
            row.response_commitment_charged >= 3 and row.hold_charged > 0
            and row.initiator_effective_commitment != "UNFUNDED"
            for row in holds
        ),
        hold_payment_status=dict(Counter(row.hold_payment_status for row in holds)),
        hold_stamina_charged=sum(row.hold_charged for row in holds),
        hold_shortfall=sum(row.hold_shortfall for row in holds),
        commitment_only_fundable_but_plus_hold_not=sum(
            row.commitment_only_fundable_but_requested_plus_hold_not for row in holds
        ),
        response_downgraded_all_exchanges=sum(
            row.responder_requested_commitment != row.responder_effective_commitment
            for row in exchanges
        ),
        response_downgraded_on_holds=sum(
            row.responder_requested_commitment != row.responder_effective_commitment
            for row in holds
        ),
    )
    paths: dict = {}
    for path in ("FINISH", "ARM_READY"):
        rows = [(r, d) for r, d in joined if d["hold_path"] == path]
        recognised = [(r, d) for r, d in rows if d["recognition"]]
        projected = [(r, d) for r, d in rows if d["projected_burden"] > d["responder_stamina"]]
        reserve = [(r, d) for r, d in rows if d["known_reserve_burden"] > d["responder_stamina"]]
        paths[path] = dict(
            eligible_decisions=len(rows),
            actual_holds=sum(r.submission_hold for r, _ in rows),
            predicted_contested_and_held=sum(d["predicted_contested"] and r.submission_hold for r, d in rows),
            predicted_contested_not_held=sum(d["predicted_contested"] and not r.submission_hold for r, d in rows),
            predicted_other_but_held=sum(not d["predicted_contested"] and r.submission_hold for r, d in rows),
            predicted_other_not_held=sum(not d["predicted_contested"] and not r.submission_hold for r, d in rows),
            recognition_decisions=len(recognised),
            perceived_funded_true_unfunded=sum(
                d["initiator_perceived_funded"] and not d["initiator_true_funded"]
                for _, d in recognised
            ),
            perceived_unfunded_true_funded=sum(
                not d["initiator_perceived_funded"] and d["initiator_true_funded"]
                for _, d in recognised
            ),
            projected_burden_unaffordable=len(projected),
            projected_unaffordable_actual_hold_charged=sum(
                r.hold_requested > 0 for r, _ in projected
            ),
            projected_unaffordable_rule1_waived=sum(
                r.submission_hold and r.hold_requested == 0 for r, _ in projected
            ),
            projected_unaffordable_no_hold=sum(not r.submission_hold for r, _ in projected),
            projected_unaffordable_no_lower_commitment=sum(
                not d["alternatives"] for _, d in projected
            ),
            projected_unaffordable_free_downgrade_exists=sum(
                any(a["affordable"] and a["no_defensive_loss"] for a in d["alternatives"])
                for _, d in projected
            ),
            projected_unaffordable_downgrade_only_with_defensive_loss=sum(
                bool(d["alternatives"])
                and not any(a["affordable"] and a["no_defensive_loss"] for a in d["alternatives"])
                for _, d in projected
            ),
            lower_commitment_predicted_grades=dict(Counter(
                f'{a["commitment"]}:{a["predicted_grade"]}'
                for _, d in projected for a in d["alternatives"]
            )),
            known_reserve_unaffordable=len(reserve),
            known_reserve_unaffordable_without_actual_hold=sum(
                not r.submission_hold or r.hold_requested == 0 for r, _ in reserve
            ),
        )
    out["paths"] = paths
    return out


def measure() -> dict:
    report = {"production": {}, "attribution_ladder": {}}
    for name, kwargs in production_surfaces().items():
        report["production"][name] = characterize(*observe_batch(**kwargs))
    for name, kwargs in attribution_ladder().items():
        rows = run_escape_first_batch(
            **{**kwargs, "measure_stamina_economy": True}
        ).stamina_economy.exchanges
        holds = [row for row in rows if row.submission_hold]
        report["attribution_ladder"][name] = dict(
            holds=len(holds),
            hold_requested_nonzero=sum(row.hold_requested > 0 for row in holds),
            commitment_only_fundable_but_plus_hold_not=sum(
                row.commitment_only_fundable_but_requested_plus_hold_not
                for row in holds
            ),
            additive_response_plus_hold=sum(
                row.response_commitment_charged >= 3 and row.hold_charged > 0
                for row in holds
            ),
            hold_stamina_charged=sum(row.hold_charged for row in holds),
            taps=sum(row.tapped for row in rows),
        )
    return report


if __name__ == "__main__":
    target = Path("docs/evidence/r1_affordability_characterization.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(measure(), indent=2, sort_keys=True) + "\n")
    print(target)
