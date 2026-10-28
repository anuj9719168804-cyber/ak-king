import asyncio
import importlib
import signal
from pyrogram import idle
from Extractor.modules import ALL_MODULES

loop = asyncio.get_event_loop()

# Graceful shutdown
should_exit = asyncio.Event()

def shutdown():
    print("Shutting down gracefully...")
    should_exit.set()  # triggers exit from idle

for _sig in (signal.SIGTERM, signal.SIGINT):
    try:
        loop.add_signal_handler(_sig, shutdown)
    except (NotImplementedError, RuntimeError):
        pass

async def sumit_boot():
    for all_module in ALL_MODULES:
        importlib.import_module("Extractor.modules." + all_module)

    print("» ʙᴏᴛ ᴅᴇᴘʟᴏʏ sᴜᴄᴄᴇssғᴜʟʟʏ ✨ 🎉")
    idle_task = asyncio.ensure_future(idle())
    exit_task = asyncio.ensure_future(should_exit.wait())
    await asyncio.wait({idle_task, exit_task}, return_when=asyncio.FIRST_COMPLETED)
    for t in (idle_task, exit_task):
        t.cancel()

    print("» ɢᴏᴏᴅ ʙʏᴇ ! sᴛᴏᴘᴘɪɴɢ ʙᴏᴛ.")

if __name__ == "__main__":
    try:
        loop.run_until_complete(sumit_boot())
    except KeyboardInterrupt:
        print("Interrupted by user.")
    finally:
        # Cancel pending tasks to avoid "destroyed but pending" error
        pending = asyncio.all_tasks(loop)
        for task in pending:
            task.cancel()
        loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        loop.close()
        print("Loop closed.")
