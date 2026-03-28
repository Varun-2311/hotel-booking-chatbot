"""
knowledge.py - deterministic extractors for high-value hotel facts.

These helpers improve factual reliability without changing the model.
"""

from __future__ import annotations

import re
from pathlib import Path


DOCS_DIR = Path(__file__).parent.parent / "docs"
GUIDE_PATH = DOCS_DIR / "grand_azure_hotel_guide.txt"

ROOM_ORDER = [
    "Standard Room",
    "Deluxe Room",
    "Junior Suite",
    "Grand Suite",
    "Presidential Suite",
]

ROOM_ALIASES = {
    "standard": "Standard Room",
    "standard room": "Standard Room",
    "deluxe": "Deluxe Room",
    "deluxe room": "Deluxe Room",
    "junior suite": "Junior Suite",
    "grand suite": "Grand Suite",
    "presidential suite": "Presidential Suite",
}

POLICY_TITLES = [
    "Cancellation Policy",
    "Payment",
    "Children Policy",
    "Extra Bed",
    "Internet / Wi-Fi",
    "Pet Policy",
    "Smoking Policy",
]

AMENITY_TITLES = [
    "Azure Spa (2nd Floor)",
    "Fitness Centre (2nd Floor)",
    "Swimming Pool (3rd Floor)",
    "Concierge Services",
    "Business Centre (Lobby Level)",
    "Conference and Banquet",
    "Laundry and Dry Cleaning",
    "Airport Transfer",
    "Valet Parking",
]

DINING_TITLES = [
    "Azure Brasserie (Ground Floor)",
    "The Rooftop Grill (12th Floor)",
    "In-Room Dining",
]

FAQ_ANSWERS = {
    "breakfast": (
        "Breakfast is not included in standard room rates. "
        "It can be added for INR 850 per person per day, and some promotional packages include it."
    ),
    "accessible_rooms": (
        "Yes. The hotel has 4 fully accessible rooms: 2 Standard Rooms, 1 Deluxe Room, and 1 Junior Suite. "
        "They include roll-in showers, grab bars, and lowered fixtures."
    ),
    "wheelchair_accessible": (
        "Yes. The hotel is wheelchair accessible, with step-free entrances, lifts to all floors, "
        "accessible bathrooms, and trained staff to assist guests with mobility needs."
    ),
    "family_friendly": (
        "Yes. The hotel is family-friendly and offers family rooms, baby cots, a kids' menu at Azure Brasserie, "
        "and babysitting services through the concierge with advance notice."
    ),
    "long_stay": (
        "Yes. Stays of 7 nights or more receive a 10 percent discount, and stays of 14 nights or more receive a 15 percent discount. "
        "For extended-stay rates, guests should contact reservations."
    ),
    "luggage": "Yes. Complimentary luggage storage is available at the concierge desk after check-out.",
    "checkin_age": "Guests must be 18 years or older to check in, and a valid government-issued photo ID is required.",
}


def load_guide_text() -> str:
    if not GUIDE_PATH.exists():
        return ""
    return GUIDE_PATH.read_text(encoding="utf-8", errors="ignore")


def _normalize(text: str) -> str:
    return (
        text.replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\u2019", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("â€“", "-")
        .replace("â€”", "-")
        .replace("â€™", "'")
    )


def _extract_named_block(text: str, title: str) -> str | None:
    pattern = rf"^{re.escape(title)}:\n((?:- .*(?:\n|$)|  .*(?:\n|$))+)"
    match = re.search(pattern, text, flags=re.MULTILINE)
    if not match:
        return None
    return match.group(1).strip()


def _extract_line(block: str, label: str) -> str | None:
    match = re.search(rf"^- {re.escape(label)}:\s*(.+)$", block, flags=re.MULTILINE)
    return match.group(1).strip() if match else None


def _extract_multiline_value(block: str, label: str) -> str | None:
    match = re.search(
        rf"^- {re.escape(label)}:\s*(.+(?:\n  .+)*)",
        block,
        flags=re.MULTILINE,
    )
    if not match:
        return None
    return re.sub(r"\n\s+", " ", match.group(1)).strip()


def extract_room_details(text: str) -> dict[str, dict[str, str]]:
    text = _normalize(text)
    details: dict[str, dict[str, str]] = {}

    for room in ROOM_ORDER:
        block = _extract_named_block(text, room)
        if not block:
            continue
        details[room] = {
            "size": _extract_line(block, "Size") or "",
            "bed": _extract_line(block, "Bed options") or _extract_line(block, "Bed") or "",
            "view": _extract_line(block, "View") or "",
            "rate": _extract_line(block, "Rate") or "",
            "amenities": _extract_multiline_value(block, "Amenities")
            or _extract_multiline_value(block, "All Standard amenities plus")
            or _extract_multiline_value(block, "All Deluxe amenities plus")
            or _extract_multiline_value(block, "All Junior Suite amenities plus")
            or _extract_multiline_value(block, "All Grand Suite amenities plus")
            or "",
        }

        # Preserve single-line view statements that are not keyed
        if not details[room]["view"]:
            for line in block.splitlines():
                raw = line.strip()
                if raw.startswith("- ") and "view" in raw.lower() and ":" not in raw:
                    details[room]["view"] = raw[2:].strip()
                    break

        if not details[room]["bed"]:
            for line in block.splitlines():
                raw = line.strip()
                if raw.startswith("- ") and "bed" in raw.lower() and ":" not in raw:
                    details[room]["bed"] = raw[2:].strip()
                    break

    return details


def extract_room_rates(text: str) -> dict[str, str]:
    room_details = extract_room_details(text)
    return {room: data["rate"] for room, data in room_details.items() if data.get("rate")}


def extract_basic_facts(text: str) -> dict[str, str]:
    text = _normalize(text)
    facts: dict[str, str] = {}
    patterns = {
        "check_in": r"Check-in time:\s*([^\n]+)",
        "check_out": r"Check-out time:\s*([^\n]+)",
        "address": r"Address:\s*([^\n]+)",
        "phone": r"Phone:\s*([^\n]+)",
        "email": r"Email:\s*([^\n]+)",
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            facts[key] = match.group(1).strip()
    return facts


def extract_section_items(text: str, title: str) -> list[str]:
    text = _normalize(text)
    block = _extract_named_block(text, title)
    if not block:
        return []
    items: list[str] = []
    current = ""
    for line in block.splitlines():
        raw = line.rstrip()
        if raw.startswith("- "):
            if current:
                items.append(current.strip())
            current = raw[2:].strip()
        elif raw.startswith("  "):
            current += " " + raw.strip()
    if current:
        items.append(current.strip())
    return items


def _looks_like_room_pricing_query(query: str) -> bool:
    q = query.lower()
    return (
        ("room" in q or "suite" in q)
        and any(word in q for word in ["rate", "rates", "cost", "costs", "price", "prices", "pricing", "listing"])
    )


def _looks_like_room_extreme_query(query: str) -> bool:
    q = query.lower()
    return any(term in q for term in ["least expensive", "cheapest", "most affordable", "lowest price", "most expensive"])


def _looks_like_checkin_query(query: str) -> bool:
    q = query.lower()
    return "check-in" in q or "check in" in q or "check-out" in q or "check out" in q


def _looks_like_contact_query(query: str) -> bool:
    q = query.lower()
    return any(token in q for token in ["address", "phone", "email", "contact", "location"])


def _looks_like_policy_query(query: str) -> bool:
    q = query.lower()
    return any(
        token in q
        for token in [
            "policy",
            "cancellation",
            "cancel",
            "payment",
            "deposit",
            "refund",
            "pet",
            "smoking",
            "wifi",
            "internet",
            "children",
            "child",
            "kids",
            "extra bed",
        ]
    )


def _looks_like_amenity_query(query: str) -> bool:
    q = query.lower()
    return any(
        token in q
        for token in [
            "amenities",
            "facilities",
            "services",
            "spa",
            "gym",
            "fitness",
            "pool",
            "parking",
            "airport transfer",
            "concierge",
            "laundry",
            "business centre",
            "business center",
            "restaurant",
            "dining",
            "food",
        ]
    )


def _looks_like_comparison_query(query: str) -> bool:
    q = query.lower()
    return (
        any(alias in q for alias in ROOM_ALIASES)
        and any(term in q for term in ["compare", "difference", "vs", "versus", "better than", "everything about", "all about"])
    )


def _looks_like_faq_query(query: str) -> bool:
    q = query.lower()
    return any(
        token in q
        for token in [
            "breakfast",
            "accessible",
            "wheelchair",
            "family-friendly",
            "family friendly",
            "kids",
            "children",
            "long stay",
            "long-stay",
            "discount",
            "luggage",
            "check-in age",
            "check in age",
            "age requirement",
            "accessible rooms",
        ]
    )


def _looks_like_recommendation_query(query: str) -> bool:
    q = query.lower()
    return any(term in q for term in ["best room", "best choice", "recommend", "which room", "good for"]) and any(
        token in q
        for token in [
            "family",
            "couple",
            "business",
            "traveler",
            "traveller",
            "work",
            "romantic",
            "two people",
            "2 people",
            "one person",
            "solo",
        ]
    )


def _format_bullets(title: str, items: list[str], closing: str | None = None) -> str:
    lines = [title]
    lines.extend(f"- {item}" for item in items)
    if closing:
        lines.append(closing)
    return "\n".join(lines)


def _parse_rate_value(rate: str) -> int:
    digits = re.sub(r"[^\d]", "", rate)
    return int(digits) if digits else 0


def _answer_room_rates(text: str) -> str | None:
    rates = extract_room_rates(text)
    if not rates:
        return None
    lines = ["Here are the room rates from the hotel guide:"]
    for room in ROOM_ORDER:
        if room in rates:
            lines.append(f"- {room}: {rates[room]}")
    lines.append("If you'd like, I can also compare room types or help you book one.")
    return "\n".join(lines)


def _answer_room_extreme(query: str, text: str) -> str | None:
    rates = extract_room_rates(text)
    if not rates:
        return None

    ordered = sorted(rates.items(), key=lambda item: _parse_rate_value(item[1]))
    q = query.lower()

    if any(term in q for term in ["most expensive", "highest price"]):
        room, rate = ordered[-1]
        return f"The most expensive room is the {room} at {rate}."

    room, rate = ordered[0]
    return f"The least expensive room is the {room} at {rate}."


def _answer_checkin(query: str, facts: dict[str, str]) -> str | None:
    q = query.lower()
    if "check-out" in q or "check out" in q:
        if "check_out" in facts:
            return f"Check-out time is {facts['check_out']}."
    if "check-in" in q or "check in" in q:
        if "check_in" in facts:
            return f"Check-in time is {facts['check_in']}."
    if "check_in" in facts and "check_out" in facts:
        return f"Check-in time is {facts['check_in']}, and check-out time is {facts['check_out']}."
    return None


def _answer_contact(query: str, facts: dict[str, str]) -> str | None:
    q = query.lower()
    parts: list[str] = []
    if "address" in q or "location" in q:
        if "address" in facts:
            parts.append(f"Address: {facts['address']}")
    if "phone" in q or "call" in q or "contact" in q:
        if "phone" in facts:
            parts.append(f"Phone: {facts['phone']}")
    if "email" in q or "contact" in q:
        if "email" in facts:
            parts.append(f"Email: {facts['email']}")
    if parts:
        return "Here are the hotel contact details:\n- " + "\n- ".join(parts)
    return None


def _answer_policy(query: str, text: str) -> str | None:
    q = query.lower()
    title_map = {
        "cancellation": "Cancellation Policy",
        "cancel": "Cancellation Policy",
        "payment": "Payment",
        "deposit": "Payment",
        "children": "Children Policy",
        "child": "Children Policy",
        "kids": "Children Policy",
        "extra bed": "Extra Bed",
        "wifi": "Internet / Wi-Fi",
        "internet": "Internet / Wi-Fi",
        "pet": "Pet Policy",
        "smoking": "Smoking Policy",
    }

    selected = None
    for token, title in title_map.items():
        if token in q:
            selected = title
            break

    if selected:
        items = extract_section_items(text, selected)
        if items:
            return _format_bullets(f"Here is the {selected.lower()}:", items)

    if "policy" in q or "policies" in q:
        lines = ["Here are the key hotel policies:"]
        for title in POLICY_TITLES:
            items = extract_section_items(text, title)
            if items:
                lines.append(f"- {title}: {items[0]}")
        return "\n".join(lines)

    return None


def _answer_amenity(query: str, text: str) -> str | None:
    q = query.lower()

    if "dining options" in q or "restaurants" in q:
        lines = ["Here are the dining options at the hotel:"]
        for title in DINING_TITLES:
            items = extract_section_items(text, title)
            if items:
                lines.append(f"- {title}: {items[0]}")
        return "\n".join(lines)

    title_map = {
        "spa": "Azure Spa (2nd Floor)",
        "gym": "Fitness Centre (2nd Floor)",
        "fitness": "Fitness Centre (2nd Floor)",
        "pool": "Swimming Pool (3rd Floor)",
        "parking": "Valet Parking",
        "airport transfer": "Airport Transfer",
        "concierge": "Concierge Services",
        "laundry": "Laundry and Dry Cleaning",
        "business centre": "Business Centre (Lobby Level)",
        "business center": "Business Centre (Lobby Level)",
        "restaurant": "Azure Brasserie (Ground Floor)",
        "dining": "In-Room Dining",
        "food": "Azure Brasserie (Ground Floor)",
    }

    for token, title in title_map.items():
        if token in q:
            items = extract_section_items(text, title)
            if items:
                return _format_bullets(f"Here are the details for {title}:", items)

    if "amenities" in q or "facilities" in q or "services" in q:
        lines = ["Here are the main hotel amenities and services:"]
        for title in AMENITY_TITLES:
            items = extract_section_items(text, title)
            if items:
                lines.append(f"- {title}: {items[0]}")
        return "\n".join(lines)

    if "restaurant" in q:
        lines = ["Here are the dining options at the hotel:"]
        for title in DINING_TITLES:
            items = extract_section_items(text, title)
            if items:
                lines.append(f"- {title}: {items[0]}")
        return "\n".join(lines)

    return None


def _answer_room_comparison(query: str, text: str) -> str | None:
    room_details = extract_room_details(text)
    q = query.lower()
    mentioned: list[str] = []
    for alias, room in ROOM_ALIASES.items():
        if alias in q and room not in mentioned:
            mentioned.append(room)
    if len(mentioned) < 2:
        return None

    left, right = mentioned[0], mentioned[1]
    left_data = room_details.get(left)
    right_data = room_details.get(right)
    if not left_data or not right_data:
        return None

    lines = [f"Here is a detailed comparison between the {left} and the {right}:"]

    summary_left = [
        f"Rate: {left_data.get('rate') or 'Not specified'}",
        f"Size: {left_data.get('size') or 'Not specified'}",
        f"Bed: {left_data.get('bed') or 'Not specified'}",
        f"View: {left_data.get('view') or 'Not specified'}",
        f"Highlights: {left_data.get('amenities') or 'Not specified'}",
    ]
    summary_right = [
        f"Rate: {right_data.get('rate') or 'Not specified'}",
        f"Size: {right_data.get('size') or 'Not specified'}",
        f"Bed: {right_data.get('bed') or 'Not specified'}",
        f"View: {right_data.get('view') or 'Not specified'}",
        f"Highlights: {right_data.get('amenities') or 'Not specified'}",
    ]

    lines.append(f"- {left}:")
    lines.extend(f"  - {item}" for item in summary_left)
    lines.append(f"- {right}:")
    lines.extend(f"  - {item}" for item in summary_right)

    left_rate = left_data.get("rate")
    right_rate = right_data.get("rate")
    left_size = left_data.get("size")
    right_size = right_data.get("size")
    lines.append("- Key takeaway:")
    takeaway_parts = []
    if left_rate and right_rate:
        takeaway_parts.append(f"the {right} is priced higher than the {left}")
    if left_size and right_size:
        takeaway_parts.append(f"the {right} is larger")
    if right_data.get("amenities"):
        takeaway_parts.append(f"the {right} adds more premium features")
    if takeaway_parts:
        lines.append(f"  - Overall, {', '.join(takeaway_parts)}.")
    lines.append("If you'd like, I can also recommend which one fits your budget or travel style better.")
    return "\n".join(lines)


def _answer_faq(query: str) -> str | None:
    q = query.lower()

    if "breakfast" in q:
        return FAQ_ANSWERS["breakfast"]

    if "accessible room" in q or ("accessible" in q and "room" in q):
        return FAQ_ANSWERS["accessible_rooms"]

    if "wheelchair" in q or ("accessible" in q and "hotel" in q):
        return FAQ_ANSWERS["wheelchair_accessible"]

    if "family-friendly" in q or "family friendly" in q:
        return FAQ_ANSWERS["family_friendly"]

    if "long stay" in q or "long-stay" in q or "discount" in q:
        return FAQ_ANSWERS["long_stay"]

    if "luggage" in q:
        return FAQ_ANSWERS["luggage"]

    if "check-in age" in q or "check in age" in q or "age requirement" in q:
        return FAQ_ANSWERS["checkin_age"]

    if "kids" in q or ("children" in q and "family" in q):
        return FAQ_ANSWERS["family_friendly"]

    return None


def _answer_recommendation(query: str, text: str) -> str | None:
    room_details = extract_room_details(text)
    q = query.lower()

    if "two people" in q or "2 people" in q:
        deluxe = room_details.get("Deluxe Room", {})
        junior = room_details.get("Junior Suite", {})
        return (
            "For two people, I would usually recommend the Deluxe Room if you want the best balance of comfort and price. "
            f"It offers {deluxe.get('bed', 'a flexible bed setup')}, {deluxe.get('view', 'a good view')}, and costs {deluxe.get('rate', 'the listed rate')}. "
            f"If you'd like more space, the Junior Suite is the stronger upgrade because it offers {junior.get('size', 'more space')}, "
            f"{junior.get('view', 'an upgraded view')}, and a separate living area at {junior.get('rate', 'the listed rate')}."
        )

    if "one person" in q or "solo" in q:
        standard = room_details.get("Standard Room", {})
        return (
            "For one person, I would usually recommend the Standard Room if you want the most budget-friendly option. "
            f"It offers {standard.get('bed', 'comfortable bedding')}, {standard.get('view', 'a city view')}, and costs {standard.get('rate', 'the listed rate')}. "
            "If you'd prefer a more premium stay, the Deluxe Room is the next best step up."
        )

    if "family" in q:
        return (
            "For a family, I would recommend the Presidential Suite if budget allows because it offers a master bedroom plus guest bedroom, "
            "a living room, a kitchen, and complimentary spa access for two. "
            "If you'd like a more moderate option, the Junior Suite is a strong choice because it has a separate living area and more space than the standard rooms."
        )

    if "couple" in q or "romantic" in q:
        grand = room_details.get("Grand Suite", {})
        return (
            "For a couple, I would recommend the Grand Suite. "
            f"It offers {grand.get('view', 'a premium view')}, a private balcony, and butler service, which makes it feel more special for a romantic or celebratory stay."
        )

    if "business" in q or "traveler" in q or "traveller" in q or "work" in q:
        deluxe = room_details.get("Deluxe Room", {})
        return (
            "For a business traveler, I would recommend the Deluxe Room. "
            f"It balances comfort and cost well at {deluxe.get('rate', 'the listed rate')}, while adding premium toiletries, a pillow menu, and turndown service over the Standard Room."
        )

    return None


def answer_known_hotel_fact(query: str, guide_text: str | None = None) -> str | None:
    text = _normalize(guide_text or load_guide_text())
    if not text:
        return None

    facts = extract_basic_facts(text)

    if _looks_like_room_extreme_query(query):
        answer = _answer_room_extreme(query, text)
        if answer:
            return answer

    if _looks_like_room_pricing_query(query):
        answer = _answer_room_rates(text)
        if answer:
            return answer

    if _looks_like_recommendation_query(query):
        answer = _answer_recommendation(query, text)
        if answer:
            return answer

    if _looks_like_comparison_query(query):
        answer = _answer_room_comparison(query, text)
        if answer:
            return answer

    if _looks_like_checkin_query(query):
        answer = _answer_checkin(query, facts)
        if answer:
            return answer

    if _looks_like_contact_query(query):
        answer = _answer_contact(query, facts)
        if answer:
            return answer

    if _looks_like_policy_query(query):
        answer = _answer_policy(query, text)
        if answer:
            return answer

    if _looks_like_faq_query(query):
        answer = _answer_faq(query)
        if answer:
            return answer

    if _looks_like_amenity_query(query):
        answer = _answer_amenity(query, text)
        if answer:
            return answer

    return None
