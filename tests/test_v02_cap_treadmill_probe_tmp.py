import unittest

from bjj_game.domain.action import Commitment
from bjj_game.domain.model import BottomBehavior, TopBehavior
from bjj_game.interfaces.batch import run_escape_first_batch


class TemporaryCapTreadmillProbe(unittest.TestCase):
    def test_print_pressure_protect_setup_batch(self):
        summary = run_escape_first_batch(
            matches=1000,
            base_seed=42,
            top_behavior=TopBehavior.PRESSURE,
            bottom_behavior=BottomBehavior.PROTECT,
            commitment=Commitment.MEDIUM,
            initial_clock=300,
            starting_axis=1.50,
            interval_seconds=5,
            top_stamina=100,
            bottom_stamina=100,
            enable_v02_setup=True,
        )
        self.assertEqual(sum(summary.outcome_counts.values()), 1000)
        print("V02_CAP_TREADMILL_PROBE_BEGIN")
        print(
            "V02_CAP_TREADMILL_PROBE|"
            + ",".join(
                f"{key}={summary.outcome_counts.get(key, 0)}"
                for key in ("Half Guard", "Open Guard", "Reversal", "TIMEOUT — Mount retained")
            )
            + f"|top_stamina={summary.top_final_stamina_mean:.2f}"
            + f"|bottom_stamina={summary.bottom_final_stamina_mean:.2f}"
            + f"|bridge={summary.bottom_action_counts.get('Bridge', 0)}"
            + f"|trap_roll={summary.bottom_action_counts.get('Trap-and-Roll', 0)}"
            + f"|bottom_setup={summary.bottom_setup_action_count}"
            + f"|bottom_completed_chains={summary.bottom_completed_setup_chain_count}"
            + f"|bottom_resets={summary.bottom_reset_count}"
        )
        print("V02_CAP_TREADMILL_PROBE_END")


if __name__ == "__main__":
    unittest.main()
