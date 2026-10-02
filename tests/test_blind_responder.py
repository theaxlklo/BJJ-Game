import unittest

from bjj_game.domain.model import Band, Side
from bjj_game.interfaces.blind import RandomBlindResponder, random_mix_band_metrics, render_random_mix_band_metrics


class RandomBlindResponderTests(unittest.TestCase):
    def test_fixed_policy_matches_playtest_mix(self):
        self.assertEqual(
            RandomBlindResponder.mix_description(Side.BOTTOM),
            "Frame=4, Tight Elbows=3",
        )
        self.assertEqual(
            RandomBlindResponder.mix_description(Side.TOP),
            "Wide Base=2, Hip Follow=1",
        )

    def test_seeded_sequence_is_replayable(self):
        first = RandomBlindResponder(42)
        second = RandomBlindResponder(42)

        sides = [
            Side.BOTTOM,
            Side.TOP,
            Side.BOTTOM,
            Side.TOP,
            Side.BOTTOM,
            Side.TOP,
        ]
        a = [first.choose(side) for side in sides]
        b = [second.choose(side) for side in sides]

        self.assertEqual(
            [(x.response_id, x.draw, x.total_weight) for x in a],
            [(x.response_id, x.draw, x.total_weight) for x in b],
        )
        self.assertEqual(
            [x.response.short_name for x in a],
            ["Tight Elbows", "Wide Base", "Frame", "Hip Follow", "Frame", "Wide Base"],
        )
        self.assertEqual([x.ordinal for x in a], [1, 2, 3, 4, 5, 6])

    def test_per_band_metrics_keep_axis_and_escape_separate(self):
        rows = random_mix_band_metrics()

        def row(side, band, short_name):
            return next(
                item
                for item in rows
                if item.side is side
                and item.band is band
                and item.action.short_name == short_name
            )

        self.assertAlmostEqual(
            row(Side.TOP, Band.STABLE, "Crossface").expected_attacker_axis_delta,
            2 / 7,
        )
        self.assertAlmostEqual(
            row(Side.TOP, Band.STABLE, "Americana Isolation").expected_attacker_axis_delta,
            2 / 7,
        )
        self.assertAlmostEqual(
            row(Side.TOP, Band.STABLE, "Climb High").expected_attacker_axis_delta,
            1 / 7,
        )

        # Top's frozen Loose positional modifier changes the raw equilibrium math.
        self.assertAlmostEqual(
            row(Side.TOP, Band.LOOSE, "Americana Isolation").expected_attacker_axis_delta,
            -2 / 7,
        )
        self.assertLess(
            row(Side.TOP, Band.LOOSE, "Crossface").expected_attacker_axis_delta,
            0,
        )
        self.assertLess(
            row(Side.TOP, Band.LOOSE, "Climb High").expected_attacker_axis_delta,
            0,
        )

        self.assertAlmostEqual(
            row(Side.BOTTOM, Band.STABLE, "Elbow-Knee Escape").expected_attacker_axis_delta,
            0.0,
        )
        self.assertAlmostEqual(
            row(Side.BOTTOM, Band.STABLE, "Trap-and-Roll").expected_attacker_axis_delta,
            0.0,
        )
        self.assertAlmostEqual(
            row(Side.BOTTOM, Band.STABLE, "Bridge").expected_attacker_axis_delta,
            -1 / 3,
        )

        self.assertAlmostEqual(
            row(Side.BOTTOM, Band.STRONG, "Elbow-Knee Escape").expected_attacker_axis_delta,
            -2 / 3,
        )
        self.assertAlmostEqual(
            row(Side.BOTTOM, Band.STRONG, "Trap-and-Roll").expected_attacker_axis_delta,
            -1.0,
        )
        self.assertAlmostEqual(
            row(Side.BOTTOM, Band.STRONG, "Bridge").expected_attacker_axis_delta,
            -4 / 3,
        )

        elbow_loose = row(Side.BOTTOM, Band.LOOSE, "Elbow-Knee Escape")
        self.assertAlmostEqual(elbow_loose.escape_probability_min, 0.0)
        self.assertAlmostEqual(elbow_loose.escape_probability_max, 2 / 3)

        trap_loose = row(Side.BOTTOM, Band.LOOSE, "Trap-and-Roll")
        self.assertAlmostEqual(trap_loose.escape_probability_min, 1 / 3)
        self.assertAlmostEqual(trap_loose.escape_probability_max, 1 / 3)

        for name in ("Bridge", "Elbow-Knee Escape", "Trap-and-Roll"):
            strong = row(Side.BOTTOM, Band.STRONG, name)
            self.assertEqual(strong.escape_probability_min, 0.0)
            self.assertEqual(strong.escape_probability_max, 0.0)

    def test_rendered_band_metrics_report_no_combined_utility(self):
        lines = render_random_mix_band_metrics()
        self.assertIn(
            "BLIND MIX BAND METRICS: baseline PRESSURE/ESCAPE, no exhaustion; "
            "action cost MEDIUM=7; axis and escape are reported separately.",
            lines,
        )
        self.assertIn(
            "BLIND MIX: Bottom / Strong / Elbow-Knee Escape: "
            "attacker-axis -0.667; escape 0.0%",
            lines,
        )
        self.assertIn(
            "BLIND MIX SUMMARY: Bottom / Strong: best attacker-axis -0.667 "
            "via Elbow-Knee Escape; negative-vs-RESET-axis=Bridge, "
            "Elbow-Knee Escape, Trap-and-Roll",
            lines,
        )

    def test_zero_weight_responses_never_exist_in_policy(self):
        bottom_names = {
            choice.response.short_name
            for choice in [RandomBlindResponder(seed).choose(Side.BOTTOM) for seed in range(50)]
        }
        top_names = {
            choice.response.short_name
            for choice in [RandomBlindResponder(seed).choose(Side.TOP) for seed in range(50)]
        }
        self.assertNotIn("Turn In", bottom_names)
        self.assertNotIn("Post", top_names)


if __name__ == "__main__":
    unittest.main()
