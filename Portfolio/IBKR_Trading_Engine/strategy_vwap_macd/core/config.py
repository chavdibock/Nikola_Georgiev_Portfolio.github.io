from dotenv import load_dotenv, dotenv_values
import os
import logging

# loading variables from .env file
load_dotenv()

logging.basicConfig(filename="newfile.log",
                    format='%(asctime)s %(message)s',
                    filemode='w')


class Settings:
    logging.basicConfig(filename="newfile.log",
                        format='%(asctime)s %(message)s',
                        filemode='w')

    STOP_LOSS: float = float(os.getenv("STOP_LOSS"))
    TAKE_PROFIT: float = float(os.getenv("TAKE_PROFIT"))

    user: str = os.getenv("PARTNER")
    trading_env: str = os.getenv("TRADING_ENV")

    env: str = os.getenv("ENV")

    db_env: str = os.getenv("DB_ENV")
    db_host_env: str = os.getenv("DB_HOST")
    if user == "NIKOLA":
        if trading_env == "PAPER":
            IBKR_USER: str = os.getenv("IBKR_ACC_PAPER_NIKOLA")
        else:
            IBKR_USER: str = os.getenv("IBKR_ACC_NIKOLA")
    elif user == "MISHO":
        if trading_env == "PAPER":
            IBKR_USER: str = os.getenv("IBKR_ACC_PAPER_MISHO")
        else:
            IBKR_USER: str = os.getenv("IBKR_ACC_MISHO")

    if env is None:
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

    elif db_host_env == "CLOUD":
        DB_HOST: str = os.getenv("DB_HOST_CLOUD")
        DB_USERNAME: str = os.getenv("DB_USERNAME_CLOUD")
        DB_PASSWORD: str = os.getenv("DB_PASSWORD_CLOUD")

        if db_env == "PROD":
            DB_DATABASE: str = os.getenv("DB_DATABASE")
        else:
            DB_DATABASE: str = os.getenv("DB_DATABASE_DEV")


    DATABASE_URL = f"{DB_CONNECTION}://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_DATABASE}"
    logger = logging.getLogger()
    logger.info(DATABASE_URL)

settings = Settings()
