import aiohttp
import asyncio
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger("remna-bot.api")

class RemnawaveAPIAdapter:
    """Async API client adapter for Remnawave Panel v2/v3."""

    def __init__(self, url: str, token: str, timeout: int = 7):
        self.base_url = url.rstrip('/') if url else ""
        self.token = token
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.detected_version = "v3.0.0"

    def get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "X-Remnawave-Client-Type": "browser"
        }

    async def detect_version(self) -> str:
        """Detects the installed Remnawave Panel API version asynchronously."""
        if not self.base_url or not self.token:
            return self.detected_version

        headers = self.get_headers()
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            # 1. Try version endpoint
            try:
                async with session.get(f"{self.base_url}/api/system/version", headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        ver = data.get("version") or data.get("response", {}).get("version")
                        if ver:
                            clean_ver = ver if ver.startswith("v") else f"v{ver}"
                            self.detected_version = clean_ver
                            logger.info(f"Detected Remnawave Panel Version: {clean_ver} (Official compatibility range: v2.7.4+)")
                            return self.detected_version
            except Exception as e:
                logger.debug(f"Version probe failed: {e}")

            # 2. Probe /api/nodes (v3 / v2.8+)
            try:
                async with session.get(f"{self.base_url}/api/nodes", headers=headers) as resp:
                    if resp.status == 200:
                        self.detected_version = "v2.8.0+"
                        return self.detected_version
            except Exception:
                pass

            # 3. Probe /api/hosts (v2.7.4+)
            try:
                async with session.get(f"{self.base_url}/api/hosts", headers=headers) as resp:
                    if resp.status == 200:
                        self.detected_version = "v2.7.4+"
                        return self.detected_version
            except Exception:
                pass

        return self.detected_version

    async def check_connection(self) -> bool:
        """Checks if the Remnawave panel API is reachable and token is valid."""
        if not self.base_url or not self.token:
            return False

        headers = self.get_headers()
        endpoints = ["/api/nodes", "/api/hosts", "/api/system/version", "/api/config-profiles"]
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            for ep in endpoints:
                try:
                    async with session.get(f"{self.base_url}{ep}", headers=headers) as resp:
                        if resp.status in (200, 201):
                            return True
                except Exception as e:
                    logger.debug(f"Endpoint test {ep} error: {e}")
        return False

    async def fetch_hosts_list(self) -> List[Dict[str, Any]]:
        """Fetches the list of nodes/hosts from the Remnawave panel."""
        if not self.base_url or not self.token:
            return []

        headers = self.get_headers()
        endpoints = ["/api/nodes", "/api/hosts"]
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            for ep in endpoints:
                try:
                    async with session.get(f"{self.base_url}{ep}", headers=headers) as resp:
                        if resp.status == 200:
                            res = await resp.json()
                            if isinstance(res, list):
                                return res
                            if isinstance(res, dict):
                                return res.get("response", res.get("nodes", res.get("hosts", [])))
                except Exception as e:
                    logger.error(f"Error fetching hosts from {ep}: {e}")
        return []

    async def fetch_users_list(self, query: str = "") -> List[Dict[str, Any]]:
        """Fetches and filters users asynchronously by Telegram ID, Username, user_ID, UUID, or t.me links."""
        if not self.base_url or not self.token:
            return []

        headers = self.get_headers()
        endpoints = ["/api/users", "/api/subscriptions"]
        
        # Smart query sanitizer
        clean_q = query.strip().lower()

        # Handle Telegram profile links (t.me/username or https://t.me/username)
        if "t.me/" in clean_q:
            clean_q = clean_q.split("t.me/")[-1].split("?")[0].split("/")[0]

        # Handle @username
        clean_q = clean_q.lstrip('@')

        # Extract numeric ID if user pasted 'user_123456789' or raw numbers
        raw_digits = "".join(filter(str.isdigit, clean_q))

        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            for ep in endpoints:
                try:
                    async with session.get(f"{self.base_url}{ep}", headers=headers) as resp:
                        if resp.status == 200:
                            res = await resp.json()
                            users = res if isinstance(res, list) else res.get("response", res.get("users", []))
                            if clean_q:
                                filtered = []
                                for u in users:
                                    uid = str(u.get("id", "")).lower()
                                    uname = str(u.get("username", "")).lower()
                                    tg_id = str(u.get("telegramId", "")).lower()
                                    uuid_str = str(u.get("uuid", "")).lower()
                                    short_uuid = str(u.get("shortUuid", "")).lower()

                                    # Match conditions:
                                    # 1. Clean query substring match
                                    # 2. Raw digits match telegramId or user_<digits>
                                    if (
                                        clean_q in uid or
                                        clean_q in uname or
                                        clean_q in tg_id or
                                        clean_q in uuid_str or
                                        clean_q in short_uuid or
                                        (raw_digits and raw_digits in tg_id) or
                                        (raw_digits and raw_digits in uname)
                                    ):
                                        filtered.append(u)
                                return filtered
                            return users
                except Exception as e:
                    logger.error(f"Error fetching users from {ep}: {e}")
        return []

    async def fetch_stats_summary(self) -> Dict[str, Any]:
        """Calculates system stats summary for MiniApp dashboard matching official Remnawave UI."""
        hosts = await self.fetch_hosts_list()
        users = await self.fetch_users_list()
        
        online_nodes = sum(
            1 for h in hosts
            if h.get("status") == "ONLINE" or h.get("isOnline") is True or h.get("isDisabled") is False
        )
        total_bytes = sum(u.get("usedTraffic", 0) for u in users)
        traffic_gb = total_bytes // (1024 ** 3)

        active_users = sum(1 for u in users if (u.get("status") or "").upper() == "ACTIVE" or u.get("disabled") is False and u.get("isExpired") is False)
        expired_users = sum(1 for u in users if (u.get("status") or "").upper() == "EXPIRED" or u.get("isExpired") is True)
        limited_users = sum(1 for u in users if (u.get("status") or "").upper() == "LIMITED" or u.get("isLimited") is True)
        disabled_users = sum(1 for u in users if (u.get("status") or "").upper() == "DISABLED" or u.get("disabled") is True)

        return {
            "version": self.detected_version,
            "total_nodes": len(hosts),
            "online_nodes": online_nodes,
            "total_users": len(users),
            "active_users": active_users,
            "expired_users": expired_users,
            "limited_users": limited_users,
            "disabled_users": disabled_users,
            "total_traffic": f"{traffic_gb} GB"
        }

    async def reset_user_traffic(self, user_uuid: str) -> bool:
        """Resets traffic for a given user UUID."""
        if not self.base_url or not self.token:
            return False

        headers = self.get_headers()
        endpoints = [f"/api/users/{user_uuid}/reset-traffic", f"/api/subscriptions/{user_uuid}/reset-traffic"]
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            for ep in endpoints:
                try:
                    async with session.post(f"{self.base_url}{ep}", headers=headers, json={}) as resp:
                        if resp.status in (200, 201, 204):
                            return True
                except Exception as e:
                    logger.error(f"Error resetting traffic at {ep}: {e}")
        return False

    async def create_node(self, name: str, address: str, port: int = 443, profile_uuid: str = "") -> Dict[str, Any]:
        """Creates a new node entry in Remnawave Panel."""
        if not self.base_url or not self.token:
            return {"success": False, "error": "No URL or Token"}

        headers = self.get_headers()
        payload = {"name": name, "address": address, "port": port}
        if profile_uuid:
            payload["configProfileUuid"] = profile_uuid

        endpoints = ["/api/nodes", "/api/hosts"]
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            for ep in endpoints:
                try:
                    async with session.post(f"{self.base_url}{ep}", headers=headers, json=payload) as resp:
                        if resp.status in (200, 201):
                            data = await resp.json()
                            return {"success": True, "data": data}
                except Exception as e:
                    logger.error(f"Error creating node at {ep}: {e}")
        return {"success": False, "error": "API error creating node"}

    async def delete_node(self, node_uuid: str) -> bool:
        """Deletes a node from Remnawave Panel by UUID."""
        if not self.base_url or not self.token:
            return False

        headers = self.get_headers()
        endpoints = [f"/api/nodes/{node_uuid}", f"/api/hosts/{node_uuid}"]
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            for ep in endpoints:
                try:
                    async with session.delete(f"{self.base_url}{ep}", headers=headers) as resp:
                        if resp.status in (200, 204):
                            return True
                except Exception as e:
                    logger.error(f"Error deleting node at {ep}: {e}")
        return False

# Helper standalone async functions
async def check_remnawave_connection(url: str, token: str) -> bool:
    adapter = RemnawaveAPIAdapter(url, token)
    return await adapter.check_connection()

async def fetch_hosts_list(url: str, token: str) -> List[Dict[str, Any]]:
    adapter = RemnawaveAPIAdapter(url, token)
    return await adapter.fetch_hosts_list()

async def fetch_stats_summary(url: str, token: str) -> Dict[str, Any]:
    adapter = RemnawaveAPIAdapter(url, token)
    return await adapter.fetch_stats_summary()

