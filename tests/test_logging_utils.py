import unittest
from unittest.mock import patch

from mediakit_toolkit.logging_utils import log_event


class LoggingTests(unittest.TestCase):
    @patch("mediakit_toolkit.logging_utils.LOGGER.info")
    def test_event_logs_redact_url_query(self, info):
        log_event(
            "task_completed",
            result_url="https://example.com/out.mp4?token=secret",
        )
        rendered = info.call_args.args[1]
        self.assertNotIn("secret", rendered)
        self.assertIn("https://example.com/out.mp4", rendered)
        self.assertNotIn("?token=", rendered)


if __name__ == "__main__":
    unittest.main()
