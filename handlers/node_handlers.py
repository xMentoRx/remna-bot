import asyncio
import logging
from aiogram import Router, types, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from config import API_URL, API_TOKEN, load_settings
from services.remnawave_api import RemnawaveAPIAdapter
from services.node_deployer import audit_node_async

logger = logging.getLogger("remna-bot.node-handlers")
router = Router(name="node_router")

def get_api_adapter() -> RemnawaveAPIAdapter:
    settings = load_settings()
    url = settings.get("api_url") or API_URL
    token = settings.get("api_token") or API_TOKEN
    return RemnawaveAPIAdapter(url, token)

@router.callback_query(F.data == "btn_nodes")
async def cb_nodes_list(callback: types.CallbackQuery):
    await callback.answer()
    adapter = get_api_adapter()
    hosts = await adapter.fetch_hosts_list()

    if not hosts:
        await callback.message.edit_text(
            "🖥️ **Управление нодами**\n\nНоды не найдены или панель недоступна.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🚀 Развернуть новую ноду", callback_data="btn_deploy_node_wiz")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="btn_main_menu")]
            ]),
            parse_mode="Markdown"
        )
        return

    text = "🖥️ **Список Нод Инфраструктуры:**\n\n"
    kb = []
    for h in hosts:
        name = h.get("name", "Node")
        status = "🟢 ONLINE" if (h.get("status") == "ONLINE" or h.get("isOnline") is True or h.get("isDisabled") is False) else "🔴 OFFLINE"
        ip = h.get("address", "--")
        text += f"• **{name}** ({ip}) — {status}\n"
        kb.append([InlineKeyboardButton(text=f"⚙️ {name} ({status})", callback_data=f"node_detail:{h.get('uuid', name)}")])

    kb.append([InlineKeyboardButton(text="🚀 Развернуть новую ноду", callback_data="btn_deploy_node_wiz")])
    kb.append([InlineKeyboardButton(text="🔄 Обновить список", callback_data="btn_nodes")])

    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="Markdown")

@router.callback_query(F.data.startswith("node_detail:"))
async def cb_node_detail(callback: types.CallbackQuery):
    await callback.answer()
    node_id = callback.data.split(":")[1]
    adapter = get_api_adapter()
    hosts = await adapter.fetch_hosts_list()
    target = next((h for h in hosts if str(h.get("uuid")) == node_id or h.get("name") == node_id), None)

    if not target:
        await callback.message.edit_text("❌ Нода не найдена.")
        return

    name = target.get("name", "Node")
    ip = target.get("address", "--")
    port = target.get("port", 443)
    status = "🟢 ONLINE" if (target.get("status") == "ONLINE" or target.get("isOnline") is True or target.get("isDisabled") is False) else "🔴 OFFLINE"

    text = (
        f"🖥️ **Карточка Ноды: {name}**\n\n"
        f"🌐 **IP:** `{ip}`\n"
        f"🔌 **Порт:** `{port}`\n"
        f"📡 **Статус:** {status}\n\n"
        f"Выберите действие:"
    )

    kb = [
        [InlineKeyboardButton(text="🛡️ Аудит 5/5", callback_data=f"audit_node:{ip}")],
        [InlineKeyboardButton(text="🗑️ Удалить ноду", callback_data=f"delete_node:{target.get('uuid', node_id)}")],
        [InlineKeyboardButton(text="🔙 Назад к списку", callback_data="btn_nodes")]
    ]

    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="Markdown")

@router.callback_query(F.data.startswith("delete_node:"))
async def cb_delete_node(callback: types.CallbackQuery):
    node_uuid = callback.data.split(":")[1]
    adapter = get_api_adapter()
    ok = await adapter.delete_node(node_uuid)
    if ok:
        await callback.answer("✅ Нода успешно удалена из панели!", show_alert=True)
        await cb_nodes_list(callback)
    else:
        await callback.answer("❌ Ошибка при удалении ноды.", show_alert=True)

