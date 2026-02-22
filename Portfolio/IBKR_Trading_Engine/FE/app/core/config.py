from dotenv import load_dotenv, dotenv_values
import os

# loading variables from .env file
load_dotenv()


class Settings:
    partner: str = os.getenv("PARTNER")
    env: str = os.getenv("ENV")
    be_endpoint_env = os.getenv("BE_ENV")
    if env is None:
        IBKR_BASE: str = os.getenv("IBKR_CLIENT_LOCAL")
    elif env == "DOCKER":
        IBKR_BASE: str = os.getenv("IBKR_CLIENT_DOCKER")
    elif env == "CLOUD":
        IBKR_BASE: str = os.getenv("IBKR_CLIENT_CLOUD")

    if partner == "NIKOLA":
        PARTNER_ACC: str = os.getenv("IBKR_ACC_PAPER_NIKOLA")
    elif partner == "MISHO":
        PARTNER_ACC: str = os.getenv("IBKR_ACC_PAPER_MISHO")
    else:
        PARTNER_ACC: str = os.getenv("IBKR_ACC_PAPER_NIKOLA")

    if be_endpoint_env == "LOCAL":
        BE_BASE: str = os.getenv("BE_ENDPOINT_LOCAL")
    else:
        BE_BASE: str = os.getenv("BE_ENDPOINT_DOCKER")


settings = Settings()
