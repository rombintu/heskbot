from tools.logger import logger as log
# import json
from core.api import api
from core.api import PostMessage, api_paths
from core.cache import cache
import pytest
import asyncio
from tools import utils 

def test_encode_to_json():
    pm = PostMessage("test", "test", "test")
    log.debug(api_paths["email"]["post"])

def test_send_code():
    error = api.send_code("rnikolskiy@at-consulting.ru", 111)
    log.debug(error.get("error"))


def test_cache():
    cache.clear("test")
    log.debug(cache.get("test"))
    cache.save("test", "testing1")
    value = cache.get("test")
    log.debug(value)
    assert value == "testing1"

async def test_get_client():
    resp = await api.client_get(0)
    log.debug(resp)


@pytest.mark.asyncio
async def test_save_client_info():
    client_info = {
        "isadmin": False,
        "email": "admin@admin.com",
        "username": "testing",
        "fio": "Ivanich"
    }
    telegram_id = 1111
    await cache.save_dict(client_info, telegram_id)
    # await cache.delete_client_info(telegram_id)
    pyalod = await cache.get_dict(telegram_id)
    log.debug(pyalod)

def test_client_reg():
    resp = api.client_registration(111, "admin@admin.com", "Ivan", None)
    log.debug(resp)

def test_html2text():
    html_text = """
<!DOCTYPE html>
<html>
<head>
    <title>Example HTML Page</title>
</head>
<body>
    <h1>Hello, World!</h1>
    <p>This is an example paragraph.</p>
    <p>Another paragraph with <a href="https://example.com">a link</a>.</p>
</body>
</html>
"""
    no_html_text = """
    Example HTML Page

Hello, World!
This is an example paragraph.
Another paragraph with a link.
"""
    html2text_right = utils.html2text(html_text)
    html2text_left = utils.html2text(no_html_text)
    log.debug(html2text_left)
    log.debug(html2text_right)
    

def test_save_file_from_ticket():
    filename = 'kenguru.png'
    data = api.attachments_get_data(filename)
    log.debug(data)