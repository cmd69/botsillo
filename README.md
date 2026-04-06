# Botsillo

Bot de **Telegram** para [Expensivo](https://github.com/cmd69/expense): registrar gastos e ingresos desde el móvil con teclados inline. Este repo solo contiene el bot; **Postgres y el backend FastAPI los usa los de Expensivo**, en la misma red Docker.

## Qué necesitas

- **Docker** con plugin Compose v2 (`docker compose`).
- Una instancia de **Expensivo ya levantada** (dev o prod) con Postgres y API accesibles por **nombre de contenedor** en una red Docker compartida.
- Un **token de bot** de [@BotFather](https://t.me/BotFather).
- En Expensivo, el usuario debe tener vinculado el **Telegram chat id** (flujo desde la app / ajustes, según tu versión de Expensivo).

## Cómo se conecta a Expensivo

| Dirección | Uso |
|-----------|-----|
| **Postgres** (`DATABASE_URL` vía `DB_*`) | Solo **lecturas** (auth: usuario por `telegram_chat_id`). |
| **API** (`API_BASE_URL`) | **Escrituras** (transacciones, etc.) con JWT firmado con la misma `SECRET_KEY` que el backend de Expensivo. |

El `docker-compose.*.yml` de Botsillo declara la red de Expensivo como **externa**; no arranca Postgres ni el backend.

## Alinear la red Docker

En este repo, la red externa está fijada así:

| Entorno | Fichero | Red externa (`name:`) |
|---------|---------|-------------------------|
| Desarrollo | `docker-compose.dev.yml` | `expensivo-dev_expense_network_dev` |
| Producción | `docker-compose.prod.yml` | `expense_network` |

Debe ser **exactamente** la red a la que están unidos los contenedores de Postgres y backend de Expensivo. Si tu carpeta de Expensivo no se llama `expensivo-dev` o el nombre de red en su compose es otro:

1. Lista redes: `docker network ls`.
2. Inspecciona la de Expensivo: `docker network inspect <nombre>`.
3. Ajusta `networks.expensivo_net.name` en el `docker-compose` de Botsillo que uses (dev o prod).

## Variables de entorno

```bash
make setup    # copia .env.example -> .env si no existe
```

Edita `.env`. Valores típicos al **conectar con Expensivo en el mismo host**:

| Variable | Descripción |
|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Token del bot. |
| `SECRET_KEY` | **Igual** que la del backend de Expensivo (JWT compatibles). |
| `DB_USER` / `DB_PASSWORD` | Credenciales Postgres de Expensivo. |
| `DB_HOST` | Nombre del **contenedor** Postgres en esa red (ej. el que uses en el compose de Expensivo). |
| `DB_NAME` | Nombre de la base de datos de Expensivo. |
| `API_BASE_URL` | URL base del API, **alcanzable desde el contenedor del bot** (ej. `http://<servicio_backend>:8000`). |

Los valores de ejemplo en `.env.example` apuntan a nombres habituales en desarrollo; cámbialos según tu `docker compose` de Expensivo.

## Arranque

### Producción

```bash
make build    # primera vez o tras cambiar Dockerfile/requirements
make up
make logs     # opcional: ver salida
```

### Desarrollo (código montado con volumen, hot-reload manual al editar)

```bash
make build-dev
make up-dev
make logs-dev
```

Comandos dentro del contenedor (mismo servicio `bot` en ambos compose):

```bash
docker compose -f docker-compose.dev.yml exec bot python -m pytest   # ejemplo
make shell-dev    # o make shell en prod
```

## Referencia rápida de `make`

| Objetivo | Producción | Desarrollo |
|----------|------------|------------|
| Levantar | `make up` | `make up-dev` |
| Parar | `make down` | `make down-dev` |
| Parar + volúmenes | `make down-v` | `make down-v-dev` |
| Reiniciar | `make restart` | `make restart-dev` |
| Logs | `make logs` | `make logs-dev` |
| Build | `make build` | `make build-dev` |
| Shell | `make shell` | `make shell-dev` |
| Crear `.env` | `make setup` | `make setup` |

## Comprobar que todo va bien

1. Expensivo (API + Postgres) en marcha y en la **misma red** que la declarada en el compose de Botsillo.
2. `.env` coherente con nombres de contenedor/servicio y credenciales reales.
3. Tras `make up` o `make up-dev`, sin errores en logs al hacer polling de Telegram.
4. En Telegram, `/start` y el menú; el usuario debe estar vinculado en Expensivo.

## Más documentación

- Convenciones y stack detallado: `CLAUDE.md`
- Plan de implementación: `docs/PLAN.md`
