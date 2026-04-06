"""Formato de fechas, importes y campos de API para mensajes del bot."""
from datetime import date


def fmt_date_ddmmyyyy(iso: str) -> str:
    return date.fromisoformat(iso).strftime("%d/%m/%Y")


def category_emoji_display(raw: object) -> str:
    """Evita 'None' en pantalla cuando la API devuelve null o falta emoji."""
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return "-"
    return str(raw).strip()


def parse_positive_amount(raw: str) -> float | None:
    """Parsea un importe estrictamente positivo, o None si no es valido."""
    text = raw.strip().replace(",", ".")
    try:
        amount = float(text)
    except (ValueError, TypeError):
        return None
    if amount <= 0:
        return None
    return amount
