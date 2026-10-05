"""D1 observer-only tracing. Scoped wrappers delegate each engine call once.

No candidate mechanics are implemented. Not thread-safe: run this standalone
measurement in one process, never concurrently with gameplay.
"""
from contextlib import ExitStack
from dataclasses import asdict, is_dataclass
from enum import Enum
import gzip
import json
from pathlib import Path
from unittest.mock import patch

from ..domain.stamina import StaminaPool, StaminaBand
from ..engine.match import MountMatch
from ..interfaces.batch import run_escape_first_batch
from ..interfaces.production_policy import GATE_G_STAMINA_RECOVERY_POLICY
from .stamina_adoption_candidate import _surface_e_prod_kwargs
from .stamina_adoption_handoff import horizon_counts, match_level_sensitivity


def scalar(value):
    if is_dataclass(value):
        return scalar(asdict(value))
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): scalar(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [scalar(v) for v in value]
    return value


def trace_batch(**kwargs):
    """Return unmodified BatchSummary plus ordered, detached mutation records."""
    events = []
    matches = []
    context = {}
    originals = {name: getattr(MountMatch, name) for name in
                 ('advance', 'attempt', 'reset_window')}

    def wrap(name):
        def delegated(match, *args, **kw):
            if not any(existing is match for existing in matches):
                matches.append(match)
            context.update(match=match, kind=name, inputs=scalar(kw),
                           mutations=[])
            before_setup = scalar(match.setup_state)
            before_submission = scalar(match.submission_state)
            result = originals[name](match, *args, **kw)
            events.append(dict(
                match_index=next(i for i, m in enumerate(matches) if m is match),
                time=match.elapsed_simulated_time, kind=name,
                inputs=scalar(kw), bottom_behavior=match.bottom.behavior.value,
                mutations=context['mutations'], result=scalar(asdict(result)),
                setup_before=before_setup, setup_after=scalar(match.setup_state),
                submission_before=before_submission,
                submission_after=scalar(match.submission_state),
                bottom_stamina=match.bottom.stamina.current,
                bottom_exhausted=match.bottom.stamina.band is StaminaBand.EXHAUSTED,
            ))
            context.clear()
            return result
        return delegated

    def pool_wrap(name, original):
        def delegated(pool, requested):
            before_exhausted = pool.band is StaminaBand.EXHAUSTED
            result = original(pool, requested)
            match = context.get('match')
            if match is not None and pool is match.bottom.stamina:
                context['mutations'].append(dict(
                    operation=name, **asdict(result),
                    exhausted_before=before_exhausted,
                    exhausted_after=pool.band is StaminaBand.EXHAUSTED,
                ))
            return result
        return delegated

    with ExitStack() as stack:
        for name in originals:
            stack.enter_context(patch.object(MountMatch, name, wrap(name)))
        for name in ('spend_up_to', 'recover_up_to'):
            stack.enter_context(patch.object(StaminaPool, name,
                pool_wrap(name, getattr(StaminaPool, name))))
        summary = run_escape_first_batch(**kwargs)
    return summary, events


def characterize(summary, events):
    """Retain zero-time spends after clear; never count pre-clear mutations."""
    episodes = []
    for index, event in enumerate(events):
        for mi, mutation in enumerate(event['mutations']):
            if not (mutation['exhausted_before'] and not mutation['exhausted_after']):
                continue
            following = []
            for ei in range(index, len(events)):
                later = events[ei]
                if later['match_index'] != event['match_index']:
                    break
                if later['time'] - event['time'] > 30:
                    break
                selected = later['mutations'][mi + 1:] if ei == index else later['mutations']
                following.append({**later, 'mutations': selected,
                                  'offset': later['time'] - event['time']})
            episodes.append(dict(match_index=event['match_index'],
                clear_time=event['time'], clear=mutation, following=following,
                match_end=next(h.match_end_elapsed_seconds for h in
                    summary.reexhaustion_handoffs.episodes if
                    h.match_index == event['match_index'] and
                    h.clear_elapsed_seconds == event['time'])))
    handoffs = summary.reexhaustion_handoffs.episodes
    return dict(clears=len(episodes), episodes=episodes,
        horizons=[asdict(horizon_counts(handoffs, h)) for h in (5,10,15,20,30)],
        match_sensitivity={str(h): asdict(match_level_sensitivity(handoffs, h))
                           for h in (5,10,15,20,30)})


def measure():
    reports = {}
    for seed in (42, 142):
        kwargs = _surface_e_prod_kwargs(stalling=False, shadow=True, base_seed=seed)
        kwargs.update(GATE_G_STAMINA_RECOVERY_POLICY.batch_settings(
            bottom_behavior_mode=kwargs['bottom_behavior_mode']))
        summary, events = trace_batch(**kwargs)
        reports[str(seed)] = characterize(summary, events)
    return reports


if __name__ == '__main__':
    target = Path('docs/evidence/handoff_d1_trace.json.gz')
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(gzip.compress(
        (json.dumps(measure(), indent=2, sort_keys=True) + '\n').encode(),
        mtime=0))
    print(target)
