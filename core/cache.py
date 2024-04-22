# import asyncio
import aioredis
import aioredis.exceptions
from tools.logger import logger as log
from tools.utils import exist_or_none
import json
import pickle

class Cache:
    def __init__(self):
        self.driver = aioredis.Redis() # Connect to localhost
    
    async def save(self, key: str, value: str, uuid: int = 0):
        log.debug(f"CACHE | SAVE [{key}] | [{value}]")
        await self.driver.set(f"user:{uuid}:{key}", value.encode(), ex=86400)

    async def get(self, key: str, uuid: int = 0):
        value = await self.driver.get(f"user:{uuid}:{key}")
        log.debug(f"CACHE | LOAD [{uuid}:{key}] | [{value}]")
        return exist_or_none(value)
    
    async def clear(self, key: str, uuid: int = 0):
        log.debug(f"CACHE | CLEAR [{uuid}:{key}]")
        await self.driver.delete(f"user:{uuid}:{key}")

    # async def save_client_info(self, telegram_id: int,  client_info: dict):
    #     name = f"client_info_{telegram_id}"
    #     await self.driver.set(name, pickle.dumps(client_info))
        # for k, v in client_info.items():
        #     log.debug(f"CACHE | HASH SAVE {name}[{k}] | [{v}]")
        #     await self.driver.hset(name, k, str(v))
    
    # async def get_client_info(self, telegram_id: int):
    #     name = f"client_info_{telegram_id}"
    #     log.debug(f"CACHE | HASH LOAD ALL INFO FOR [{name}]")
    #     client_info = await self.driver.get(name)
    #     if client_info:
    #         return pickle.loads(client_info)
    #     return client_info
        # return {
        #     "isadmin" :  exist_or_none(await self.driver.hget(name, "isadmin"), want_type="bool"),
        #     "email":  exist_or_none(await self.driver.hget(name, "email")),
        #     "username": exist_or_none(await self.driver.hget(name, "username")),
        #     "fio": exist_or_none(await self.driver.hget(name, "fio"))
        # }

    async def save_dict(self, data: dict, name: str):
        log.debug(f"CACHE | SAVE JSON [{name}] | {data}")
        await self.driver.set(name, pickle.dumps(data), ex=86400)
    
    async def get_dict(self, name: str):
        data = await self.driver.get(name)
        if data:
            data = pickle.loads(data)
        log.debug(f"CACHE | LOAD JSON [{name}] | {data}")
        return data
    # async def try_get_client_info(self, telegram_id: int):
    #     skip = ["username"] # TODO
    #     client_info = await self.get_client_info(telegram_id)
    #     for k, v in client_info.items():
    #         if k in skip and not v:
    #             continue
    #         if not v:
    #             return None
    #     return client_info
    
    async def delete_dict(self, name):
        log.debug(f"CACHE | HASH DELETE DICT [{name}]")
        await self.driver.delete(name)

cache = None
try:
    cache = Cache()
except aioredis.exceptions.ConnectionError as err:
    log.error(err)
