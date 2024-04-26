from aiogram.utils.keyboard import InlineKeyboardBuilder as ikbuilder
from aiogram.utils.keyboard import ReplyKeyboardBuilder as rkbuilder
# from aiogram.types import InlineKeyboardButton as btn
from core.config import Config

btns = {
    "profile": {
        "reload": "Синхронизировать ⚙️",
        "delete": "Удалить профиль 🗑",
    },
    "ticket": {
        # "back": "⬅️ Назад", 
        "reload": "Синхронизировать ⚙️",
        "delete": "Удалить 🗑",
        # "like": "👍",
        "close": "Решена ✅",
    }
}

def client_reload_info(telegram_id: int):
    builder = ikbuilder()
    for action, ru in btns["profile"].items():
        builder.button(
            text=ru, 
            callback_data=f"clients_{action}_{telegram_id}")
    builder.adjust(1, 2)
    return builder.as_markup()

def categories_list(categories: list):
    builder = ikbuilder()
    action = "newticket"
    for c in categories:
        builder.button(
            text=c.get('name'), 
            callback_data=f"categories_{action}_{c.get('id')}")
    builder.adjust(1, 1)
    return builder.as_markup()

def tickets_list(tickets: list):
    builder = ikbuilder()
    for t in tickets:
        builder.button(
            text=f"{t.get('trackid')} {t.get('category_name')}", 
            callback_data=f"tickets_get_{t.get('trackid')}")
    builder.adjust(1, 1)
    return builder.as_markup()

def ticket_actions(track_id: str):
    builder = ikbuilder()
    for action, ru in btns["ticket"].items():
        builder.button(
            text=ru, 
            callback_data=f"tickets_{action}_{track_id}")
    builder.button(
        text="Подробнее 🖥", url=f"{Config.web_url}/admin/admin_ticket.php?track={track_id}"
    )
    builder.adjust(1, 2)
    return builder.as_markup()

def back(route_name = 'categories', action='back'):
    builder = ikbuilder()
    builder.button(
        text="⬅️ Назад", 
        callback_data=f"{route_name}_{action}")
    builder.adjust(1, 1)
    return builder.as_markup()

def back_or_send(ticket_id: int):
    builder = ikbuilder()
    builder.button(
        text="⬅️ Назад", 
        callback_data="categories_back")
    builder.button(
        text="Отправить ➡️",
        callback_data=f"tickets_send_{ticket_id}"
    )
    builder.adjust(2, 2)
    return builder.as_markup()

def custom_fields_select_kb(chooses = []):
    if not chooses: 
        return None
    builder = rkbuilder()
    for c in chooses:
        builder.button(text=c)
    builder.adjust(3, 3)
    return builder.as_markup()

def keyboard_cf_if_need(custom_field: dict):
    if not custom_field:
        return None
    start_values = [] if custom_field.get('req') == 0 else ['Пропустить']
    if custom_field.get('default_value'):
        start_values.append(custom_field.get('default_value'))
    end_values = []
    match custom_field.get('type'):
        case 'select':
            end_values = [*start_values, *custom_field.get('select_options')]
        # case 'checkbox': # TODO
        #     end_values = [*start_values, *['Нет', 'Да']]
        case 'radio':
            end_values = [*start_values, *custom_field.get('radio_options')]
        # case 'textarea':
        #     ...
        # case 'date':
        #     ...
        # case 'email':
        #     ...
        # case 'hidden':
        #     ...
        case _:
            return None
    return custom_fields_select_kb(end_values)