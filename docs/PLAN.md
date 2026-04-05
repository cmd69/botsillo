# Plan de implementacion — Botsillo

Bot de Telegram para Expensivo — registro de gastos/ingresos desde el movil con teclados inline (inspirado en portfolioTeleBot). Futuro canal de notificaciones.

Proyecto: `~/homelab/docker/botsillo-dev/` (repo independiente, par prod/dev)

## Decisiones clave

- Ubicacion: repo separado `botsillo-dev/`, se conecta a la red Docker de expensivo
- Comunicacion: HTTP API del backend para escrituras, DB directa (read-only) para lecturas
- Libreria: aiogram v3 (async, FSM built-in)
- Teclados: Inline keyboards con edit-in-place (patron portfolioTeleBot)
- Vinculacion: `/start <token>` con JWT temporal desde frontend de expensivo
- Calendario: `python-telegram-bot-calendar` (`DetailedTelegramCalendar`) para seleccion YYMM y YYMMDD

## Conexion a la red de Expensivo

El bot vive en su propio compose pero se conecta a la red de expensivo-dev como red externa:

```yaml
# docker-compose.dev.yml
services:
  bot:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: botsillo_bot_dev
    env_file: .env
    environment:
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - DATABASE_URL=postgresql+asyncpg://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:5432/${DB_NAME}
      - API_BASE_URL=http://expensivo_backend_dev:8000
      - SECRET_KEY=${SECRET_KEY}
    networks:
      - expensivo_net
    restart: "no"

networks:
  expensivo_net:
    external: true
    name: expense_network_dev
```

Variables `.env` necesarias (compartidas con expensivo):

```
TELEGRAM_BOT_TOKEN=          # de BotFather
SECRET_KEY=misma_que_expensivo  # para generar JWT compatibles
DB_USER=expensivo_user
DB_PASSWORD=...
DB_HOST=expensivo_postgres_dev  # nombre del contenedor postgres de expensivo
DB_NAME=expensivo_db
```

Requisito: expensivo-dev debe estar levantado primero (`make up` en expensivo-dev).

## Arquitectura

```
botsillo-dev/                         expensivo-dev/
┌─────────────┐  HTTP POST            ┌──────────┐
│   Bot       │───────────────────────>│ Backend  │
│  (aiogram)  │  Bearer <JWT>         │ (FastAPI)│
│             │                        └──────────┘
│             │  SQLAlchemy read-only  ┌──────────┐
│             │───────────────────────>│ Postgres │
└─────────────┘                        └──────────┘
      <-> expense_network_dev (red compartida)
```

## Flujos UI

### Menu principal

```
┌──────────────────────────────────┐
│ 💸 Nuevo Gasto  │ 💰 Nuevo Ingreso│
│ 📊 Resumen Mes  │ 📋 Ultimos 10   │
│ ⚙️ Configuracion                  │
└──────────────────────────────────┘
```

### Flujo gasto (FSM, edit-in-place)

```
/gasto -> Mes (YYMM calendar) -> Categoria (paginado 3x2) -> Dia (YYMMDD calendar)
       -> Importe (texto) -> Descripcion (texto/saltar) -> Confirmacion
```

Cada paso actualiza el mismo mensaje (edit-in-place). Siempre boton Atras y Cancelar.

### Vinculacion

1. En Settings de Expensivo: "Vincular Telegram" genera deep link `t.me/BotsilloBot?start=<jwt>`
2. `/start <token>` valida JWT, guarda `telegram_chat_id`, responde "Vinculado"

## Estructura del proyecto

```
botsillo-dev/
├── CLAUDE.md
├── Makefile
├── Dockerfile
├── docker-compose.dev.yml
├── docker-compose.prod.yml
├── .env.example
├── .gitignore
├── requirements.txt
├── app/
│   ├── __init__.py
│   ├── main.py              # Entry point, bot setup, polling
│   ├── config.py            # BOT_TOKEN, DB_URL, API_URL, SECRET_KEY
│   ├── db.py                # AsyncEngine + queries read-only
│   ├── api_client.py        # HTTP client para backend API (escrituras)
│   ├── auth.py              # JWT gen/validation (shared SECRET_KEY)
│   ├── states.py            # FSM StatesGroup definitions
│   ├── texts.py             # Strings UI centralizados
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── start.py         # /start, vinculacion
│   │   ├── menu.py          # Menu principal
│   │   ├── expense.py       # FSM flujo gasto
│   │   ├── income.py        # FSM flujo ingreso
│   │   └── query.py         # Resumen mes, ultimos gastos
│   ├── keyboards/
│   │   ├── __init__.py
│   │   ├── main_menu.py     # Teclado menu principal
│   │   ├── calendar.py      # Wrapper sobre telegram-bot-calendar
│   │   ├── categories.py    # Category picker paginado
│   │   └── common.py        # Back, cancel, confirm
│   └── middlewares/
│       ├── __init__.py
│       └── auth.py          # Verificar telegram_chat_id vinculado
```

## Cambios necesarios en expensivo-dev

| Accion | Archivo | Que |
|---|---|---|
| Crear | `backend/app/api/v1/telegram_routes.py` | 3 endpoints vinculacion |
| Editar | `backend/app/api/v1/router.py` | Registrar telegram_routes |
| Editar | `frontend/pages/settings.tsx` | Card vinculacion Telegram |

Endpoints vinculacion:
- `POST /api/v1/users/telegram-link-token` — JWT temporal (10min, purpose=telegram_link)
- `GET /api/v1/users/telegram-status` — `{linked, chat_id}`
- `DELETE /api/v1/users/telegram-unlink` — borra telegram_chat_id

## Archivos de referencia

| Archivo | Para que |
|---|---|
| `~/homelab/docker/portfolioTeleBot/cleanBot.py` | Teclados, FSM, calendar, edit-in-place |
| `~/homelab/docker/luz_informer_bot/src/telegram_bot/` | Patron aiogram v3 handlers + keyboards |
| `~/homelab/docker/chatid_bot/bot.py` | Estructura minima aiogram v3 |
| `~/homelab/docker/expensivo-dev/backend/app/utils/auth.py` | JWT (SECRET_KEY, HS256) |
| `~/homelab/docker/expensivo-dev/backend/app/models/user.py` | telegram_chat_id ya existe |
| `~/homelab/docker/expensivo-dev/backend/app/api/v1/transaction_routes.py` | POST /transactions/ schema |

## Dependencias

```
aiogram>=3.0
python-telegram-bot-calendar>=1.0.5
sqlalchemy[asyncio]>=2.0
asyncpg>=0.29
python-jose[cryptography]>=3.3
httpx>=0.25
pydantic-settings>=2.1
```

## Orden de implementacion

1. Scaffold proyecto: CLAUDE.md, Makefile, Dockerfile, compose, .env.example, .gitignore
2. `app/config.py` + `app/main.py` (polling basico, /start)
3. `app/db.py` + `app/auth.py` (conexion DB + JWT)
4. En expensivo-dev: `telegram_routes.py` + registrar en router
5. `app/middlewares/auth.py` (verificar usuario vinculado)
6. `app/keyboards/` (calendar wrapper, categories, common, main_menu)
7. `app/handlers/menu.py` (menu principal)
8. `app/handlers/expense.py` + `app/states.py` (flujo gasto)
9. `app/handlers/income.py` (reutiliza keyboards)
10. `app/handlers/query.py` (resumen, ultimos gastos)
11. En expensivo-dev: card Telegram en Settings
12. Testing E2E
