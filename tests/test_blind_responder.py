import unittest

from bjj_game.domain.model import Side
from bjj_game.interfaces.blind import RandomBlindResponder


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
