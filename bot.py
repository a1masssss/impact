import asyncio
import logging
import os
import json
import requests
from aiogram import Bot, Dispatcher, F, types
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from aiogram.types import Message
from aiogram import Router
from dotenv import load_dotenv

# ---------- ЗАГРУЗКА ПЕРЕМЕННЫХ ----------
load_dotenv()

API_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
MANAGERS_CHAT_ID = int(os.getenv("MANAGERS_CHAT_ID"))
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

# ---------- ИНИЦИАЛИЗАЦИЯ ----------
logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()
dp.include_router(router)

# ---------- СОСТОЯНИЯ ----------
class LeadForm(StatesGroup):
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_country = State()
    waiting_for_voice = State()

# ---------- ХЕНДЛЕРЫ ----------
@router.message(F.text == "/start")
async def cmd_start(message: Message, state: FSMContext):
    await state.set_state(LeadForm.waiting_for_name)
    await message.answer("Здравствуйте! Я бот для записи в нашу программу. Пожалуйста, введите ваше ФИО:")

@router.message(StateFilter(LeadForm.waiting_for_name))
async def get_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(LeadForm.waiting_for_phone)
    await message.answer("Отлично! Теперь введите свой номер телефона:")

@router.message(StateFilter(LeadForm.waiting_for_phone))
async def get_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await state.set_state(LeadForm.waiting_for_country)
    await message.answer("Спасибо! Теперь укажите страну, куда хотите поехать:")

@router.message(StateFilter(LeadForm.waiting_for_country))
async def get_country(message: Message, state: FSMContext):
    await state.update_data(country=message.text)
    await state.set_state(LeadForm.waiting_for_voice)
    await message.answer("Принято! Хотите оставить голосовое сообщение? Пришлите его или введите /skip.")

@router.message(F.text == "/skip", StateFilter(LeadForm.waiting_for_voice))
async def skip_voice(message: Message, state: FSMContext):
    await state.update_data(voice_text=None)
    user_data = await state.get_data()
    save_to_notion(user_data)
    await notify_managers(user_data)
    await message.answer("Спасибо! Ваши данные сохранены. Мы свяжемся с вами.")
    await state.clear()

@router.message(StateFilter(LeadForm.waiting_for_voice), F.voice)
async def handle_voice(message: Message, state: FSMContext):
    await state.update_data(voice_text="<Голосовое сообщение>")
    user_data = await state.get_data()
    save_to_notion(user_data)
    await notify_managers(user_data)
    await message.answer("Спасибо! Голосовое получено. Мы с вами свяжемся!")
    await state.clear()

@router.message(StateFilter(LeadForm.waiting_for_voice))
async def handle_other(message: Message):
    await message.answer("Пожалуйста, отправьте голосовое или введите /skip.")

# ---------- СЕРВИС ----------
def save_to_notion(user_data: dict):
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    new_page = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "Name": {
                "title": [{"text": {"content": user_data.get("name", "")}}]
            },
            "Phone Number": {
                "phone_number": user_data.get("phone", "")
            },
            "Countries": {
                "rich_text": [{"text": {"content": user_data.get("country", "")}}]
            }
        }
    }

    response = requests.post(url, headers=headers, data=json.dumps(new_page))
    if response.status_code != 200:
        logging.error("Ошибка при отправке в Notion: %s", response.text)
    else:
        logging.info("Данные успешно сохранены в Notion")

async def notify_managers(user_data: dict):
    text = (
        f"<b>Новый лид!</b>\n"
        f"<b>ФИО:</b> {user_data.get('name')}\n"
        f"<b>Телефон:</b> {user_data.get('phone')}\n"
        f"<b>Страна:</b> {user_data.get('country')}\n"
        f"<b>Голосовое:</b> {user_data.get('voice_text') or 'нет'}"
    )
    await bot.send_message(chat_id=MANAGERS_CHAT_ID, text=text)

# ---------- ЗАПУСК ----------
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
