import asyncio
import logging
from aiogram import Bot
from typing import Dict, List, Tuple, Optional, Any

from config import (
    ADMIN_IDS, API_URL, API_TOKEN, ALERT_CHAT_ID, ALERT_TOPIC_ID, load_settings
)
from services.remnawave_api import RemnawaveAPIAdapter

logger = logging.getLogger("remna-bot.monitoring")

# State tracking for node offline alerts to prevent spam and send recovery alerts
node_offline_state: Dict[str, bool] = {}

async def send_alert_notification(bot: Bot, text: str):
    """Sends an alert notification to configured alert chat, topic, or admin IDs."""
    settings = load_settings()
    target_chat = settings.get("alert_chat_id") or ALERT_CHAT_ID
    target_topic = settings.get("alert_topic_id") or ALERT_TOPIC_ID

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
            await bot.send_message(chat_id, text, **kwargs)
        except Exception as e:
            logger.error(f"Failed sending alert to chat {chat_id} (topic {thread_id}): {e}")

async def node_monitoring_loop(bot: Bot, interval_seconds: int = 300):
    """Background task monitoring node uptime and sending status change alerts."""
    global node_offline_state
    logger.info("🛡️ Node monitoring loop started.")
    is_first_run = True
    
    while True:
        try:
            settings = load_settings()
            url = settings.get("api_url") or API_URL
            token = settings.get("api_token") or API_TOKEN

            if url and token:
                adapter = RemnawaveAPIAdapter(url, token)
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
                        # Record initial status silently without alert spam
                        node_offline_state[node_id] = not is_online
                        continue

                    was_offline = node_offline_state.get(node_id, False)

                    if not is_online and not was_offline:
                        # Node went offline
                        node_offline_state[node_id] = True
                        msg = (
                            f"🔴 **АЛЕРТ МОНИТОРИНГА НОД**\n\n"
                            f"⚠️ Нода **{name}** (`{ip}`) ушла в **OFFLINE**!\n"
                            f"⏰ Время обнаружения: `только что`"
                        )
                        await send_alert_notification(bot, msg)

                    elif is_online and was_offline:
                        # Node recovered online
                        node_offline_state[node_id] = False
                        msg = (
                            f"🟢 **ВОССТАНОВЛЕНИЕ НОДЫ**\n\n"
                            f"✅ Нода **{name}** (`{ip}`) снова **ONLINE**!\n"
                            f"Связь восстановлена."
                        )
                        await send_alert_notification(bot, msg)

                if is_first_run:
                    is_first_run = False
                    logger.info("🟢 Monitoring baseline status initialized silently.")

        except Exception as e:
            logger.error(f"Error in monitoring loop: {e}")
            
        await asyncio.sleep(interval_seconds)

