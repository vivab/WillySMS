"""
Adapter for your own/authorized SMS service.
This module intentionally does not intercept third-party OTP messages.
"""
def send_sms(phone: str, service_name: str) -> bool:
    # Integrate your own authorized SMS provider here.
    return True
