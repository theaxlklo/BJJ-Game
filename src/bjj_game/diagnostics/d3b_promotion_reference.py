"""Code-version-independent gameplay fingerprints for D3-B promotion PG5/PG6.

Uses only APIs that exist both at the D3-B result checkpoint (1b96ffc) and
after promotion, so the same file can be run against either source tree:

    PYTHONPATH=<tree>/src python src/bjj_game/diagnostics/d3b_promotion_reference.py OUT.json

Fingerprints are sha256 of repr((summary, per-match gameplay signatures)) as
captured by the Gate-G equivalence tool (deterministic; no object addresses).
"""

from __future__ import annotations

import hashlib
from inspect import Parameter, signature
import json
import sys

from bjj_game.diagnostics.stamina_adoption_candidate import _surface_e_prod_kwargs
from bjj_game.diagnostics.stamina_adoption_verification import (
    POLICY_KEYS,
    _run_captured,
    diagnostic_kwargs,
)
from bjj_game.engine.match import MountMatch
from bjj_game.interfaces.batch import BatchBehaviorMode, run_escape_first_batch
from bjj_game.interfaces.production_policy import PRODUCTION_STAMINA_RECOVERY_POLICY


def _fingerprint(kwargs: dict) -> str:
    return hashlib.sha256(repr(_run_captured(kwargs)).encode()).hexdigest()


def _defaults(function) -> dict:
    return {
        name: repr(parameter.default)
        for name, parameter in signature(function).parameters.items()
        if parameter.default is not Parameter.empty
    }


def raw_default_kwargs() -> dict:
    """Only the required batch arguments (E-PROD values); every option default."""
    eprod = _surface_e_prod_kwargs(stalling=False, shadow=True)
    return {
        name: eprod[name]
        for name, parameter in signature(run_escape_first_batch).parameters.items()
        if parameter.default is Parameter.empty
    }


def canonical_surface_kwargs(name: str) -> dict:
    """Surface A or B with every stamina/recovery setting from the canonical policy."""
    base = {k: v for k, v in diagnostic_kwargs(name).items() if k not in POLICY_KEYS}
    return {
        **base,
        **PRODUCTION_STAMINA_RECOVERY_POLICY.batch_settings(
            bottom_behavior_mode=base.get("bottom_behavior_mode", BatchBehaviorMode.FIXED)
        ),
    }


def reference() -> dict:
    return {
        "batch_defaults": _defaults(run_escape_first_batch),
        "match_defaults": _defaults(MountMatch),
        "raw_default_batch": _fingerprint(raw_default_kwargs()),
        "canonical_A": _fingerprint(canonical_surface_kwargs("A")),
        "canonical_B": _fingerprint(canonical_surface_kwargs("B")),
    }


if __name__ == "__main__":
    with open(sys.argv[1], "w") as handle:
        json.dump(reference(), handle, indent=1, sort_keys=True)
