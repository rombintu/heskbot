from core.config import Config
from aiogram import Bot
from aiogram.client.bot import DefaultBotProperties

bot = Bot(Config.bot_token, default=DefaultBotProperties(link_preview_is_disabled=True))
