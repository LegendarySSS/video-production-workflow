import contextlib
import io
import getpass
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/video-production-workflow/scripts'))
from video_api import jobs
from video_api.cli import main
from video_api.config import VideoError, configure, load_keys
from video_api.transport import APIError

KEYS = {'KLING_API_KEY': 'test-secret'}
SPEC = {'provider': 'kling', 'prompt': '女孩转身，拿起杯子', 'duration': 5}


class FakeTransport:
    def __init__(self, outcomes):
        self.outcomes = iter(outcomes)
        self.calls = []

    def request(self, method, url, headers, body=None):
        self.calls.append(method)
        outcome = next(self.outcomes)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class JobTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.directory = self.root / 'shot-v1'

    def test_submit_persists_id_then_refuses_duplicate_directory(self):
        transport = FakeTransport([{'code': 0, 'data': {'id': 'task-1'}}])
        record = jobs.submit(SPEC, self.directory, KEYS, transport)
        self.assertEqual(record['task_id'], 'task-1')
        self.assertEqual(jobs.load_record(self.directory)['status'], 'queued')
        self.assertNotIn('test-secret', (self.directory / 'task.json').read_text())
        with self.assertRaises(VideoError):
            jobs.submit(SPEC, self.directory, KEYS, transport)
        self.assertEqual(transport.calls, ['POST'])

    def test_network_uncertainty_is_durable_and_recoverable(self):
        transport = FakeTransport([APIError('timeout', ambiguous=True)])
        with self.assertRaises(VideoError):
            jobs.submit(SPEC, self.directory, KEYS, transport)
        record = jobs.load_record(self.directory)
        self.assertEqual(record['status'], 'submission_unknown')
        self.assertIsNone(record['task_id'])
        self.assertEqual(jobs.attach(self.directory, 'recovered-id')['task_id'], 'recovered-id')
        with self.assertRaises(VideoError):
            jobs.attach(self.directory, 'another-id')

    def test_http_rejection_does_not_retry(self):
        with self.assertRaises(VideoError):
            jobs.submit(SPEC, self.directory, KEYS, FakeTransport([APIError('HTTP 401')]))
        self.assertEqual(jobs.load_record(self.directory)['status'], 'rejected')

    def test_kling_business_rejection_is_not_an_unknown_submission(self):
        with self.assertRaises(VideoError):
            jobs.submit(SPEC, self.directory, KEYS, FakeTransport([{'code': 1002, 'message': 'invalid key'}]))
        self.assertEqual(jobs.load_record(self.directory)['status'], 'rejected')

    def test_missing_id_after_submit_is_uncertain(self):
        with self.assertRaises(VideoError):
            jobs.submit(SPEC, self.directory, KEYS, FakeTransport([{'code': 0, 'data': {}}]))
        self.assertEqual(jobs.load_record(self.directory)['status'], 'submission_unknown')

    def test_secret_in_backend_error_is_redacted_in_record(self):
        with self.assertRaises(VideoError):
            jobs.submit(SPEC, self.directory, KEYS, FakeTransport([APIError('bad test-secret')]))
        self.assertNotIn('test-secret', (self.directory / 'task.json').read_text())

    def test_timeout_retains_task_and_only_polls(self):
        jobs.submit(SPEC, self.directory, KEYS, FakeTransport([{'code': 0, 'data': {'id': 'task-1'}}]))
        transport = FakeTransport([{'code': 0, 'data': [{'id': 'task-1', 'status': 'processing'}]}])
        with patch('video_api.jobs.time.monotonic', side_effect=[0, 2]):
            record, timed_out = jobs.wait(self.directory, KEYS, transport, timeout=1, interval=5)
        self.assertTrue(timed_out)
        self.assertEqual(record['task_id'], 'task-1')
        self.assertEqual(transport.calls, ['GET'])

    def test_preview_runs_without_keys_or_network(self):
        spec_file = self.root / 'shot.json'
        spec_file.write_text(json.dumps(SPEC))
        output = io.StringIO()
        with patch.dict(os.environ, {}, clear=True), patch('video_api.cli.Transport') as network, contextlib.redirect_stdout(output):
            result = main(['--env-file', str(self.root / 'absent.env'), 'preview', '--spec', str(spec_file)])
        self.assertEqual(result, 0)
        network.assert_not_called()
        self.assertFalse(json.loads(output.getvalue())['billable'])

    def test_submit_requires_explicit_spending_authorization(self):
        with contextlib.redirect_stdout(io.StringIO()):
            result = main(['--env-file', str(self.root / 'absent.env'), 'submit', '--spec', 'absent.json', '--job-dir', str(self.directory)])
        self.assertEqual(result, 2)
        self.assertFalse(self.directory.exists())

    def test_doctor_is_offline_and_does_not_disclose_key(self):
        output = io.StringIO()
        with patch.dict(os.environ, {'KLING_API_KEY': 'test-secret'}, clear=True), contextlib.redirect_stdout(output):
            result = main(['--env-file', str(self.root / 'absent.env'), 'doctor', '--provider', 'kling'])
        self.assertEqual(result, 0)
        self.assertNotIn('test-secret', output.getvalue())
        self.assertIn('configured_not_verified', output.getvalue())

    def test_configure_no_echo_no_overwrite_and_load_precedence(self):
        env_file = self.root / '.env'
        with patch('video_api.config.getpass.getpass', return_value='local-secret'):
            configure('kling', env_file)
        if os.name == 'posix':
            self.assertEqual(env_file.stat().st_mode & 0o777, 0o600)
        with self.assertRaises(VideoError):
            configure('seedance', env_file)
        with patch.dict(os.environ, {'KLING_API_KEY': 'process-secret'}, clear=True):
            self.assertEqual(load_keys(env_file)['KLING_API_KEY'], 'process-secret')

    def test_env_file_is_not_executed(self):
        env_file = self.root / '.env'
        marker = self.root / 'should-not-exist'
        env_file.write_text(f'OTHER=$(touch {marker})\nKLING_API_KEY="local-key"\n')
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(load_keys(env_file)['KLING_API_KEY'], 'local-key')
        self.assertFalse(marker.exists())

    def test_configure_refuses_plaintext_fallback(self):
        env_file = self.root / '.env'
        with patch('video_api.config.getpass.getpass', side_effect=getpass.GetPassWarning), self.assertRaises(VideoError):
            configure('kling', env_file)
        self.assertFalse(env_file.exists())

    def test_successful_download_is_still_pending_quality_review(self):
        jobs.submit(SPEC, self.directory, KEYS, FakeTransport([{'code': 0, 'data': {'id': 'task-1'}}]))
        transport = FakeTransport([{'code': 0, 'data': [{'id': 'task-1', 'status': 'succeeded',
                                                        'outputs': [{'type': 'video', 'url': 'https://cdn.example.com/out.mp4'}]}]}])
        destination = self.root / 'out.mp4'
        transport.download = lambda url, path, maximum: str(path)
        record = jobs.download(self.directory, KEYS, transport, destination, 0, 10000)
        self.assertEqual(record['quality_review'], 'pending')
        self.assertEqual(record['downloads'][0]['path'], str(destination))
        self.assertEqual(transport.calls, ['GET'])

    def test_existing_download_is_not_overwritten(self):
        destination = self.root / 'existing.mp4'
        destination.write_bytes(b'original')
        transport = FakeTransport([])
        with self.assertRaises(VideoError):
            jobs.download(self.directory, KEYS, transport, destination, 0, 1000)
        self.assertEqual(destination.read_bytes(), b'original')
        self.assertFalse(transport.calls)

    def test_terminal_failure_stops_polling(self):
        jobs.submit(SPEC, self.directory, KEYS, FakeTransport([{'code': 0, 'data': {'id': 'task-1'}}]))
        transport = FakeTransport([{'code': 0, 'data': [{'id': 'task-1', 'status': 'failed', 'message': 'bad input'}]}])
        record, timed_out = jobs.wait(self.directory, KEYS, transport, 60, 5)
        self.assertEqual(record['status'], 'failed')
        self.assertFalse(timed_out)
        self.assertEqual(len(transport.calls), 1)


if __name__ == '__main__':
    unittest.main()
