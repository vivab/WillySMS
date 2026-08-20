from config import SUPERADMIN_IDS
from database import is_admin

def is_superadmin(user_id):
    return user_id in SUPERADMIN_IDS

def has_admin_access(user_id):
    return is_superadmin(user_id) or is_admin(user_id)

def parse_price(value):
    return float(value.replace("$", "").replace(",", ".").strip())
