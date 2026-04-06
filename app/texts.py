# Strings UI centralizados

WELCOME_LINKED = "Hola {username}! Usa /menu para ver las opciones."
WELCOME_UNLINKED = (
    "Hola! Soy Botsillo, el bot de Expensivo.\n\n"
    "Para usar este bot necesitas vincular tu cuenta desde la app de Expensivo "
    "(Settings > Vincular Telegram)."
)
LINK_SUCCESS = "Cuenta vinculada correctamente!\n\nUsa /menu para ver las opciones disponibles."
LINK_INVALID = "El enlace de vinculacion es invalido o ha expirado."
LINK_ALREADY = "Este chat ya esta vinculado a una cuenta de Expensivo."
LINK_FAILED = "No se pudo vincular la cuenta. Intentalo de nuevo."
NOT_LINKED = (
    "No tienes una cuenta vinculada.\n"
    "Vincula tu cuenta desde Expensivo (Settings > Vincular Telegram)."
)

# Menu
MENU_TITLE = "Que quieres hacer?"

# Expense flow
EXPENSE_SELECT_MONTH = "Selecciona el mes:"
EXPENSE_SELECT_CATEGORY = "Selecciona la categoria:"
EXPENSE_SELECT_DAY = "Selecciona el dia:"
EXPENSE_ENTER_AMOUNT = "Introduce el importe:"
EXPENSE_ENTER_DESC = "Descripcion (o pulsa Saltar):"
EXPENSE_CONFIRM = (
    "Nuevo gasto:\n\n"
    "Mes: {month}\n"
    "Categoria: {category}\n"
    "Dia: {day}\n"
    "Importe: {amount:.2f} EUR\n"
    "Descripcion: {description}\n\n"
    "Confirmar?"
)
EXPENSE_SAVED = "Gasto guardado!"
EXPENSE_ERROR = "Error al guardar el gasto. Intentalo de nuevo."

# Income flow
INCOME_SELECT_MONTH = "Selecciona el mes:"
INCOME_SELECT_DAY = "Selecciona el dia:"
INCOME_ENTER_AMOUNT = "Introduce el importe:"
INCOME_ENTER_DESC = "Descripcion (o pulsa Saltar):"
INCOME_CONFIRM = (
    "Nuevo ingreso:\n\n"
    "Mes: {month}\n"
    "Dia: {day}\n"
    "Importe: {amount:.2f} EUR\n"
    "Descripcion: {description}\n\n"
    "Confirmar?"
)
INCOME_SAVED = "Ingreso guardado!"
INCOME_ERROR = "Error al guardar el ingreso. Intentalo de nuevo."

# Query
SUMMARY_TITLE = "Resumen de {month}:"
SUMMARY_BODY = (
    "Gastos: {expenses:.2f} EUR\n"
    "Ingresos: {income:.2f} EUR\n"
    "Balance: {balance:.2f} EUR"
)
NO_TRANSACTIONS = "No hay transacciones para este periodo."

# Common
BTN_BACK = "Atras"
BTN_CANCEL = "Cancelar"
BTN_CONFIRM = "Confirmar"
BTN_SKIP = "Saltar"
CANCELLED = "Operacion cancelada."
