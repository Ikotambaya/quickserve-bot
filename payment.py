import os
import requests
from dotenv import load_dotenv

load_dotenv()

PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY")
PAYSTACK_PUBLIC_KEY = os.getenv("PAYSTACK_PUBLIC_KEY")
PAYSTACK_BASE_URL = "https://api.paystack.co"

def create_paystack_payment(order_id, amount_ngn):
    """Create a Paystack payment link."""
    url = f"{PAYSTACK_BASE_URL}/transaction/initialize"
    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json",
    }
    data = {
        "email": "customer@example.com",  # Placeholder email; real app can ask for email
        "amount": amount_ngn * 100,  # Paystack expects amount in kobo
        "metadata": {"order_id": order_id},
        "callback_url": "https://your-ngrok-url/paystack/callback",  # update this after deploy
    }
    response = requests.post(url, headers=headers, json=data)
    res_json = response.json()
    if res_json.get("status") == True:
        return res_json["data"]["authorization_url"]
    else:
        return None

def verify_paystack_payment(order_id):
    """Verify payment by checking Paystack transaction list."""
    url = f"{PAYSTACK_BASE_URL}/transaction/verify/{order_id}"
    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
    }
    response = requests.get(url, headers=headers)
    res_json = response.json()
    if res_json.get("status") == True and res_json["data"]["status"] == "success":
        return True
    return False
