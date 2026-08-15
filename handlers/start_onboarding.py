import asyncio
import logging
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup

from config import BOT_TOKEN, ADMIN_IDS, API_URL, API_TOKEN, load_settings, save_settings
from services.remnawave_api import RemnawaveAPIAdapter
from services.panel_deployer import deploy_fresh_panel_async

logger = logging.getLogger("remna-bot.onboarding")
router = Router(name="onboarding_router")

class OnboardingStates(StatesGroup):
    waiting_for_url = State()
    waiting_for_token = State()

class PanelDeployStates(StatesGroup):
    waiting_for_ip = State()
    waiting_for_pass = State()
    waiting_for_panel_domain = State()
    waiting_for_sub_domain = State()

def is_admin(user_id: int) -> bool:
    return not ADMIN_IDS or user_id in ADMIN_IDS

def get_mini_app_keyboard(webapp_url: str = ""):
    kb = []
    if webapp_url and webapp_url.startswith("https://"):
        embed_url = f"{webapp_url.rstrip('/')}/remna_embed"
        kb.append([InlineKeyboardButton(text="📱 Открыть Remna-Bot MiniApp", web_app=WebAppInfo(url=embed_url))])
        kb.append([InlineKeyboardButton(text="⚙️ Подключить другую панель", callback_data="btn_connect_panel")])
    else:
        kb.append([InlineKeyboardButton(text="🚀 1-Click Деплой Свежей Панели", callback_data="btn_deploy_panel_wiz")])
        kb.append([InlineKeyboardButton(text="🔌 Подключить имеющуюся панель", callback_data="btn_connect_panel")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещен. Ваш ID не находится в списке ADMIN_CHAT_IDS.")
        return

    await state.clear()
    settings = load_settings()
    current_url = settings.get("api_url") or API_URL
    current_token = settings.get("api_token") or API_TOKEN

    if current_url and current_token:
        adapter = RemnawaveAPIAdapter(current_url, current_token)
        if await adapter.check_connection():
            ver = await adapter.detect_version()
            await message.answer(
                f"🚀 **Remna-Bot подключен и готов к работе!**\n\n"
                f"🔗 **Панель:** `{current_url}`\n"
                f"⚡ **Версия:** `{ver}`\n"
                f"🟢 **Статус:** Связь активна\n\n"
                f"Выберите действие ниже:",
                reply_markup=get_mini_app_keyboard(current_url),
                parse_mode="Markdown"
            )
            return

    await message.answer(
        "👋 **Приветствуем в Remna-Bot!**\n\n"
        "Панель еще не привязана. Нажмите кнопку ниже, чтобы развернуть новую панель на чистый VPS или подключить существующую в 1 клик!",
        reply_markup=get_mini_app_keyboard(),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "btn_open_app")
async def cb_open_app(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_text(
        "👋 **Панель управления Remna-Bot**\n\n"
        "Выберите необходимое действие:\n"
        "1️⃣ **🚀 1-Click Деплой Свежей Панели** — Автоматическая установка Docker, PostgreSQL 16, Remnawave Backend и Caddy SSL на чистый VPS.\n"
        "2️⃣ **🔌 Подключить имеющуюся панель** — Ввод URL и API Bearer Token уже существующей панели.",
        reply_markup=get_mini_app_keyboard(),
        parse_mode="Markdown"
    )

# --- 🔌 Подключение существующей панели ---

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
            f"Нажмите кнопку ниже для управления:",
            reply_markup=get_mini_app_keyboard(url),
            parse_mode="Markdown"
        )
    else:
        await msg.edit_text("❌ **Ошибка подключения!** Проверьте URL и API токен.")

# --- 🚀 1-Click Деплой Свежей Панели через Telegram ---

@router.callback_query(F.data == "btn_deploy_panel_wiz")
async def start_panel_deploy_wizard(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_text(
        "🚀 **1-Click Развертывание Свежей Панели Remnawave**\n\n"
        "Шаг 1 из 4: Отправьте **IP-адрес чистого VPS** (Ubuntu 22.04 / 24.04):",
        parse_mode="Markdown"
    )
    await state.set_state(PanelDeployStates.waiting_for_ip)

@router.message(PanelDeployStates.waiting_for_ip)
async def process_deploy_ip(message: types.Message, state: FSMContext):
    ip = message.text.strip()
    await state.update_data(ip=ip)
    await message.answer("🔑 Шаг 2 из 4: Отправьте **Root-пароль** от этого VPS:")
    await state.set_state(PanelDeployStates.waiting_for_pass)

@router.message(PanelDeployStates.waiting_for_pass)
async def process_deploy_pass(message: types.Message, state: FSMContext):
    password = message.text.strip()
    await state.update_data(password=password)
    await message.answer(
        "🌐 Шаг 3 из 4: Отправьте **Основной Домен Панели** (например `panel.domain.com`):\n\n"
        "⚠️ *Убедитесь, что заранее создали A-запись на IP сервера!*"
    )
    await state.set_state(PanelDeployStates.waiting_for_panel_domain)

@router.message(PanelDeployStates.waiting_for_panel_domain)
async def process_deploy_panel_domain(message: types.Message, state: FSMContext):
    panel_domain = message.text.strip().lower()
    await state.update_data(panel_domain=panel_domain)
    await message.answer(
        "🔗 Шаг 4 из 4: Отправьте **Домен подписок / Webhook** (например `sub.domain.com`):\n\n"
        "⚠️ *A-запись этого домена также должна указывать на IP сервера!*"
    )
    await state.set_state(PanelDeployStates.waiting_for_sub_domain)

@router.message(PanelDeployStates.waiting_for_sub_domain)
async def process_deploy_sub_domain(message: types.Message, state: FSMContext):
    sub_domain = message.text.strip().lower()
    data = await state.get_data()
    await state.clear()

    ip = data.get("ip")
    password = data.get("password")
    panel_domain = data.get("panel_domain")

    status_msg = await message.answer("🛠 **Инициализация установки Панели...**")
    main_loop = asyncio.get_running_loop()

    def progress_callback(update_text: str):
        try:
            asyncio.run_coroutine_threadsafe(
                status_msg.edit_text(f"🛠 **Процесс установки Панели:**\n\n{update_text}", parse_mode="Markdown"),
                main_loop
            )
        except Exception as e:
            logger.debug(f"Progress edit failed: {e}")

    result = await deploy_fresh_panel_async(
        host=ip,
        password=password,
        panel_domain=panel_domain,
        sub_domain=sub_domain,
        harden_vps=True,
        progress_cb=progress_callback
    )

    if result.get("success"):
        panel_url = f"https://{panel_domain}"
        admin_pass = result.get("admin_password", "")
        token = result.get("token", "")
        if token:
            save_settings(panel_url, token)

        await status_msg.edit_text(
            f"🎉 **Панель Remnawave успешно развернута!**\n\n"
            f"🌐 **URL Панели:** `{panel_url}`\n"
            f"👤 **Логин:** `admin`\n"
            f"🔑 **Пароль:** `{admin_pass}`\n\n"
            f"🔒 **SSH Порт VPS изменен на 5422** для защиты от брутфорса!\n\n"
            f"Нажмите кнопку ниже для управления нодами и сквадами:",
            reply_markup=get_mini_app_keyboard(panel_url),
            parse_mode="Markdown"
        )
    else:
        err = result.get("error", "Неизвестная ошибка")
        await status_msg.edit_text(f"❌ **Ошибка установки Панели:**\n\n{err}", parse_mode="Markdown")


