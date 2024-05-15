from tools.logger import logger as log
from datetime import datetime
from bs4 import BeautifulSoup as bs

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
    if p.isdigit():
        p = int(p)
        if 0 <= p <= 3:
            priority = {
                0: "🚨 Критический",
                1: "🚀 Высокий",
                2: "🏎 Нормальный",
                3: "🦽 Низкий"
            }.get(p)
    return priority