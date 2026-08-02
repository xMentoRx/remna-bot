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
    balancer_uuids = set(await adapter.fetch_balancer_host_uuids())

    if not hosts:
        await callback.message.edit_text(
            "🖥️ **Управление нодами**\n\nНоды не найдены или панель недоступна.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⚖️ Инициализировать Балансировщик 🇪🇺", callback_data="btn_setup_balancer")],
                [InlineKeyboardButton(text="🚀 Развернуть новую ноду", callback_data="btn_deploy_node_wiz")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="btn_main_menu")]
            ]),
            parse_mode="Markdown"
        )
        return

    text = f"🖥️ **Список Нод Инфраструктуры (В балансировщике: {len(balancer_uuids)}):**\n\n"
    kb = []
    for h in hosts:
        uuid_val = str(h.get("uuid") or h.get("id"))
        name = h.get("name", "Node")
        status = "🟢 ONLINE" if (h.get("status") == "ONLINE" or h.get("isOnline") is True or h.get("isDisabled") is False) else "🔴 OFFLINE"
        ip = h.get("address", "--")
        is_bal = "⚖️" if uuid_val in balancer_uuids else ""
        text += f"• **{name}** ({ip}) — {status} {is_bal}\n"
        kb.append([InlineKeyboardButton(text=f"⚙️ {name} ({status}) {is_bal}", callback_data=f"node_detail:{uuid_val}")])

    kb.append([InlineKeyboardButton(text="⚖️ Инициализировать '🇪🇺 Автовыбор'", callback_data="btn_setup_balancer")])
    kb.append([InlineKeyboardButton(text="🚀 Развернуть новую ноду", callback_data="btn_deploy_node_wiz")])
    kb.append([InlineKeyboardButton(text="🔄 Обновить список", callback_data="btn_nodes")])

    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="Markdown")

@router.callback_query(F.data.startswith("node_detail:"))
async def cb_node_detail(callback: types.CallbackQuery):
    await callback.answer()
    node_id = callback.data.split(":")[1]
    adapter = get_api_adapter()
    hosts = await adapter.fetch_hosts_list()
    target = next((h for h in hosts if str(h.get("uuid")) == node_id or str(h.get("id")) == node_id or h.get("name") == node_id), None)

    if not target:
        await callback.message.edit_text("❌ Нода не найдена.")
        return

    target_uuid = str(target.get("uuid") or target.get("id") or node_id)
    name = target.get("name", "Node")
    ip = target.get("address", "--")
    port = target.get("port", 443)
    status = "🟢 ONLINE" if (target.get("status") == "ONLINE" or target.get("isOnline") is True or target.get("isDisabled") is False) else "🔴 OFFLINE"

    balancer_uuids = set(await adapter.fetch_balancer_host_uuids())
    in_bal = target_uuid in balancer_uuids
    bal_btn_text = "⚖️ Удалить из Балансировщика" if in_bal else "⚖️ Добавить в Балансировщик"

    text = (
        f"🖥️ **Карточка Ноды: {name}**\n\n"
        f"🌐 **IP:** `{ip}`\n"
        f"🔌 **Порт:** `{port}`\n"
        f"📡 **Статус:** {status}\n"
        f"⚖️ **Клиентский Балансировщик:** {'✅ Включен в Автовыбор' if in_bal else '❌ Выключен'}\n\n"
        f"Выберите действие:"
    )

    kb = [
        [InlineKeyboardButton(text=bal_btn_text, callback_data=f"toggle_bal:{target_uuid}")],
        [InlineKeyboardButton(text="⚡ Буст BBRv3 / FQ", callback_data=f"boost_prompt:{ip}")],
        [InlineKeyboardButton(text="🛡️ Аудит 5/5", callback_data=f"audit_prompt:{ip}")],
        [InlineKeyboardButton(text="🗑️ Удалить ноду", callback_data=f"delete_node:{target_uuid}")],
        [InlineKeyboardButton(text="🔙 Назад к списку", callback_data="btn_nodes")]
    ]

    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="Markdown")

@router.callback_query(F.data.startswith("toggle_bal:"))
async def cb_toggle_balancer(callback: types.CallbackQuery):
    node_uuid = callback.data.split(":")[1]
    adapter = get_api_adapter()
    res = await adapter.toggle_host_in_balancer(node_uuid)
    if res.get("success"):
        await callback.answer(res.get("message", "Балансировщик обновлен!"), show_alert=True)
        await cb_node_detail(callback)
    else:
        await callback.answer(f"❌ Ошибка: {res.get('error', 'Сбой обновления')}", show_alert=True)

@router.callback_query(F.data == "btn_setup_balancer")
async def cb_setup_balancer(callback: types.CallbackQuery):
    adapter = get_api_adapter()
    res = await adapter.ensure_balancer_exists(flag="🇪🇺", name="Автовыбор")
    if res.get("success"):
        await callback.answer("🎉 Виртуальный хост '🇪🇺 Автовыбор' и профиль балансировщика готовы!", show_alert=True)
        await cb_nodes_list(callback)
    else:
        await callback.answer(f"❌ Ошибка: {res.get('error')}", show_alert=True)

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

