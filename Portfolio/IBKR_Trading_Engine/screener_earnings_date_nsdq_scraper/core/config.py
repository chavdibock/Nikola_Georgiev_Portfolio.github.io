import logging

from dotenv import load_dotenv, dotenv_values
import os
import logging

# loading variables from .env file
load_dotenv()

logging.basicConfig(filename="newfile.log",
                    format='%(asctime)s %(message)s',
                    filemode='w')


class Settings:
    PERIOD: str = os.getenv("PERIOD")
    BARS_SIZE: str = os.getenv("BARS_SIZE")
    CALC_VWAP_WINDOW: int = os.getenv("CALC_VWAP_WINDOW")
    MOVING_AVG_WINDOW: str = os.getenv("MOVING_AVG_WINDOW")
    MACD_LEN: int = int(os.getenv("MACD_LEN"))
    MACD_FAST: int = int(os.getenv("MACD_FAST"))
    MACD_SLOW: int = int(os.getenv("MACD_SLOW"))
    CALC_ST_LOSS: int = os.getenv("CALC_ST_LOSS")
    SCR_ID: str = f"{PERIOD}_{BARS_SIZE}_{CALC_VWAP_WINDOW}_{MOVING_AVG_WINDOW}_{CALC_ST_LOSS}_{MACD_LEN}_{MACD_FAST}_{MACD_SLOW}"
    user: str = os.getenv("PARTNER")
    trading_env: str = os.getenv("TRADING_ENV")

    env: str = os.getenv("ENV")

    db_env: str = os.getenv("DB_ENV")

    db_host_env: str = os.getenv("DB_HOST")
    if env == "LOCAL":
        IBKR_BASE: str = os.getenv("IBKR_CLIENT_LOCAL")
    elif env == "DOCKER":
        IBKR_BASE: str = os.getenv("IBKR_CLIENT_DOCKER")
    elif env == "CLOUD":
        IBKR_BASE: str = os.getenv("IBKR_CLIENT_CLOUD")

    DB_CONNECTION: str = os.getenv("DB_CONNECTION")

    DB_PORT: int = os.getenv("DB_PORT")

    if db_host_env == "LOCAL":
        DB_HOST: str = os.getenv("DB_HOST_LOCAL")
        DB_USERNAME: str = os.getenv("DB_USERNAME_LOCAL")
        DB_PASSWORD: str = os.getenv("DB_PASSWORD_LOCAL")
        DB_DATABASE: str = os.getenv("DB_DATABASE_LOCAL")

    else:
        DB_HOST: str = os.getenv("DB_HOST_CLOUD")
        DB_USERNAME: str = os.getenv("DB_USERNAME_CLOUD")
        DB_PASSWORD: str = os.getenv("DB_PASSWORD_CLOUD")

        if db_env == "PROD":
            DB_DATABASE: str = os.getenv("DB_DATABASE")
        else:
            DB_DATABASE: str = os.getenv("DB_DATABASE_DEV")

    DATABASE_URL = f"{DB_CONNECTION}://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_DATABASE}"
    print(DATABASE_URL)

    logger = logging.getLogger()
    logger.info(DATABASE_URL)


settings = Settings()
