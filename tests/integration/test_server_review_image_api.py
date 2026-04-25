import os
import tempfile
import unittest
from pathlib import Path

import requests

from external_api.server.models import VerifyConfirm
from external_api.server.server_api import HttpError, ServerApi
from utils.computer_resource import get_system_uuid


RUN_INTEGRATION_TESTS = os.getenv("RUN_INTEGRATION_TESTS") == "1"


@unittest.skipUnless(RUN_INTEGRATION_TESTS, "Set RUN_INTEGRATION_TESTS=1 to run live server integration tests.")
class ServerReviewImageIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server_api = ServerApi()
        cls.device_id = get_system_uuid()
        if not cls.device_id:
            raise unittest.SkipTest("Cannot read local device id.")

        auth = cls.server_api.auth_verify(device_id=cls.device_id)
        if not isinstance(auth, VerifyConfirm):
            raise unittest.SkipTest(f"Local device is not authorized: {auth.reason}")
        cls.mall_id = auth.mall_id

    def _make_temp_file(self, *, suffix: str, content: bytes) -> Path:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        tmp.write(content)
        tmp.close()
        self.addCleanup(lambda: Path(tmp.name).exists() and Path(tmp.name).unlink())
        return Path(tmp.name)

    def test_upload_public_url_and_cleanup_flow(self):
        image_path = self._make_temp_file(
            suffix=".jpg",
            content=b"fake-jpeg-bytes-for-mime-based-server-validation",
        )

        upload = self.server_api.upload_review_image(
            file_path=image_path,
            device_id=self.device_id,
            mall_id=self.mall_id,
            source_row_id="integration-test",
            job_id="integration-test-job",
        )

        self.assertTrue(upload.image_id.startswith("img_"))
        self.assertTrue(upload.url.startswith("https://"))
        self.assertEqual(upload.content_type, "image/jpeg")
        self.assertGreater(upload.size_bytes, 0)

        fetch_response = requests.get(
            upload.url,
            timeout=10,
            verify=self.server_api.config.api_ca_cert_path,
        )
        self.assertEqual(fetch_response.status_code, 200)
        self.assertEqual(fetch_response.content, b"fake-jpeg-bytes-for-mime-based-server-validation")

        cleanup = self.server_api.cleanup_review_images(
            device_id=self.device_id,
            mall_id=self.mall_id,
            image_ids=[upload.image_id],
            job_id="integration-test-job",
        )
        self.assertEqual(cleanup.deleted, [upload.image_id])
        self.assertEqual(cleanup.not_found, [])
        self.assertEqual(cleanup.failed, [])

        deleted_fetch = requests.get(
            upload.url,
            timeout=10,
            verify=self.server_api.config.api_ca_cert_path,
        )
        self.assertEqual(deleted_fetch.status_code, 404)

    def test_invalid_file_type_is_rejected(self):
        text_path = self._make_temp_file(suffix=".txt", content=b"not an image")

        with self.assertRaises(HttpError) as ctx:
            self.server_api.upload_review_image(
                file_path=text_path,
                device_id=self.device_id,
                mall_id=self.mall_id,
                source_row_id="invalid-file-type",
            )

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertEqual(ctx.exception.payload.get("code"), "unsupported_content_type")

    def test_unknown_device_is_rejected(self):
        image_path = self._make_temp_file(suffix=".jpg", content=b"image")

        with self.assertRaises(HttpError) as ctx:
            self.server_api.upload_review_image(
                file_path=image_path,
                device_id="unknown-device-for-integration-test",
                mall_id=self.mall_id,
                source_row_id="unknown-device",
            )

        self.assertEqual(ctx.exception.status_code, 401)
        self.assertEqual(ctx.exception.payload.get("code"), "unknown_device")

    def test_wrong_mall_id_is_rejected(self):
        image_path = self._make_temp_file(suffix=".jpg", content=b"image")

        with self.assertRaises(HttpError) as ctx:
            self.server_api.upload_review_image(
                file_path=image_path,
                device_id=self.device_id,
                mall_id="wrong-mall-id",
                source_row_id="wrong-mall-id",
            )

        self.assertEqual(ctx.exception.status_code, 403)
        self.assertEqual(ctx.exception.payload.get("code"), "mall_id_mismatch")


if __name__ == "__main__":
    unittest.main()
