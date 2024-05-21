from aiogram import Router, F, types
from core.content import html_mode
from core.api import api
from tools.logger import logger as log
from tools import utils
from core.keyboards import stats_admins_list
from aiogram.exceptions import TelegramBadRequest

router = Router()

def filter_tickets(tickets: list):
    filter_data = {
        "total": len(tickets),
        "resolved": 0,
        "inprogress": 0,
        "tracks_inprogress": ""
    }
    for t in tickets:
        match t.get('status'):
            case 0:
                filter_data["tracks_inprogress"] += f"\n<code>{t.get('trackid')}</code>: Новая (Открыто)"
            case 1:
                filter_data["tracks_inprogress"] += f"\n<code>{t.get('trackid')}</code>: Получен комментарий"
            case 2:
                filter_data["tracks_inprogress"] += f"\n<code>{t.get('trackid')}</code>: Комментарий отправлен"
            case 3:
                filter_data["resolved"] += 1
            case 4:
                filter_data["inprogress"] += 1
                filter_data["tracks_inprogress"] += f"\n<code>{t.get('trackid')}</code>: В работе 🛠"
            case 5:
                filter_data["tracks_inprogress"] += f"\n<code>{t.get('trackid')}</code>: Приостановлена"
            case _:
                filter_data["tracks_inprogress"] += f"\n<code>{t.get('trackid')}</code>: Неизвестный статус"
    return filter_data

def get_admin_info(admins_list: list, search_admin_id: int):
    for a in admins_list:
        if a.get('id') == search_admin_id:
            return a
    return None

@router.callback_query(F.data.startswith(f"stats_"))
async def stats_callbacks(c: types.CallbackQuery):
    data = c.data.split("_")[1:]
    action = data[0] 
    match action:
        case "reload":
            admins_list = await api.admins_get(reload=True)
            if not admins_list:
                await c.answer('Исполнители не найдены, попробуйте позже')
                return
            admins_workloaded = api.admins_get_workloaded()
            admins_list = utils.admins_mapping_workloaded(admins_list, admins_workloaded)
            try:
                await c.message.edit_reply_markup(reply_markup=stats_admins_list(admins_list))
            except TelegramBadRequest as err:
                log.warning(err)
        case "get":
            admin_id = data[-1]
            if admin_id.isdigit():
                admin_id = int(admin_id)
            else:
                admin_id = None
            admins_list = await api.admins_get()
            if not admins_list:
                await c.answer('Исполнители не найдены, попробуйте позже')
                return
            admins_workloaded = api.admins_get_workloaded()
            admins_list = utils.admins_mapping_workloaded(admins_list, admins_workloaded)
            admin_info = get_admin_info(admins_list, admin_id)
            log.debug(admin_info)
            if not admins_list or not admin_info:
                await c.answer('Ошибка, попробуйте позже')
                return
            tickets_data: dict = api.tickets_get_by_user_id(admin_id)
            message = f"<b>{admin_info.get('name')}</b>\n{admin_info.get('email')}\n"
            if not tickets_data:
                message += "Ни одной заявки не найдено\nобновите информацию"
                await c.message.edit_text(
                    message, reply_markup=stats_admins_list(admins_list, admin_id), 
                    parse_mode=html_mode
                )
                return
            stat = filter_tickets(tickets_data)
            message += f"[♻️ <b>{stat['total']}</b>] "
            message += f"[✅ <b>{stat['resolved']}</b>] "
            message += f"[🛠 <b>{stat['inprogress']}</b>] "
            message += stat["tracks_inprogress"]
            message += f"\n{utils.admins_is_workloaded(stat['inprogress'])}"
            await c.message.edit_text(
                message, 
                reply_markup=stats_admins_list(admins_list, admin_id), 
                parse_mode=html_mode)
    await c.answer("Операция выполнена")