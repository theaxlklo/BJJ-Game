import unittest

from mount_v0.catalog import TOP_RESPONSE_HIP_FOLLOW_REPUMMEL
from mount_v0.names import RESOLVER, normalize_name


class NameTests(unittest.TestCase):
    def test_symbol_character_normalization(self):
        self.assertEqual(normalize_name("follow+knee"), "follow and knee")
        self.assertEqual(normalize_name("follow&knee"), "follow and knee")

    def test_full_hip_follow_variants_resolve(self):
        variants = [
            "Hip Follow + Knee Re-Pummel",
            "Hip Follow & Knee Repummel",
            "hip_follow_and_knee_repummel",
            "HIP-FOLLOW-AND-KNEE-RE-PUMMEL",
        ]
        for value in variants:
            self.assertEqual(RESOLVER.resolve(value).id, TOP_RESPONSE_HIP_FOLLOW_REPUMMEL)

    def test_repummel_alias(self):
        self.assertEqual(RESOLVER.resolve("Repummel").id, TOP_RESPONSE_HIP_FOLLOW_REPUMMEL)

    def test_upa_is_trap_and_roll(self):
        self.assertEqual(RESOLVER.resolve("upa").canonical_name, "Trap-and-Roll Escape")

    def test_reserved_names_do_not_resolve(self):
        for value in ["High Mount", "S-Mount", "Elbow-Knee Connection", "Hip Frame", "Body Frame"]:
            with self.assertRaises(ValueError, msg=value):
                RESOLVER.resolve(value)

    def test_no_alias_collisions(self):
        self.assertEqual(RESOLVER.collision_map(), {})
