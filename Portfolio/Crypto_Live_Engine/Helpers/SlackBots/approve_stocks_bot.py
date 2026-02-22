import time
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from Config.get_settings import config_slack_dict

token = config_slack_dict['SLACK_TOKEN']
channel_id = config_slack_dict['SLACK_APPROVE_STOCKS_CHANEL']
client = WebClient(token=token)


def post_message_with_reactions(stock_symbol, number, total):
    """
    Sends a message to Slack requesting approval and adds reaction options.
    """
    try:
        tradingview_url = f"https://www.tradingview.com/symbols/{stock_symbol}/"

        # Post the message
        response = client.chat_postMessage(
            channel=channel_id,
            text=f"Stock wtih number {number} / {total} \n\n"
                 f"Should I start trading {stock_symbol}? React with 👍 to approve or 👎 to decline.\n\n"
                 f"Here is the TradingView chart for {stock_symbol}: {tradingview_url}"
        )
        message_ts = response["ts"]

        # Optionally add initial reactions
        client.reactions_add(channel=channel_id, name="thumbsup", timestamp=message_ts)
        client.reactions_add(channel=channel_id, name="thumbsdown", timestamp=message_ts)
        client.reactions_add(channel=channel_id, name="point_up", timestamp=message_ts)
        print(f"Message sent: {message_ts}")
        return message_ts
    except SlackApiError as e:
        print(f"Error posting message or adding reactions: {e.response['error']}")
        return None


def await_reaction(message_ts, timeout=600):
    """
    Waits for a reaction (`👍` or `👎`) on the message.
    :param message_ts: The timestamp of the message to monitor reactions on.
    :param timeout: The maximum time to wait for a reaction, in seconds.
    :return: True for approval, False for decline, or None for timeout.
    """
    print(f"Waiting for reactions on message: {message_ts}")
    start_time = time.time()
    res_dict = {
        "trade": 0,
        "reset": 0
    }
    while time.time() - start_time < timeout:
        try:

            # Get reactions on the message
            response = client.reactions_get(channel=channel_id, timestamp=message_ts)
            reactions = response["message"].get("reactions", [])

            # Debug log: Show current reactions
            print(f"Reactions: {reactions}")

            for reaction in reactions:
                # Look for thumbs-up and thumbs-down reactions
                if reaction["name"] == "+1":
                    if reaction["count"] > 1:  # count > 1 indicates a valid reaction
                        res_dict["trade"] = 1  # Approved
                        return res_dict
                elif reaction["name"] == "-1":
                    if reaction["count"] > 1:  # count > 1 indicates a valid reaction
                        res_dict["trade"] = -1  # Declined
                        return res_dict
                elif reaction["name"] == 'point_up':
                    if reaction["count"] > 1:
                        res_dict["reset"] = 1
                        return res_dict
            time.sleep(5)  # Wait before checking again
        except SlackApiError as e:
            print(f"Error fetching reactions: {e.response['error']}")
            time.sleep(5)



async def send_stock_for_approval(stock_symbol, number, total):
    message_ts = post_message_with_reactions(stock_symbol, number, total)

    if message_ts:
        print("Waiting for a reaction...")
        decision = await_reaction(message_ts)
        print("Resived Reaction")
        print(decision)
        if decision["trade"] == 1:
            print(f"Approved! Starting analysis for {stock_symbol}.")
            return "True"
            # Place your analysis logic here
        elif decision["trade"] == -1:
            print(f"Declined. Stopping analysis for {stock_symbol}.")
            return "False"
        elif decision["reset"] == 1:
            print(f"Resetting the stock approval process.")
            return "Resetting"
        elif decision["reset"] == 0 and decision["trade"] == 0:
            print("Timeout hit. No decision made. Trading starts")
            # Send timeout message to Slack
            try:
                client.chat_postMessage(
                    channel=channel_id,
                    text=f"Timeout hit for {stock_symbol}. It will be traded."
                )
            except SlackApiError as e:
                print(f"Error sending timeout message: {e.response['error']}")
            return "True"
