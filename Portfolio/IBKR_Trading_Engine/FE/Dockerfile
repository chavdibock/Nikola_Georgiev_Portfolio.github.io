FROM python:3.11-bullseye

WORKDIR /code

COPY ./requirements.txt /code/reqrequirements.txt
COPY ./.env /code/.env

RUN pip install --no-cache-dir --upgrade -r /code/reqrequirements.txt


copy ./app /code/app


WORKDIR /code/app


CMD ["uvicorn", "main:app", "--host", "0.0.0.0"]