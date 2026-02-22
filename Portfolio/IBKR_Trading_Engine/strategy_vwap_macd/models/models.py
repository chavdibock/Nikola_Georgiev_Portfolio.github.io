from datetime import datetime

from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Define the base class for ORM models
Base = declarative_base()

# Define the Stock model
class Stock(Base):
    __tablename__ = "stocks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=True)  # Correct timestamp column
    symbol = Column(String(45), nullable=True)
    price = Column(Float, nullable=True, default=0)
    vwap = Column(Float, nullable=True, default=0)
    macd = Column(Float, nullable=True, default=0)
    vwap_calculation = Column(Float, nullable=True, default=0)
    ma_calculation = Column(Float, nullable=True, default=0)
    stop_loss = Column(Float, nullable=True, default=0)
    macd_condition = Column(Boolean, nullable=True)


