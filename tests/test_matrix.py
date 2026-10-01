import unittest

from mount_v0.catalog import (
    BOTTOM_ELBOW_KNEE_ESCAPE,
    BOTTOM_RESPONSE_FOREARM_FRAME,
    BOTTOM_RESPONSE_TIGHT_ELBOW_ARM_DEFENSE,
    BOTTOM_RESPONSE_TURN_IN_RECOVERY,
    TOP_CROSSFACE_PRESSURE,
    TOP_HIGH_MOUNT_CLIMB,
    TOP_RESPONSE_WIDE_MOUNT_BASE,
)
from mount_v0.matrix import RAW_GRADES, raw_grade
from mount_v0.model import Grade


class MatrixTests(unittest.TestCase):
    def test_exactly_18_entries(self):
        self.assertEqual(len(RAW_GRADES), 18)

    def test_corrected_high_mount_row(self):
        self.assertEqual(raw_grade(TOP_HIGH_MOUNT_CLIMB, BOTTOM_RESPONSE_FOREARM_FRAME), Grade.SUCCESS)
        self.assertEqual(raw_grade(TOP_HIGH_MOUNT_CLIMB, BOTTOM_RESPONSE_TURN_IN_RECOVERY), Grade.CONTESTED)
        self.assertEqual(raw_grade(TOP_HIGH_MOUNT_CLIMB, BOTTOM_RESPONSE_TIGHT_ELBOW_ARM_DEFENSE), Grade.FAILURE)

    def test_crossface_beats_turn_in(self):
        self.assertEqual(raw_grade(TOP_CROSSFACE_PRESSURE, BOTTOM_RESPONSE_TURN_IN_RECOVERY), Grade.SUCCESS)

    def test_elbow_knee_vs_wide_base_is_success(self):
        self.assertEqual(raw_grade(BOTTOM_ELBOW_KNEE_ESCAPE, TOP_RESPONSE_WIDE_MOUNT_BASE), Grade.SUCCESS)
