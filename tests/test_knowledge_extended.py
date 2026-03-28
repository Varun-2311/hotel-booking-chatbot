import unittest

from app.knowledge import answer_known_hotel_fact, load_guide_text


class ExtendedKnowledgeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.text = load_guide_text()

    def test_cheapest_room_answer(self) -> None:
        answer = answer_known_hotel_fact("what is the cheapest room", self.text)
        self.assertEqual(answer, "The least expensive room is the Standard Room at INR 6,500 per night.")

    def test_cancellation_policy_answer(self) -> None:
        answer = answer_known_hotel_fact("what is your cancellation policy", self.text)
        self.assertIsNotNone(answer)
        self.assertIn("Free cancellation up to 48 hours before check-in.", answer)

    def test_room_comparison_answer(self) -> None:
        answer = answer_known_hotel_fact("compare deluxe room vs junior suite", self.text)
        self.assertIsNotNone(answer)
        self.assertIn("Deluxe Room", answer)
        self.assertIn("Junior Suite", answer)
        self.assertIn("Rate:", answer)
        self.assertIn("Key takeaway:", answer)

    def test_standard_vs_deluxe_deep_comparison(self) -> None:
        answer = answer_known_hotel_fact("i wanna know everything about the deluxe vs standard", self.text)
        self.assertIsNotNone(answer)
        self.assertIn("Standard Room", answer)
        self.assertIn("Deluxe Room", answer)
        self.assertIn("INR 6,500 per night", answer)
        self.assertIn("INR 9,500 per night", answer)
        self.assertIn("Panoramic city or garden view", answer)

    def test_amenities_summary_answer(self) -> None:
        answer = answer_known_hotel_fact("what amenities do you have", self.text)
        self.assertIsNotNone(answer)
        self.assertIn("main hotel amenities and services", answer.lower())
        self.assertIn("Azure Spa", answer)

    def test_breakfast_answer(self) -> None:
        answer = answer_known_hotel_fact("is breakfast included", self.text)
        self.assertIsNotNone(answer)
        self.assertIn("not included in standard room rates", answer.lower())
        self.assertIn("INR 850", answer)

    def test_accessibility_answer(self) -> None:
        answer = answer_known_hotel_fact("do you have accessible rooms", self.text)
        self.assertIsNotNone(answer)
        self.assertIn("4 fully accessible rooms", answer)

    def test_family_friendly_answer(self) -> None:
        answer = answer_known_hotel_fact("is the hotel family friendly", self.text)
        self.assertIsNotNone(answer)
        self.assertIn("family-friendly", answer.lower())

    def test_long_stay_discount_answer(self) -> None:
        answer = answer_known_hotel_fact("do you offer long stay discounts", self.text)
        self.assertIsNotNone(answer)
        self.assertIn("10 percent", answer.lower())
        self.assertIn("15 percent", answer.lower())

    def test_business_traveler_recommendation(self) -> None:
        answer = answer_known_hotel_fact("which room is best for a business traveler", self.text)
        self.assertIsNotNone(answer)
        self.assertIn("Deluxe Room", answer)

    def test_family_recommendation(self) -> None:
        answer = answer_known_hotel_fact("which room is best for a family", self.text)
        self.assertIsNotNone(answer)
        self.assertTrue("Presidential Suite" in answer or "Junior Suite" in answer)

    def test_two_people_recommendation(self) -> None:
        answer = answer_known_hotel_fact("what is the best choice for two people", self.text)
        self.assertIsNotNone(answer)
        self.assertIn("Deluxe Room", answer)
        self.assertIn("Junior Suite", answer)


if __name__ == "__main__":
    unittest.main()
