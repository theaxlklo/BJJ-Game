import unittest

from bjj_game.diagnostics.checker import (
    V02GateStatus,
    _commitment_outcome_effect_count,
    _exhausted_positive_weight_escape_hits,
    _responder_exhaustion_differential_count,
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

    def test_gate_1_status_follows_perfect_response_measurement(self):
        expected = (
            V02GateStatus.PASS
            if not self.report.perfect_response_lock
            else V02GateStatus.OPEN
        )
        self.assertIs(self.gates[1].status, expected)

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

    def test_gate_4_status_follows_bridge_count_in_standard_batch(self):
        batch = _v02_standard_batch()
        bridge_count = batch.bottom_action_counts.get("Bridge", 0)
        expected = (
            V02GateStatus.PASS
            if bridge_count > 0
            else V02GateStatus.OPEN
        )
        self.assertIs(self.gates[4].status, expected)
        self.assertIn(f"={bridge_count}/", self.gates[4].metric)

    def test_gate_5_status_follows_top_position_attack_rate(self):
        batch = _v02_standard_batch()
        rate = batch.top_position_attack_count / batch.matches
        expected = (
            V02GateStatus.PASS
            if rate > 1.0
            else V02GateStatus.OPEN
        )
        self.assertIs(self.gates[5].status, expected)
        self.assertIn(f"={rate:.3f}", self.gates[5].metric)

    def test_gate_6_status_follows_positive_weight_exhausted_reachability(self):
        hits = _exhausted_positive_weight_escape_hits()
        routes = {
            (hit.action_id, hit.top_behavior, hit.destination)
            for hit in hits
        }
        expected = (
            V02GateStatus.PASS
            if routes
            else V02GateStatus.OPEN
        )
        self.assertIs(self.gates[6].status, expected)
        self.assertIn(f"={len(routes)}", self.gates[6].metric)

    def test_gate_7_status_follows_commitment_outcome_probe(self):
        effects = _commitment_outcome_effect_count()
        expected = (
            V02GateStatus.PASS
            if effects > 0
            else V02GateStatus.OPEN
        )
        self.assertIs(self.gates[7].status, expected)
        self.assertIn(f"={effects}", self.gates[7].metric)

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
