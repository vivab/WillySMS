import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
SUPERADMIN_IDS = [int(x) for x in os.getenv("SUPERADMIN_IDS", "").split(",") if x.strip()]
DB_NAME = os.getenv("DB_NAME", "bot.db")

MIN_WITHDRAWAL = float(os.getenv("MIN_WITHDRAWAL", "1.0"))
CRYPTO_PAY_TOKEN = os.getenv("CRYPTO_PAY_TOKEN", "")
CRYPTO_ASSET = os.getenv("CRYPTO_ASSET", "USDT")

AUTO_RELEASE_TIME = int(os.getenv("AUTO_RELEASE_TIME", "300"))
MAX_SERVICES_PER_REQUEST = int(os.getenv("MAX_SERVICES_PER_REQUEST", "1"))
