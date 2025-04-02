import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message
from aiogram import Router

API_TOKEN = "7487382135:AAG1Jd7HiHEPlUXYYKbAsW6woCRJPF855sg"

bot = Bot(
    token=API_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

# Используем router, чтобы его включить в Dispatcher
router = Router()

@router.message()
async def get_chat_id(message: Message):
    await message.answer(f"Chat ID: <code>{message.chat.id}</code>")
    print("CHAT ID:", message.chat.id)

dp = Dispatcher()

async def main():
    dp.include_router(router)  
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
