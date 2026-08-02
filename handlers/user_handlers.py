import asyncio
import logging
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from config import API_URL, API_TOKEN, load_settings
from services.remnawave_api import RemnawaveAPIAdapter

logger = logging.getLogger("remna-bot.user-handlers")
router = Router(name="user_router")

def get_api_adapter() -> RemnawaveAPIAdapter:
    settings = load_settings()
    url = settings.get("api_url") or API_URL
    token = settings.get("api_token") or API_TOKEN
    return RemnawaveAPIAdapter(url, token)

class UserSearchStates(StatesGroup):
    waiting_for_query = State()

@router.callback_query(F.data == "btn_users")
async def cb_start_user_search(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_text(
        "👥 **Поиск пользователя Remnawave**\n\n"
        "Отправьте **Telegram ID, Username или UUID** пользователя для поиска:",
        parse_mode="Markdown"
    )
    await state.set_state(UserSearchStates.waiting_for_query)

@router.message(UserSearchStates.waiting_for_query)
async def process_user_search_query(message: types.Message, state: FSMContext):
    query = message.text.strip()
    await state.clear()

    adapter = get_api_adapter()
    users = await adapter.fetch_users_list(query=query)

    if not users:
        await message.answer(
            f"❌ Пользователи по запросу `{query}` не найдены.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔍 Искать снова", callback_data="btn_users")]
            ]),
            parse_mode="Markdown"
        )
        return

    text = f"👥 **Результаты поиска ({len(users)}):**\n\n"
    kb = []
    for u in users[:10]:
        usr_id = u.get("id") or u.get("uuid") or "user"
        raw_name = u.get("username") or ""
        tg_id = u.get("telegramId") or ""
        
        display_name = raw_name or (f"user_{tg_id}" if tg_id else f"ID: {usr_id[:8]}")
        traffic_used = u.get("usedTraffic", 0) // (1024**2) # MB
        
        text += f"• **{display_name}** `[TG: {tg_id or '—'}]` — {traffic_used} MB трафика\n"
        kb.append([InlineKeyboardButton(text=f"👤 {display_name}", callback_data=f"usr_detail:{usr_id}")])

    kb.append([InlineKeyboardButton(text="🔍 Новый поиск", callback_data="btn_users")])

    await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="Markdown")

@router.callback_query(F.data.startswith("usr_detail:"))
async def cb_user_detail(callback: types.CallbackQuery):
    await callback.answer()
    user_id = callback.data.split(":")[1]
    adapter = get_api_adapter()
    users = await adapter.fetch_users_list(query=user_id)

    if not users:
        await callback.message.edit_text("❌ Пользователь не найден.")
        return

    u = users[0]
    uuid_str = u.get("uuid", str(user_id))
    name = u.get("username") or u.get("telegramId") or uuid_str
    traffic_used = u.get("usedTraffic", 0) // (1024**3) # GB
    traffic_limit = u.get("trafficLimit", 0) // (1024**3) if u.get("trafficLimit") else "∞"

    text = (
        f"👤 **Карточка пользователя: {name}**\n\n"
        f"🆔 **UUID:** `{uuid_str}`\n"
        f"📊 **Использовано:** {traffic_used} GB / {traffic_limit} GB\n"
        f"🟢 **Статус:** Активен\n\n"
        f"Выберите действие:"
    )

    kb = [
        [InlineKeyboardButton(text="🔄 Сбросить трафик", callback_data=f"reset_traffic:{uuid_str}")],
        [InlineKeyboardButton(text="🔍 Поиск", callback_data="btn_users")]
    ]

    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="Markdown")

@router.callback_query(F.data.startswith("reset_traffic:"))
async def cb_reset_traffic(callback: types.CallbackQuery):
    user_uuid = callback.data.split(":")[1]
    adapter = get_api_adapter()
    ok = await adapter.reset_user_traffic(user_uuid)
    if ok:
        await callback.answer("✅ Трафик успешно сброшен!", show_alert=True)
    else:
        await callback.answer("❌ Ошибка при сбросе трафика.", show_alert=True)

