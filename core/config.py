import os
from dotenv import load_dotenv
load_dotenv()

class Config:
    bot_token = os.getenv("BOT_TOKEN")
    api_url = os.getenv("API_URL")
    valid_host_mail = os.getenv("VALID_HOST_MAIL")