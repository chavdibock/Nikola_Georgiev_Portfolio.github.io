from crud import crud
from db.db import get_db
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from core.config import settings

app = FastAPI()
print(settings.DATABASE_URL)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/screener-stocks-be")
def read_root(db: Session = Depends(get_db)):
    return crud.get_all_stocks(db=db)
