import functools
import asyncio
import signal
import sys

from tools.logger import logger
from core.main_route import start_bot

def exit(signame, loop):
    logger.warning(f'Received {signame} signal. Cancelling all tasks...')
    for task in asyncio.all_tasks():
        logger.info(f"Task: {task.get_name()} is stopped...")
        task.cancel()
    try:
        loop.stop()
        sys.exit(0)
    except RuntimeError as err:
        logger.error(err)

async def run_bot():
    await start_bot()

async def handle_signals():
    loop = asyncio.get_running_loop()
    for signame in {'SIGINT', 'SIGTERM'}:
        loop.add_signal_handler(
            getattr(signal, signame),
            functools.partial(exit, signame, loop))


async def main():
    bot_task = asyncio.create_task(run_bot(), name="Bot")
    handle_signals_task = asyncio.create_task(handle_signals(), name="Handler signals")

    tasks = [bot_task, handle_signals_task]
    group_tasks = asyncio.gather(*tasks)
    try:
        await group_tasks
    except KeyboardInterrupt:
        logger.info("Received SIGINT signal. Cancelling all tasks...")
        group_tasks.cancel()
    except Exception as err:
        logger.warning(err)
        group_tasks.cancel()

# TODO
if __name__ == "__main__":
    logger.info("Service is starting...")
    asyncio.run(main())


