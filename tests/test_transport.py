import io
import json
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/video-production-workflow/scripts'))
from video_api.config import VideoError
from video_api.transport import APIError, NoRedirect, Transport


class Response(io.BytesIO):
    def __init__(self, body, headers=None):
        super().__init__(body)
        self.headers = headers or {}


def http_error(code, body=b'', headers=None):
    return urllib.error.HTTPError('https://api.example.com', code, 'test', headers or {}, io.BytesIO(body))


class TransportTests(unittest.TestCase):
    def setUp(self):
        self.transport = Transport({'KLING_API_KEY': 'test-secret'})
        self.transport.opener = Mock()

    def test_post_network_timeout_is_not_retried(self):
        self.transport.opener.open.side_effect = TimeoutError()
        with self.assertRaises(APIError) as caught:
            self.transport.request('POST', 'https://api.example.com', {'Authorization': 'Bearer test-secret'}, {})
        self.assertTrue(caught.exception.ambiguous)
        self.assertEqual(self.transport.opener.open.call_count, 1)

    def test_post_500_is_not_retried(self):
        self.transport.opener.open.side_effect = http_error(500)
        with self.assertRaises(APIError) as caught:
            self.transport.request('POST', 'https://api.example.com', {}, {})
        self.assertTrue(caught.exception.ambiguous)
        self.assertEqual(self.transport.opener.open.call_count, 1)

    def test_get_rate_limit_retries_with_bounded_backoff(self):
        self.transport.opener.open.side_effect = [http_error(429, headers={'Retry-After': '9999'}), Response(b'{"id":"task"}')]
        with patch('video_api.transport.time.sleep') as sleep:
            result = self.transport.request('GET', 'https://api.example.com', {})
        self.assertEqual(result['id'], 'task')
        sleep.assert_called_once_with(10)

    def test_auth_failure_does_not_retry_or_disclose_secret(self):
        self.transport.opener.open.side_effect = http_error(401, json.dumps({'message': 'bad test-secret'}).encode())
        with self.assertRaises(APIError) as caught:
            self.transport.request('GET', 'https://api.example.com', {})
        self.assertNotIn('test-secret', str(caught.exception))
        self.assertEqual(self.transport.opener.open.call_count, 1)

    def test_malformed_post_response_is_ambiguous(self):
        self.transport.opener.open.return_value = Response(b'<html>error</html>')
        with self.assertRaises(APIError) as caught:
            self.transport.request('POST', 'https://api.example.com', {}, {})
        self.assertTrue(caught.exception.ambiguous)

    def test_api_redirect_cannot_forward_credentials(self):
        handler = NoRedirect()
        self.assertIsNone(handler.redirect_request(None, None, 302, '', {}, 'https://other.example.com'))
        self.transport.opener.open.side_effect = http_error(302, headers={'Location': 'https://other.example.com'})
        with self.assertRaises(APIError):
            self.transport.request('POST', 'https://api.example.com', {'Authorization': 'Bearer test-secret'}, {})
        self.assertEqual(self.transport.opener.open.call_count, 1)

    def test_download_redirects_never_send_api_credentials(self):
        media = b'\x00\x00\x00\x18ftypisom' + b'video' * 20
        self.transport.opener.open.side_effect = [http_error(302, headers={'Location': 'https://cdn.example.com/result.mp4'}),
                                                  Response(media, {'Content-Length': str(len(media))})]
        with tempfile.TemporaryDirectory() as temporary, patch('video_api.transport.public_download_url') as validate:
            destination = Path(temporary) / 'out.mp4'
            self.transport.download('https://assets.example.com/result', destination, 10000)
            self.assertEqual(destination.read_bytes(), media)
            self.assertEqual(validate.call_count, 2)
            self.assertFalse(list(Path(temporary).glob('*.part')))
        for call in self.transport.opener.open.call_args_list:
            self.assertIsNone(call.args[0].get_header('Authorization'))

    def test_rejects_html_disguised_as_video(self):
        self.transport.opener.open.return_value = Response(b'<html>access denied</html>')
        with tempfile.TemporaryDirectory() as temporary, patch('video_api.transport.public_download_url'):
            destination = Path(temporary) / 'out.mp4'
            with self.assertRaises(VideoError):
                self.transport.download('https://assets.example.com/result', destination, 1000)
            self.assertFalse(destination.exists())

    def test_size_limit_and_truncated_download_leave_no_output(self):
        for headers, maximum in [({}, 12), ({'Content-Length': '1000'}, 2000)]:
            self.transport.opener.open.return_value = Response(b'\x00\x00\x00\x18ftypisom-video', headers)
            with self.subTest(headers=headers), tempfile.TemporaryDirectory() as temporary, patch('video_api.transport.public_download_url'):
                destination = Path(temporary) / 'out.mp4'
                with self.assertRaises(VideoError):
                    self.transport.download('https://assets.example.com/result', destination, maximum)
                self.assertFalse(destination.exists())
                self.assertEqual(list(Path(temporary).iterdir()), [])

    def test_private_download_destination_rejected(self):
        from video_api.transport import public_download_url
        addresses = [(2, 1, 6, '', ('127.0.0.1', 443))]
        with patch('video_api.transport.socket.getaddrinfo', return_value=addresses), self.assertRaises(VideoError):
            public_download_url('https://localhost/result.mp4')


if __name__ == '__main__':
    unittest.main()
