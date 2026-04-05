COMPOSE_DEV = -f docker-compose.dev.yml
COMPOSE_PROD = -f docker-compose.prod.yml

.PHONY: help up down restart logs build shell up-pro down-pro logs-pro setup

help: ## Mostrar esta ayuda
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# === Desarrollo (default) ===

up: ## Iniciar desarrollo con hot-reload
	docker compose $(COMPOSE_DEV) up -d

down: ## Detener desarrollo
	docker compose $(COMPOSE_DEV) down

restart: ## Reiniciar desarrollo
	docker compose $(COMPOSE_DEV) restart

logs: ## Ver logs de desarrollo
	docker compose $(COMPOSE_DEV) logs -f

build: ## Construir imagen de desarrollo
	docker compose $(COMPOSE_DEV) build

shell: ## Shell interactivo en el contenedor dev
	docker compose $(COMPOSE_DEV) exec bot bash

# === Produccion ===

up-pro: ## Iniciar produccion
	docker compose $(COMPOSE_PROD) up -d

down-pro: ## Detener produccion
	docker compose $(COMPOSE_PROD) down

logs-pro: ## Ver logs de produccion
	docker compose $(COMPOSE_PROD) logs -f

# === Setup ===

setup: ## Crear .env desde .env.example si no existe
	@[ -f .env ] && echo ".env ya existe" || (cp .env.example .env && echo ".env creado — editalo antes de levantar")
