from tools.logger import logger as log
from datetime import datetime
from bs4 import BeautifulSoup as bs
from core.config import Config
# from jinja2 import Environment, FileSystemLoader
# import requests
import ssl
# from io import BytesIO
from urllib import request
import pathlib

tmp_dir = pathlib.Path('./tmp')

def str2bool(s: str):
    if s.lower() in ["true", "1"]:
        return True
    return False

def exist_or_none(val, want_type='str'):
    if not val:
        return None
    match want_type:
        case "str":
            return val.decode()
        case "int":
            val = val.decode()
            if val.isdigit():
                return int(val)
            return None
        case "bool":
            return str2bool(val.decode())
        case _: 
            return None
        
def is_client_info(client_info: dict):
    if not client_info:
        return False
    flag = True
    keys_to_check = ["isadmin", "email", "username", "fio"]
    for key in keys_to_check:
        if key not in client_info.keys():
            flag = False
    return flag

def validate_date(date_str: str):
    try:
        datetime.strptime(date_str, "%d-%m-%Y")
        return True
    except ValueError:
        return False

def get_today():
    return datetime.now().strftime("%d-%m-%Y")

def if_type_is_date(row: dict):
    value: str = row.get('value')
    if not value:
        return '-'
    value = int(value) if value.isdigit() else None
    if not value: return value
    date = datetime.fromtimestamp(value)
    return date.strftime("%d-%m-%Y")

# statuses = {
#     0: "Новая",
#     1: "Получен комментарий",
#     2: "Комментарий отправлен",
#     3: "Решена",
#     4: "В работе",
#     5: "Приостановлена",
# }

def file_exist(filepath: pathlib.Path):
    if filepath.exists() and filepath.is_file():
        return True
    return False

def file_get(filename: str):
    filepath = tmp_dir.joinpath(filename)
    if file_exist(filepath):
        return filepath
    else:
        return None 

def parse_image_from_html(html_text: str):
    soup = bs(html_text, 'html5lib')
    images: list[str] = soup.findAll('img')
    images_bytes = []
    if images:
        for image in images:
            images_bytes.append(image['src'].replace('data:image/png;base64,', ''))
    return images_bytes

def parse_attachment_from_ticket_url(att_id: int, trackid: str):
    self_signed_cert_context = ssl.create_default_context()
    self_signed_cert_context.check_hostname = False
    self_signed_cert_context.verify_mode = ssl.CERT_NONE
    try:
        log.debug(f"{Config.web_url}/download_attachment.php?att_id={att_id}&track={trackid}&token=pBXZrGpJrBzppPuuNkGDuwM.zXw5H1")
        with request.urlopen(
            f"{Config.web_url}/download_attachment.php?att_id={att_id}&track={trackid}",
            context=self_signed_cert_context) as f:
            return f.read()
    except Exception as err:
        log.error(err)
    return None

def html2text(html_text: str):
    soup = bs(html_text, 'html5lib')
    return soup.get_text()

def to_body(html_or_text: str, max_len=255, html=True):
    warning_symbols = ['<', '>']
    body: str = html2text(html_or_text)
    if len(body) > max_len:
        body = body[:max_len] + "..."
    for s in warning_symbols:
        if s in body:
            body = body.replace(s, '🔸')
    if html:
        return f'<code>{body}</code>'
    else:
        return body

def priorities(p: str):
    priority = "🤷‍♂️ Неизвестный"
    if p and p.isdigit():
        p = int(p)
        if 0 <= p <= 3:
            priority = {
                0: "🚨 Критический",
                1: "🚀 Высокий",
                2: "🏎 Нормальный",
                3: "🦽 Низкий"
            }.get(p)
    return priority

def admins_mapping_workloaded(admins_list: list, admins_workloaded: list):
    for a1 in admins_list:
        found = False
        for a2 in admins_workloaded:
            if a1['id'] == a2['id']:
                a1['inprogress'] = a2['inprogress']
                found = True
                break
        if not found:
            a1['inprogress'] = 0
    return admins_list

def admins_is_workloaded(value: int):
    is_not_workloaded = "Свободен 😴"
    if value == 0:
        return is_not_workloaded
    elif value in [1,2,3]:
        return "Относительно свободен 😏"
    elif value in [4,5]:
        return "Загружен 🫡"
    elif value > 5:
        return "Очень загружен 💀"
    return is_not_workloaded
