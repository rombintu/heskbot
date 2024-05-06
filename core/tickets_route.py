from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram import Router, F, types
from core.content import txt_message, txt_subject, html_mode
from core.cache import cache
from core.api import api, Ticket
from core import bot
from tools.logger import logger as log
from core.keyboards import categories_list, back, keyboard_cf_if_need, back_or_send, tickets_list
from core.keyboards import ticket_actions, admins_list
from aiogram.exceptions import TelegramBadRequest
# from aiogram.types.reply_keyboard_remove import ReplyKeyboardRemove
from tools.utils import validate_date, get_today, if_type_is_date, to_body, priorities

router = Router()

class FormTicket(StatesGroup):
    ticket_data = State()
    message_id = State()
    subject = State()
    message = State()
    custom_fields = State()

class FormSearchTicket(StatesGroup):
    track_or_email = State()

def options2text(row: dict, key: str):
    buff = ""
    if not row.get(key):
        return row.get('value')
    for option in row.get(key):
        buff += f"\n    | {option}"
    return buff

def value_isxist(row: dict):
    match row.get('type'):
        case 'select':
            return options2text(row, 'select_options')
        case 'radio':
            return options2text(row, 'radio_options')
        case 'checkbox':
            return options2text(row, 'checkbox_options')
        case 'date':
            return if_type_is_date(row)
        case _:
            return row.get('value')

# def to_body(html_or_text: str):
#     body: str = html2text(html_or_text)
#     if len(body) > 255:
#         body = body[:255] + "..."
#     return f'<code>{body}</code>'

def ticket2text(t: dict, stage=txt_subject, done=False):
    status = '<em>Создание</em>'
    if done:
        status = '<em>Подтверждение</em>'
    if stage == 'end':
        status = '<em>Отправлена</em>'
    status = status if not t.get('status') else f"<em>{t['status']}</em>"
    body = '' if not t.get('message') else to_body(t.get('message'))
    
    custom_fields_data = ""
    if t.get('custom_fields'):
        for cf in t.get('custom_fields'):
            value = '-' if not cf.get("value") else value_isxist(cf)
            custom_fields_data += f'''\n- {"<b>>" if stage==cf.get("name") else ""} {cf.get("name") }{"*️⃣" if cf.get("req") else ""}: {"</b>" if stage==cf.get("name") else ""} \
<code>{value}</code>'''
    note = ''
    if not done:
        note = '\n*️⃣ - <em>Необходимо указать</em>\n⚠️ Используйте знак минус - для пропуска\n'
    return f"""Статус заявки: {status}\
        {note}\
        \n <b>    --- Информация ---    </b> \
        \n👨‍💻 {t.get('name')} \
        \n📪 {t.get('email')} 🔗 {'Ссылка скрыта' if not t.get('username') else '@'+t.get('username')}\
        \n🔬 Категория: {t.get('category_name')}\
        \n{'<b> ->' if stage==txt_subject else ''} Тема: {'</b>' if stage==txt_subject else ''} <em>{'' if not t.get('subject') else t['subject']}</em>\
        \n{'<b> ->' if stage==txt_message else ''} Сообщение*️⃣: {'</b>' if stage==txt_message else ''} {body}\
        \nДополнительные поля:\
        \n{'- Нет' if not custom_fields_data else custom_fields_data}"""

def ticket2workflow2text(t: dict):
    replies_count = t.get('replies') | 0
    replies = ""
    if replies_count > 0:
        replies_list = api.ticket_get_replies(t.get('trackid'))
        if replies_list:
            replies = "\n<b>    --- Диалог ---    </b>"
            for r in replies_list:
                replies += f"\n<em>{r.get('name')}</em>: {to_body(r.get('message'), 516)}"
    buff = ticket2text(t, stage=None, done=True)
    buff += f"""\n\n<b>Рабочая информация</b>\
    \n🆔 <code>{t.get('trackid')}</code>\
    \n🛠 Исполнитель: {t.get('owner_name') if t.get('owner_name') else 'Не назначен'}\
    \n{priorities(t.get('priority'))} приоритет\
    \n💬 Ответов: {replies_count}"""
    buff += replies
    return buff

@router.message(FormTicket.subject)
async def handle_ticket_subject(message: types.Message, state: FSMContext):
    match message.text:
        case "/cancel":
            await message.answer("Отмена создания заявки")
            await state.clear()
        case None:
            await state.set_state(FormTicket.subject)
            await message.answer("Ожидается тема обращения заявки\
                                 \n/cancel - Отмена")
        case _:
            # await state.update_data(subject=message.text)
            await state.set_state(FormTicket.message)
            state_data = await state.get_data()
            ticket_data = state_data.get('ticket_data')
            ticket_data['subject'] = message.text
            await state.update_data(ticket_data=ticket_data)
            await bot.edit_message_text(
                text=ticket2text(ticket_data, stage=txt_message),
                chat_id=message.chat.id,
                message_id=state_data.get('message_id'),
                parse_mode=html_mode,
                reply_markup=back()
            )
            log.debug(f'DATA FROM STATE >> {await state.get_data()}')
            

@router.message(FormTicket.message)
async def handle_ticket_message(message: types.Message, state: FSMContext):
    match message.text:
        case "/cancel":
            await message.answer("Отмена создания заявки")
            await state.clear()
        case _:
            # await state.update_data(message=message.text)
            await state.set_state(FormTicket.custom_fields)
            state_data = await state.get_data()
            ticket_data: dict = state_data.get('ticket_data')
            ticket_data['message'] = message.text
            custom_fields: list = ticket_data.get('custom_fields')
            next_stage = None
            keyboard_cf = None
            if custom_fields:
                next_stage = custom_fields[0].get('name')
                if custom_fields[0].get('type') == 'date':
                    await message.answer('Ожидается дата формата: \nдень-месяц-год [31-12-2024]')
                keyboard_cf = keyboard_cf_if_need(custom_fields[0])
                ticket_data['current_cf_name'] = next_stage
                ticket_data['current_cf_i'] = 0
            await state.update_data(ticket_data=ticket_data)
            done = False if next_stage else True
            if not done:
                await bot.edit_message_text(
                    text=ticket2text(ticket_data, stage=next_stage, done=done),
                    chat_id=message.chat.id,
                    message_id=state_data.get('message_id'),
                    parse_mode=html_mode,
                    reply_markup=back(),
                )
            else:
                ticket_id: int = state_data.get('message_id')
                await cache.save_dict(ticket_data, f"tickets_{ticket_id}")
                await bot.delete_message(message.chat.id, ticket_id)
                await message.answer(
                    text=ticket2text(ticket_data, stage=next_stage, done=done),
                    parse_mode=html_mode,
                    reply_markup=back_or_send(ticket_id),
                )
            if keyboard_cf:
                await message.answer('Выберите опциональные поля', reply_markup=keyboard_cf)
            
            log.debug(f'DATA FROM STATE >> {await state.get_data()}')
            # await message.answer(
            #     "Допишите дополнительные поля",
            #     reply_to_message_id=state_data.get('message_id'))

@router.message(FormTicket.custom_fields)
async def handle_ticket_custom_fields(message: types.Message, state: FSMContext):
    match message.text:
        case "/cancel":
            await message.answer("Отмена создания заявки")
            await state.clear()
        case _:
            state_data = await state.get_data()
            ticket_data: dict = state_data.get('ticket_data')
            # ticket_data['message'] = message.text
            custom_fields = ticket_data.get('custom_fields')
            next_stage = None
            keyboard_cf = None
            if custom_fields:
                message_text = message.text
                current_i = ticket_data.get('current_cf_i')
                is_req = custom_fields[current_i].get('req')
                if custom_fields[current_i].get('type') == 'date':
                    if not is_req and message.text == '-':
                        message_text = get_today()
                    elif not validate_date(message.text):
                        await message.answer('Ожидается дата формата: \nдень-месяц-год [31-12-2024]\nНапишите минус "-", чтобы пропустить (если поле необязательно)')
                        return
                custom_fields[current_i]['value'] = message_text
                try:
                    next_stage = custom_fields[current_i+1].get('name')
                    if custom_fields[current_i+1].get('type') == 'date':
                        await message.answer('Ожидается дата формата: \nдень-месяц-год [31-12-2024]')
                    ticket_data['current_cf_name'] = next_stage
                    ticket_data['current_cf_i'] = current_i+1
                    keyboard_cf = keyboard_cf_if_need(custom_fields[current_i+1])
                    # if not keyboard_cf:
                    #     await message.answer(
                    #         "Опциональные поля выбраны", 
                    #         reply_markup=ReplyKeyboardRemove())
                except IndexError:
                    pass
            await state.set_state(FormTicket.custom_fields)
            await state.update_data(ticket_data=ticket_data)
            done = False if next_stage else True
            if not done:
                await bot.edit_message_text(
                    text=ticket2text(ticket_data, stage=next_stage, done=done),
                    chat_id=message.chat.id,
                    message_id=state_data.get('message_id'),
                    parse_mode=html_mode,
                    reply_markup=back(),
                )
            else:
                ticket_id: int = state_data.get('message_id')
                await cache.save_dict(ticket_data, f"tickets_{ticket_id}")
                await bot.delete_message(message.chat.id, state_data.get('message_id'))
                await message.answer(
                    text=ticket2text(ticket_data, stage=next_stage, done=done),
                    parse_mode=html_mode,
                    reply_markup=back_or_send(ticket_id),
                )
            if keyboard_cf:
                await message.answer('Выберите опциональные поля', reply_markup=keyboard_cf)
            log.debug(f'DATA FROM STATE >> {await state.get_data()}')

@router.message(FormSearchTicket.track_or_email)
async def handle_ticket_search(message: types.Message, state: FSMContext):
    # await state.clear()
    match message.text:
        case "/cancel":
            await message.answer("Отмена поиска")
            await state.clear()
        case None:
            await state.set_state(FormSearchTicket.track_or_email)
            await message.answer("Ожидается трек или почта, тикета, который ищете\
                                 \n/cancel - Отмена")
        case _:
            await state.clear()
            tickets = []
            track_or_email: str = message.text
            if "@" in track_or_email:
                tickets = api.tickets_get_my_all(track_or_email, all_status=True)
            else:
                tickets.append(api.ticket_get_by_trackid(track_or_email))
            if not tickets:
                await message.answer('Ничего не найдено')
            elif len(tickets) == 1:
                ticket = tickets[0]
                await message.answer(
                    ticket2workflow2text(ticket),
                    parse_mode=html_mode,
                    reply_markup=ticket_actions(ticket.get('trackid'))
                )
            else:
                await message.answer(
                    "Список заявок:", 
                    reply_markup=tickets_list(tickets)
                )


@router.callback_query(F.data.startswith(f"categories_"))
async def categories_callbacks(c: types.CallbackQuery, state: FSMContext):
    await state.clear()
    data = c.data.split("_")[1:]
    client_info = await api.client_get(c.message.chat.id)
    if not client_info:
        await c.answer("Внутренняя ошибка, обратитесь к администратору")
        return
    categories = await api.categories_get(client_info.get('isadmin'))
    action = data[0]
    if action == 'back':
        await state.clear()
        await c.message.edit_text(
            "Выберите нужную категорию:", 
            reply_markup=categories_list(categories),
            )
        await c.answer("Отмена создания заявки")
        return
    category_id = data[-1]
    category_name = "Не выбрано"
    for cat in categories:
        if str(cat.get('id')) == category_id:
            category_name = cat.get('name')
    match action:
        case "newticket":
            custom_fields = await api.custom_fields_mapping_by_category_id(category_id)
            for cf in custom_fields:
                if cf.get('default_value'):
                    cf['value'] = cf.get('default_value')
            ticket_data = {
                'name': client_info.get("fio"),
                'email': client_info.get("email"),
                'username': client_info.get("username"),
                'category_name': category_name,
                'category_id': category_id,
                'custom_fields': custom_fields,
            }
            await c.message.edit_text(
                ticket2text(ticket_data), 
                parse_mode=html_mode,
                reply_markup=back('categories')
                )
            log.debug(f'DATA FROM STATE >> {await state.get_data()}')
            await state.set_state(FormTicket.ticket_data)
            await state.update_data(ticket_data=ticket_data)

            await state.set_state(FormTicket.message_id)
            await state.update_data(message_id=c.message.message_id)

            await state.set_state(FormTicket.subject)
            # await c.message.answer("Напишите тему заявки, данные будут изменяться в сообщении")
            await c.answer(
                "Вписывайте поочередно данные для заявки. Стрелка в сообщении указывает на текущий вопрос",
                show_alert=True
                )
            log.debug(f'DATA FROM STATE >> {await state.get_data()}')
        case _:
            await c.answer('Ошибка')
            return
    return

def skip_actions_by_status(status: str):
    match status:
        case 'Решена':
            return ['inprogress', 'close', 'assigned']
        case 'В работе':
            return ['inprogress', 'open']
        case _:
            return ['open']
        
@router.callback_query(F.data.startswith(f"tickets_"))
async def tickets_callbacks(c: types.CallbackQuery, state: FSMContext):
    await state.clear()
    data = c.data.split("_")[1:]
    # client_info = await api.client_get(c.message.chat.id)
    action = data[0] 
    match action:
        case "send":
            ticket_id = data[-1]
            ticket_data: dict = await cache.get_dict(f"tickets_{ticket_id}")
            if not ticket_data:
                c.answer("Данные заявки не найдены")
                return
            custom_fields = {}
            custom_fields_list: list = ticket_data.get('custom_fields')
            if custom_fields_list:
                for cf in custom_fields_list:
                    custom_fields[cf.get('custom_id')] = cf.get('value')
            ticket = Ticket(
                name = ticket_data.get('name'),
                email= ticket_data.get('email'),
                subject= ticket_data.get('subject'),
                message= ticket_data.get('message'),
                category= ticket_data.get('category_id'),
                custom_fields= custom_fields,
            )
            log.debug(ticket)
            # await bot.delete_message(c.message.chat.id, ticket_id)
            await c.message.edit_text(
                ticket2text(ticket_data, stage='end', done=True), 
                parse_mode=html_mode,
                reply_markup=None,
                )
            await c.answer("Операция выполнена")
            await api.ticket_create(ticket)
            return
        case "get" | "reload":
            trackid = data[-1]
            ticket = api.ticket_get_by_trackid(trackid)
            if not ticket:
                await c.answer(f"Заявка {trackid} не найдена")
                return            
            try:
                skip_actions = skip_actions_by_status(ticket.get('status'))
                await c.message.edit_text(
                    ticket2workflow2text(ticket),
                    parse_mode=html_mode,
                    reply_markup=ticket_actions(ticket.get('trackid'), skip_actions)
                )
            except TelegramBadRequest as err:
                log.warning(err)
        case "hide":
            await c.message.delete()
        case "assigned":
            trackid = data[-1]
            ticket = api.ticket_get_by_trackid(trackid)
            admins = await api.admins_get()
            try:
                await c.message.edit_text(
                    ticket2workflow2text(ticket),
                    parse_mode=html_mode,
                    reply_markup=admins_list(admins, trackid)
                )
            except TelegramBadRequest as err:
                log.warning(err)
        case "assignedch":
            trackid = data[-1]
            on_change_id = data[-2]
            if on_change_id.isdigit():
                api.ticket_update_owner(trackid, on_change_id)
            ticket = api.ticket_get_by_trackid(trackid)
            try:
                skip_actions = skip_actions_by_status(ticket.get('status'))
                await c.message.edit_text(
                    ticket2workflow2text(ticket),
                    parse_mode=html_mode,
                    reply_markup=ticket_actions(ticket.get('trackid'), skip_actions=skip_actions)
                )
            except TelegramBadRequest as err:
                log.warning(err)
        case "close" | "open" | "inprogress":
            trackid = data[-1]
            new_status = 3
            skip_actions = ['open', 'assigned']
            if action == 'inprogress': 
                new_status = 4
                skip_actions.append('inprogress')
            elif action == 'open': 
                new_status = 0
            ticket = api.ticket_get_by_trackid(trackid)
            if not ticket:
                await c.answer(f"Заявка {trackid} не найдена")
                return
            api.ticket_update_status(data[-1], new_status=new_status)
            ticket['status'] = 'Изменен (Выполните синхронизацию)'
            try:
                await c.message.edit_text(
                    ticket2workflow2text(ticket),
                    parse_mode=html_mode,
                    reply_markup=ticket_actions(ticket.get('trackid'), skip_actions=skip_actions)
                )
            except TelegramBadRequest as err:
                log.warning(err)
        case "text":
            trackid = data[-1]
            ticket = api.ticket_get_by_trackid(trackid)
            if not ticket:
                await c.answer(f"Заявка {trackid} не найдена")
                return
            await c.message.answer(
                to_body(ticket.get('message'), max_len=4090, html=False), parse_mode=html_mode)
    await c.answer("Операция выполнена")