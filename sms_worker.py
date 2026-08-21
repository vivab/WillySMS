"""
Adapter for your own / authorized SMS provider.
This module intentionally does not intercept third-party OTP messages.
"""

async def on_request_taken(phone: str, request_id: int, service_name: str):
    pass


async def on_request_completed(phone: str, request_id: int, approved: bool):
    pass
