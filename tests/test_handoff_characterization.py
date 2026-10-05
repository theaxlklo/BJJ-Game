import unittest
from unittest.mock import patch

from bjj_game.diagnostics.handoff_characterization import trace_batch, characterize
from bjj_game.diagnostics.stamina_adoption_candidate import _surface_e_prod_kwargs
from bjj_game.engine.match import MountMatch
from bjj_game.domain.stamina import StaminaPool
from bjj_game.interfaces.batch import run_escape_first_batch, ReExhaustionHandoffEpisode


class HandoffObserverTests(unittest.TestCase):
    def test_full_summary_identity_and_replay_with_stalling_off_and_on(self):
        for stalling, seed in ((False, 42), (False, 142), (True, 42)):
            with self.subTest(stalling=stalling, seed=seed):
                kwargs = _surface_e_prod_kwargs(stalling=stalling, shadow=False,
                                                base_seed=seed)
                original = MountMatch.attempt
                summary, events = trace_batch(**kwargs)
                self.assertIs(MountMatch.attempt, original)
                self.assertEqual(summary, run_escape_first_batch(**kwargs))
                replay, replay_events = trace_batch(**kwargs)
                self.assertEqual(summary, replay)
                self.assertEqual(events, replay_events)
                report = characterize(summary, events)
                self.assertEqual(report['clears'],
                                 len(summary.reexhaustion_handoffs.episodes))
                for event in events:
                    for mutation in event['mutations']:
                        delta = mutation.get('recovered', -mutation.get('charged', 0))
                        self.assertEqual(mutation['after'] - mutation['before'], delta)

    def test_wrappers_restore_after_exception(self):
        original = StaminaPool.spend_up_to
        with patch.object(MountMatch, 'advance', side_effect=RuntimeError('probe')):
            with self.assertRaisesRegex(RuntimeError, 'probe'):
                trace_batch(**_surface_e_prod_kwargs(stalling=False, shadow=False))
        self.assertIs(StaminaPool.spend_up_to, original)

    def test_same_timestamp_spend_after_clear_is_included(self):
        clear = dict(exhausted_before=True, exhausted_after=False, before=33, after=35)
        spend = dict(exhausted_before=False, exhausted_after=False, before=35, after=28)
        class Handoffs:
            episodes = (ReExhaustionHandoffEpisode(
                match_index=0, clear_elapsed_seconds=100,
                reexhausted_elapsed_seconds=None, match_end_elapsed_seconds=140),)
        class Summary:
            reexhaustion_handoffs = Handoffs()
        events = [dict(match_index=0, time=100, mutations=[clear]),
                  dict(match_index=0, time=100, mutations=[spend]),
                  dict(match_index=0, time=135, mutations=[spend])]
        report = characterize(Summary(), events)
        self.assertEqual(len(report['episodes'][0]['following']), 2)
        self.assertEqual(report['episodes'][0]['following'][1]['offset'], 0)
        self.assertEqual(report['episodes'][0]['following'][0]['mutations'], [])
