import unittest

import pandas as pd

from review_article_builder import (
    EXCEL_COLUMN_CONTENT,
    EXCEL_COLUMN_TITLE,
    build_article_from_excel_row,
)


class ReviewArticleBuilderTests(unittest.TestCase):
    def test_image_url_is_sent_as_cafe24_attachment(self):
        row = pd.Series(
            {
                EXCEL_COLUMN_TITLE: "Great product",
                EXCEL_COLUMN_CONTENT: "Loved it",
            }
        )

        result = build_article_from_excel_row(
            row,
            product_no=41,
            image_url_override="https://example.com/review-images/uploaded.jpg",
            image_filename="venel_review.jpg",
        )

        self.assertIsNotNone(result.article)
        self.assertEqual(result.article["content"], "Loved it")
        self.assertEqual(
            result.article["attach_file_urls"],
            [
                {
                    "name": "venel_review.jpg",
                    "url": "https://example.com/review-images/uploaded.jpg",
                }
            ],
        )

    def test_attachment_filename_falls_back_to_url_path(self):
        row = pd.Series(
            {
                EXCEL_COLUMN_TITLE: "Great product",
                EXCEL_COLUMN_CONTENT: "Loved it",
            }
        )

        result = build_article_from_excel_row(
            row,
            product_no=41,
            image_url_override="https://cdn.example.com/path/review.jpg",
        )

        self.assertEqual(result.article["attach_file_urls"][0]["name"], "review.jpg")


if __name__ == "__main__":
    unittest.main()
