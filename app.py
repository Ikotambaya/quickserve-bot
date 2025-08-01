from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

# Simple in-memory session store (phone -> state)
user_sessions = {}
# Store orders per user
user_orders = {}

# Your Paystack payment link (replace this with your real Paystack payment URL)
PAYSTACK_PAYMENT_URL = "https://paystack.com/pay/your-payment-link"

# Sample available items
AVAILABLE_ITEMS = ['Pizza', 'Burger', 'Soda', 'Fries']

@app.route('/whatsapp', methods=['POST'])
def whatsapp_webhook():
    incoming_msg = request.values.get('Body', '').strip().lower()
    from_number = request.values.get('From', '')
    resp = MessagingResponse()
    msg = resp.message()

    # Get current user state or set default
    state = user_sessions.get(from_number, 'start')

    if state == 'start':
        # Welcome and main menu
        reply = ("Welcome to QuickServe! What would you like to do?\n"
                 "1. Make Order\n"
                 "2. Dispatch Rider\n"
                 "Please reply with 1 or 2.")
        msg.body(reply)
        user_sessions[from_number] = 'menu'

    elif state == 'menu':
        if incoming_msg == '1':
            # Show available items for order
            items_list = "\n".join(f"{idx+1}. {item}" for idx, item in enumerate(AVAILABLE_ITEMS))
            reply = ("Please select items by sending the item numbers separated by commas.\n"
                     f"Available items:\n{items_list}\n\nExample: 1,3 for Pizza and Soda")
            msg.body(reply)
            user_sessions[from_number] = 'ordering'

        elif incoming_msg == '2':
            reply = "Dispatch rider feature coming soon! Reply with 'menu' to go back."
            msg.body(reply)
            # Keep user in menu state or reset to start?
            user_sessions[from_number] = 'menu'

        elif incoming_msg == 'menu':
            # Repeat menu
            reply = ("Main Menu:\n1. Make Order\n2. Dispatch Rider\nPlease reply with 1 or 2.")
            msg.body(reply)

        else:
            msg.body("Invalid input. Please reply with 1 or 2.")

    elif state == 'ordering':
        # Parse selected items from user input
        try:
            selections = [int(x.strip()) for x in incoming_msg.split(',')]
            selected_items = [AVAILABLE_ITEMS[i-1] for i in selections if 1 <= i <= len(AVAILABLE_ITEMS)]
            if not selected_items:
                msg.body("No valid items selected. Please try again.")
            else:
                user_orders[from_number] = selected_items
                items_str = ', '.join(selected_items)
                reply = (f"You selected: {items_str}\n"
                         "Type 'pay' to proceed to payment or 'cancel' to cancel the order.")
                msg.body(reply)
                user_sessions[from_number] = 'payment'
        except Exception:
            msg.body("Invalid input format. Please send numbers separated by commas, e.g. 1,2")

    elif state == 'payment':
        if incoming_msg == 'pay':
            # Send Paystack payment link
            order_items = user_orders.get(from_number, [])
            items_str = ', '.join(order_items)
            reply = (f"Great! Please complete your payment for: {items_str}\n"
                     f"Click here to pay: {PAYSTACK_PAYMENT_URL}\n\n"
                     "After completing payment, reply with 'done'.")
            msg.body(reply)
            user_sessions[from_number] = 'awaiting_payment_confirmation'

        elif incoming_msg == 'cancel':
            user_orders.pop(from_number, None)
            user_sessions[from_number] = 'start'
            msg.body("Your order has been cancelled. Reply any message to start over.")

        else:
            msg.body("Please type 'pay' to proceed to payment or 'cancel' to cancel the order.")

    elif state == 'awaiting_payment_confirmation':
        if incoming_msg == 'done':
            msg.body("Thank you! Your payment is confirmed.\nYour order will be delivered in approx 30 minutes.")
            # Clear session and order data
            user_sessions.pop(from_number, None)
            user_orders.pop(from_number, None)
        else:
            msg.body("Please reply 'done' after you complete the payment.")

    else:
        # Catch-all fallback
        msg.body("Sorry, I didn't understand that. Reply 'menu' to see options.")
        user_sessions[from_number] = 'start'

    return str(resp)


if __name__ == '__main__':
    app.run(port=8080, debug=True)
