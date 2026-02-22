from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import time

from datetime import datetime, timedelta


def get_next_weekday(start_date=None):
    if start_date is None:
        start_date = datetime.today()
    next_day = start_date + timedelta(days=1)
    while next_day.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
        next_day += timedelta(days=1)
    return next_day


def is_same_trading_week(date):
    today = datetime.today()

    # Get Sunday of the current week
    start_of_week = today - timedelta(days=today.weekday() + 1 if today.weekday() < 6 else 0)
    # Saturday is 6 days after Sunday
    end_of_week = start_of_week + timedelta(days=6)

    return start_of_week.date() <= date.date() <= end_of_week.date()


def configure_driver():
    """Initialize and return the WebDriver with desired options."""
    chrome_options = Options()

    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument("--enable-javascript")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument('--ignore-certificate-errors')
    chrome_options.add_argument('--log-level=3')

    # Uncomment to enable headless mode (if GUI is not required)
    # chrome_options.add_argument('--headless')

    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)


def get_stocks_with_earnings():
    url = 'https://www.nasdaq.com/market-activity/earnings'
    web_driver = configure_driver()
    web_driver.get(url)
    time.sleep(1)
    try:
        advanced_btn = web_driver.find_element(By.ID, 'onetrust-accept-btn-handler')
        advanced_btn.click()
        time.sleep(2)
    except Exception as e:
        print("Error: ", e)

    try:
        next_trading_day = get_next_weekday()
        year = str(next_trading_day.year)
        month = f"{next_trading_day.month:02d}"
        day = f"{next_trading_day.day:02d}"
        print(year, month, day)
        print(is_same_trading_week(next_trading_day))
        if not is_same_trading_week(next_trading_day):
            calendar_btn = web_driver.find_element(By.XPATH,
                                                   '/html/body/div[2]/div/main/div[2]/article/div/div[1]/div[2]/div/div[2]/div/div/div[1]/div/div/div[3]/div[2]/button')
            calendar_btn.click()

            time.sleep(0.5)

            el_month = web_driver.find_element(By.XPATH,
                                               '/html/body/div[2]/div/main/div[2]/article/div/div[1]/div[2]/div/div[2]/div/div/div[1]/div/div/div[3]/div[2]/div/div[2]/h5/span')

            if el_month.text == next_trading_day.strftime("%B").upper():
                next_month_btn = web_driver.find_element(By.XPATH,
                                                         "/html/body/div[2]/div/main/div[2]/article/div/div[1]/div[2]/div/div[2]/div/div/div[1]/div/div/div[3]/div[2]/div/div[2]/button[3]")

                next_month_btn.click()
                time.sleep(5)

                # Wait until the correct month and year are shown (optional — can include calendar navigation here)
                # Build selector for the date cell
                selector = f'a.ui-state-default[data-date="{day}"]'

                try:
                    date_button = web_driver.find_element(By.CSS_SELECTOR, selector)
                    date_button.click()
                    print(f"Clicked on date: {next_trading_day.strftime('%A, %B %d, %Y')}")
                except Exception as e:
                    print(f"Could not click date {day}: {e}")

            else:
                selector = f'a.ui-state-default[data-date="{day}"]'
                element = web_driver.find_element(By.CSS_SELECTOR, selector)
                element.click()

        selector = f'button.jupiter22-time-belt__item[data-year="{year}"][data-month="{month}"][data-day="{day}"]'

        button = web_driver.find_element(By.CSS_SELECTOR, selector)
        button.click()
        time.sleep(1)

    except Exception as e:
        print("Error: ", e)
    try:

        drop_down = web_driver.find_element(By.ID, 'recordsPerpage')
        drop_down.click()
        list_items = web_driver.find_elements(By.XPATH,
                                              "/html/body/div[2]/div/main/div[2]/article/div/div[1]/div[2]/div/div[2]/div/div/div[1]/div/div/div[6]/div/div[1]/div/ul")

        number = web_driver.find_elements(By.CSS_SELECTOR, "li.list-item")

        # Click the last item
        if number:
            number[-1].click()
        time.sleep(2)
    except Exception as e:
        print("Error clicking the max rows", e)

    shadow_host = web_driver.find_element(By.XPATH,
                                          '/html/body/div[2]/div/main/div[2]/article/div/div[1]/div[2]/div/div[2]/div/div/div[1]/div/div/div[5]/nsdq-table-sort')

    shadow_root = web_driver.execute_script("return arguments[0].shadowRoot", shadow_host)

    # Get all table rows inside the shadow root
    rows = shadow_root.find_elements(By.CSS_SELECTOR, 'div[part="table-row"]')

    symbols = []
    for row in rows:
        try:
            cells = row.find_elements(By.CSS_SELECTOR, 'div.table-cell')
            if len(cells) > 1:
                symbol_element = cells[1].find_element(By.TAG_NAME, 'a')
                symbols.append(symbol_element.text.strip())
        except Exception as e:
            print(f"Skipping a row: {e}")

    # Print all extracted symbols

    return symbols


if __name__ == "__main__":
    stocks = get_stocks_with_earnings()

    print(stocks)
