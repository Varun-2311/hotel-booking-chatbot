import unittest

from db.models import Booking, Customer


class ModelTests(unittest.TestCase):
    def test_customer_string(self) -> None:
        customer = Customer(
            customer_id="c1",
            name="Varun",
            email="varun@example.com",
            phone="1234567890",
        )
        self.assertIn("Varun", str(customer))
        self.assertIn("varun@example.com", str(customer))

    def test_booking_from_dict(self) -> None:
        booking = Booking.from_dict(
            {
                "booking_id": "ABC12345",
                "booking_type": "Deluxe Room",
                "date": "2026-04-15",
                "time": "2:00 PM",
                "status": "confirmed",
            }
        )
        self.assertEqual(booking.id, "ABC12345")
        self.assertIn("Deluxe Room", booking.summary())


if __name__ == "__main__":
    unittest.main()
