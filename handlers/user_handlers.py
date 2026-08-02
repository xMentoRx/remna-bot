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
        raw_used = u.get("usedTraffic", 0)
        mb_used = raw_used / (1024 * 1024)
        if mb_used >= 1024:
            traffic_used = f"{mb_used / 1024:.2f} GB"
        else:
            traffic_used = f"{mb_used:.1f} MB"
        
        text += f"• **{display_name}** `[TG: {tg_id or '—'}]` — {traffic_used} трафика\n"
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
    
    raw_used = u.get("usedTraffic", 0)
    mb_used = raw_used / (1024 * 1024)
    traffic_used = f"{mb_used / 1024:.2f} GB" if mb_used >= 1024 else f"{mb_used:.1f} MB"
    
    raw_limit = u.get("trafficLimit", 0)
    traffic_limit = f"{raw_limit / (1024**3):.1f} GB" if raw_limit else "∞"

    sub_url = u.get("subscriptionUrl") or u.get("subUrl") or f"{adapter.base_url}/sub/{uuid_str}"

    text = (
        f"👤 **Карточка пользователя: {name}**\n\n"
        f"🆔 **UUID:** `{uuid_str}`\n"
        f"📊 **Использовано:** {traffic_used} / {traffic_limit}\n"
        f"🔗 **Ссылка подписки:** `{sub_url}`\n\n"
        f"Выберите действие:"
    )

    kb = [
        [InlineKeyboardButton(text="📲 QR-код подписки", callback_data=f"get_user_qr:{uuid_str}")],
        [InlineKeyboardButton(text="🔄 Сбросить трафик", callback_data=f"reset_traffic:{uuid_str}")],
        [InlineKeyboardButton(text="🔍 Поиск", callback_data="btn_users")]
    ]

    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="Markdown")

@router.callback_query(F.data.startswith("get_user_qr:"))
async def cb_get_user_qr(callback: types.CallbackQuery):
    user_uuid = callback.data.split(":")[1]
    adapter = get_api_adapter()
    users = await adapter.fetch_users_list(query=user_uuid)
    
    if not users:
        await callback.answer("❌ Пользователь не найден.", show_alert=True)
        return
        
    u = users[0]
    sub_url = u.get("subscriptionUrl") or u.get("subUrl") or f"{adapter.base_url}/sub/{user_uuid}"
    qr_image_url = f"https://api.qrserver.com/v1/create-qr-code/?size=400x400&data={sub_url}"
    name = u.get("username") or u.get("telegramId") or user_uuid[:8]

    await callback.answer()
    await callback.message.answer_photo(
        photo=qr_image_url,
        caption=(
            f"📲 **QR-код подписки для {name}**\n\n"
            f"🔗 `{sub_url}`\n\n"
            f"📱 Отсканируйте камерой смартфона в приложении **Happ / Hiddify / Streisand** для автоматического импорта!"
        ),
        parse_mode="Markdown"
    )

@router.callback_query(F.data.startswith("reset_traffic:"))
async def cb_reset_traffic(callback: types.CallbackQuery):
    user_uuid = callback.data.split(":")[1]
    adapter = get_api_adapter()
    ok = await adapter.reset_user_traffic(user_uuid)
    if ok:
        await callback.answer("✅ Трафик успешно сброшен!", show_alert=True)
    else:
        await callback.answer("❌ Ошибка при сбросе трафика.", show_alert=True)

@router.callback_query(F.data.startswith("quick_disable_usr:"))
async def cb_quick_disable_user(callback: types.CallbackQuery):
    user_uuid = callback.data.split(":")[1]
    adapter = get_api_adapter()
    ok = await adapter.disable_user(user_uuid)
    if ok:
        await callback.answer("🚫 Подписка пользователя успешно приостановлена!", show_alert=True)
        await callback.message.edit_text(
            f"{callback.message.text}\n\n🛑 **СТАТУС:** _Подписка пользователя заблокирована администратором._",
            parse_mode="Markdown"
        )
    else:
        await callback.answer("❌ Ошибка блокировки пользователя.", show_alert=True)

