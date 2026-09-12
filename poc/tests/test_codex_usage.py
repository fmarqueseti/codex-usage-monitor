import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from poc.codex_usage import UsageError, _interactive_message, parse_status


NOW = datetime(2026, 9, 12, 13, 48, tzinfo=ZoneInfo("America/Belem"))


def status(remaining, weekly="09:44 on 19 Sep"):
    return f"5h limit: [████████] {remaining}% left (resets 14:44)\nWeekly limit: [████] 50% left (resets {weekly})"


class ParserTests(unittest.TestCase):
    def test_percentages(self):
        for value in (100, 80, 50, 25, 5, 0):
            result = parse_status(status(value), NOW)
            self.assertEqual(result["five_hour"]["remaining_percent"], value)
            self.assertEqual(result["five_hour"]["used_percent"], 100 - value)

    def test_reset_without_date_is_local_and_tomorrow_when_past(self):
        result = parse_status(status(80), NOW)
        self.assertEqual(result["five_hour"]["reset_at"], "2026-09-12T14:44:00-03:00")
        self.assertEqual(result["five_hour"]["seconds_until_reset"], 3360)

    def test_reset_with_date(self):
        result = parse_status(status(80), NOW)
        self.assertEqual(result["weekly"]["reset_at"], "2026-09-19T09:44:00-03:00")

    def test_year_rollover(self):
        now = datetime(2026, 12, 31, 23, 0, tzinfo=ZoneInfo("America/Belem"))
        result = parse_status(status(80, "09:44 on 1 Jan"), now)
        self.assertEqual(result["weekly"]["reset_at"][:10], "2027-01-01")

    def test_missing_or_empty_output(self):
        for text in ("", "5h limit: 50% left (resets 14:44)"):
            with self.assertRaises(UsageError):
                parse_status(text, NOW)

    def test_unexpected_format(self):
        with self.assertRaises(UsageError):
            parse_status("Weekly limit: 50% remaining", NOW)

    def test_non_terminal_diagnostic(self):
        for error in ("Error: stdout is not a terminal", "Error: stdin is not a terminal"):
            message = _interactive_message(error)
            self.assertIn("TTY", message)
            self.assertNotIn("is not a terminal", message)


if __name__ == "__main__":
    unittest.main()
