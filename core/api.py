import requests, json
from dataclasses import dataclass, is_dataclass, asdict
from core.config import Config
from core.cache import cache
from tools.logger import logger as log
from tools.utils import is_client_info
import aiohttp

api_paths = {
    "tickets": {
        "default": "tickets",
        "post": "tickets",
    },
    "email": {
        "post": "email"
    },
    "clients": {
        "get": "clients/{telegram_id}",
        "post": "clients/create",
        "delete": "clients/{telegram_id}",
        "reload": "clients/reload/{telegram_id}"
    },
    "categories": {
        "get": "categories",
        "custom_fields_mapping": "custom_fields/mapping/{category_id}"
    }
}


@dataclass
class Ticket:
    name: str
    email: str
    subject: str
    message: str
    category: int
    custom_fields: dict # customX: value


@dataclass
class PostMessage:
    subject: str
    to_addr: str
    body: str
    is_html: bool = False

@dataclass
class Client:
    telegram_id: int
    email: str
    fio: str
    username: str

internal_error = {"error": "500. Повторите попытку позже"}

class API:
    headers = {"content-type": "application/json"}
    def __init__(self, url: str):
        self.url = url

    def post_request(self, path, data):
        response = internal_error
        try:
            resp = requests.post(f"{self.url}/{path}", json=data, headers=self.headers)
            log.debug(data)
            log.debug(resp.url)
            response = resp.json()
        except requests.exceptions.ConnectionError as errConn:
            log.error(errConn)
        return response
    
    async def async_post_request(self, path, data):
        error = internal_error
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.url}/{path}", json=data):
                    log.debug(f"async POST request to {self.url}/{path}")
                    error = {}
        except requests.exceptions.ConnectionError as errConn:
            log.error(errConn)
        return error
        
    def get_request(self, path, params={}):
        response = internal_error
        try:
            reps = requests.get(f"{self.url}/{path}", headers=self.headers, params=params)
            log.debug(reps.url)
            response = reps.json()
        except requests.exceptions.ConnectionError as errConn:
            log.error(errConn)
        return response
        
    def delete_request(self, path):
        response = internal_error
        try:
            resp = requests.delete(f"{self.url}/{path}", headers=self.headers)
            log.debug(resp.url)
            response = resp.json()
        except requests.exceptions.ConnectionError as errConn:
            log.error(errConn)
        return response

    async def tickets_get_my_all(self, email: str):
        # tickets = await cache.get_dict(f"mytickets_{telegram_id}")
        # if reload or not tickets:
        params = {'email': email}
        tickets = self.get_request(api_paths['tickets']['default'], params)
        if not tickets:
            return []
            # await cache.save_dict(tickets, f"mytickets_{telegram_id}")
        return tickets

    async def tickets_get_my_all_adm(self, email: str):
        # tickets = await cache.get_dict(f"mytickets_{telegram_id}")
        # if reload or not tickets:
        params = {'admin_email': email}
        tickets = self.get_request(api_paths['tickets']['default'], params)
        if not tickets:
            return []
            # await cache.save_dict(tickets, f"mytickets_{telegram_id}")
        return tickets
    
    def ticket_get_by_trackid(self, trackid: str):
        params = {'track': trackid}
        ticket = self.get_request(api_paths['tickets']['default'], params)
        if not ticket:
            return {}
            # await cache.save_dict(tickets, f"mytickets_{telegram_id}")
        return ticket

    async def ticket_create(self, ticket: Ticket):
        log.debug(ticket)
        await self.async_post_request(api_paths["tickets"]["post"], ticket.__dict__)

    def send_code(self, to_addr: str, code: int, subject="Регистрация пользователя в БКС_бот"):
        message = PostMessage(
            subject, to_addr, f"Ваш код для регистрации <b>{code}</b>", is_html=True
        )
        response = self.post_request(api_paths["email"]["post"], message.__dict__)
        return response
    
    def client_registration(self, telegram_id: int, email: str, fio: str, username: str = None):
        client_data = Client(telegram_id, email, fio, username)
        response = self.post_request(api_paths["clients"]["post"], client_data.__dict__)
        return response
    
    async def client_get(self, telegram_id: int):
        client_info = await cache.get_dict(telegram_id)
        if client_info:
            return client_info
        response = self.get_request(api_paths["clients"]["get"].format(telegram_id=telegram_id))
        if is_client_info(response):
            await cache.save_dict(response, telegram_id)
            return response
        return None
    
    async def client_delete(self, telegram_id: int):
        response = self.delete_request(api_paths["clients"]["delete"].format(telegram_id=telegram_id))
        if not response:
            await cache.delete_dict(telegram_id)
        return response
    
    async def client_reload(self, telegram_id: int):
        response = self.get_request(api_paths["clients"]["reload"].format(telegram_id=telegram_id))
        if is_client_info(response):
            await cache.save_dict(response, telegram_id)
        return response
    
    @staticmethod
    def filter_categories(categories: dict, isadmin: False):
        filtered_categories = []
        for c in categories:
            if not isadmin and c.get('type') == '1':
                continue    
            filtered_categories.append(c)
        return filtered_categories

    async def categories_get(self, isadmin=False):
        categories = await cache.get_dict(api_paths["categories"]["get"])
        if categories:
            return self.filter_categories(categories, isadmin)
        response = self.get_request(api_paths["categories"]["get"])
        if type(response) == list and len(response) > 0:
            categories = [
                    {
                        "id": c.get("id"),
                        "name": c.get("name"),
                        "type": c.get("type")
                    } for c in response
                ]
            await cache.save_dict(categories, api_paths["categories"]["get"])
            return self.filter_categories(categories, isadmin)
        return []
    
    async def custom_fields_mapping_by_category_id(self, category_id):
        custom_fields = await cache.get_dict(f"custom_fields_mapping_{category_id}")
        if custom_fields:
            return custom_fields
        response = self.get_request(
            api_paths["categories"]["custom_fields_mapping"].format(category_id=category_id))
        if type(response) == list and len(response) > 0:
            custom_fields = [
                    {
                        "id": c.get("id"),
                        "custom_id": f"custom{c.get('id')}",
                        "name": c.get("name"),
                        "type": c.get("type"), # text, select, checkbox, date 
                        "req": int(c.get("req")) if c.get('req').isdigit() else 0,
                        "value": None,
                        "default_value": 
                            c.get("value").get("default_value") 
                            if c.get("value") else None,
                        "select_options": 
                            c.get("value").get("select_options") 
                            if c.get("value") else [],
                        "checkbox_options": 
                            c.get("value").get("checkbox_options") 
                            if c.get("value") else [],
                        "radio_options":
                            c.get("value").get("radio_options") 
                            if c.get("value") else [],
                    } for c in response
                ]
            await cache.save_dict(custom_fields, f"custom_fields_mapping_{category_id}")
            return custom_fields
        return []

api = API(Config.api_url)
