#!/usr/bin/env python3
"""Invoke unchanged Python contracts; no port calculations form expectations."""
import json
from dataclasses import asdict
from pathlib import Path
from bjj_game.domain.stamina import StaminaPool, StaminaBand
from bjj_game.domain.action import Commitment
from bjj_game.domain.model import TopBehavior, BottomBehavior
from bjj_game.engine.stamina import (
    DEFAULT_STAMINA_COST_POLICY as COST,
    DEFAULT_BEHAVIOR_STAMINA_POLICY as FLOW,
    DEFAULT_EXHAUSTION_POLICY as EXHAUSTION,
    BehaviorStaminaMeter, StaminaCostPolicy, BehaviorStaminaPolicy,
)


def state(pool, meter):
    return dict(current=pool.current, maximum=pool.maximum, band=pool.band.value,
                enter=pool.exhaustion_enter_threshold,
                clear=pool.exhaustion_recover_threshold, remainder=meter.remainder_units)


def trace(current, maximum, operations, remainder=0):
    pool, meter = StaminaPool(current, maximum), BehaviorStaminaMeter(remainder)
    steps = []
    for op in operations:
        result, error = {}, False
        try:
            kind, value = op['kind'], op['value']
            if kind == 'set':
                pool.set_current(value)
            elif kind == 'spend':
                r = pool.spend_up_to(value)
                result = dict(asdict(r), fully_paid=r.fully_paid)
            elif kind == 'recover':
                result = asdict(pool.recover_up_to(value))
            elif kind == 'flow':
                behavior = (TopBehavior(op['behavior']) if op['behavior'] in
                            {'PRESSURE', 'HOLD', 'CONSERVE'} else BottomBehavior(op['behavior']))
                r = FLOW.apply(pool=pool, meter=meter, behavior=behavior, duration_seconds=value)
                result = dict(asdict(r), behavior=r.behavior.value, net_change=r.net_change)
        except (ValueError, TypeError, KeyError):
            error = True
        steps.append(dict(operation=op, rejected=error, result=result, state=state(pool, meter)))
    return dict(current=current, maximum=maximum, remainder=remainder, steps=steps)


def main():
    # Rejections precede valid operations, proving replay remains usable.
    traces = [trace(26, 100, [dict(kind=k, value=v) for k, v in
              [('set', -1), ('set', 101), ('spend', -1), ('recover', -1),
               ('flow', -1), ('spend', 0), ('recover', 0), ('spend', 1),
               ('set', 34), ('set', 35), ('set', 34), ('set', 25),
               ('recover', 100), ('spend', 200), ('recover', 0)]] )]
    traces[0]['steps'][4]['operation']['behavior'] = 'PRESSURE'
    for maximum in (1, 2, 3, 7, 11, 99, 100, 101, 137, 1000):
        for current in range(maximum + 1):
            traces.append(trace(current, maximum, [dict(kind=k, value=v) for k, v in
                [('spend', 0), ('recover', 0), ('spend', 3), ('recover', 7),
                 ('set', maximum), ('spend', maximum), ('recover', maximum)]]))
    behaviors = ['PRESSURE', 'HOLD', 'ESCAPE', 'PROTECT', 'CONSERVE']
    for current in (0, 1, 25, 26, 34, 35, 99, 100):
        for remainder in (-9, -4, -1, 0, 1, 4, 9):
            ops = [dict(kind='flow', behavior=b, value=d)
                   for b in behaviors for d in (-1, 0, 1, 2, 4, 5, 6, 17)]
            ops.insert(0, dict(kind='flow', behavior='INVALID', value=5))
            traces.append(trace(current, 100, ops, remainder))
        for behavior in behaviors:
            for durations in ([1]*5, [5], [1, 2, 7], [10], [0, 5, 0]):
                traces.append(trace(current, 100, [dict(kind='flow', behavior=behavior, value=d)
                                                  for d in durations]))
    constructors = []
    for current, maximum in ((-1, 100), (101, 100), (0, 0), (0, -1), (0, 1), (1, 1)):
        try:
            StaminaPool(current, maximum)
            rejected = False
        except (ValueError, TypeError):
            rejected = True
        constructors.append(dict(current=current, maximum=maximum, rejected=rejected))
    costs = []
    for config in ({'LOW':3, 'MEDIUM':7, 'HIGH':12}, {'LOW':0,'MEDIUM':1,'HIGH':2},
                   {}, {'LOW':3,'MEDIUM':3,'HIGH':12}, {'LOW':-1,'MEDIUM':7,'HIGH':12},
                   {'LOW':3,'MEDIUM':7,'HIGH':12,'INVALID':0}, {'LOW':3,'MEDIUM':7.5,'HIGH':12}):
        try:
            policy = StaminaCostPolicy.build(config)
            rejected = False
        except (ValueError, TypeError):
            rejected = True
        cases = []
        if not rejected:
            for requested in [*Commitment, 'INVALID']:
                for available in range(-1, 15):
                    try:
                        effective = policy.effective_commitment(requested=requested, available_stamina=available)
                        requested_cost = policy.cost(requested)
                        effective_cost = policy.cost(effective) if effective is not None else 0
                        result = dict(requested=str(requested.value), effective=effective.value if effective else '',
                                      requested_cost=requested_cost, effective_cost=effective_cost,
                                      funding_gap=requested_cost-effective_cost)
                        failed = False
                    except (ValueError, KeyError):
                        failed, result = True, {}
                    cases.append(dict(requested=requested, available=available, rejected=failed, result=result))
        costs.append(dict(config=config, rejected=rejected, cases=cases))
    exhaustion = [dict(initiator=a.value, responder=b.value,
                      initiator_modifier=EXHAUSTION.initiator_grade_modifier(a),
                      responder_modifier=EXHAUSTION.responder_grade_modifier(b),
                      modifier=EXHAUSTION.exchange_grade_modifier(initiator_band=a, responder_band=b))
                  for a in StaminaBand for b in StaminaBand]
    flow_configs = []
    defaults = {b.value: r for b, r in FLOW.points_per_quantum.items()}
    for quantum, rates in ((5, defaults), (1, defaults), (0, defaults), (-1, defaults),
                           (5, {}), (5, dict(defaults, INVALID=0)), (5, dict(defaults, HOLD=0.5))):
        try:
            BehaviorStaminaPolicy.build(quantum_seconds=quantum, points_per_quantum=rates)
            rejected = False
        except (ValueError, TypeError):
            rejected = True
        flow_configs.append(dict(quantum=quantum, rates=rates, rejected=rejected))
    assert dict(COST.costs) == {'LOW':3, 'MEDIUM':7, 'HIGH':12}
    assert FLOW.quantum_seconds == 5 and defaults == dict(PRESSURE=-1,HOLD=0,ESCAPE=-1,PROTECT=0,CONSERVE=2)
    output = Path(__file__).parent / 'generated' / 'stamina_reference.json'
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(dict(schema=1, constructors=constructors, traces=traces,
                                     costs=costs, exhaustion=exhaustion, flow_configs=flow_configs),
                                sort_keys=True, separators=(',', ':'))+'\n')
    print(f'Python stamina fixtures: {len(traces)} traces, {sum(len(t["steps"]) for t in traces)} operations')


if __name__ == '__main__':
    main()
