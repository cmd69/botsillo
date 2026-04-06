COMPOSE_DEV = -f docker-compose.dev.yml
COMPOSE_PROD = -f docker-compose.prod.yml

.PHONY: help setup \
	up down down-v restart logs build shell \
	up-dev down-dev down-v-dev restart-dev logs-dev build-dev shell-dev

help: ## Mostrar esta ayuda
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'

# === Producción (default: make up, make logs, …) ===

up: ## [pro] Levantar el bot
	docker compose $(COMPOSE_PROD) up -d

down: ## [pro] Parar el bot
	docker compose $(COMPOSE_PROD) down

down-v: ## [pro] Parar y borrar volúmenes del compose
	docker compose $(COMPOSE_PROD) down -v

restart: ## [pro] Reiniciar
	docker compose $(COMPOSE_PROD) restart

logs: ## [pro] Seguir logs
	docker compose $(COMPOSE_PROD) logs -f

build: ## [pro] Construir imagen
	docker compose $(COMPOSE_PROD) build

shell: ## [pro] Shell en el contenedor
	docker compose $(COMPOSE_PROD) exec bot bash

# === Desarrollo (hot-reload del código en ./app) ===

up-dev: ## [dev] Levantar con docker-compose.dev.yml
	docker compose $(COMPOSE_DEV) up -d

down-dev: ## [dev] Parar
	docker compose $(COMPOSE_DEV) down

down-v-dev: ## [dev] Parar y borrar volúmenes del compose
	docker compose $(COMPOSE_DEV) down -v

restart-dev: ## [dev] Reiniciar
	docker compose $(COMPOSE_DEV) restart

logs-dev: ## [dev] Seguir logs
	docker compose $(COMPOSE_DEV) logs -f

build-dev: ## [dev] Construir imagen
	docker compose $(COMPOSE_DEV) build

shell-dev: ## [dev] Shell en el contenedor
	docker compose $(COMPOSE_DEV) exec bot bash

# === Setup ===

setup: ## Crear .env desde .env.example si no existe
	@[ -f .env ] && echo ".env ya existe" || (cp .env.example .env && echo ".env creado — editalo antes de levantar")
