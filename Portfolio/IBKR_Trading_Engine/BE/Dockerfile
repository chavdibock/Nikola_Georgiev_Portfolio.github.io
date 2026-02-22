FROM python:3.11-bullseye

WORKDIR /app

COPY . .

RUN pip install -r requirements.txt

WORKDIR ./app

CMD ["uvicorn", "main:app", "--host","0.0.0.0"]