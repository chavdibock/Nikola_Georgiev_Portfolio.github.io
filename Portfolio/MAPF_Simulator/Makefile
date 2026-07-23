-include .env

PENETRATION ?= 0.05
TRAINING_ITERATIONS ?= 3
ROLLOUT_STEPS ?= 2048
OUTPUT_DIR ?= /app/outputs/checkpoints
SIMULATOR_PORT ?= 8000
REPLAY_SCENARIO ?= surge
REPLAY_STEPS ?= 1800
REPLAY_DELAY_MS ?= 120
HOST_SIMULATOR_URL := http://127.0.0.1:$(SIMULATOR_PORT)

.PHONY: up down logs smoke-test train evaluate replay

up:
	docker compose up --build --detach

down:
	docker compose down

logs:
	docker compose logs --follow simulator-service

smoke-test:
	docker compose run --rm training-service python -m api_client.smoke_test

train:
	docker compose run --rm training-service python training/train.py \
		--iterations $(TRAINING_ITERATIONS) \
		--steps $(ROLLOUT_STEPS) \
		--penetration-rate $(PENETRATION) \
		--output-dir $(OUTPUT_DIR)

evaluate:
	docker compose run --rm training-service python evaluation/evaluate.py
	docker compose run --rm training-service python evaluation/plots.py

replay:
	.venv/bin/python replay/gui_replay.py \
		--simulator-url $(HOST_SIMULATOR_URL) \
		--scenario $(REPLAY_SCENARIO) \
		--penetration-rate $(PENETRATION) \
		--steps $(REPLAY_STEPS) \
		--delay-ms $(REPLAY_DELAY_MS)
