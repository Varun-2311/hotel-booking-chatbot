import unittest
from datetime import date, timedelta

from app.validation import (
    validate_date,
    validate_email,
    validate_phone,
    validate_slots,
    validate_time,
)


class ValidationTests(unittest.TestCase):
    def test_validate_email(self) -> None:
        self.assertTrue(validate_email("guest@example.com"))
        self.assertFalse(validate_email("guest@example"))

    def test_validate_phone(self) -> None:
        self.assertTrue(validate_phone("+1 (555) 123-4567"))
        self.assertFalse(validate_phone("abc123"))

    def test_validate_date_future_only(self) -> None:
        tomorrow = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
        yesterday = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
        self.assertTrue(validate_date(tomorrow))
        self.assertFalse(validate_date(yesterday))

    def test_validate_time(self) -> None:
        self.assertTrue(validate_time("2:00 PM"))
        self.assertTrue(validate_time("14:00"))
        self.assertFalse(validate_time("tomorrow evening"))

    def test_validate_slots_reports_supported_errors(self) -> None:
        errors = validate_slots(
            {
                "email": "bad-email",
                "phone": "xyz",
                "date": "2000-01-01",
                "time": "whenever",
            }
        )
        self.assertEqual(len(errors), 4)


if __name__ == "__main__":
    unittest.main()
