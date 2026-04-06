"""Utilidades compartidas sobre la lista plana de categorias de la API."""


def roots(cats: list[dict]) -> list[dict]:
    return [c for c in cats if not c.get("parent_category_id")]


def children(cats: list[dict], parent_id: str) -> list[dict]:
    return [c for c in cats if str(c.get("parent_category_id", "")) == parent_id]


def category_button_label(cat: dict) -> str:
    emoji = cat.get("emoji", "")
    return f"{emoji} {cat['name']}".strip() if emoji else cat["name"]
