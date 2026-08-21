import httpx
from config import CRYPTO_PAY_TOKEN, CRYPTO_ASSET, CRYPTO_PAY_API_URL


class CryptoPayError(Exception):
    """Ошибка при обращении к Crypto Pay API (недостаточно средств, юзер не открывал @CryptoBot и т.д.)"""
    pass


async def transfer_crypto(user_id: int, amount: float, spend_id: str, comment: str = "") -> dict:
    """
    Отправляет выплату пользователю через Crypto Pay API (@CryptoBot).

    ВАЖНО: пользователь должен был хотя бы раз запустить @CryptoBot,
    иначе перевод невозможен — Crypto Pay вернёт ошибку.

    spend_id должен быть уникальным для каждой транзакции (используем id заявки на вывод),
    это защищает от повторного списания при повторных вызовах / ретраях.

    Возвращает данные перевода при успехе.
    Бросает CryptoPayError при любой ошибке (недостаточно средств на балансе приложения,
    юзер не найден в @CryptoBot, сетевая ошибка и т.п.) — вызывающий код должен
    откатывать резерв средств у пользователя при этой ошибке.
    """
    if not CRYPTO_PAY_TOKEN:
        raise CryptoPayError("CRYPTO_PAY_TOKEN не задан в переменных окружения")

    payload = {
        "user_id": user_id,
        "asset": CRYPTO_ASSET,
        "amount": f"{amount:.2f}",
        "spend_id": spend_id,
    }
    # comment не отправляем

    headers = {"Crypto-Pay-API-Token": CRYPTO_PAY_TOKEN}

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(f"{CRYPTO_PAY_API_URL}/transfer", json=payload, headers=headers)
            data = resp.json()
    except (httpx.HTTPError, ValueError) as e:
        raise CryptoPayError(f"Сетевая ошибка Crypto Pay: {e}")

    if not data.get("ok"):
        error = data.get("error", {}) or {}
        raise CryptoPayError(f"{error.get('code', '?')}: {error.get('name', 'unknown error')}")

    return data["result"]


async def create_invoice(amount: float, description: str = "Пополнение баланса приложения") -> dict:
    """
    Создаёт счёт (invoice) в Crypto Pay на сумму amount в CRYPTO_ASSET.
    После того как счёт будет оплачен (в том числе тобой самим со своего
    личного баланса в @CryptoBot), сумма зачисляется на баланс приложения.
    Возвращает данные счёта, среди которых result['pay_url'] / result['bot_invoice_url']
    — ссылка, которую нужно открыть и оплатить.
    """
    if not CRYPTO_PAY_TOKEN:
        raise CryptoPayError("CRYPTO_PAY_TOKEN не задан в переменных окружения")

    payload = {
        "asset": CRYPTO_ASSET,
        "amount": f"{amount:.2f}",
        "description": description[:1024],
    }

    headers = {"Crypto-Pay-API-Token": CRYPTO_PAY_TOKEN}

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(f"{CRYPTO_PAY_API_URL}/createInvoice", json=payload, headers=headers)
            data = resp.json()
    except (httpx.HTTPError, ValueError) as e:
        raise CryptoPayError(f"Сетевая ошибка Crypto Pay: {e}")

    if not data.get("ok"):
        error = data.get("error", {}) or {}
        raise CryptoPayError(f"{error.get('code', '?')}: {error.get('name', 'unknown error')}")

    return data["result"]


async def get_app_balance() -> dict:
    """
    Возвращает баланс приложения в Crypto Pay по всем валютам.
    Можно использовать для мониторинга / алертов о низком балансе.
    """
    if not CRYPTO_PAY_TOKEN:
        raise CryptoPayError("CRYPTO_PAY_TOKEN не задан в переменных окружения")

    headers = {"Crypto-Pay-API-Token": CRYPTO_PAY_TOKEN}

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(f"{CRYPTO_PAY_API_URL}/getBalance", headers=headers)
            data = resp.json()
    except (httpx.HTTPError, ValueError) as e:
        raise CryptoPayError(f"Сетевая ошибка Crypto Pay: {e}")

    if not data.get("ok"):
        error = data.get("error", {}) or {}
        raise CryptoPayError(f"{error.get('code', '?')}: {error.get('name', 'unknown error')}")

    return data["result"]
