import unittest

from app.knowledge import answer_known_hotel_fact, extract_room_rates, load_guide_text


class KnowledgeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.text = load_guide_text()

    def test_extract_room_rates(self) -> None:
        rates = extract_room_rates(self.text)
        self.assertEqual(rates["Standard Room"], "INR 6,500 per night")
        self.assertEqual(rates["Presidential Suite"], "INR 45,000 per night")

    def test_answer_room_pricing_query(self) -> None:
        answer = answer_known_hotel_fact("what is the cost listing of the rooms", self.text)
        self.assertIsNotNone(answer)
        self.assertIn("Standard Room: INR 6,500 per night", answer)
        self.assertIn("Grand Suite: INR 22,000 per night", answer)

    def test_answer_checkin_query(self) -> None:
        answer = answer_known_hotel_fact("what is the check-in time", self.text)
        self.assertEqual(answer, "Check-in time is 2:00 PM.")


if __name__ == "__main__":
    unittest.main()
