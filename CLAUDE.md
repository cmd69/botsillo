# botsillo-dev

Bot de Telegram para Expensivo — registro de gastos/ingresos desde el movil con teclados inline (inspirado en portfolioTeleBot). Futuro canal de notificaciones.

## Stack

- **Lenguaje:** Python 3.12
- **Libreria:** aiogram v3 (async, FSM built-in)
- **Base de datos:** ninguna propia — lee de Postgres de expensivo (read-only), escribe via API HTTP
- **APIs externas:** Telegram Bot API, Expensivo backend (FastAPI)
- **Deploy:** Docker Compose (red compartida con expensivo)
- **Tipo:** par prod/dev — `botsillo/` (prod) + `botsillo-dev/` (dev)

## Arrancar

```bash
make up         # desarrollo (default en -dev)
make down       # parar
make logs       # logs
make build      # rebuild
make shell      # shell interactivo en el contenedor
```

**Requisito:** expensivo-dev debe estar levantado (`make up-dev` en expensivo-dev).

## Ejecucion de comandos

**Todos los comandos con librerias se ejecutan dentro del contenedor:**

```bash
docker compose -f docker-compose.dev.yml exec bot python -m pytest
docker compose -f docker-compose.dev.yml exec bot pip install <paquete>
make shell
```

**Nunca ejecutar `python3`, `pip install` directamente en el host.**

## Estructura

```
botsillo-dev/
├── docker-compose.dev.yml      # desarrollo con hot-reload
├── docker-compose.prod.yml     # build para registry
├── Dockerfile
├── .env.example                # template (en git)
├── .env                        # NO en git
├── Makefile
├── README.md
├── CLAUDE.md
├── requirements.txt
├── .gitignore
└── app/
    ├── __init__.py
    ├── main.py                 # entry point, bot setup, polling
    ├── config.py               # settings via pydantic-settings
    ├── db.py                   # AsyncEngine + queries read-only a expensivo
    ├── api_client.py           # HTTP client para backend API (escrituras)
    ├── auth.py                 # JWT validation (shared SECRET_KEY con expensivo)
    ├── states.py               # FSM StatesGroup definitions
    ├── texts.py                # strings UI centralizados
    ├── handlers/
    │   ├── __init__.py
    │   ├── start.py            # /start, vinculacion con deep link
    │   ├── menu.py             # menu principal
    │   ├── expense.py          # FSM flujo gasto
    │   ├── income.py           # FSM flujo ingreso
    │   └── query.py            # resumen mes, ultimos gastos
    ├── keyboards/
    │   ├── __init__.py
    │   ├── main_menu.py        # teclado menu principal
    │   ├── calendar.py         # month picker + day grid
    │   ├── categories.py       # category picker paginado
    │   └── common.py           # back, cancel, confirm
    └── middlewares/
        ├── __init__.py
        └── auth.py             # verificar telegram_chat_id vinculado
```

## Conexion a expensivo

El bot se conecta a la red Docker de expensivo como red externa:

```yaml
# docker-compose.dev.yml
networks:
  expensivo_net:
    external: true
    name: expense_network_dev
```

### Comunicacion

- **Lecturas:** SQLAlchemy async (read-only) contra Postgres de expensivo
- **Escrituras:** HTTP POST al backend FastAPI de expensivo con Bearer JWT

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

## Variables de entorno

Ver `.env.example`. Variables minimas:

| Variable | Descripcion |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Token del bot (BotFather) |
| `SECRET_KEY` | Misma que expensivo, para JWT compatibles |
| `DB_USER` | Usuario de Postgres de expensivo |
| `DB_PASSWORD` | Password de Postgres de expensivo |
| `DB_HOST` | Nombre del contenedor postgres (`expense_postgres_dev`) |
| `DB_NAME` | Nombre de la base de datos (`expensivo_db`) |
| `API_BASE_URL` | URL del backend de expensivo (`http://expense_backend_dev:8000`) |

## Puertos

Ninguno. El bot usa polling a Telegram, no expone puertos.

## Vinculacion usuario

1. En Settings de Expensivo: "Vincular Telegram" genera deep link `t.me/BotsilloBot?start=<jwt>`
2. `/start <token>` valida JWT, guarda `telegram_chat_id` en el usuario
3. Middleware verifica vinculacion en cada mensaje

## Dependencias

```
aiogram>=3.0
sqlalchemy[asyncio]>=2.0
asyncpg>=0.29
python-jose[cryptography]>=3.3
httpx>=0.25
pydantic-settings>=2.1
```

## Cambios necesarios en expensivo-dev

| Accion | Archivo | Que |
|---|---|---|
| Crear | `backend/app/api/v1/telegram_routes.py` | 3 endpoints vinculacion |
| Editar | `backend/app/api/v1/router.py` | Registrar telegram_routes |
| Editar | `frontend/pages/settings.tsx` | Card vinculacion Telegram |

## Archivos de referencia

| Archivo | Para que |
|---|---|
| `~/homelab/docker/portfolioTeleBot/cleanBot.py` | Teclados, FSM, calendar, edit-in-place |
| `~/homelab/docker/luz_informer_bot/src/telegram_bot/` | Patron aiogram v3 handlers + keyboards |
| `~/homelab/docker/chatid_bot/bot.py` | Estructura minima aiogram v3 |
| `~/homelab/docker/expensivo-dev/backend/app/utils/auth.py` | JWT (SECRET_KEY, HS256) |
| `~/homelab/docker/expensivo-dev/backend/app/models/user.py` | telegram_chat_id ya existe |
| `~/homelab/docker/expensivo-dev/backend/app/api/v1/transaction_routes.py` | POST /transactions/ schema |

## Convencion de commits

```
[NN] TYPE(scope): descripcion breve
```

- `[NN]` secuencial por repo (siguiente: `[01]`)
- Tipos: `FEAT` `FIX` `DOCS` `REFACTOR` `CHORE` `TEST` `CI` `INFRA` `STYLE`
- Guia completa: `~/.agent/CODING.md`
