import unittest

from bjj_game.domain.action import Commitment
from bjj_game.domain.model import BottomBehavior, TopBehavior
from bjj_game.interfaces.batch import (
    BatchBehaviorMode,
    run_escape_first_batch,
)


class TemporaryV02LowStaminaProbe(unittest.TestCase):
    def test_print_setup_enabled_25_stamina_matrix(self):
        cases = (
            ("HOLD vs ESCAPE / fixed", TopBehavior.HOLD, BottomBehavior.ESCAPE, BatchBehaviorMode.FIXED, BatchBehaviorMode.FIXED),
            ("HOLD vs ESCAPE / Bottom recover", TopBehavior.HOLD, BottomBehavior.ESCAPE, BatchBehaviorMode.FIXED, BatchBehaviorMode.RECOVER),
            ("HOLD vs ESCAPE / Top recover", TopBehavior.HOLD, BottomBehavior.ESCAPE, BatchBehaviorMode.RECOVER, BatchBehaviorMode.FIXED),
            ("PRESSURE vs ESCAPE / fixed", TopBehavior.PRESSURE, BottomBehavior.ESCAPE, BatchBehaviorMode.FIXED, BatchBehaviorMode.FIXED),
            ("PRESSURE vs ESCAPE / Top recover", TopBehavior.PRESSURE, BottomBehavior.ESCAPE, BatchBehaviorMode.RECOVER, BatchBehaviorMode.FIXED),
            ("PRESSURE vs PROTECT / Top recover", TopBehavior.PRESSURE, BottomBehavior.PROTECT, BatchBehaviorMode.RECOVER, BatchBehaviorMode.FIXED),
            ("HOLD vs PROTECT / Bottom recover", TopBehavior.HOLD, BottomBehavior.PROTECT, BatchBehaviorMode.FIXED, BatchBehaviorMode.RECOVER),
            ("PRESSURE vs PROTECT / Bottom recover", TopBehavior.PRESSURE, BottomBehavior.PROTECT, BatchBehaviorMode.FIXED, BatchBehaviorMode.RECOVER),
        )

        print("V02_LOW_STAMINA_PROBE_BEGIN")
        for name, top_behavior, bottom_behavior, top_mode, bottom_mode in cases:
            summary = run_escape_first_batch(
                matches=1000,
                base_seed=42,
                top_behavior=top_behavior,
                bottom_behavior=bottom_behavior,
                commitment=Commitment.MEDIUM,
                initial_clock=300,
                starting_axis=1.50,
                interval_seconds=5,
                top_stamina=25,
                bottom_stamina=25,
                top_behavior_mode=top_mode,
                bottom_behavior_mode=bottom_mode,
                enable_v02_setup=True,
            )
            self.assertEqual(sum(summary.outcome_counts.values()), 1000)
            print(
                "V02_LOW_STAMINA_PROBE|"
                + name
                + "|"
                + ",".join(
                    f"{key}={summary.outcome_counts.get(key, 0)}"
                    for key in ("Half Guard", "Open Guard", "Reversal", "TIMEOUT — Mount retained")
                )
                + f"|top_stamina={summary.top_final_stamina_mean:.2f}"
                + f"|bottom_stamina={summary.bottom_final_stamina_mean:.2f}"
                + f"|top_conserve={summary.top_behavior_window_counts.get('CONSERVE', 0)}"
                + f"|bottom_conserve={summary.bottom_behavior_window_counts.get('CONSERVE', 0)}"
            )
        print("V02_LOW_STAMINA_PROBE_END")


if __name__ == "__main__":
    unittest.main()
