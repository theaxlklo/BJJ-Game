"""Negative-first tests for current-attempt qualification evidence."""
import unittest
from watch_qualification import qualification_state


class WatchTests(unittest.TestCase):
    def test_reject_stale_missing_and_contradictory_evidence(self):
        valid = dict(name='qualification results', run_id=42, run_attempt=2, head_sha='a'*40, status='completed', conclusion='success')
        changes = [
            {'run_id':41}, {'run_attempt':1}, {'head_sha':'b'*40},
            {'run_attempt':None}, {'head_sha':None}, {'status':'unknown'},
            {'conclusion':'unknown'}, {'conclusion':None},
            {'status':'queued', 'conclusion':'success'},
        ]
        for change in changes:
            with self.subTest(change=change):
                with self.assertRaises(ValueError):
                    qualification_state([valid | change], 'qualification results', 42, 2, 'a'*40)
        with self.assertRaises(ValueError):
            qualification_state([valid, valid], 'qualification results', 42, 2, 'a'*40)

    def test_wait_and_terminal_results(self):
        valid = dict(name='qualification results', run_id=42, run_attempt=2, head_sha='a'*40, status='completed', conclusion='success')
        self.assertEqual(qualification_state([], 'qualification results', 42, 2, 'a'*40), 'pending')
        cases = [('completed', 'success', 'success')]
        cases += [(state, None, 'pending') for state in ('queued', 'in_progress', 'waiting', 'pending')]
        cases += [('completed', conclusion, 'failure') for conclusion in ('failure','cancelled','skipped','timed_out','neutral','action_required','stale','startup_failure')]
        for status, conclusion, expected in cases:
            with self.subTest(status=status, conclusion=conclusion):
                actual = qualification_state([valid | dict(status=status, conclusion=conclusion)], 'qualification results', 42, 2, 'a'*40)
                self.assertEqual(actual, expected)


if __name__ == '__main__':
    unittest.main(verbosity=2)


class PaginationTests(unittest.TestCase):
    def test_paginated_and_incomplete_api_evidence(self):
        import io
        import json
        from unittest.mock import patch
        from watch_qualification import fetch_jobs
        pages = [dict(jobs=[{'name':'first'}], total_count=2), dict(jobs=[{'name':'second'}], total_count=2)]
        with patch('watch_qualification.urllib.request.urlopen', side_effect=[io.BytesIO(json.dumps(page).encode()) for page in pages]) as request:
            self.assertEqual(len(fetch_jobs('https://api.github.com', 'owner/repo', 42, 2, 'test-token')), 2)
            self.assertIn('/attempts/2/jobs', request.call_args_list[0].args[0].full_url)
            self.assertIn('page=2', request.call_args_list[1].args[0].full_url)
        with patch('watch_qualification.urllib.request.urlopen', return_value=io.BytesIO(b'{"jobs":[],"total_count":1}')):
            with self.assertRaises(ValueError):
                fetch_jobs('https://api.github.com', 'owner/repo', 42, 2, 'test-token')
