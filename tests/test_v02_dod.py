import unittest

from bjj_game.diagnostics.checker import (
    V02GateStatus,
    _commitment_low_dominance_probe,
    _exhausted_bottom_dynamic_escape_counts,
    _exhausted_positive_weight_escape_routes_by_top_behavior,
    _responder_exhaustion_differential_count,
    _v02_ready_gate_evidence,
    _v02_standard_batch,
    measure_v02_definition_of_done,
    render_reset_lock_probe,
    render_v02_definition_of_done,
    run_checks,
)


class V02DefinitionOfDoneMeasurementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = run_checks()
        cls.gates = {
            gate.number: gate
            for gate in measure_v02_definition_of_done(cls.report)
        }

    def test_gate_1_status_requires_contested_best_defense_everywhere(self):
        evidence = _v02_ready_gate_evidence()
        expected = (
            V02GateStatus.PASS
            if all(
                item.reachable_states > 0
                and item.contested_best_states == item.reachable_states
                for item in evidence.values()
            )
            else V02GateStatus.OPEN
        )
        self.assertIs(self.gates[1].status, expected)
        for side, item in evidence.items():
            self.assertIn(
                f"{side.value}:{item.reachable_states}/"
                f"best-contested:{item.contested_best_states}/"
                f"guaranteed:{item.guaranteed_attacker_states}",
                self.gates[1].metric,
            )

    def test_gate_2_status_follows_reset_probe(self):
        probe = render_reset_lock_probe()
        locked_timeout = (
            "TIMEOUT — Mount retained" in probe
            and "band Locked" in probe
        )
        expected = (
            V02GateStatus.OPEN
            if locked_timeout
            else V02GateStatus.PASS
        )
        self.assertIs(self.gates[2].status, expected)

    def test_gate_3_status_follows_responder_exhaustion_differential(self):
        differences = _responder_exhaustion_differential_count()
        expected = (
            V02GateStatus.PASS
            if differences > 0
            else V02GateStatus.OPEN
        )
        self.assertIs(self.gates[3].status, expected)
        self.assertIn(f"={differences}", self.gates[3].metric)
        self.assertEqual(differences, 258)

    def test_gate_4_status_follows_completed_bridge_chain_value(self):
        batch = _v02_standard_batch()
        bridge_count = batch.bottom_action_counts.get("Bridge", 0)
        setup_count = batch.bottom_setup_action_count
        completed_builds = batch.bottom_completed_setup_build_count
        expected = (
            V02GateStatus.PASS
            if completed_builds > 0
            else V02GateStatus.OPEN
        )
        self.assertIs(self.gates[4].status, expected)
        self.assertIn(f"={bridge_count}/", self.gates[4].metric)
        self.assertIn(
            f"setup-priority selections={setup_count}",
            self.gates[4].metric,
        )
        self.assertIn(
            f"completed-chain Bridge builds={completed_builds}",
            self.gates[4].metric,
        )

    def test_gate_5_status_follows_completed_setup_chain_activity(self):
        batch = _v02_standard_batch()
        position_rate = batch.top_followup_position_attack_count / batch.matches
        completed_setup_rate = (
            batch.top_followup_completed_setup_build_count / batch.matches
        )
        rate = position_rate + completed_setup_rate
        expected = (
            V02GateStatus.PASS
            if rate > 1.0
            else V02GateStatus.OPEN
        )
        self.assertIs(self.gates[5].status, expected)
        self.assertIn(f"={rate:.3f}", self.gates[5].metric)
        self.assertIn(f"position:{position_rate:.3f}", self.gates[5].metric)
        self.assertIn(
            f"completed-setup-builds:{completed_setup_rate:.3f}",
            self.gates[5].metric,
        )
        self.assertIn("setup builders count only when", self.gates[5].evidence)

    def test_gate_6_accepts_measured_path_b_when_static_lockout_has_dynamic_route(self):
        routes_by_behavior = (
            _exhausted_positive_weight_escape_routes_by_top_behavior()
        )
        counts = {
            behavior: len(routes)
            for behavior, routes in routes_by_behavior.items()
        }
        dynamic = _exhausted_bottom_dynamic_escape_counts()
        lockouts = tuple(
            behavior
            for behavior, count in counts.items()
            if count == 0
        )
        if all(count > 0 for count in counts.values()):
            expected = V02GateStatus.PASS
        elif lockouts and all(dynamic[behavior] > 0 for behavior in lockouts):
            expected = V02GateStatus.ACCEPTED
        else:
            expected = V02GateStatus.OPEN

        self.assertIs(self.gates[6].status, expected)
        for behavior, count in counts.items():
            self.assertIn(
                f"{behavior.value}:{count}",
                self.gates[6].metric,
            )
            self.assertIn(
                f"{behavior.value}:{dynamic[behavior]}",
                self.gates[6].metric,
            )

    def test_gate_7_status_follows_low_dominance_probe(self):
        low_dominates, advantage_states = _commitment_low_dominance_probe()
        expected = (
            V02GateStatus.OPEN
            if low_dominates
            else V02GateStatus.PASS
        )
        self.assertIs(self.gates[7].status, expected)
        self.assertIn(
            f"low_strictly_dominates={low_dominates}",
            self.gates[7].metric,
        )
        self.assertIn(
            f"higher-commitment advantage states={advantage_states}",
            self.gates[7].metric,
        )

    def test_renderer_uses_measured_status_objects(self):
        lines = render_v02_definition_of_done(self.report)
        self.assertEqual(len(lines), 7)
        for gate, line in zip(self.gates.values(), lines, strict=True):
            self.assertIn(
                f"V0.2 DOD GATE {gate.number} [{gate.status.value}]",
                line,
            )
            self.assertIn(gate.metric, line)


if __name__ == "__main__":
    unittest.main()
