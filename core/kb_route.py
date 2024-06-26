import base64
from aiogram import Router, F, types
from core.api import api
from tools.logger import logger as log
from core.keyboards import kb_categories_list 
from aiogram.exceptions import TelegramBadRequest
from tools.utils import to_body, parse_image_from_html
from aiogram.utils.media_group import MediaGroupBuilder

router = Router()

@router.callback_query(F.data.startswith(f"kb_"))
async def kb_callbacks(c: types.CallbackQuery):
    data = c.data.split("_")[1:]
    action = data[0]
    client_info = await api.client_get(c.message.chat.id)
    isadmin = client_info.get('isadmin')
    kb_categories = await api.kb_categories_get()
    kb_articles = await api.kb_articles_get()
    match action:
        case "list":
            position = int(data[-1]) if data[-1].isdigit() else 1
            try:
                await c.message.edit_text(
                    '🗄 База знаний:', 
                    reply_markup=kb_categories_list(kb_categories, kb_articles, isadmin, position=position),
                    )
            except TelegramBadRequest as err:
                log.warning(err)            
        case "reload":
            kb_categories = await api.kb_categories_get(reload=True)
            kb_articles = await api.kb_articles_get(reload=True)
            try:
                await c.message.edit_text(
                    '🗄 База знаний:', 
                    reply_markup=kb_categories_list(kb_categories, kb_articles, isadmin),
                    )
            except TelegramBadRequest as err:
                log.warning(err)
        case "read":
            article_id = int(data[-1]) if data[-1].isdigit() else None
            if not article_id:
                await c.answer('Ошибка')
                return
            article = await api.kb_article_get_content(article_id)
            content = to_body(article.get('content'), 4090, False)
            images: list[str] = parse_image_from_html(article.get('content'))
            if images:
                media_group = MediaGroupBuilder(caption=f"Файлы из статьи {article_id}")
                for i, img in enumerate(images):
                    b_img = None
                    try:
                        b_img = base64.b64decode(img)
                    except Exception as err:
                        log.error(err)
                        continue

                    media_group.add_photo(types.BufferedInputFile(
                        file=b_img, filename=f'image{i}'
                    ))
                await c.message.answer_media_group(
                    media=media_group.build()
                    )
            await c.message.edit_text(
                f"<b>{article.get('subject')}:</b>\n{content}", 
                reply_markup=kb_categories_list(None, None, isadmin, position=0), 
                parse_mode='html')
        case _:
            await c.answer('Ошибка')
            return
    await c.answer("Операция выполнена")