from . import session

from typing import Generator


def get_db() -> Generator:
    db = session.SessionLocal()
    try:
        yield db
    finally:
        db.close()
