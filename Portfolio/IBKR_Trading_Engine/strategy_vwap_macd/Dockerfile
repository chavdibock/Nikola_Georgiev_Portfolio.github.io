FROM python:3.11-bullseye

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir --upgrade -r requirements.txt

CMD ["python", "-u", "main.py"]