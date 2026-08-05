import unittest

from mediakit_toolkit.redaction import redact_text, strip_url_query


class RedactionTests(unittest.TestCase):
    def test_url_query_is_removed(self):
        self.assertEqual(
            strip_url_query("https://example.com/video.mp4?auth_key=secret"),
            "https://example.com/video.mp4",
        )

    def test_api_key_is_redacted(self):
        self.assertNotIn(
            "secret-value",
            redact_text("MEDIAKIT_API_KEY=secret-value"),
        )


if __name__ == "__main__":
    unittest.main()

