import datetime
import os
import time

import requests
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from twilio.rest import Client
from webdriver_manager.chrome import ChromeDriverManager

# loading variables from .env file
load_dotenv()


class Settings:
    user: str = os.getenv("PARTNER")
    trading_env: str = os.getenv("TRADING_ENV")

    if user == "MISHO":
        ibkr_user: str = os.getenv("IBKR_USERNAME_MISHO")
        ibkr_paper_user: str = os.getenv("IBKR_PAPER_USER_MISHO")
        ibkr_pass: str = os.getenv("IBKR_PASS_MISHO")
        twilio_sid: str = os.getenv("ACCOUNT_SID_MISHO")
        twilio_token: str = os.getenv("AUTH_TOKEN_MISHO")
        twilio_phone: str = os.getenv("TWILIO_PHONE_NUMBER_MISHO")
    else:
        ibkr_user: str = os.getenv("IBKR_USERNAME_NIKOLA")
        ibkr_paper_user: str = os.getenv("IBKR_PAPER_USER_NIKOLA")
        ibkr_pass: str = os.getenv("IBKR_PASS_NIKOLA")
        twilio_sid: str = os.getenv("ACCOUNT_SID_NIKOLA")
        twilio_token: str = os.getenv("AUTH_TOKEN_NIKOLA")
        twilio_phone: str = os.getenv("TWILIO_PHONE_NUMBER_NIKOLA")

    ibkr_base_url: str = "http://localhost:5000"


settings = Settings()

twilio_client = Client(settings.twilio_sid, settings.twilio_token)


def fetch_messages():
    try:
        messages = twilio_client.messages.list(
            to=settings.twilio_phone,  # Filter messages sent to your Twilio number
            limit=1
        )
        for message in messages:
            print(f"Body: {message.body}")
        return messages[-1].body.split(':')[-1]
    except Exception as e:
        print("################## ERROR WHILE FETCHING TWILIO MESSAGES ##################")
        print(e)


def disable_twilio_webhook():
    """Disable Twilio SMS URL to stop receiving further messages."""
    try:
        incoming_phone_numbers = twilio_client.incoming_phone_numbers.list()
        for number in incoming_phone_numbers:
            if number.phone_number == settings.twilio_phone:
                number.update(sms_url="")
                print(f"Disabled webhook for Twilio number: {number.phone_number}")
                return
    except Exception as e:
        print("Failed to disable Twilio webhook:", e)


def reauth_api_endp():
    try:
        url = f'{settings.ibkr_base_url}/v1/api/iserver/reauthenticate'
        auth_req = requests.post(url=url, verify=False)
        time.sleep(5)
    except Exception as e:
        print("Error while re-authenticating: ", e)


def tickle():
    url = f'{settings.ibkr_base_url}/v1/api/tickle'
    auth_req = requests.post(url=url, verify=False)


def auth_checker():
    """Continuously checks authentication status and triggers re-authentication if needed."""

    url = f'{settings.ibkr_base_url}/v1/api/iserver/auth/status'
    time.sleep(5)  # Initial wait

    while True:
        try:
            # Fetch authentication status
            auth_req = requests.get(url=url, verify=False)
            if auth_req.text == "":
                print(auth_req.text)
                print("Authentication required, starting the authentication")
                authenticate()
            print(auth_req.json()["authenticated"])
            if auth_req.json()["authenticated"] is False:
                print(auth_req.text)
                print("Authentication required, starting the authentication")
                reauth_api_endp()
        except Exception as e:
            print(f"Error checking authentication: {e}")
        print("Waiting for the next  auth check")
        time.sleep(60)


def configure_driver():
    """Initialize and return the WebDriver with desired options."""
    chrome_options = Options()
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument("--enable-javascript")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument('--ignore-certificate-errors')
    chrome_options.add_argument('--log-level=3')

    # Uncomment to enable headless mode (if GUI is not required)
    # chrome_options.add_argument('--headless')

    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)


def wait_for_endpoint(timeout=60):
    start_time = time.time()
    res = "Timed Out for MFA"
    while time.time() - start_time < timeout:
        try:
            auth_req = requests.get(url=f'{settings.ibkr_base_url}/v1/api/iserver/auth/status', verify=False)
            if auth_req.status_code == 200 and auth_req.json().get("authenticated", False):
                res = "Authenticated Successfully"
                break

        except requests.RequestException as e:
            print(f"Request failed: {e}")

        time.sleep(1)  # Wait 1 second before retrying

    print(f"Finished waiting. {res}")


def wait_for_new_code(prev_mess, timeout=60):
    start_time = time.time()
    res = "Timed Out for MFA"
    while time.time() - start_time < timeout:
        try:
            cur_message = fetch_messages()
            if prev_mess != cur_message:
                res = "Code received Successfully"
                print(f"Finished waiting. {res}")
                return cur_message
        except requests.RequestException as e:
            print(f"Request failed: {e}")

        time.sleep(1)  # Wait 1 second before retrying

    print(f"Finished waiting. {res}")


def authenticate():
    """Main function to execute the script."""
    # Configure the WebDriver

    try:
        driver = configure_driver()
        print(f"Authenticating {settings.user} ON {datetime.datetime.now()}")
        while True:
            response = requests.get(settings.ibkr_base_url, verify=False)
            print("calling the ibkr-client")
            if response.status_code == 200:
                print("Exited with status code 200")
                break
            time.sleep(1)

        # Navigate to the URL
        prev_tw_code = fetch_messages()
        driver.get(settings.ibkr_base_url)
        if driver.page_source.__contains__('closeDetails":"Hide advanced"'):
            # print(driver.page_source)
            advanced_btn = driver.find_element(By.ID, 'details-button')
            advanced_btn.click()
            time.sleep(1)
            link = driver.find_element(By.ID, 'proceed-link')
            time.sleep(1)
            link.click()
            time.sleep(1)

        if driver.page_source.__contains__('xyz-field-username'):
            print("Filling the credentials")
            if settings.trading_env == "PROD":
                driver.find_element(by=By.ID, value="xyz-field-username").send_keys(settings.ibkr_user)
            else:
                driver.find_element(By.XPATH, "/html/body/section/div/div/div[2]/div[2]/form[2]/div[1]/div/div/label").click()
                driver.find_element(by=By.ID, value="xyz-field-username").send_keys(settings.ibkr_paper_user)

            driver.find_element(by=By.ID, value="xyz-field-password").send_keys(settings.ibkr_pass)
            driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
            time.sleep(2)
            print("Clicked the log in Btn")

        if settings.trading_env == "PAPER" and settings.user == "NIKOLA":
            new_code = wait_for_new_code(prev_mess=prev_tw_code, timeout=60)
            driver.find_element(By.XPATH,
                                '/html/body/section/div/div/div[2]/div[2]/div[4]/form/div[1]/input').send_keys(new_code)
            driver.find_element(By.XPATH, '/html/body/section/div/div/div[2]/div[2]/div[4]/form/div[3]/button').click()

        wait_for_endpoint(timeout=60)
        disable_twilio_webhook()
        driver.quit()
    except Exception as e:
        print("Error during login process:")
        print(e)


if __name__ == '__main__':
    auth_checker()
