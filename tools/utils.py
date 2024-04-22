from tools.logger import logger as log
from datetime import datetime

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
    
statuses = {
    0: "Новая",
    1: "Получен комментарий",
    2: "Комментарий отправлен",
    3: "Решена",
    4: "В работе",
    5: "Приостановлена",
}
