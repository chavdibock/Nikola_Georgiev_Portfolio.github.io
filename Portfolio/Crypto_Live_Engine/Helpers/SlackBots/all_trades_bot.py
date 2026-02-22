import slack_sdk
from slack_sdk.errors import SlackApiError
from Config.get_settings import config_slack_dict

# Fetch the Slack Bot Token from the environment
slack_token = config_slack_dict['SLACK_TOKEN']
# Initialize the Slack client
client = slack_sdk.WebClient(token=slack_token)

channel_id = config_slack_dict['SLACK_ALL_TRADES_CHANNEL']


def send_trade_message(symbol, price, side):
    """
    Sends a message to Slack with detailed information about a trade order.
    """
    try:
        message = f"Trade Executed* \n- Ticker: `{symbol}` \n- Price: `{price}` \n- Side: `{side}`"

        # Post the message to Slack
        response = client.chat_postMessage(
            channel=channel_id,
            text=message
        )

        message_ts = response["ts"]
        print(f"Trade message sent: {message_ts}")
    except SlackApiError as e:
        print(f"Error posting message: {e.response['error']}")

def send_closed_position_message(symbol, price):
    """
    Sends a message to Slack with detailed information about a trade order.
    """
    try:
        message = f"Position Closed* \n- Ticker: `{symbol}` \n- Price: `{price}`"

        # Post the message to Slack
        response = client.chat_postMessage(
            channel=channel_id,
            text=message
        )

        message_ts = response["ts"]
        print(f"Trade message sent: {message_ts}")
        return message_ts
    except SlackApiError as e:
        print(f"Error posting message: {e.response['error']}")
        return None