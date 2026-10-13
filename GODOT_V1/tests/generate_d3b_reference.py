#!/usr/bin/env python3
"""D3-B controller and headless lifecycle oracle; no gameplay formulas copied."""
from dataclasses import asdict
from itertools import product
from pathlib import Path
import json
from bjj_game.engine.match import MountMatch
from bjj_game.domain.action import Commitment
from bjj_game.domain.model import Side, TopBehavior, BottomBehavior
from bjj_game.domain.stamina import StaminaPool
from bjj_game.domain.setup import SetupTier
from bjj_game.domain.submission import SubmissionStage
from bjj_game.interfaces.handoff_policy import D3BTokenLockoutController
from bjj_game.interfaces.batch import AdaptiveBehaviorPolicy, BatchBehaviorMode
from bjj_game.interfaces.production_policy import PRODUCTION_STAMINA_RECOVERY_POLICY
from generate_exchange_reference import normalized, attempt_fields, snapshot
from generate_mount_lifecycle_reference import state
from bjj_game.positions.mount.catalog import (TOP_AMERICANA_ARM_ISOLATION, BOTTOM_TRAP_AND_ROLL_ESCAPE,
    TOP_HIGH_MOUNT_CLIMB, TOP_CROSSFACE_PRESSURE, BOTTOM_BRIDGE, TOP_RESPONSE_POST_AND_BASE,
    BOTTOM_RESPONSE_FOREARM_FRAME, BOTTOM_RESPONSE_TURN_IN_RECOVERY)
FINISH = 'mount.top.americana_submission_finish'


def token_state(c):
    return dict(armed=c.armed, token_consumed=c.token_consumed, previous_exhausted=c._exhausted,
                recovery_hold_mode=c.recovery_hold_mode)


def run(label, commands, *, start=25, top=100, capacity=100, axis=1.5, stage='', production=True):
    settings = dict(enable_v02_setup=True, enable_v03_submissions=True, enable_v04_commitment_semantics=True,
                    **(PRODUCTION_STAMINA_RECOVERY_POLICY.match_settings() if production else {}))
    m = MountMatch(initial_clock=180, starting_axis=axis, **settings)
    m.top.stamina = StaminaPool(top, capacity)
    m.bottom.stamina = StaminaPool(start, capacity)
    if stage:
        m.submission_state.stage = SubmissionStage(stage)
    c = D3BTokenLockoutController(m) if production else None
    policy = AdaptiveBehaviorPolicy(Side.BOTTOM, BottomBehavior.ESCAPE, BatchBehaviorMode.RECOVER)
    def capture():
        out = state(m)
        out['controller'] = token_state(c) if c else None
        if not m.ended:
            out['legal_actions'] = list(m.legal_action_ids())
            out['legal_responses'] = {a:list(m.legal_response_ids(a)) for a in m.legal_action_ids()}
        return out
    initial = capture()
    steps = []
    for command in commands:
        before = capture()
        op = command['op']
        rejected = False
        terminal_override = False
        expected = None
        try:
            if op == 'set':
                m.competitor(Side(command['side'])).stamina.set_current(command['value'])
            elif op == 'side':
                m.initiator = Side(command['value'])
            elif op == 'free':
                m.free_initiative_pending = True
                m.free_initiative_beneficiary = Side(command['side'])
            elif op == 'consume':
                side = m.consume_free_initiative_window()
                expected = dict(side=side.value if side else None)
            elif op == 'advance':
                m.interval_seconds = command['duration']
                m.bottom.set_behavior(policy.choose(m))
                r = m.advance()
                if c:
                    c.observe_advance(m)
                expected = normalized(asdict(r))
                expected['top_stamina']['net_change'] = r.top_stamina.net_change
                expected['bottom_stamina']['net_change'] = r.bottom_stamina.net_change
                if not m.ended:
                    m.bottom.set_behavior(policy.choose(m))
            elif op == 'controller':
                expected = normalized(asdict(c.decide(m, armed=False)))
            elif op == 'hold':
                expected = normalized(asdict(m.recovery_hold()))
            elif op == 'reset':
                expected = normalized(asdict(m.reset_window()))
            elif op in ('attempt','legacy'):
                if op == 'legacy':
                    expected = normalized(asdict(m.decide(action_id=command['action'], response_id=command['response'])))
                    expected['exit_destination'] = expected['exit_destination'] or ''
                else:
                    r = m.attempt(action_id=command['action'],response_id=command['response'],
                            commitment=Commitment(command['commitment']),response_commitment=Commitment.MEDIUM)
                    expected = attempt_fields(r, before, snapshot(m))
            elif op == 'bottom':
                # Batch's controller classification precedes the adopted decision.
                if m.initiator is not Side.BOTTOM:
                    raise RuntimeError('Bottom required')
                decision = c.decide(m, armed=False) if c else None
                if decision and decision.hold:
                    settlement = normalized(asdict(m.recovery_hold()))
                elif not command.get('action'):
                    settlement = normalized(asdict(m.reset_window()))
                else:
                    r = m.attempt(action_id=command['action'], response_id=command['response'],
                                  commitment=Commitment(command['commitment']), response_commitment=Commitment.MEDIUM)
                    settlement = attempt_fields(r, before, snapshot(m))
                expected = dict(decision=normalized(asdict(decision)) if decision else None, settlement=settlement)
        except (ValueError, RuntimeError, KeyError):
            rejected = True
            assert capture() == before, (label, command, 'unexpected Python mutation')
        if before['ended'] and op in ('attempt','legacy','reset','hold','bottom','consume'):
            # Established strict Godot admission; source terminal differences are
            # recorded, not misreported as source-outcome-equivalent operations.
            terminal_override = not rejected
        steps.append(dict(command=command, rejected=rejected, expected=expected, state=capture(), terminal_override=terminal_override))
        if terminal_override:
            break
    return dict(label=label, settings=settings, initial=initial, production=production, stage=stage, steps=steps)


def main():
    cases=[]
    for capacity, start, production in product((7,100,101),(0,1,2,3,6,7,11,12,24,25,34,35,100),(False,True)):
        if start > capacity: continue
        commands=[dict(op='controller')] if production else [] # Top negative first
        commands += [dict(op='side',value='bottom'),dict(op='bottom'),dict(op='side',value='bottom'),dict(op='advance',duration=30),
                     dict(op='set',side='bottom',value=int(capacity*.25)),dict(op='side',value='bottom')]
        for i in range(3):
            commands += [dict(op='bottom',action=BOTTOM_BRIDGE,response=TOP_RESPONSE_POST_AND_BASE,commitment='LOW'),dict(op='side',value='bottom')]
        commands += [dict(op='free',side='top'),dict(op='consume'),dict(op='free',side='bottom'),dict(op='consume'),
                     dict(op='advance',duration=30),dict(op='set',side='bottom',value=0),dict(op='side',value='bottom')]
        commands += [dict(op='bottom'),dict(op='side',value='bottom'),dict(op='bottom'),dict(op='advance',duration=200)]
        cases.append(run(f'token/{capacity}/{start}/{production}',commands,start=start,top=capacity,capacity=capacity,production=production))
    # Full lifecycle: setup builders -> Ready isolation -> submission stages -> Tap.
    for production in (False,True):
        commands=[]
        actions = [(TOP_HIGH_MOUNT_CLIMB,BOTTOM_RESPONSE_FOREARM_FRAME,'HIGH')]*2 + [(TOP_AMERICANA_ARM_ISOLATION,BOTTOM_RESPONSE_FOREARM_FRAME,'HIGH')]+[(FINISH,BOTTOM_RESPONSE_TURN_IN_RECOVERY,'HIGH')]*3
        for index, (action,response,commitment) in enumerate(actions):
            commands += [dict(op='advance',duration=5),dict(op='attempt',action=action,response=response,commitment=commitment)]
            if index < len(actions)-1:
                commands.append(dict(op='reset'))
        complete = run(f'complete-tap/{production}', commands, start=100,axis=0.5,production=production)
        assert complete['steps'][-1]['state']['submission_tapped'], 'Tap lifecycle must actually finish'
        assert not any(x['rejected'] for x in complete['steps']), 'positive lifecycle must have no rejected commands'
        cases.append(complete)
        # Legacy decisions remain stamina free; modern escape exits Mount.
        cases.append(run(f'legacy/{production}',[dict(op='legacy',action=TOP_HIGH_MOUNT_CLIMB,response=BOTTOM_RESPONSE_FOREARM_FRAME),dict(op='legacy',action=BOTTOM_BRIDGE,response=TOP_RESPONSE_POST_AND_BASE)],start=100,production=production))
        cases.append(run(f'escape/{production}',[dict(op='side',value='bottom'),dict(op='attempt',action='mount.bottom.elbow_knee_escape',response=TOP_RESPONSE_POST_AND_BASE,commitment='HIGH')],start=100,axis=0.4,production=production))
        cases.append(run(f'timeout/{production}',[dict(op='advance',duration=180),dict(op='reset')],production=production))
    path=Path(__file__).parent/'generated'/'d3b_reference.jsonl'
    with path.open('w') as out:
        for case in cases: out.write(json.dumps(case,allow_nan=False,separators=(',',':'))+'\n')
    print(f'D3-B/lifecycle oracle: {len(cases)} scenarios, {sum(len(c["steps"]) for c in cases)} operations')

if __name__=='__main__': main()
