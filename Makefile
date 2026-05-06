.PHONY: api-check dev docker-up migrate seed web-check

dev:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build api web

docker-up:
	docker compose up --build

api-check:
	./scripts/check-api.sh

web-check:
	./scripts/check-web.sh

migrate:
	./scripts/migrate-api.sh

seed:
	./scripts/seed-api.sh
