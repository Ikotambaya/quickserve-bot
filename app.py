import os
import json
from flask import Flask, request, jsonify, render_template, redirect, url_for
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
from dotenv import load_dotenv
from payment import create_paystack_payment, verify_paystack_payment
from ai_helper import get_ai_recommendation
from utils import estimate_eta_from_address
import sqlite3
import uuid

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")

# Twilio client setup
twilio_client = Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")

# DB setup
DB_PATH = "database.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id TEXT PRIMARY KEY,
        customer_number TEXT,
        message TEXT,
        ai_suggestion TEXT,
        payment_ref TEXT,
        payment_verified INTEGER DEFAULT 0,
        delivery_method TEXT,
        address TEXT,
        eta TEXT,
        status TEXT DEFAULT 'Pending'
    )
    """)
    conn.commit()
    conn.close()

init_db()

# In-memory session store (for simplicity)
sessions = {}

@app.route("/whatsapp", methods=["POST"])
def whatsapp_webhook():
    sender = request.values.get("From", "")
    body = request.values.get("Body", "").strip().lower()
    resp = MessagingResponse()
    msg = resp.message()

    # Initialize session if not exists
    if sender not in sessions:
        sessions[sender] = {"stage": "greet"}
    
    session = sessions[sender]

    if session["stage"] == "greet":
        msg.body("👋 Hello! Welcome to QuickServe. What kind of food are you craving today? Tell me a little about your taste or mood!")
        session["stage"] = "waiting_for_preference"
        return str(resp)

    elif session["stage"] == "waiting_for_preference":
        # Get AI recommendation for menu
        recommendation = get_ai_recommendation(body)
        session["ai_suggestion"] = recommendation
        session["stage"] = "awaiting_payment"
        
        # Create a unique order ID and payment link
        order_id = str(uuid.uuid4())
        payment_url = create_paystack_payment(order_id, 1500)  # Assuming flat NGN 1500 price; adjust as needed
        
        # Save partial order to DB (not verified yet)
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT INTO orders (id, customer_number, message, ai_suggestion) VALUES (?, ?, ?, ?)", 
                  (order_id, sender, body, recommendation))
        conn.commit()
        conn.close()

        msg.body(f"Here's what I recommend:\n\n{recommendation}\n\nTo confirm your order, please complete payment of ₦1500 here:\n{payment_url}\n\nReply 'PAID' once you complete payment.")
        session["order_id"] = order_id
        return str(resp)

    elif session["stage"] == "awaiting_payment":
        if "paid" in body:
            order_id = session.get("order_id")
            if order_id and verify_paystack_payment(order_id):
                # Mark payment verified in DB
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute("UPDATE orders SET payment_verified=1 WHERE id=?", (order_id,))
                conn.commit()
                conn.close()

                msg.body("Payment confirmed! Would you like to pick up your order or have it delivered? Reply with 'pickup' or 'delivery'.")
                session["stage"] = "awaiting_delivery_method"
                return str(resp)
            else:
                msg.body("Payment not confirmed yet. Please complete your payment at the link sent earlier, then reply 'PAID'.")
                return str(resp)
        else:
            msg.body("Please reply with 'PAID' after completing payment.")
            return str(resp)

    elif session["stage"] == "awaiting_delivery_method":
        if body in ["pickup", "delivery"]:
            order_id = session.get("order_id")
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()

            if body == "pickup":
                c.execute("UPDATE orders SET delivery_method=?, status='Ready for Pickup' WHERE id=?", ("pickup", order_id))
                conn.commit()
                conn.close()
                msg.body("Thanks! Your order will be ready for pickup in 30 minutes. We look forward to seeing you!")
                sessions.pop(sender)
                return str(resp)

            elif body == "delivery":
                c.execute("UPDATE orders SET delivery_method=? WHERE id=?", ("delivery", order_id))
                conn.commit()
                conn.close()
                msg.body("Please provide your delivery address.")
                session["stage"] = "awaiting_address"
                return str(resp)
        else:
            msg.body("Reply with 'pickup' or 'delivery'.")
            return str(resp)

    elif session["stage"] == "awaiting_address":
        order_id = session.get("order_id")
        eta = estimate_eta_from_address(body)
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("UPDATE orders SET address=?, eta=?, status='Out for Delivery' WHERE id=?", (body, eta, order_id))
        conn.commit()
        conn.close()

        msg.body(f"Thanks for your address! Your food will arrive in approximately {eta}. Enjoy your meal! 🍽️")
        sessions.pop(sender)
        return str(resp)

    else:
        msg.body("Sorry, I didn't understand that. Please start again.")
        sessions.pop(sender, None)
        return str(resp)

@app.route("/paystack/webhook", methods=["POST"])
def paystack_webhook():
    # Paystack webhook to update payment verification status (optional)
    payload = request.get_json()
    event = payload.get("event")
    data = payload.get("data", {})
    order_id = data.get("metadata", {}).get("order_id")

    if event == "charge.success" and order_id:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("UPDATE orders SET payment_verified=1 WHERE id=?", (order_id,))
        conn.commit()
        conn.close()
    return "OK", 200

@app.route("/admin")
def admin_dashboard():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, customer_number, message, ai_suggestion, payment_verified, delivery_method, address, eta, status FROM orders ORDER BY rowid DESC")
    orders = c.fetchall()
    conn.close()
    return render_template("admin.html", orders=orders)

if __name__ == "__main__":
    app.run(port=8080, debug=True)
