.PHONY: build up test down

build:
	docker compose build

up:
	docker compose up -d --build

test:
	python -m pytest -v

down:
	docker compose down