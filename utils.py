from config import SUPERADMIN_IDS
from database import is_admin
import re


def is_superadmin(user_id: int) -> bool:
    return user_id in SUPERADMIN_IDS


def has_admin_access(user_id: int) -> bool:
    return is_superadmin(user_id) or is_admin(user_id)


def parse_price(value: str) -> float:
    return float(value.replace("$", "").replace(",", ".").strip())


def normalize_phone(raw: str) -> str | None:
    """Приводит номер к +7XXXXXXXXXX или международному виду."""
    digits = re.sub(r"\D", "", raw)
    if digits.startswith("8") and len(digits) == 11:
        digits = "7" + digits[1:]
    if digits.startswith("7") and len(digits) == 11:
        return "+" + digits
    if len(digits) == 10:
        return "+7" + digits
    if raw.strip().startswith("+") and 11 <= len(digits) <= 15:
        return "+" + digits
    return None
