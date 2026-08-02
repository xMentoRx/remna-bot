import asyncio
import logging
from aiogram import Bot
from typing import Dict, List, Tuple, Optional, Any

from aiogram.types import FSInputFile
from config import (
    ADMIN_IDS, API_URL, API_TOKEN, ALERT_CHAT_ID, ALERT_TOPIC_ID, SHARING_ALERT_TOPIC_ID, BACKUP_ALERT_TOPIC_ID, load_settings
)
from services.remnawave_api import RemnawaveAPIAdapter

logger = logging.getLogger("remna-bot.monitoring")

# State tracking for node offline alerts to prevent spam and send recovery alerts
node_offline_state: Dict[str, bool] = {}
# Cache for alerted sharing violations to prevent spamming
alerted_sharing_cache: Dict[str, int] = {}

async def send_alert_notification(bot: Bot, text: str, reply_markup=None, topic_override: Optional[int] = None):
    """Sends an alert notification to configured alert chat, topic, or admin IDs."""
    settings = load_settings()
    target_chat = settings.get("alert_chat_id") or ALERT_CHAT_ID
    target_topic = topic_override if topic_override is not None else (settings.get("alert_topic_id") or ALERT_TOPIC_ID)

    destinations: List[Tuple[Any, Optional[int]]] = []
    if target_chat:
        destinations.append((target_chat, target_topic))
    else:
        for admin_id in ADMIN_IDS:
            destinations.append((admin_id, None))

    for chat_id, thread_id in destinations:
        try:
            kwargs = {"parse_mode": "Markdown"}
            if thread_id:
                kwargs["message_thread_id"] = int(thread_id)
            if reply_markup:
                kwargs["reply_markup"] = reply_markup
            await bot.send_message(chat_id, text, **kwargs)
        except Exception as e:
            logger.error(f"Failed sending alert to chat {chat_id} (topic {thread_id}): {e}")

async def send_backup_file_notification(bot: Bot, file_path: str, caption: str):
    """Sends a PostgreSQL backup archive file to configured backup topic or admin chat."""
    settings = load_settings()
    target_chat = settings.get("alert_chat_id") or ALERT_CHAT_ID
    target_topic = settings.get("backup_alert_topic_id") or BACKUP_ALERT_TOPIC_ID or settings.get("alert_topic_id") or ALERT_TOPIC_ID

    destinations: List[Tuple[Any, Optional[int]]] = []
    if target_chat:
        destinations.append((target_chat, target_topic))
    else:
        for admin_id in ADMIN_IDS:
            destinations.append((admin_id, None))

    input_file = FSInputFile(file_path)
    for chat_id, thread_id in destinations:
        try:
            kwargs = {"caption": caption, "parse_mode": "Markdown"}
            if thread_id:
                kwargs["message_thread_id"] = int(thread_id)
            await bot.send_document(chat_id, input_file, **kwargs)
        except Exception as e:
            logger.error(f"Failed sending backup document to chat {chat_id} (topic {thread_id}): {e}")

async def daily_backup_loop(bot: Bot, interval_seconds: int = 86400):
    """Background task performing daily PostgreSQL backups of Remnawave Panel."""
    logger.info("💾 Daily PostgreSQL Backup loop started.")
    await asyncio.sleep(60) # Initial warmup delay
    
    while True:
        try:
            settings = load_settings()
            panel_url = settings.get("api_url") or API_URL
            
            # Extract host IP/domain from panel_url if available
            if panel_url:
                from urllib.parse import urlparse
                host = urlparse(panel_url).hostname
                if host:
                    from services.panel_deployer import backup_panel_database_async
                    # Attempt backup if SSH key or default credentials exist
                    res = await backup_panel_database_async(host=host, password="")
                    if res.get("success") and res.get("local_path"):
                        caption = (
                            f"💾 **ЕЖЕДНЕВНЫЙ БЭКАП ПАНЕЛИ REMNAWAVE**\n\n"
                            f"📦 **Файл:** `{res['filename']}`\n"
                            f"⏰ **Дата генерации:** `только что`\n\n"
                            f"✅ Дамп базы данных PostgreSQL успешно сформирован."
                        )
                        await send_backup_file_notification(bot, res["local_path"], caption)
        except Exception as e:
            logger.error(f"Error in daily backup loop: {e}")
            
        await asyncio.sleep(interval_seconds)

async def node_monitoring_loop(bot: Bot, interval_seconds: int = 300):
    """Background task monitoring node uptime and HWID / Multi-IP sharing violations."""
    global node_offline_state, alerted_sharing_cache
    logger.info("🛡️ Node & HWID Multi-IP Security Monitoring loop started.")
    is_first_run = True
    
    while True:
        try:
            settings = load_settings()
            url = settings.get("api_url") or API_URL
            token = settings.get("api_token") or API_TOKEN

            if url and token:
                adapter = RemnawaveAPIAdapter(url, token)
                
                # 1. Audit Nodes Uptime
                hosts = await adapter.fetch_hosts_list()

                for h in hosts:
                    node_id = str(h.get("uuid") or h.get("name"))
                    name = h.get("name", "Node")
                    ip = h.get("address", "--")
                    is_online = (
                        h.get("status") == "ONLINE" or
                        h.get("isOnline") is True or
                        h.get("isDisabled") is False
                    )

                    if is_first_run:
                        node_offline_state[node_id] = not is_online
                        continue

                    was_offline = node_offline_state.get(node_id, False)

                    if not is_online and not was_offline:
                        node_offline_state[node_id] = True
                        msg = (
                            f"🔴 **АЛЕРТ МОНИТОРИНГА НОД**\n\n"
                            f"⚠️ Нода **{name}** (`{ip}`) ушла в **OFFLINE**!\n"
                            f"⏰ Время обнаружения: `только что`"
                        )
                        await send_alert_notification(bot, msg)

                    elif is_online and was_offline:
                        node_offline_state[node_id] = False
                        msg = (
                            f"🟢 **ВОССТАНОВЛЕНИЕ НОДЫ**\n\n"
                            f"✅ Нода **{name}** (`{ip}`) снова **ONLINE**!\n"
                            f"Связь восстановлена."
                        )
                        await send_alert_notification(bot, msg)

                # 2. Audit HWID Device Limits & Multi-IP Subscription Leaks
                try:
                    violations = await adapter.scan_multi_ip_violations()
                    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
                    
                    for v in violations:
                        u_uuid = v["uuid"]
                        actual = v["actual_devices"]
                        cache_key = f"{u_uuid}_{actual}"
                        
                        if cache_key in alerted_sharing_cache:
                            continue
                            
                        alerted_sharing_cache[cache_key] = actual
                        ips_str = ", ".join(f"`{ip}`" for ip in v["ips"]) if v["ips"] else "Не определены"
                        
                        alert_msg = (
                            f"🚨 **АЛЕРТ: РАСШАРИВАНИЕ ПОДПИСКИ (HWID / MULTI-IP LEAK)**\n\n"
                            f"👤 **Пользователь:** `{v['name']}`\n"
                            f"⚙️ **Юзернейм:** `@{v['username']}`\n"
                            f"🆔 **TG ID:** `{v['telegram_id']}`\n"
                            f"🗝️ **UUID:** `{u_uuid}`\n\n"
                            f"📱 **Лимит устройств по тарифу:** `{v['limit']} устр.`\n"
                            f"📲 **Фактически подключено устройств:** `{v['actual_devices']} шт.` (Превышение!)\n"
                            f"🌐 **Уникальных IP-адресов:** `{v['unique_ips_count']} шт.`\n"
                            f"📍 **IP-адреса сессий:** {ips_str}\n\n"
                            f"⚠️ _Обнаружен вероятный слив подписки нескольким клиентам._"
                        )

                        kb = InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text="🚫 Заблокировать подписку", callback_data=f"quick_disable_usr:{u_uuid}")],
                            [InlineKeyboardButton(text="🔄 Сбросить трафик в 0", callback_data=f"reset_traffic:{u_uuid}")]
                        ])

                        sharing_topic = settings.get("sharing_alert_topic_id") or SHARING_ALERT_TOPIC_ID
                        await send_alert_notification(bot, alert_msg, reply_markup=kb, topic_override=sharing_topic)
                        logger.info(f"Sent HWID violation alert for user {v['name']} (UUID: {u_uuid})")

                except Exception as leak_err:
                    logger.error(f"Error checking HWID leak violations: {leak_err}")

                if is_first_run:
                    is_first_run = False
                    logger.info("🟢 Monitoring baseline status initialized silently.")

        except Exception as e:
            logger.error(f"Error in monitoring loop: {e}")
            
        await asyncio.sleep(interval_seconds)

