FROM python:3.12.10-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    MPLBACKEND=Agg

WORKDIR /app

RUN python -m pip install --index-url https://download.pytorch.org/whl/cpu torch==2.7.1 \
    && python -m pip install \
        numpy==2.2.6 \
        matplotlib==3.10.3 \
        httpx==0.28.1 \
        websockets==15.0.1

COPY . .

CMD ["sh", "-c", "trap : TERM INT; sleep infinity & wait"]
