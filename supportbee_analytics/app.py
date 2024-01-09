import json
import datetime
import requests
import html
from dotenv import load_dotenv
import os

load_dotenv()

def get_tickets(support_bee_token, until):
    supportbee_url = "https://hasgeek.supportbee.com/tickets"
    supportbee_headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    supportbee_params1 = {
        "auth_token": support_bee_token,
        "until": until,
        "replies": "false",
        "total_only": "true",
    }
    supportbee_params2 = {
        "auth_token": support_bee_token,
        "replies": "false",
    }

    try:
        supportbee_response1 = requests.get(
            supportbee_url, headers=supportbee_headers, params=supportbee_params1
        )
        supportbee_response2 = requests.get(
            supportbee_url, headers=supportbee_headers, params=supportbee_params2
        )

        ticket_open_4_hours = json.loads(supportbee_response1.content)
        total_tickets_open = json.loads(supportbee_response2.content)

        return ticket_open_4_hours, total_tickets_open
    except requests.RequestException as e:
        print(f"Request failed: {e}")
        return None, None


def format_message(total_tickets_open, ticket_open_4_hours):
    formatted_data = "\n".join(
        [
            f"<b>{obj['requester']['first_name']}</b>: <a href='https://hasgeek.supportbee.com/tickets/{obj['id']}'>{html.escape(obj['subject'])}</a> <i>({obj['current_user_assignee']['user']['first_name'] if obj['current_user_assignee'] else 'unassigned'})</i>\n"
            for obj in total_tickets_open["tickets"]
        ]
    )

    message = f"""
    🎟️ Total unanswered tickets: <b><a href='https://hasgeek.supportbee.com/tickets'>{total_tickets_open['total']}🎟️</a></b>
    🚨 Tickets unanswered for more than 4 hours: <b><a href='https://hasgeek.supportbee.com/tickets'>{ticket_open_4_hours['total']}🚨</a></b>

    {formatted_data}
    """
    return message


def send_telegram_message(message, telegram_chat_id, bot_url):
    bot_payload = {
        "chat_id": telegram_chat_id,
        "text": str(message),
        "parse_mode": "html",
    }

    try:
        response = requests.post(bot_url, json=bot_payload)
        return response.status_code, response.text
    except requests.RequestException as e:
        print(f"Request failed: {e}")
        return None, None


def lambda_handler(event, context):
    SUPPORT_BEE_TOKEN = os.getenv("SUPPORTBEE_AUTH_TOKEN")
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
    bot_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    until = (datetime.datetime.now() - datetime.timedelta(hours=4)).strftime(
        "%Y-%m-%dT%H:%M:%S"
    )

    ticket_open_4_hours, total_tickets_open = get_tickets(SUPPORT_BEE_TOKEN, until)

    if ticket_open_4_hours is None or total_tickets_open is None:
        return {"statusCode": 500, "body": "Error fetching data"}

    message = format_message(total_tickets_open, ticket_open_4_hours)

    status_code, response_text = send_telegram_message(
        message, TELEGRAM_CHAT_ID, bot_url
    )

    if status_code == 200:
        print("Message sent successfully")
        return {"statusCode": 200, "body": "Message sent successfully"}
    else:
        print("Error:", response_text)
        return {"statusCode": status_code, "body": "Error: " + response_text}
