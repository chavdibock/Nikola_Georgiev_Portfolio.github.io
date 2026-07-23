FROM python:3.12.10-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends libatomic1 libgl1 libxrender1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN python -m pip install \
    eclipse-sumo==1.27.1 \
    fastapi==0.115.14 \
    pydantic==2.11.7 \
    uvicorn==0.34.3 \
    websockets==15.0.1

COPY . .
RUN python network/generate_grid.py

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
