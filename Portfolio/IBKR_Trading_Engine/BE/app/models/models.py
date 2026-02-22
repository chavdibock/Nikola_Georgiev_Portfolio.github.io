from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base

# Define the base class for ORM models
Base = declarative_base()


# Define the Stock model
class Stock(Base):
    __tablename__ = "stocks"
    # id, con_id, ticker, amount, screener_id, screener_weight
    id = Column(Integer, primary_key=True, autoincrement=True)
    con_id = Column(Integer, nullable=True)
    ticker = Column(String(45), nullable=True, default=0)
    amount = Column(Integer, nullable=True, default=0)
    screener_id = Column(Integer, nullable=True, default=0)
    screener_weight = Column(Float, nullable=True, default=0)
