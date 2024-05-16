from aiogram import Dispatcher, types
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext

from aiogram.fsm.storage.redis import RedisStorage
from core.content import start_message, reg_start_message, html_mode, NOT_OK, OK
# from core.keyboards import *
from tools.logger import logger
from core import tickets_route
from core import clients_route
from core import stats_route
from core import kb_route
from core.api import api
from core.bot import bot
from core.cache import cache
from tools import utils
from core.keyboards import client_reload_info, stats_admins_list, tickets_list, kb_categories_list
from dotenv import load_dotenv
load_dotenv()

dp = Dispatcher(storage=RedisStorage(redis=cache.driver))
dp.include_router(tickets_route.router)
dp.include_router(clients_route.router)
dp.include_router(kb_route.router)
dp.include_router(stats_route.router)


async def setup_bot_commands():
    bot_commands = [
        types.BotCommand(command="/start", description="Активация бота, помощь"),
        types.BotCommand(command="/profile", description="Регистрация, личный кабинет"),
        # types.BotCommand(command="/ticket", description="Создать новый тикет"),
        types.BotCommand(command="/knowledgebase", description="База знаний, меню"),
        types.BotCommand(command="/mylist", description="Получить мои заявки (как Клиента)"),
        types.BotCommand(command="/stats", description="Статистика. Администратор"),
        types.BotCommand(command="/mylistadm", description="Получить мои заявки. Администратор"),
        types.BotCommand(command="/search", description="Поиск тикета по треку или почте. Администратор"),
        types.BotCommand(command="/reset_categories", description="Очистка кеша (Категории). Администратор"),
        types.BotCommand(command="/reset_clients", description="Очистка кеша (Клиенты). Администратор"),
        types.BotCommand(command="/reset_knowledgebase", description="Очистка кеша (База знаний). Администратор"),        
    ]
    await bot.set_my_commands(bot_commands)

async def start_bot():
    logger.info("Bot is starting...")
    await setup_bot_commands()
    await dp.start_polling(bot)

@dp.message(Command('start', 'activate'))
async def handle_message_start(message: types.Message):
    await message.answer(
        start_message,
        parse_mode=html_mode
    )

# # Создание новой заявки
# @dp.message(Command('new', 'create', 'ticket'))
# @clients_route.check_client_isexist
# async def handle_command_new(message: types.Message):
#     # await state.set_state(tickets.FormTicket.name)
#     client_info = await api.client_get(message.chat.id)
#     if not client_info:
#         message.answer("Не удалось получить категории")
#         return
#     isadmin = client_info.get('isadmin')
#     filtered_categories = await api.categories_get(isadmin)
#     if not filtered_categories:
#         message.answer("Не удалось получить категории")
#         return 
#     await message.answer(
#         "Выберите нужную категорию:", 
#         reply_markup=categories_list(filtered_categories))

# Регистрация пользователя
@dp.message(Command('reg', 'registration', 'profile'))
async def handle_command_profile(message: types.Message, state: FSMContext):
    client_info = await api.client_get(message.chat.id)
    if not client_info:
        await cache.save("reg", NOT_OK, message.chat.id)
        await state.set_state(clients_route.ClientRegistrationInfo.fio)
        await message.answer(reg_start_message)
    elif client_info.get("error"):
        await message.answer(client_info["error"])
    else:
        await cache.save("reg", OK, message.chat.id)
        await message.answer(
            clients_route.client2text(message.chat.id, client_info), 
            reply_markup=client_reload_info(message.chat.id))
        
@dp.message(Command('reset_categories'))
@clients_route.check_client_isadmin
async def handle_command_reset_categories(message: types.Message, state: FSMContext):
    await cache.delete_dict("categories")
    async for key in cache.driver.scan_iter("custom_fields_mapping_*"):
        await cache.driver.delete(key)
    await message.answer("Операция выполнена")

@dp.message(Command('reset_knowledgebase'))
@clients_route.check_client_isadmin
async def handle_command_reset_categories(message: types.Message, state: FSMContext):
    async for key in cache.driver.scan_iter("kb_articles_*"):
        await cache.driver.delete(key)
    await message.answer("Операция выполнена")

@dp.message(Command('mylist'))
@clients_route.check_client_isexist
# @clients_route.check_client_isadmin
async def handle_command_get_my_tickets(message: types.Message):
    client_info = await api.client_get(message.chat.id)
    tickets = api.tickets_get_my_all(client_info.get('email'))
    if not tickets:
        await message.answer(f"Нет текущих заявок на вашу почту")
        return
    await message.answer("Список текущих заявок:", reply_markup=tickets_list(tickets))

@dp.message(Command('mylistadm'))
# @clients_route.check_client_isexist
@clients_route.check_client_isadmin
async def handle_command_get_my_tickets_adm(message: types.Message, state: FSMContext):
    client_info = await api.client_get(message.chat.id)
    tickets = api.tickets_get_my_all_adm(client_info.get('email'))
    if not tickets:
        await message.answer(f"Нет текущих заявок на вашу почту")
        return
    await message.answer("Список заявок назначенных на меня:", reply_markup=tickets_list(tickets))


@dp.message(Command('search'))
@clients_route.check_client_isadmin
async def handle_command_search_ticket(message: types.Message, state: FSMContext):
    await state.set_state(tickets_route.FormSearchTicket.track_or_email)
    await message.answer("Введите трек или почту заявителя, тикета который ищете\n/cancel - Отмена")

@dp.message(Command('stats'))
@clients_route.check_client_isadmin
async def handle_command_stats(message: types.Message, state: FSMContext):
    admins_list = await api.admins_get()
    if not admins_list:
        await message.answer('Исполнители не найдены, попробуйте позже')
        return
    admins_workloaded = api.admins_get_workloaded()
    admins_list = utils.admins_mapping_workloaded(admins_list, admins_workloaded)
    await message.answer("Статистика исполнителей:", reply_markup=stats_admins_list(admins_list))


@dp.message(Command('knowledgebase'))
@clients_route.check_client_isexist
async def handle_command_knowledgebase(message: types.Message):
    client_info = await api.client_get(message.chat.id)
    isadmin = client_info.get('isadmin')
    kb_categories = await api.kb_categories_get()
    kb_articles = await api.kb_articles_get()
    if not kb_categories:
        await message.answer('База знаний пока пуста')
    else:
        await message.answer(
            '🗄 База знаний:', 
            reply_markup=kb_categories_list(kb_categories, kb_articles, isadmin),
            )