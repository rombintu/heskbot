from random import randint

from core.api import api
from core.config import Config
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram import Router, F, types
from core.cache import cache
from core.keyboards import client_reload_info
from aiogram.exceptions import TelegramBadRequest
from tools.logger import logger as log
# from core import bot
from core.content import NOT_OK, OK, reg_email_message, reg_code_message

router = Router()

class ClientRegistrationInfo(StatesGroup):
    fio = State()
    email = State()
    code = State()

def client2text(telegram_id, client: dict):
    return f"""{client.get('fio')}:\
        \n👨‍💻 Вы {'администратор' if client.get('isadmin') else "клиент"}\
        \n📨 {client.get('email')}\
        \n🔗 {'Ссылка скрыта' if not client.get('username') else '@'+client.get('username')} 🆔 {telegram_id}
        """

def check_client_isexist(func):
    async def wrapper(message: types.Message):
        client = None
        ok = await cache.get("reg", message.chat.id)
        match ok:
            case "OK":
                await func(message) # Идем дальше
            case "NOT OK" | None:
                # Не пропускаем дальше
                await message.answer("Анонимные заявки не разрешены.\nПройдите пожалуйста проверку /profile")
            case None:
                client = await api.client_get(message.chat.id)
                if client:
                    await cache.save("reg", OK, message.chat.id)
                    await func(message) # Идем дальше
                else:
                    await cache.save("reg", NOT_OK, message.chat.id)
    return wrapper

def check_client_isexist_with_state(func):
    async def wrapper(message: types.Message, state: FSMContext):
        client = None
        ok = await cache.get("reg", message.chat.id)
        match ok:
            case "OK":
                await func(message, state) # Идем дальше
            case "NOT OK" | None:
                # Не пропускаем дальше
                await message.answer("Анонимные заявки не разрешены.\nПройдите пожалуйста проверку /profile")
            case None:
                client = await api.client_get(message.chat.id)
                if client:
                    await cache.save("reg", OK, message.chat.id)
                    await func(message, state) # Идем дальше
                else:
                    await cache.save("reg", NOT_OK, message.chat.id)
    return wrapper


def check_client_isadmin(func):
    async def wrapper(message: types.Message, state: FSMContext):
        client = await api.client_get(message.chat.id)
        if client and client.get('isadmin'):
            await func(message, state)
        else:
            await message.answer("Вы не являетесь администратором")
    return wrapper

@router.message(ClientRegistrationInfo.fio)
async def handle_client_fio(message: types.Message, state: FSMContext):
    match message.text:
        case "/cancel":
            await message.answer("Отмена создания заявки")
            await state.clear()
        case None:
            await state.set_state(ClientRegistrationInfo.fio)
            await message.answer("Ожидается почта at-consulting\n/cancel - Отмена")
        case _:
            if len(message.text) < 8:
                await message.answer("Ожидается полное имя")
                await message.answer("Отмена создания заявки")
                await state.clear()
                return
            await state.update_data(fio=message.text)
            await state.set_state(ClientRegistrationInfo.email)
            await message.answer(reg_email_message)


@router.message(ClientRegistrationInfo.email)
async def handle_client_email(message: types.Message, state: FSMContext):
    match message.text:
        case "/cancel":
            await message.answer("Отмена создания заявки")
            await state.clear()
        case None:
            await state.set_state(ClientRegistrationInfo.email)
            await message.answer("Ожидается почта at-consulting\n/cancel - Отмена")
        case _:
            if message.text.split("@")[-1] != Config.valid_host_mail:
                await message.answer("Введен неправильный адрес почты. Обратитесь к администратору")
                await message.answer("Отмена создания заявки")
                await state.clear()
                return
            client_email = message.text.strip()
            await state.update_data(email=client_email)
            await state.set_state(ClientRegistrationInfo.code)
            # TODO
            code = randint(100000, 999999)
            if code % 2 != 0:
                code += 1
            await state.update_data(code=code)
            error = api.send_code(client_email, code)
            if error.get("error"):
                await message.answer(error.get("error"))
                return
            await message.answer(reg_code_message)

@router.message(ClientRegistrationInfo.code)
async def handle_client_code(message: types.Message, state: FSMContext):
    match message.text:
        case "/cancel":
            await message.answer("Отмена создания заявки")
            await state.clear()
        case None:
            await state.set_state(ClientRegistrationInfo.code)
            await message.answer("Ожидается код с почты\n/cancel - Отмена")
        case _:
            data_by_context = await state.get_data()
            # If values is None in data, try get value from cache
            if str(data_by_context.get("code")) == message.text:
                # TODO REG
                error = api.client_registration(
                    telegram_id=message.chat.id, 
                    email=data_by_context.get("email"), 
                    fio=data_by_context.get("fio"),
                    username=message.chat.username)
                if error:
                    await message.answer(error.get("error"))
                    await state.clear()
                    return
                await cache.save("reg", "OK", message.chat.id)
                await message.answer("Регистрация прошла успешно ✅")
            else:
                await message.answer("Введенный код неверен, обратитесь к администратору сервиса")


@router.callback_query(F.data.startswith(f"clients_"))
async def clients_callbacks(c: types.CallbackQuery):
    data = c.data.split("_")[1:]
    action = data[0]
    telegram_id = data[-1]
    match action:
        case "delete":
            error = await api.client_delete(telegram_id)
            if error and error.get('error'):
                await c.answer(error['error'])
                return
            await c.message.delete()
        case "reload":
            client_or_error = await api.client_reload(telegram_id)
            if client_or_error and client_or_error.get('error'):
                await c.answer(client_or_error['error'])
                return
            try:
                if not client_or_error:
                    await c.message.edit_text("Вы не зарегистрированы\n/profile - Регистрация")
                    return
                await c.message.edit_text(
                    client2text(c.message.chat.id, client_or_error), 
                    reply_markup=client_reload_info(client_or_error.get("telegram_id")))
            except TelegramBadRequest as err:
                log.warning(err)
        case _:
            await c.answer('Ошибка')
    await c.answer("Операция выполнена")