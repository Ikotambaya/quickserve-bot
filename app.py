from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import os

app = Flask(__name__)

# In-memory session store
user_sessions = {}
user_orders = {}

# Load environment variables
PAYSTACK_PAYMENT_URL = os.environ.get("PAYSTACK_PAYMENT_URL", "#")

# Sample available items
AVAILABLE_ITEMS = ['Pizza', 'Burger', 'Soda', 'Fries']


@app.route('/whatsapp', methods=['POST'])
def whatsapp_webhook():
    incoming_msg = request.values.get('Body', '').strip().lower()
    from_number = request.values.get('From', '')
    resp = MessagingResponse()
    msg = resp.message()

    state = user_sessions.get(from_number, 'start')

    if state == 'start':
        reply = (
            "Welcome to QuickServe! What would you like to do?\n"
            "1. Make Order\n"
            "2. Dispatch Rider\n"
            "Please reply with 1 or 2."
        )
        msg.body(reply)
        user_sessions[from_number] = 'menu'

    elif state == 'menu':
        if incoming_msg == '1':
            items_list = "\n".join(f"{idx+1}. {item}" for idx, item in enumerate(AVAILABLE_ITEMS))
            reply = (
                "Please select items by sending the item numbers separated by commas.\n"
                f"Available items:\n{items_list}\n\nExample: 1,3 for Pizza and Soda"
            )
            msg.body(reply)
            user_sessions[from_number] = 'ordering'

        elif incoming_msg == '2':
            msg.body("Dispatch rider feature coming soon! Reply with 'menu' to go back.")
            user_sessions[from_number] = 'menu'

        elif incoming_msg == 'menu':
            reply = (
                "Main Menu:\n"
                "1. Make Order\n"
                "2. Dispatch Rider\n"
                "Please reply with 1 or 2."
            )
            msg.body(reply)

        else:
            msg.body("Invalid input. Please reply with 1 or 2.")

    elif state == 'ordering':
        try:
            selections = [int(x.strip()) for x in incoming_msg.split(',')]
            selected_items = [AVAILABLE_ITEMS[i-1] for i in selections if 1 <= i <= len(AVAILABLE_ITEMS)]

            if not selected_items:
                msg.body("No valid items selected. Please try again.")
            else:
                user_orders[from_number] = selected_items
                items_str = ', '.join(selected_items)
                reply = (
                    f"You selected: {items_str}\n"
                    "Type 'pay' to proceed to payment or 'cancel' to cancel the order."
                )
                msg.body(reply)
                user_sessions[from_number] = 'payment'

        except Exception:
            msg.body("Invalid input format. Please send numbers separated by commas, e.g. 1,2")

    elif state == 'payment':
        if incoming_msg == 'pay':
            order_items = user_orders.get(from_number, [])
            items_str = ', '.join(order_items)
            reply = (
                f"Great! Please complete your payment for: {items_str}\n"
                f"Click here to pay: {PAYSTACK_PAYMENT_URL}\n\n"
                "After completing payment, reply with 'done'."
            )
            msg.body(reply)
            user_sessions[from_number] = 'awaiting_payment_confirmation'

        elif incoming_msg == 'cancel':
            user_orders.pop(from_number, None)
            user_sessions[from_number] = 'start'
            msg.body("Your order has been cancelled. Reply anything to start again.")

        else:
            msg.body("Please type 'pay' to proceed to payment or 'cancel' to cancel the order.")

    elif state == 'awaiting_payment_confirmation':
        if incoming_msg == 'done':
            msg.body("Thank you! Your payment is confirmed. Your order will be delivered in approx 30 minutes.")
            user_sessions.pop(from_number, None)
            user_orders.pop(from_number, None)
        else:
            msg.body("Please reply 'done' after you complete the payment.")

    else:
        msg.body("Sorry, I didn't understand that. Reply 'menu' to see options.")
        user_sessions[from_number] = 'start'

    return str(resp)


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
