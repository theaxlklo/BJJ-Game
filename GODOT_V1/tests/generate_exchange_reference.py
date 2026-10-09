#!/usr/bin/env python3
"""Independent exchange oracle: unchanged MountMatch.attempt(), no copied math."""
import json
from dataclasses import asdict
from enum import Enum
from pathlib import Path

from bjj_game.domain.action import Commitment
from bjj_game.domain.model import Band, Side, TopBehavior, BottomBehavior, ExitDestination
from bjj_game.domain.setup import SetupTier
from bjj_game.domain.stamina import StaminaPool
from bjj_game.domain.submission import SubmissionStage
from bjj_game.engine.match import MountMatch
from bjj_game.engine.stamina import StaminaCostPolicy
from bjj_game.interfaces.production_policy import PRODUCTION_STAMINA_RECOVERY_POLICY
from bjj_game.positions.mount.catalog import (
    MOUNT_CATALOG, TOP_HIGH_MOUNT_CLIMB, TOP_CROSSFACE_PRESSURE,
    TOP_AMERICANA_ARM_ISOLATION, TOP_AMERICANA_SUBMISSION_FINISH,
    BOTTOM_BRIDGE, BOTTOM_TRAP_AND_ROLL_ESCAPE,
    TOP_RESPONSE_POST_AND_BASE, TOP_RESPONSE_WIDE_MOUNT_BASE, TOP_RESPONSE_HIP_FOLLOW_REPUMMEL,
    BOTTOM_RESPONSE_FOREARM_FRAME, BOTTOM_RESPONSE_TURN_IN_RECOVERY, BOTTOM_RESPONSE_TIGHT_ELBOW_ARM_DEFENSE,
)
from bjj_game.positions.mount.matchups import MOUNT_MATCHUPS

BANDS = {b: i for i, b in enumerate(Band)}
FLAGS = ['enable_v02_setup', 'enable_v03_submissions', 'enable_v03b_stalling',
         'enable_v04_commitment_semantics', 'enable_v04b_recognition',
         'enable_stamina_settlement_rules', 'enable_unfunded_responder_cost_waiver',
         'enable_supplemental_hold_settlement']
POLICIES = {
    'raw': {}, 'v04': dict(enable_v04_commitment_semantics=True),
    'production': dict(enable_v04_commitment_semantics=True,
                       **PRODUCTION_STAMINA_RECOVERY_POLICY.match_settings()),
    'rule1': dict(enable_v04_commitment_semantics=True, enable_unfunded_responder_cost_waiver=True),
    'rule2': dict(enable_v04_commitment_semantics=True, enable_supplemental_hold_settlement=True),
    'both': dict(enable_v04_commitment_semantics=True, enable_stamina_settlement_rules=True),
}


def normalized(value):
    if isinstance(value, Band):
        return BANDS[value]
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {k: normalized(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [normalized(v) for v in value]
    return value


def resolution(r):
    out = normalized(asdict(r))
    out['exit_destination'] = r.exit_destination.value if r.exit_destination else ''
    return out


def spend(r):
    return dict(asdict(r), fully_paid=r.fully_paid) if r is not None else None


def snapshot(m, history=True):
    out = dict(axis=m.axis, control_axis=m.position.control.value, band=BANDS[m.band],
               broken=m.position.broken, crossing_axis=m.position.crossing_axis,
               initiator=m.initiator.value, initial_clock=m.initial_clock, clock_seconds=m.clock_seconds,
               top_stamina=m.top.stamina.current, bottom_stamina=m.bottom.stamina.current,
               top_maximum=m.top.stamina.maximum, bottom_maximum=m.bottom.stamina.maximum,
               top_band=m.top.stamina.band.value, bottom_band=m.bottom.stamina.band.value,
               americana_tier=int(m.setup_state.tier(TOP_AMERICANA_ARM_ISOLATION)),
               trap_tier=int(m.setup_state.tier(BOTTOM_TRAP_AND_ROLL_ESCAPE)),
               submission_stage=m.submission_state.stage.value if m.submission_state.stage else '',
               submission_tapped=m.submission_tapped,
               exit_destination=m.exit_destination.value if m.exit_destination else '',
               exit_reason=m.exit_reason or '', ended=m.ended)
    if history:
        out['history'] = normalized(asdict(m.history))
    return out


def attempt_fields(r, before, after):
    out = normalized(asdict(r))
    for key in ('stamina', 'response_stamina', 'submission_hold_stamina'):
        out[key] = spend(getattr(r, key))
    for key in ('base_resolution', 'resolution'):
        out[key] = resolution(getattr(r, key))
    out['attempt']['effective_commitment'] = out['attempt']['effective_commitment'] or ''
    for key in ('response_requested_commitment', 'response_effective_commitment'):
        out[key] = out[key] or ''
    side = r.attempt.initiator.value
    other = r.attempt.initiator.opponent.value
    out['initiator_stamina_before'] = before[side+'_stamina']
    out['responder_stamina_before'] = before[other+'_stamina']
    out['outcome'] = {k:v for k,v in after.items() if k != 'history'}
    return out


def request(action, response, commitment='MEDIUM', response_commitment=''):
    return dict(action_id=action, response_id=response, commitment=commitment,
                response_commitment=response_commitment)


def scenario(label, mode, commands, *, axis=1.5, band=None, side='top',
             top=100, bottom=100, setup=False, submissions=False,
             americana_tier=0, trap_tier=0, stage='', behavior=('PRESSURE','ESCAPE'),
             costs=None, top_history=(), bottom_history=(), clock=300, initial_clock=300, capacity=100, tapped=False, broken=False):
    settings = dict(POLICIES[mode], enable_v02_setup=setup, enable_v03_submissions=submissions)
    kwargs = dict(starting_axis=axis, initial_clock=initial_clock, **settings)
    if costs is not None:
        kwargs['stamina_cost_policy'] = StaminaCostPolicy.build(costs)
    m = MountMatch(**kwargs)
    m.initiator = Side(side)
    if band is not None:
        m.position.control.apply(axis, list(Band)[band])
    m.top.stamina = StaminaPool(current=top, maximum=capacity)
    m.bottom.stamina = StaminaPool(current=bottom, maximum=capacity)
    for value in top_history:
        m.top.stamina.set_current(value)
    for value in bottom_history:
        m.bottom.stamina.set_current(value)
    m.setup_state.tracks[TOP_AMERICANA_ARM_ISOLATION].tier = SetupTier(americana_tier)
    m.setup_state.tracks[BOTTOM_TRAP_AND_ROLL_ESCAPE].tier = SetupTier(trap_tier)
    m.submission_state.stage = SubmissionStage(stage) if stage else None
    m.set_behaviors(top=TopBehavior(behavior[0]), bottom=BottomBehavior(behavior[1]))
    m.clock_seconds = clock
    m.submission_tapped = tapped
    if broken:
        m.position.break_mount(-0.5)
        m.exit_destination = ExitDestination.OPEN_GUARD
    initial = snapshot(m)
    steps = []
    for command in commands:
        before = snapshot(m)
        c = command['commitment']
        rc = command['response_commitment']
        try:
            r = m.attempt(action_id=command['action_id'], response_id=command['response_id'],
                          commitment=Commitment._value2member_map_.get(c, c),
                          response_commitment=Commitment._value2member_map_.get(rc, rc) if rc else None)
            after = snapshot(m)
            result, rejected = attempt_fields(r, before, after), False
        except (ValueError, KeyError, RuntimeError, TypeError) as error:
            result, rejected = {}, True
            after = snapshot(m)
            if not before['ended']:
                assert after == before, (label, 'unexpected non-atomic rejection', str(error))
        steps.append(dict(request=command, rejected=rejected, expected=result, state=after,
                          terminal_override=before["ended"]))
        if before["ended"]:
            break # Record the observed Python anomaly separately; Godot must reject atomically.
    return dict(label=label, mode=mode, settings={flag:getattr(m,flag) for flag in FLAGS},
                initial=initial, costs=costs or {'LOW':3,'MEDIUM':7,'HIGH':12}, steps=steps,
                top_history=list(top_history), bottom_history=list(bottom_history),
                top_initial=top, bottom_initial=bottom,
                top_behavior=behavior[0], bottom_behavior=behavior[1])


def main():
    cases = []
    # Negative traces first. Valid commands after rejection test replay integrity.
    bad = [request('', BOTTOM_RESPONSE_FOREARM_FRAME), request(TOP_HIGH_MOUNT_CLIMB, ''),
           request('INVALID', BOTTOM_RESPONSE_FOREARM_FRAME),
           request(BOTTOM_BRIDGE, TOP_RESPONSE_POST_AND_BASE),
           request(TOP_HIGH_MOUNT_CLIMB, TOP_RESPONSE_POST_AND_BASE),
           request(TOP_HIGH_MOUNT_CLIMB, 'INVALID'),
           request(TOP_HIGH_MOUNT_CLIMB, BOTTOM_RESPONSE_FOREARM_FRAME, 'INVALID'),
           request(TOP_HIGH_MOUNT_CLIMB, BOTTOM_RESPONSE_FOREARM_FRAME, 'MEDIUM', 'INVALID')]
    for mode in POLICIES:
        cases.append(scenario('reject-then-valid/'+mode, mode,
            bad+[request(TOP_HIGH_MOUNT_CLIMB, BOTTOM_RESPONSE_FOREARM_FRAME)]))
        cases.append(scenario('not-ready/'+mode, mode,
            [request(TOP_AMERICANA_ARM_ISOLATION, BOTTOM_RESPONSE_FOREARM_FRAME)], setup=True))
        cases.append(scenario('ready-defense/'+mode, mode,
            [request(TOP_AMERICANA_ARM_ISOLATION, BOTTOM_RESPONSE_TIGHT_ELBOW_ARM_DEFENSE)],
            setup=True, americana_tier=2))
        cases.append(scenario('inactive-finish/'+mode, mode,
            [request(TOP_AMERICANA_SUBMISSION_FINISH, BOTTOM_RESPONSE_FOREARM_FRAME)], setup=True, submissions=True))
        cases.append(scenario('finish-defense/'+mode, mode,
            [request(TOP_AMERICANA_SUBMISSION_FINISH, BOTTOM_RESPONSE_TIGHT_ELBOW_ARM_DEFENSE)],
            setup=True, submissions=True, stage='Threat'))
    # Every legal frozen pair, each effort combination and policy entry point.
    resources = [(100,100), (26,25), (25,26), (2,2), (11,6)]
    axes = [(0.1,0), (1.9,2), (2.9,3), (4.0,3)]
    for index,(action,response) in enumerate(sorted(MOUNT_MATCHUPS.entries)):
        side = MOUNT_CATALOG.get(action).side.value
        for mode in POLICIES:
            for commitment in Commitment:
                for response_commitment in ['', 'LOW', 'MEDIUM', 'HIGH']:
                    for i,(top,bottom) in enumerate(resources):
                        axis, band = axes[(index+i)%len(axes)]
                        cases.append(scenario(f'v0/{action}/{response}/{mode}/{commitment.value}/{response_commitment}/{i}',
                            mode, [request(action,response,commitment.value,response_commitment)],
                            axis=axis, band=band, side=side, top=top,bottom=bottom,
                            behavior=[('PRESSURE','ESCAPE'),('HOLD','PROTECT'),('CONSERVE','CONSERVE')][i%3]))
    thresholds = [0,1,2,3,6,7,11,12,25,26,34,35,100]
    pairs = list(dict.fromkeys([(n,n) for n in thresholds]+[(n,100) for n in thresholds]+[(100,n) for n in thresholds]))
    for mode in POLICIES:
        for action in [TOP_AMERICANA_SUBMISSION_FINISH, TOP_AMERICANA_ARM_ISOLATION]:
            for index,(top,bottom) in enumerate(pairs):
                for commitment in Commitment:
                    for rc in ['LOW','MEDIUM','HIGH']:
                        for response in [BOTTOM_RESPONSE_FOREARM_FRAME,BOTTOM_RESPONSE_TURN_IN_RECOVERY]:
                            cases.append(scenario(f'hold/{mode}/{action}/{index}/{commitment.value}/{rc}/{response}', mode,
                                [request(action,response,commitment.value,rc)], axis=4.0,
                                top=top,bottom=bottom,setup=True,submissions=True,americana_tier=2,
                                stage=['Threat','Control','Finish'][index%3] if action==TOP_AMERICANA_SUBMISSION_FINISH else '',
                                behavior=('PRESSURE','PROTECT')))
        for costs in ({'LOW':0,'MEDIUM':1,'HIGH':2}, {'LOW':1,'MEDIUM':4,'HIGH':9}):
            for top,bottom in [(0,0),(1,2),(2,1),(9,9),(26,25)]:
                cases.append(scenario(f'custom/{mode}/{costs}/{top}/{bottom}', mode,
                    [request(TOP_AMERICANA_SUBMISSION_FINISH,BOTTOM_RESPONSE_TURN_IN_RECOVERY,'HIGH','HIGH')],
                    axis=4.0,top=top,bottom=bottom,setup=True,submissions=True,stage='Threat',costs=costs,
                    behavior=('PRESSURE','PROTECT')))
        cases.append(scenario('latch-history/'+mode,mode,
            [request(TOP_CROSSFACE_PRESSURE,BOTTOM_RESPONSE_TURN_IN_RECOVERY,'HIGH','LOW')],
            top=0,bottom=0,top_history=[34],bottom_history=[35]))
        cases.append(scenario('repeated/'+mode,mode,
            [request(TOP_HIGH_MOUNT_CLIMB,BOTTOM_RESPONSE_TURN_IN_RECOVERY),
             request(TOP_HIGH_MOUNT_CLIMB,BOTTOM_RESPONSE_TURN_IN_RECOVERY),
             request(BOTTOM_BRIDGE,TOP_RESPONSE_WIDE_MOUNT_BASE),
             request(TOP_HIGH_MOUNT_CLIMB,BOTTOM_RESPONSE_TURN_IN_RECOVERY)]))
        cases.append(scenario('setup-chain/'+mode,mode,
            [request(TOP_HIGH_MOUNT_CLIMB,BOTTOM_RESPONSE_TIGHT_ELBOW_ARM_DEFENSE),
             request(BOTTOM_BRIDGE,TOP_RESPONSE_WIDE_MOUNT_BASE),
             request(TOP_HIGH_MOUNT_CLIMB,BOTTOM_RESPONSE_TIGHT_ELBOW_ARM_DEFENSE),
             request(BOTTOM_BRIDGE,TOP_RESPONSE_WIDE_MOUNT_BASE),
             request(TOP_AMERICANA_ARM_ISOLATION,BOTTOM_RESPONSE_FOREARM_FRAME),
             request(BOTTOM_BRIDGE,TOP_RESPONSE_WIDE_MOUNT_BASE),
             request(TOP_AMERICANA_SUBMISSION_FINISH,BOTTOM_RESPONSE_FOREARM_FRAME)],
            axis=3.5,setup=True,submissions=True))
        for stage in ['Threat','Control','Finish']:
            cases.append(scenario(f'submission-sequence/{mode}/{stage}',mode,
                [request(TOP_AMERICANA_SUBMISSION_FINISH,BOTTOM_RESPONSE_FOREARM_FRAME,'LOW','LOW'),
                 request(BOTTOM_BRIDGE,TOP_RESPONSE_HIP_FOLLOW_REPUMMEL),
                 request(TOP_AMERICANA_SUBMISSION_FINISH,BOTTOM_RESPONSE_FOREARM_FRAME,'MEDIUM','HIGH')],
                axis=4.0,setup=True,submissions=True,stage=stage,top=100,bottom=100))
    for mode in POLICIES:
        for capacity in [17,37]:
            cases.append(scenario(f'custom-capacity/{mode}/{capacity}',mode,
                [request(TOP_HIGH_MOUNT_CLIMB,BOTTOM_RESPONSE_FOREARM_FRAME,'HIGH','HIGH'),
                 request(BOTTOM_BRIDGE,TOP_RESPONSE_HIP_FOLLOW_REPUMMEL,'HIGH','HIGH')],
                capacity=capacity,top=capacity,bottom=capacity))
        cases.append(scenario('clock-context/'+mode,mode,
            [request(TOP_AMERICANA_SUBMISSION_FINISH,BOTTOM_RESPONSE_FOREARM_FRAME,'LOW','LOW')],
            axis=4.0,setup=True,submissions=True,stage='Threat',initial_clock=90,clock=17))
        cases.append(scenario('ready-bottom-response/'+mode,mode,
            [request(BOTTOM_TRAP_AND_ROLL_ESCAPE,TOP_RESPONSE_POST_AND_BASE)],
            side='bottom',setup=True,trap_tier=2))
        cases.append(scenario('finish-bottom-initiator/'+mode,mode,
            [request(TOP_AMERICANA_SUBMISSION_FINISH,BOTTOM_RESPONSE_FOREARM_FRAME)],
            side='bottom',setup=True,submissions=True,stage='Threat'))
    for label, terminal in [('timeout', dict(clock=0)), ('tap', dict(tapped=True)), ('broken', dict(broken=True))]:
        cases.append(scenario('approved-terminal-boundary/'+label, 'production',
            [request(TOP_AMERICANA_SUBMISSION_FINISH, BOTTOM_RESPONSE_FOREARM_FRAME)],
            setup=True, submissions=True, stage='Threat', **terminal))
    config_cases=[]
    for settings in [{f:True} for f in FLAGS]+[dict(enable_v04_commitment_semantics=True,
        enable_v04b_recognition=True)]:
        try:
            MountMatch(**settings)
            rejected=False
        except ValueError:
            rejected=True
        config_cases.append(dict(settings=settings,rejected=rejected,
            unsupported=bool(not rejected and (settings.get('enable_v03b_stalling') or settings.get('enable_v04b_recognition')))))
    output=Path(__file__).parent/'generated'/'exchange_reference.jsonl'
    output.parent.mkdir(exist_ok=True)
    with output.open('w') as stream:
        stream.write(json.dumps(dict(schema=1,config_cases=config_cases,
            production_settings=PRODUCTION_STAMINA_RECOVERY_POLICY.match_settings()),sort_keys=True)+'\n')
        for case in cases:
            stream.write(json.dumps(case,sort_keys=True,separators=(',',':'))+'\n')
    print(f'Exchange oracle: {len(cases)} independent scenarios, {sum(len(c["steps"]) for c in cases)} operations, {output.stat().st_size} bytes')

if __name__ == '__main__':
    main()
