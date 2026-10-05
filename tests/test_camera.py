import unittest
from tests import test_bench as bench


class CameraTests(unittest.TestCase):
    setUp = bench.BenchTests.setUp
    tearDown = bench.BenchTests.tearDown
    post = bench.BenchTests.post

    def upload(self, data=b'\xff\xd8\xff\xe0test', mime='image/jpeg', actor='operator', source='browser_camera'):
        return self.client.post(f'/api/v1/meetings/{self.mid}/captures?source={source}',
            files={'file': ('camera.jpg', data, mime)},
            headers={'Authorization': 'Bearer ' + self.tokens[actor]})

    def test_camera_provenance_roundtrip_and_isolation(self):
        response = self.upload()
        self.assertEqual(response.status_code, 201, response.text)
        result = response.json()
        self.assertEqual(result['event']['mode'], 'manual')
        self.assertEqual(result['event']['source'], 'browser_camera')
        cid = result['capture_id']
        headers = {'Authorization': 'Bearer ' + self.tokens['remote_1']}
        path = f'/api/v1/meetings/{self.mid}/captures/{cid}'
        self.assertEqual(self.client.get(path, headers=headers).content, b'\xff\xd8\xff\xe0test')
        self.assertEqual(self.client.get(path).status_code, 401)
        other = self.post('/api/v1/meetings', {'title': 'other'}, 201)['meeting_id']
        self.assertEqual(self.client.get(f'/api/v1/meetings/{other}/captures/{cid}', headers=headers).status_code, 404)
        self.assertEqual(self.upload(source='file_upload').json()['event']['source'], 'file_upload')

    def test_invalid_uploads(self):
        self.assertEqual(self.upload(actor='remote_1').status_code, 403)
        self.assertEqual(self.upload(source='invented').status_code, 422)
        self.assertEqual(self.upload(data=b'not jpeg').status_code, 422)
        self.assertEqual(self.upload(data=b'<svg/>', mime='image/svg+xml').status_code, 422)
        self.assertEqual(self.upload(data=b'').status_code, 422)
        self.assertEqual(self.upload(data=bytes(2 * 1024 * 1024 + 1)).status_code, 413)
