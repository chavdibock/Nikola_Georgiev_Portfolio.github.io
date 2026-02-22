import slack_sdk
from slack_sdk.errors import SlackApiError
from Config.get_settings import config_slack_dict

# Fetch the Slack Bot Token and Channel ID from the configuration
slack_token = config_slack_dict.get('SLACK_TOKEN')
channel_id = config_slack_dict.get('SLACK_ERROR_CHANNEL')

# Initialize the Slack client
client = slack_sdk.WebClient(token=slack_token)

def send_error_message(error):
    """
    Sends a message to Slack with detailed information about a trade order error.
    Args:
        error (str): The error message to be sent.
    Returns:
        bool: True if the message is successfully sent, False otherwise.
    """
    try:
        # Post the error message to Slack
        response = client.chat_postMessage(
            channel=channel_id,
            text=f":warning: *Trade Order Error*\n```{error}```"
        )
        # Log the success
        print(f"Message sent successfully: {response['ts']}")
        return True
    except SlackApiError as e:
        # Log the error response from Slack
        error_msg = e.response.get('error', 'Unknown error')
        print(f"Error posting message to Slack: {error_msg}")
        return False
