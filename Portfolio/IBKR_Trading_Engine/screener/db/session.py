from sqlalchemy.orm import sessionmaker
import json
from sqlalchemy import create_engine
from core.config import settings

SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL
print("Database URL is ", SQLALCHEMY_DATABASE_URL)
engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_recycle=3600)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
