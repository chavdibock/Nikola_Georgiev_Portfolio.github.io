from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Define the base class for ORM models
Base = declarative_base()


# Define the Stock model
class Stock(Base):
    __tablename__ = "stocks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(45), nullable=True)
    price = Column(Float, nullable=True, default=0)
    vwap = Column(Float, nullable=True, default=0)
    macd = Column(Float, nullable=True, default=0)
    vwap_calculation = Column(Float, nullable=True, default=0)
    ma_calculation = Column(Float, nullable=True, default=0)
    stop_loss = Column(Float, nullable=True, default=0)
    macd_condition = Column(Boolean, nullable=True)
    scr_id = Column(String(45))


class ScreenerSettings(Base):
    __tablename__ = "scr_settings"
    scr_id = Column(String(45), primary_key=True, nullable=False)
    period = Column(String(45), nullable=True)
    bars_size = Column(String(45), nullable=True)
    calc_vwap_window = Column(Float, nullable=True, default=0)
    moving_avg_window = Column(Float, nullable=True, default=0)
    macd_len = Column(Float, nullable=True, default=0)
    macd_fast = Column(Float, nullable=True, default=0)
    macd_slow = Column(Float, nullable=True, default=0)
    calc_st_loss = Column(Float, nullable=True, default=0)
