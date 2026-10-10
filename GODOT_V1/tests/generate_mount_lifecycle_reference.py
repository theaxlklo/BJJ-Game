#!/usr/bin/env python3
"""Independent trajectories from unchanged MountMatch and AdaptiveBehaviorPolicy."""
from dataclasses import asdict
from itertools import product
from pathlib import Path
import json

from bjj_game.engine.match import MountMatch
from bjj_game.domain.stamina import StaminaPool
from bjj_game.domain.model import Side, TopBehavior, BottomBehavior
from bjj_game.interfaces.batch import AdaptiveBehaviorPolicy, BatchBehaviorMode
from generate_exchange_reference import normalized, snapshot


def state(m):
    return dict(snapshot(m), top_behavior=m.top.behavior.value,
                bottom_behavior=m.bottom.behavior.value,
                top_remainder=m.top_behavior_stamina_meter.remainder_units,
                bottom_remainder=m.bottom_behavior_stamina_meter.remainder_units)


def trajectory(top_behavior, bottom_behavior, capacity, start, recover, durations):
    m = MountMatch(initial_clock=41)
    m.top.stamina = StaminaPool(start, capacity)
    m.bottom.stamina = StaminaPool(start, capacity)
    m.set_behaviors(top=TopBehavior(top_behavior), bottom=BottomBehavior(bottom_behavior))
    policy = AdaptiveBehaviorPolicy(Side.BOTTOM, BottomBehavior(bottom_behavior),
                                   BatchBehaviorMode.RECOVER if recover else BatchBehaviorMode.FIXED)
    initial = state(m)
    steps = []
    for duration in durations:
        if recover and duration < 0:
            continue # batch never admits negative intervals; native validation tests cover this.
        before = state(m)
        if recover:
            m.bottom.set_behavior(policy.choose(m))
        m.interval_seconds = duration
        try:
            result = m.advance()
            expected = normalized(asdict(result))
            expected['top_stamina']['net_change'] = result.top_stamina.net_change
            expected['bottom_stamina']['net_change'] = result.bottom_stamina.net_change
            if recover and not m.ended:
                m.bottom.set_behavior(policy.choose(m))
            rejected = False
        except (ValueError, RuntimeError):
            expected, rejected = {}, True
            assert state(m) == before
        steps.append(dict(duration=duration, rejected=rejected, result=expected, state=state(m)))
        if m.ended:
            break
    return dict(label=f'{top_behavior}/{bottom_behavior}/{capacity}/{start}/{recover}/{durations}',
                initial=initial, recover=recover, baseline=bottom_behavior, steps=steps)


def main():
    cases = []
    for top, bottom, capacity, recover in product(('PRESSURE','HOLD','CONSERVE'),
            ('ESCAPE','PROTECT','CONSERVE'), (7, 100, 101), (False, True)):
        starts = sorted({0, capacity, int(capacity*.25), int(capacity*.35), int(capacity*.35)-1})
        for start, durations in product(starts, ([-1, 1, 4, 5, 2, 29], [0, 1, 1, 1, 1, 1, 36], [5]*9)):
            cases.append(trajectory(top, bottom, capacity, start, recover, durations))
    path = Path(__file__).parent/'generated'/'mount_lifecycle_reference.jsonl'
    path.parent.mkdir(exist_ok=True)
    with path.open('w') as out:
        for case in cases:
            out.write(json.dumps(case, allow_nan=False, separators=(',',':'))+'\n')
    print(f'Mount advancement oracle: {len(cases)} scenarios, {sum(len(c["steps"]) for c in cases)} operations')

if __name__ == '__main__':
    main()
