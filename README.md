# Botsillo

Bot de Telegram para **Expensivo**: registrar gastos e ingresos desde el móvil. El código vive en este repo; habla con el backend y la base de datos de expensivo por la red Docker compartida.

## Requisitos

- **expensivo-dev** levantado (misma red Docker que usa este compose).
- Copia de variables en `.env` (ver `.env.example`).

## Arranque

```bash
cp .env.example .env   # o: make setup
# Edita .env (token del bot, SECRET_KEY alineada con expensivo, credenciales DB)

make up     # desarrollo (docker-compose.dev.yml)
make logs   # seguir logs
make shell  # shell en el contenedor del bot
```

Para producción: `make up-pro`, `make logs-pro`.

## Más detalle

- Convenciones y stack: `CLAUDE.md`
- Plan de implementación: `docs/PLAN.md`
