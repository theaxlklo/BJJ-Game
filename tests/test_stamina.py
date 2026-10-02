import hashlib
import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from bjj_game.diagnostics.checker import render_enumeration
from bjj_game.domain.competitor import Competitor
from bjj_game.domain.model import (
    Band,
    BottomBehavior,
    Side,
    TopBehavior,
)
from bjj_game.domain.stamina import StaminaBand, StaminaPool
from bjj_game.engine.match import MountMatch
from bjj_game.interfaces.cli import main
from bjj_game.positions.mount.catalog import (
    BOTTOM_ELBOW_KNEE_ESCAPE,
    TOP_RESPONSE_POST_AND_BASE,
)


FROZEN_V0_ENUMERATE_SHA256 = "3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2"


class StaminaPoolTests(unittest.TestCase):
    def test_default_pool_is_full_and_fresh(self):
        stamina = StaminaPool()
        self.assertEqual(stamina.current, 100)
        self.assertEqual(stamina.maximum, 100)
        self.assertIs(stamina.band, StaminaBand.FRESH)
        self.assertEqual(stamina.display, "100/100 (Fresh)")

    def test_observational_band_boundaries(self):
        expected = {
            100: StaminaBand.FRESH,
            76: StaminaBand.FRESH,
            75: StaminaBand.WORKING,
            51: StaminaBand.WORKING,
            50: StaminaBand.TIRED,
            26: StaminaBand.TIRED,
            25: StaminaBand.EXHAUSTED,
            0: StaminaBand.EXHAUSTED,
        }
        for value, band in expected.items():
            with self.subTest(value=value):
                stamina = StaminaPool(current=value)
                self.assertIs(stamina.band, band)

    def test_invalid_stamina_is_rejected(self):
        with self.assertRaises(ValueError):
            StaminaPool(current=-1)
        with self.assertRaises(ValueError):
            StaminaPool(current=101)
        with self.assertRaises(TypeError):
            StaminaPool(current=50.5)  # type: ignore[arg-type]

    def test_competitors_do_not_share_stamina_pool(self):
        top = Competitor(Side.TOP, "Top", TopBehavior.PRESSURE)
        bottom = Competitor(Side.BOTTOM, "Bottom", BottomBehavior.ESCAPE)
        top.stamina.set_current(42)
        self.assertEqual(top.stamina.current, 42)
        self.assertEqual(bottom.stamina.current, 100)


class StaminaIdentityTests(unittest.TestCase):
    def test_mount_match_starts_both_competitors_fresh(self):
        match = MountMatch()
        self.assertEqual(match.top.stamina.display, "100/100 (Fresh)")
        self.assertEqual(match.bottom.stamina.display, "100/100 (Fresh)")

    def test_stamina_value_does_not_change_resolution_in_v01a(self):
        fresh = MountMatch(initial_clock=30, starting_axis=0.60)
        exhausted = MountMatch(initial_clock=30, starting_axis=0.60)
        fresh.initiator = Side.BOTTOM
        exhausted.initiator = Side.BOTTOM
        exhausted.bottom.stamina.set_current(0)

        fresh_result = fresh.decide(
            action_id=BOTTOM_ELBOW_KNEE_ESCAPE,
            response_id=TOP_RESPONSE_POST_AND_BASE,
        )
        exhausted_result = exhausted.decide(
            action_id=BOTTOM_ELBOW_KNEE_ESCAPE,
            response_id=TOP_RESPONSE_POST_AND_BASE,
        )

        self.assertEqual(fresh_result, exhausted_result)
        self.assertEqual(fresh.axis, exhausted.axis)
        self.assertEqual(fresh.band, exhausted.band)
        self.assertEqual(fresh.exit_destination, exhausted.exit_destination)

    def test_frozen_v0_enumerate_bytes_are_unchanged(self):
        cli_bytes = (render_enumeration() + "\n").encode("utf-8")
        self.assertEqual(
            hashlib.sha256(cli_bytes).hexdigest(),
            FROZEN_V0_ENUMERATE_SHA256,
        )

    def test_cli_accepts_observational_starting_stamina(self):
        output = io.StringIO()
        with patch("builtins.input", side_effect=EOFError), redirect_stdout(output):
            code = main(["--clock", "1", "--top-stamina", "75", "--bottom-stamina", "25"])
        self.assertEqual(code, 130)
        text = output.getvalue()
        self.assertIn("Top stamina: 75/100 (Working)", text)
        self.assertIn("Bottom stamina: 25/100 (Exhausted)", text)
        self.assertIn("Action stamina costs: ON (LOW=3, MEDIUM=7, HIGH=12)", text)
        self.assertIn("Standard commitment: MEDIUM", text)
        self.assertIn("Commitment resolution effects: OFF", text)
        self.assertIn("Behavior stamina: PRESSURE/ESCAPE -1 per 5s", text)
        self.assertIn("Exhaustion consequence: Exhausted initiator -1 grade", text)


if __name__ == "__main__":
    unittest.main()
