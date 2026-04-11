MENU_TITLE = "¿Que quieres hacer? Elige una seccion."


def start_welcome_html(web_url: str) -> str:
    return (
        "¡Hola! Bienvenido a <b>Botsillo</b>, tu asistente de <b>Expensivo</b>: "
        "gastos, ingresos e <b>inversiones</b>.\n\n"
        f"🌐 <a href=\"{web_url}\">Abrir la web de Expensivo</a>\n\n"
        "¿Que quieres hacer?"
    )


def expense_saved_web_link_html(web_url: str) -> str:
    return f"\n\n🌐 <a href=\"{web_url}\">Abrir Expensivo</a>"
