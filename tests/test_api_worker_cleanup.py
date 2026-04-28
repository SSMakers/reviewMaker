import unittest
from types import SimpleNamespace

from api_worker import ApiWorker


class FakeServerApi:
    def __init__(self):
        self.cleanup_calls = []

    def cleanup_review_images(self, **kwargs):
        self.cleanup_calls.append(kwargs)
        return SimpleNamespace(
            deleted=list(kwargs["image_ids"]),
            not_found=[],
            failed=[],
        )


class ApiWorkerCleanupTests(unittest.TestCase):
    def test_cleanup_is_enabled_by_default(self):
        worker = ApiWorker(
            api_interface=None,
            file_path="reviews.xlsx",
            board_no=4,
            product_no=41,
            device_id="device-1",
            mall_id="venel",
        )

        self.assertTrue(worker.client_cleanup_enabled)

    def test_cleanup_uploaded_images_calls_server_api(self):
        worker = ApiWorker(
            api_interface=None,
            file_path="reviews.xlsx",
            board_no=4,
            product_no=41,
            device_id="device-1",
            mall_id="venel",
        )
        fake_server = FakeServerApi()
        worker.server_api = fake_server
        worker.job_id = "job-1"
        worker.uploaded_image_ids = ["img_1", "img_2"]

        worker._cleanup_uploaded_images()

        self.assertEqual(
            fake_server.cleanup_calls,
            [
                {
                    "device_id": "device-1",
                    "mall_id": "venel",
                    "image_ids": ["img_1", "img_2"],
                    "job_id": "job-1",
                }
            ],
        )


if __name__ == "__main__":
    unittest.main()
