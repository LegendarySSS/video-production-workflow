import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/video-production-workflow/scripts'))
from video_api.config import VideoError
from video_api.providers import Provider, build_request

IMAGE = 'https://assets.example.com/hero.png'
VIDEO = 'https://assets.example.com/action.mp4'
KEYS = {'KLING_API_KEY': 'test-kling-key', 'ARK_API_KEY': 'test-ark-key', 'RUNWAYML_API_SECRET': 'test-runway-key'}


class FakeTransport:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []

    def request(self, method, url, headers, body=None):
        self.calls.append((method, url, headers, body))
        return next(self.responses)


class ProviderTests(unittest.TestCase):
    def test_kling_text_submission_and_new_status_protocol(self):
        plan = build_request({'provider': 'kling', 'prompt': '女孩转身', 'duration': 5})
        transport = FakeTransport([
            {'code': 0, 'data': {'id': 'task-1', 'status': 'submitted'}},
            {'code': 0, 'data': [{'id': 'other', 'status': 'failed'}, {'id': 'task-1', 'status': 'succeeded',
                                'outputs': [{'type': 'video', 'url': VIDEO}]}]},
        ])
        provider = Provider('kling', KEYS, transport)
        self.assertEqual(provider.create(plan), 'task-1')
        result = provider.status('task-1')
        self.assertEqual(result['outputs'], [VIDEO])
        self.assertEqual(result['quality_review'], 'pending')
        self.assertEqual(transport.calls[0][1], 'https://api-singapore.klingai.com/text-to-video/kling-4.0')
        self.assertEqual(transport.calls[0][3]['settings']['duration'], 5)
        self.assertEqual(transport.calls[1][1], 'https://api-singapore.klingai.com/tasks?task_ids=task-1')

    def test_kling_reference_and_keyframes_use_omni(self):
        plan = build_request({'provider': 'kling', 'prompt': '@image_1 turns like @video_1',
                              'image': IMAGE, 'last_image': IMAGE, 'reference_images': [IMAGE],
                              'reference_videos': [VIDEO], 'aspect_ratio': '9:16'})
        self.assertEqual(plan['endpoint'], '/omni-video/kling-4.0')
        items = plan['body']['contents']
        self.assertEqual([item['type'] for item in items], ['prompt', 'first_frame', 'last_frame', 'refer_image', 'feature_video'])
        self.assertEqual(items[3]['id'], 'image_1')
        self.assertEqual(plan['body']['settings']['aspect_ratio'], '9:16')

    def test_seedance_native_content_and_status(self):
        plan = build_request({'provider': 'seedance', 'prompt': '转身', 'reference_images': [IMAGE],
                              'reference_videos': [VIDEO], 'reference_audio': ['https://assets.example.com/voice.mp3'], 'audio': True})
        self.assertEqual(plan['body']['content'][1]['role'], 'reference_image')
        self.assertEqual(plan['body']['content'][2]['role'], 'reference_video')
        self.assertEqual(plan['body']['content'][3]['role'], 'reference_audio')
        self.assertTrue(plan['body']['generate_audio'])
        transport = FakeTransport([{'id': 'cgt-test'}, {'id': 'cgt-test', 'status': 'succeeded', 'content': {'video_url': VIDEO}}])
        provider = Provider('seedance', KEYS, transport)
        self.assertEqual(provider.create(plan), 'cgt-test')
        self.assertEqual(provider.status('cgt-test')['outputs'], [VIDEO])
        self.assertEqual(transport.calls[1][1], 'https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks/cgt-test')

    def test_seedance_first_and_last_frame(self):
        plan = build_request({'provider': 'seedance', 'prompt': '转身', 'image': IMAGE, 'last_image': IMAGE})
        self.assertEqual([item.get('role') for item in plan['body']['content'][1:]], ['first_frame', 'last_frame'])

    def test_seedance_25_is_selectable(self):
        plan = build_request({'provider': 'seedance', 'model': 'doubao-seedance-2-5-260628', 'prompt': '走路', 'duration': 30})
        self.assertEqual(plan['body']['duration'], 30)

    def test_runway_image_auth_and_ratio(self):
        plan = build_request({'provider': 'runway', 'prompt': 'A woman turns', 'image': IMAGE, 'aspect_ratio': '9:16', 'seed': 23})
        transport = FakeTransport([{'id': 'rw-task'}, {'id': 'rw-task', 'status': 'SUCCEEDED', 'output': [VIDEO]}])
        provider = Provider('runway', KEYS, transport)
        self.assertEqual(provider.create(plan), 'rw-task')
        self.assertEqual(provider.status('rw-task')['status'], 'succeeded')
        self.assertEqual(transport.calls[0][3]['ratio'], '720:1280')
        self.assertEqual(transport.calls[0][3]['seed'], 23)
        self.assertEqual(transport.calls[0][2]['X-Runway-Version'], '2024-11-06')
        self.assertEqual(transport.calls[0][2]['Authorization'], 'Bearer test-runway-key')

    def test_runway_text_routes_separately(self):
        plan = build_request({'provider': 'runway', 'prompt': 'A woman turns'})
        self.assertEqual(plan['endpoint'], '/text_to_video')
        self.assertNotIn('promptImage', plan['body'])

    def test_unsupported_features_fail_before_network(self):
        cases = [
            {'provider': 'runway', 'audio': True},
            {'provider': 'runway', 'reference_images': [IMAGE]},
            {'provider': 'runway', 'last_image': IMAGE},
            {'provider': 'runway', 'duration': 30},
            {'provider': 'runway', 'aspect_ratio': '9:16'},
            {'provider': 'kling', 'audio': False},
            {'provider': 'kling', 'seed': 0},
            {'provider': 'kling', 'reference_audio': [VIDEO]},
            {'provider': 'seedance', 'image': IMAGE, 'reference_images': [IMAGE]},
            {'provider': 'seedance', 'reference_audio': [VIDEO]},
            {'provider': 'seedance', 'duration': 30},
            {'provider': 'seedance', 'model': 'unverified-model'},
            {'provider': 'kling', 'image': '/tmp/hero.png'},
            {'provider': 'kling', 'api_key': 'do-not-send'},
            {'provider': 'kling', 'duration': True},
            {'provider': 'kling', 'reference_images': None},
        ]
        for values in cases:
            with self.subTest(values=values), self.assertRaises(VideoError):
                build_request({'prompt': 'turn', **values})

    def test_task_mismatch_and_unknown_status_do_not_pass(self):
        for response in ({'id': 'wrong', 'status': 'SUCCEEDED', 'output': [VIDEO]},
                         {'id': 'id-1', 'status': 'NEW_STATE'},
                         {'id': 'id-1', 'status': 'SUCCEEDED', 'output': []}):
            with self.subTest(response=response), self.assertRaises(VideoError):
                Provider('runway', KEYS, FakeTransport([response])).status('id-1')

    def test_failure_states_normalize_without_retry(self):
        for status, expected in [('PENDING', 'queued'), ('THROTTLED', 'queued'), ('RUNNING', 'running'),
                                 ('FAILED', 'failed'), ('CANCELED', 'cancelled')]:
            result = Provider('runway', KEYS, FakeTransport([{'id': 'task', 'status': status}])).status('task')
            self.assertEqual(result['status'], expected)

    def test_invalid_task_ids_rejected(self):
        for value in ('../key', 'id?query', '', 'x' * 201):
            with self.assertRaises(VideoError):
                Provider('runway', KEYS, FakeTransport([])).status(value)

    def test_malformed_outputs_are_reported_as_errors(self):
        cases = [
            ('kling', {'code': 0, 'data': [{'id': 'task', 'status': 'succeeded', 'outputs': [None]}]}),
            ('seedance', {'id': 'task', 'status': 'succeeded', 'content': []}),
            ('runway', {'id': 'task', 'status': 'SUCCEEDED', 'output': 'not-an-array'}),
        ]
        for name, response in cases:
            with self.subTest(name=name), self.assertRaises(VideoError):
                Provider(name, KEYS, FakeTransport([response])).status('task')

    def test_https_and_embedded_credentials(self):
        for url in ('http://assets.example.com/a.png', 'https://user:password@assets.example.com/a.png',
                    'https://assets.example.com:8080/a.png'):
            with self.assertRaises(VideoError):
                build_request({'provider': 'kling', 'prompt': 'turn', 'image': url})


if __name__ == '__main__':
    unittest.main()
