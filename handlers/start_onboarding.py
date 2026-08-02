import asyncio
import logging
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup

from config import BOT_TOKEN, ADMIN_IDS, API_URL, API_TOKEN, save_settings
from services.remnawave_api import RemnawaveAPIAdapter

logger = logging.getLogger("remna-bot.onboarding")
router = Router(name="onboarding_router")

class OnboardingStates(StatesGroup):
    waiting_for_url = State()
    waiting_for_token = State()

def is_admin(user_id: int) -> bool:
    return not ADMIN_IDS or user_id in ADMIN_IDS

def get_mini_app_keyboard(webapp_url: str = ""):
    kb = []
    if webapp_url:
        kb.append([InlineKeyboardButton(text="📱 Открыть Remna-Bot MiniApp", web_app=WebAppInfo(url=webapp_url))])
    else:
        # Fallback if local url is used
        kb.append([InlineKeyboardButton(text="🚀 Запустить Remna-Bot MiniApp", callback_data="btn_open_app")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещен. Ваш ID не находится в списке ADMIN_CHAT_IDS.")
        return

    current_url = API_URL
    current_token = API_TOKEN

    if current_url and current_token:
        adapter = RemnawaveAPIAdapter(current_url, current_token)
        if await adapter.check_connection():
            ver = await adapter.detect_version()
            await message.answer(
                f"🚀 **Remna-Bot MiniApp готов к работе!**\n\n"
                f"🔗 **Панель:** `{current_url}`\n"
                f"⚡ **Версия:** `{ver}`\n"
                f"🟢 **Статус:** Связь активна\n\n"
                f"Нажмите кнопку ниже для открытия интерфейса:",
                reply_markup=get_mini_app_keyboard(),
                parse_mode="Markdown"
            )
            return

    await message.answer(
        "👋 **Приветствуем в Remna-Bot!**\n\n"
        "Панель еще не привязана. Нажмите кнопку ниже, чтобы открыть MiniApp и развернуть новую панель или подключить существующую в 1 клик!",
        reply_markup=get_mini_app_keyboard(),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "btn_connect_panel")
async def start_panel_connection(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_text(
        "🔌 **Подключение к имеющейся панели Remnawave**\n\n"
        "Отправьте **URL вашей панели** (например `https://panel.domain.com`):",
        parse_mode="Markdown"
    )
    await state.set_state(OnboardingStates.waiting_for_url)

@router.message(OnboardingStates.waiting_for_url)
async def process_url_input(message: types.Message, state: FSMContext):
    url = message.text.strip().rstrip("/")
    if not url.startswith("http"):
        await message.answer("❌ Неверный формат URL. Ссылка должна начинаться с `http://` или `https://`.")
        return
    await state.update_data(api_url=url)
    await message.answer("🔑 Теперь отправьте **API Bearer Token** панели Remnawave:")
    await state.set_state(OnboardingStates.waiting_for_token)

@router.message(OnboardingStates.waiting_for_token)
async def process_token_input(message: types.Message, state: FSMContext):
    token = message.text.strip()
    data = await state.get_data()
    url = data.get("api_url")

    msg = await message.answer("⏳ **Проверка соединения...**")
    adapter = RemnawaveAPIAdapter(url, token)
    if await adapter.check_connection():
        ver = await adapter.detect_version()
        save_settings(url, token)
        await state.clear()
        await msg.edit_text(
            f"🎉 **Панель успешно подключена!**\n\n"
            f"🔗 **URL:** `{url}`\n"
            f"⚡ **Версия Remnawave:** `{ver}`\n\n"
            f"Нажмите кнопку ниже для запуска MiniApp:",
            reply_markup=get_mini_app_keyboard(),
            parse_mode="Markdown"
        )
    else:
        await msg.edit_text("❌ **Ошибка подключения!** Проверьте URL и API токен.")

