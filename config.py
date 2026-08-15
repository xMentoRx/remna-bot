import os
import json
import logging
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s"
)
logger = logging.getLogger("remna-bot.config")

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "").strip()

raw_admins = os.getenv("ADMIN_CHAT_IDS", "")
ADMIN_IDS: List[int] = [int(x.strip()) for x in raw_admins.split(",") if x.strip().isdigit()]

# Monitoring Alert Settings
ALERT_CHAT_ID: str = os.getenv("ALERT_CHAT_ID", "").strip()
ALERT_TOPIC_ID: Optional[int] = int(os.getenv("ALERT_TOPIC_ID", "0")) if os.getenv("ALERT_TOPIC_ID", "").strip().isdigit() else None
SHARING_ALERT_TOPIC_ID: Optional[int] = int(os.getenv("SHARING_ALERT_TOPIC_ID", "0")) if os.getenv("SHARING_ALERT_TOPIC_ID", "").strip().isdigit() else None
BACKUP_ALERT_TOPIC_ID: Optional[int] = int(os.getenv("BACKUP_ALERT_TOPIC_ID", "0")) if os.getenv("BACKUP_ALERT_TOPIC_ID", "").strip().isdigit() else None

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "data", "settings.json")

def load_settings() -> Dict[str, Any]:
    """Loads application runtime settings from JSON file or environment variables."""
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception as e:
            logger.error(f"Failed loading {CONFIG_FILE}: {e}")
            
    return {
        "api_url": os.getenv("API_URL", "").strip(),
        "api_token": os.getenv("API_TOKEN", "").strip(),
        "alert_chat_id": ALERT_CHAT_ID,
        "alert_topic_id": ALERT_TOPIC_ID,
        "sharing_alert_topic_id": SHARING_ALERT_TOPIC_ID,
        "backup_alert_topic_id": BACKUP_ALERT_TOPIC_ID
    }

def save_settings(
    api_url: Optional[str] = None,
    api_token: Optional[str] = None,
    alert_chat_id: Optional[str] = None,
    alert_topic_id: Optional[int] = None,
    sharing_alert_topic_id: Optional[int] = None,
    backup_alert_topic_id: Optional[int] = None
) -> Dict[str, Any]:
    """Updates and saves runtime settings to JSON config file."""
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    current = load_settings()
    
    data = {
        "api_url": api_url.rstrip("/") if api_url is not None and api_url != "" else current.get("api_url", ""),
        "api_token": api_token.strip() if api_token is not None and api_token != "" else current.get("api_token", ""),
        "alert_chat_id": alert_chat_id.strip() if alert_chat_id is not None else current.get("alert_chat_id", ALERT_CHAT_ID),
        "alert_topic_id": alert_topic_id if alert_topic_id is not None else current.get("alert_topic_id", ALERT_TOPIC_ID),
        "sharing_alert_topic_id": sharing_alert_topic_id if sharing_alert_topic_id is not None else current.get("sharing_alert_topic_id", SHARING_ALERT_TOPIC_ID),
        "backup_alert_topic_id": backup_alert_topic_id if backup_alert_topic_id is not None else current.get("backup_alert_topic_id", BACKUP_ALERT_TOPIC_ID)
    }
    
    global API_URL, API_TOKEN
    if data.get("api_url"):
        API_URL = data.get("api_url")
    if data.get("api_token"):
        API_TOKEN = data.get("api_token")

    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Failed writing settings to {CONFIG_FILE}: {e}")
        
    return data

settings = load_settings()
API_URL: str = settings.get("api_url", "")
API_TOKEN: str = settings.get("api_token", "")
ALERT_CHAT_ID = settings.get("alert_chat_id", ALERT_CHAT_ID)
ALERT_TOPIC_ID = settings.get("alert_topic_id", ALERT_TOPIC_ID)
SHARING_ALERT_TOPIC_ID = settings.get("sharing_alert_topic_id", SHARING_ALERT_TOPIC_ID)
BACKUP_ALERT_TOPIC_ID = settings.get("backup_alert_topic_id", BACKUP_ALERT_TOPIC_ID)
WEBAPP_PORT: int = int(os.getenv("WEBAPP_PORT", "8080"))
WEBAPP_HOST: str = os.getenv("WEBAPP_HOST", "0.0.0.0")

