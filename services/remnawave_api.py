import aiohttp
import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple

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
                            logger.info(f"Detected Remnawave Panel Version: {clean_ver} (Official compatibility range: v2.7.4+ .. v3.2.3+)")
                            return self.detected_version
            except Exception as e:
                logger.debug(f"Version probe failed: {e}")

            # 2. Probe /api/nodes (v3 / v3.2.x / v2.8+)
            try:
                async with session.get(f"{self.base_url}/api/nodes", headers=headers) as resp:
                    if resp.status == 200:
                        self.detected_version = "v3.2.3+"
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

    async def fetch_reality_keys(self) -> Tuple[str, str, str]:
        """Fetches or generates Reality Keypair (publicKey, privateKey) and shortId."""
        pub_key, priv_key, short_id = "", "", ""
        headers = self.get_headers()
        
        # Try Remnawave tools/x25519 or reality-keys endpoint
        if self.base_url and self.token:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                try:
                    async with session.get(f"{self.base_url}/api/system/tools/x25519/generate", headers=headers) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            kp = data.get("response", {}).get("keypairs", [])
                            if kp and len(kp) > 0:
                                priv_key = kp[0].get("privateKey", "")
                                pub_key = kp[0].get("publicKey", "")
                except Exception as e:
                    logger.debug(f"Tools x25519 probe failed: {e}")

                if not priv_key:
                    try:
                        async with session.get(f"{self.base_url}/api/system/xray/reality-keys", headers=headers) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                res = data.get("response", data)
                                pub_key = res.get("publicKey", "")
                                priv_key = res.get("privateKey", "")
                    except Exception as e:
                        logger.debug(f"Failed fetching reality keys: {e}")

                try:
                    async with session.get(f"{self.base_url}/api/system/xray/secret-key", headers=headers) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            res = data.get("response", data)
                            short_id = res.get("shortId") or res.get("secretKey") or ""
                except Exception as e:
                    logger.debug(f"Failed fetching secret key: {e}")

        # Fallback: In-memory crypto generation if panel endpoints are unavailable
        if not priv_key:
            try:
                import secrets
                import base64
                from cryptography.hazmat.primitives.asymmetric import x25519
                from cryptography.hazmat.primitives import serialization
                key = x25519.X25519PrivateKey.generate()
                priv_raw = key.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption())
                pub_raw = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
                priv_key = base64.urlsafe_b64encode(priv_raw).decode('utf-8').rstrip('=')
                pub_key = base64.urlsafe_b64encode(pub_raw).decode('utf-8').rstrip('=')
            except Exception as gen_err:
                logger.warning(f"Fallback X25519 generation failed: {gen_err}")

        if not short_id:
            import secrets
            short_id = secrets.token_hex(8)

        return pub_key, priv_key, short_id

    async def fetch_panel_pubkey(self) -> str:
        """Fetches the global Node SECRET_KEY from the Remnawave Panel (/api/keygen)."""
        if not self.base_url or not self.token:
            return ""
        headers = self.get_headers()
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            try:
                async with session.get(f"{self.base_url}/api/keygen", headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get("response", {}).get("pubKey", "") or data.get("pubKey", "")
            except Exception as e:
                logger.debug(f"Failed fetching panel pubKey via keygen: {e}")
        return ""

    async def create_self_steal_profile(self, node_name: str, domain: str = "example.com") -> Tuple[Optional[str], Optional[str]]:
        """
        Creates a dedicated Self-Steal VLESS Reality ConfigProfile for a node:
        - dest: /dev/shm/nginx.sock (Nginx Unix Socket Stealth Masking)
        - xver: 1
        - WARP AI routing rules (OpenAI, Gemini, Claude, Perplexity)
        - Torrent & Private IP blocking
        Returns (config_profile_uuid, inbound_uuid).
        """
        if not self.base_url or not self.token:
            return None, None

        import re
        import secrets

        # Sanitization
        clean_name = re.sub(r'[^\w\s-]', '', node_name).strip() or "Node"
        inbound_tag = re.sub(r'[^a-zA-Z0-9-]', '', clean_name.replace(" ", "-"))
        inbound_tag = re.sub(r'-+', '-', inbound_tag).strip("-") or "vless-reality"

        headers = self.get_headers()
        pub_key, priv_key, short_id = await self.fetch_reality_keys()

        stealth_config = {
            "log": { "loglevel": "warning" },
            "dns": {
                "queryStrategy": "UseIPv4",
                "servers": [{ "address": "https://dns.google/dns-query", "skipFallback": False }]
            },
            "inbounds": [{
                "tag": inbound_tag,
                "port": 443,
                "protocol": "vless",
                "settings": { "clients": [], "decryption": "none" },
                "sniffing": { "enabled": True, "destOverride": ["http", "tls", "quic"] },
                "streamSettings": {
                    "network": "tcp",
                    "security": "reality",
                    "realitySettings": {
                        "show": False,
                        "xver": 1,
                        "dest": "/dev/shm/nginx.sock",
                        "spiderX": "",
                        "shortIds": [short_id],
                        "privateKey": priv_key,
                        "serverNames": [domain]
                    }
                }
            }],
            "outbounds": [
                { "tag": "DIRECT", "protocol": "freedom" },
                { "tag": "BLOCK", "protocol": "blackhole" },
                {
                    "tag": "warp-out",
                    "protocol": "freedom",
                    "streamSettings": { "sockopt": { "mark": 255 } }
                }
            ],
            "routing": {
                "rules": [
                    {
                        "type": "field",
                        "domain": [
                            "geosite:openai",
                            "domain:gemini.google.com",
                            "domain:bard.google.com",
                            "domain:anthropic.com",
                            "domain:claude.ai",
                            "domain:perplexity.ai",
                            "domain:copilot.microsoft.com"
                        ],
                        "outboundTag": "warp-out"
                    },
                    { "ip": ["geoip:private"], "type": "field", "outboundTag": "BLOCK" },
                    { "type": "field", "protocol": ["bittorrent"], "outboundTag": "BLOCK" }
                ]
            }
        }

        payload = {
            "name": f"SelfSteal-{clean_name}",
            "config": stealth_config
        }

        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            prof_uuid = None
            inbound_uuid = None

            try:
                async with session.post(f"{self.base_url}/api/config-profiles", headers=headers, json=payload) as resp:
                    data = await resp.json()
                    logger.info(f"POST /api/config-profiles status: {resp.status} - data: {data}")
                    if resp.status in (200, 201):
                        res = data.get("response", data)
                        prof_uuid = res.get("uuid") or res.get("id") or (res.get("configProfile", {}).get("uuid") if isinstance(res.get("configProfile"), dict) else None)
                        inbounds = res.get("inbounds") or (res.get("config", {}).get("inbounds") if isinstance(res.get("config"), dict) else None) or []
                        if inbounds and isinstance(inbounds, list) and len(inbounds) > 0 and isinstance(inbounds[0], dict):
                            inbound_uuid = inbounds[0].get("uuid")
            except Exception as e:
                logger.warning(f"Self-steal profile creation POST error: {e}")

            # Always query GET /api/config-profiles to ensure accurate inbound_uuid from PostgreSQL
            try:
                async with session.get(f"{self.base_url}/api/config-profiles", headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        profiles = data if isinstance(data, list) else data.get("response", {}).get("configProfiles", data.get("configProfiles", data.get("response", [])))
                        if isinstance(profiles, list):
                            for p in profiles:
                                if prof_uuid and (p.get("uuid") == prof_uuid or p.get("id") == prof_uuid):
                                    prof_uuid = p.get("uuid") or p.get("id")
                                    p_inbounds = p.get("inbounds", [])
                                    if p_inbounds and isinstance(p_inbounds, list) and len(p_inbounds) > 0:
                                        inbound_uuid = p_inbounds[0].get("uuid") if isinstance(p_inbounds[0], dict) else str(p_inbounds[0])
                                    break
                                elif not prof_uuid and p.get("name") == payload["name"]:
                                    prof_uuid = p.get("uuid") or p.get("id")
                                    p_inbounds = p.get("inbounds", [])
                                    if p_inbounds and isinstance(p_inbounds, list) and len(p_inbounds) > 0:
                                        inbound_uuid = p_inbounds[0].get("uuid") if isinstance(p_inbounds[0], dict) else str(p_inbounds[0])
                                    break
            except Exception as e:
                logger.warning(f"Failed fetching config profiles list: {e}")

            logger.info(f"Resolved Self-Steal Profile: uuid={prof_uuid}, inbound_uuid={inbound_uuid}")
            return prof_uuid, inbound_uuid

    async def create_node(
        self,
        name: str,
        address: str,
        port: int = 2222,
        config_profile_uuid: str = "",
        profile_uuid: str = "",
        inbound_uuid: str = "",
        country_code: str = "NL",
        **kwargs
    ) -> Dict[str, Any]:
        """Registers a new node in Remnawave Panel via POST /api/nodes with fallback to /api/hosts."""
        if not self.base_url or not self.token:
            return {"error": "No API URL or Token provided"}

        import re
        api_name = re.sub(r'[^\w\s-]', '', name).strip() or "Node"
        code = country_code.strip()[:2].upper() if country_code else "NL"
        prof_id = config_profile_uuid or profile_uuid or kwargs.get("profile_uuid", "")

        payload = {
            "name": api_name,
            "address": address,
            "port": port,
            "configProfile": {
                "activeConfigProfileUuid": prof_id,
                "activeInbounds": [inbound_uuid] if inbound_uuid else []
            },
            "isTrafficTrackingActive": False,
            "trafficLimitBytes": 0,
            "notifyPercent": 0,
            "trafficResetDay": 31,
            "excludedInbounds": [],
            "countryCode": code,
            "consumptionMultiplier": 1.0
        }

        if prof_id:
            payload["configProfileUuid"] = prof_id
            payload["activeConfigProfileUuid"] = prof_id

        headers = self.get_headers()
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            try:
                async with session.post(f"{self.base_url}/api/nodes", headers=headers, json=payload) as resp:
                    data = await resp.json()
                    logger.info(f"create_node HTTP {resp.status}: {data}")
                    if resp.status not in (200, 201):
                        err = data.get("message") or data.get("error") or f"HTTP {resp.status}"
                        return {"error": err, "status": resp.status, "raw": data}
                    res_obj = data.get("response", data)
                    return {"success": True, "data": res_obj, "uuid": res_obj.get("uuid") if isinstance(res_obj, dict) else None, "response": res_obj}
            except Exception as e:
                logger.error(f"Exception creating node in Remnawave API: {e}")
                return {"error": str(e)}

    async def create_host(
        self,
        domain: str,
        config_uuid: str,
        inbound_uuid: str,
        remark: str = "Self-Steal Host"
    ) -> Dict[str, Any]:
        """Creates Host entry linked to the Inbound via POST /api/hosts."""
        if not self.base_url or not self.token:
            return {"error": "No API URL or Token provided"}

        # Build payload avoiding null fields that break strict schema validators
        payload = {
            "inbound": {
                "configProfileUuid": config_uuid,
                "configProfileInboundUuid": inbound_uuid
            },
            "remark": remark,
            "address": domain,
            "port": 443,
            "path": "",
            "sni": domain,
            "host": "",
            "fingerprint": "firefox",
            "allowInsecure": False,
            "isDisabled": False,
            "securityLayer": "DEFAULT"
        }

        headers = self.get_headers()
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            try:
                async with session.post(f"{self.base_url}/api/hosts", headers=headers, json=payload) as resp:
                    data = await resp.json()
                    logger.info(f"create_host HTTP {resp.status}: {data}")
                    if resp.status in (200, 201):
                        return data.get("response", data)
                    
                    # Fallback payload without nested inbound object (for older Remnawave v2 schemas)
                    fallback_payload = {
                        "configProfileUuid": config_uuid,
                        "configProfileInboundUuid": inbound_uuid,
                        "remark": remark,
                        "address": domain,
                        "port": 443,
                        "path": "",
                        "sni": domain,
                        "host": "",
                        "fingerprint": "firefox",
                        "allowInsecure": False,
                        "isDisabled": False,
                        "securityLayer": "DEFAULT"
                    }
                    async with session.post(f"{self.base_url}/api/hosts", headers=headers, json=fallback_payload) as resp2:
                        data2 = await resp2.json()
                        logger.info(f"create_host fallback HTTP {resp2.status}: {data2}")
                        if resp2.status in (200, 201):
                            return data2.get("response", data2)
                    
                    err = data.get("message") or data.get("error") or f"HTTP {resp.status}"
                    return {"error": err, "status": resp.status, "raw": data}
            except Exception as e:
                logger.error(f"Exception creating host in Remnawave API: {e}")
                return {"error": str(e)}

    async def add_inbound_to_squads(self, inbound_uuid: str) -> bool:
        """Adds a newly created Inbound to all internal squads so client keys include this node."""
        if not self.base_url or not self.token or not inbound_uuid:
            return False

        headers = self.get_headers()
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            try:
                async with session.get(f"{self.base_url}/api/internal-squads", headers=headers) as resp:
                    if resp.status != 200:
                        return False
                    data = await resp.json()
                    squads = data.get("response", {}).get("internalSquads", [])

                for squad in squads:
                    s_uuid = squad.get("uuid")
                    current_ibs = [ib.get("uuid") for ib in squad.get("inbounds", []) if ib.get("uuid")]
                    if inbound_uuid not in current_ibs:
                        current_ibs.append(inbound_uuid)
                        patch_payload = {
                            "uuid": s_uuid,
                            "inbounds": current_ibs
                        }
                        async with session.patch(f"{self.base_url}/api/internal-squads", headers=headers, json=patch_payload) as patch_resp:
                            logger.info(f"Updated squad {squad.get('name')} with inbound {inbound_uuid}: status {patch_resp.status}")
                return True
            except Exception as e:
                logger.error(f"Error updating internal squads with inbound {inbound_uuid}: {e}")
                return False

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
                                    uid = str(u.get("id") or "").lower()
                                    uname = str(u.get("username") or "").lower()
                                    tg_id = str(u.get("telegramId") or "").lower()
                                    uuid_str = str(u.get("uuid") or "").lower()
                                    short_uuid = str(u.get("shortUuid") or "").lower()

                                    # Match conditions:
                                    if (
                                        clean_q in uid or
                                        clean_q in uname or
                                        (tg_id and clean_q in tg_id) or
                                        clean_q in uuid_str or
                                        clean_q in short_uuid or
                                        (raw_digits and tg_id and raw_digits in tg_id) or
                                        (raw_digits and uname and raw_digits in uname)
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

    async def fetch_balancer_host_uuids(self) -> List[str]:
        """Fetches the list of node UUIDs injected into the Balancer profile/template."""
        if not self.base_url or not self.token:
            return []

        headers = self.get_headers()
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            try:
                # 1. Search in subscription-templates
                async with session.get(f"{self.base_url}/api/subscription-templates", headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        templates = data if isinstance(data, list) else data.get("response", {}).get("templates", data.get("subscriptionTemplates", []))
                        bal_tpl = next((t for t in templates if isinstance(t, dict) and ("balancer" in str(t.get("name")).lower() or "автовыбор" in str(t.get("name")).lower())), None)
                        if bal_tpl:
                            tpl_json = bal_tpl.get("templateJson") or bal_tpl.get("config") or {}
                            inject_hosts = tpl_json.get("remnawave", {}).get("injectHosts", [])
                            if inject_hosts:
                                vals = inject_hosts[0].get("selector", {}).get("values", [])
                                return list(vals)
            except Exception as e:
                logger.error(f"Error fetching balancer host uuids: {e}")
        return []

    async def ensure_balancer_exists(self, flag: str = "🇪🇺", name: str = "Автовыбор") -> Dict[str, Any]:
        """
        Creates/verifies Subscription Template, ConfigProfile, and Virtual Host for 'Автовыбор' Balancer.
        """
        if not self.base_url or not self.token:
            return {"success": False, "error": "No API URL or Token"}

        headers = self.get_headers()
        balancer_name = f"{flag} {name}".strip()

        default_balancer_json = {
            "outbounds": [{"tag": "direct", "protocol": "freedom"}],
            "remnawave": {
                "injectHosts": [
                    {
                        "selector": {"type": "uuids", "values": []},
                        "tagPrefix": "proxy",
                        "selectFrom": "ALL"
                    }
                ]
            },
            "routing": {
                "domainStrategy": "IPIfNonMatch",
                "balancers": [
                    {
                        "tag": "Super_Balancer",
                        "selector": ["proxy"],
                        "strategy": {"type": "leastLoad"}
                    }
                ],
                "rules": [
                    {"type": "field", "outboundTag": "Super_Balancer", "network": "tcp,udp"}
                ]
            }
        }

        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            tpl_uuid = None
            prof_uuid = None
            host_uuid = None

            # 1. Ensure Subscription Template exists
            try:
                async with session.get(f"{self.base_url}/api/subscription-templates", headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        templates = data if isinstance(data, list) else data.get("response", {})
                        if isinstance(templates, dict):
                            templates = templates.get("templates", [])
                        bal_tpl = next((t for t in templates if isinstance(t, dict) and ("balancer" in str(t.get("name")).lower() or "автовыбор" in str(t.get("name")).lower())), None)
                        if bal_tpl:
                            tpl_uuid = bal_tpl.get("uuid") or bal_tpl.get("id")

                if not tpl_uuid:
                    payload = {
                        "name": balancer_name,
                        "templateType": "XRAY_JSON",
                        "templateJson": default_balancer_json
                    }
                    async with session.post(f"{self.base_url}/api/subscription-templates", headers=headers, json=payload) as resp:
                        if resp.status in (200, 201):
                            res = await resp.json()
                            tpl_uuid = res.get("uuid") or res.get("response", {}).get("uuid")
            except Exception as e:
                logger.warning(f"Balancer subscription-template setup notice: {e}")

            # 2. Ensure ConfigProfile exists
            try:
                async with session.get(f"{self.base_url}/api/config-profiles", headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        profiles = data if isinstance(data, list) else data.get("response", {})
                        if isinstance(profiles, dict):
                            profiles = profiles.get("configProfiles", profiles.get("profiles", []))
                        bal_prof = next((p for p in profiles if isinstance(p, dict) and ("balancer" in str(p.get("name")).lower() or "автовыбор" in str(p.get("name")).lower())), None)
                        if bal_prof:
                            prof_uuid = bal_prof.get("uuid") or bal_prof.get("id")

                if not prof_uuid:
                    payload = {
                        "name": balancer_name,
                        "config": default_balancer_json
                    }
                    async with session.post(f"{self.base_url}/api/config-profiles", headers=headers, json=payload) as resp:
                        if resp.status in (200, 201):
                            res = await resp.json()
                            prof_uuid = res.get("uuid") or res.get("response", {}).get("uuid")
            except Exception as e:
                logger.warning(f"Balancer config-profile setup notice: {e}")

            # 3. Ensure Virtual Host / Dummy Node exists in Remnawave
            try:
                hosts = await self.fetch_hosts_list()
                bal_host = next((h for h in hosts if "автовыбор" in str(h.get("name")).lower() or "balancer" in str(h.get("name")).lower()), None)
                if bal_host:
                    host_uuid = bal_host.get("uuid") or bal_host.get("id")
                else:
                    res_node = await self.create_node(name=balancer_name, address="127.0.0.1", port=0, profile_uuid=prof_uuid or "")
                    if res_node.get("success"):
                        data_node = res_node.get("data", {})
                        host_uuid = data_node.get("uuid") or data_node.get("response", {}).get("uuid")
            except Exception as e:
                logger.warning(f"Balancer virtual host setup notice: {e}")

            active_hosts = await self.fetch_balancer_host_uuids()

            return {
                "success": True,
                "name": balancer_name,
                "template_uuid": tpl_uuid,
                "profile_uuid": prof_uuid,
                "host_uuid": host_uuid,
                "active_hosts_count": len(active_hosts),
                "active_hosts": active_hosts
            }

    async def toggle_host_in_balancer(self, host_uuid: str) -> Dict[str, Any]:
        """Toggles a host UUID in/out of the Balancer's injectHosts list."""
        if not self.base_url or not self.token:
            return {"success": False, "error": "No API URL or Token"}

        headers = self.get_headers()
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            try:
                # 1. Fetch balancer subscription template
                async with session.get(f"{self.base_url}/api/subscription-templates", headers=headers) as resp:
                    if resp.status != 200:
                        # Auto create balancer if missing
                        await self.ensure_balancer_exists()

                async with session.get(f"{self.base_url}/api/subscription-templates", headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        templates = data if isinstance(data, list) else data.get("response", {})
                        if isinstance(templates, dict):
                            templates = templates.get("templates", [])
                        bal_tpl = next((t for t in templates if isinstance(t, dict) and ("balancer" in str(t.get("name")).lower() or "автовыбор" in str(t.get("name")).lower())), None)

                        if not bal_tpl:
                            return {"success": False, "error": "Шаблон Балансировщика не найден на панели"}

                        tpl_uuid = bal_tpl.get("uuid") or bal_tpl.get("id")
                        tpl_json = bal_tpl.get("templateJson") or bal_tpl.get("config") or {}

                        if "remnawave" not in tpl_json:
                            tpl_json["remnawave"] = {}
                        remna_tpl = tpl_json["remnawave"]

                        if "injectHosts" not in remna_tpl or not remna_tpl["injectHosts"]:
                            remna_tpl["injectHosts"] = [
                                {
                                    "selector": {"type": "uuids", "values": []},
                                    "tagPrefix": "proxy",
                                    "selectFrom": "ALL"
                                }
                            ]

                        values = set(remna_tpl["injectHosts"][0].get("selector", {}).get("values", []))

                        is_added = False
                        if host_uuid in values:
                            values.remove(host_uuid)
                            is_added = False
                        else:
                            values.add(host_uuid)
                            is_added = True

                        remna_tpl["injectHosts"][0]["selector"]["values"] = list(values)
                        tpl_json["remnawave"] = remna_tpl

                        patch_payload = {
                            "uuid": tpl_uuid,
                            "name": bal_tpl.get("name", "🇪🇺 Автовыбор"),
                            "templateType": "XRAY_JSON",
                            "templateJson": tpl_json
                        }

                        async with session.patch(f"{self.base_url}/api/subscription-templates", headers=headers, json=patch_payload) as p_resp:
                            if p_resp.status in (200, 204):
                                return {
                                    "success": True,
                                    "is_in_balancer": is_added,
                                    "active_count": len(values),
                                    "message": f"Нода {'добавлена в' if is_added else 'удалена из'} Балансировщика!"
                                }
            except Exception as e:
                logger.error(f"Error toggling host in balancer: {e}")
                return {"success": False, "error": str(e)}

        return {"success": False, "error": "Не удалось обновить Балансировщик"}

    async def delete_node(self, node_uuid: str) -> bool:
        """Deletes a node from Remnawave Panel by UUID with cross-version fallback (v2 / v3)."""
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

    async def disable_user(self, user_uuid: str) -> bool:
        """Disables/suspends a user subscription by UUID."""
        if not self.base_url or not self.token:
            return False

        headers = self.get_headers()
        endpoints = [
            (f"/api/users/{user_uuid}", {"status": "DISABLED", "disabled": True}),
            (f"/api/subscriptions/{user_uuid}/disable", {})
        ]
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            for ep, payload in endpoints:
                try:
                    if payload:
                        async with session.patch(f"{self.base_url}{ep}", headers=headers, json=payload) as resp:
                            if resp.status in (200, 204):
                                return True
                    else:
                        async with session.post(f"{self.base_url}{ep}", headers=headers) as resp:
                            if resp.status in (200, 204):
                                return True
                except Exception as e:
                    logger.debug(f"Disable user probe {ep} error: {e}")
        return False

    async def scan_multi_ip_violations(self) -> List[Dict[str, Any]]:
        """
        Scans Remnawave users for HWID device limit & multi-IP subscription sharing leaks.
        Compares active connected devices & unique IPs against individual hwidDeviceLimit.
        """
        if not self.base_url or not self.token:
            return []

        headers = self.get_headers()
        violations = []

        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            try:
                # 1. Fetch top users by device count
                async with session.get(f"{self.base_url}/api/hwid/devices/top-users", headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        top_users = data if isinstance(data, list) else data.get("response", {}).get("users", data.get("users", []))

                        if isinstance(top_users, list):
                            for tu in top_users:
                                if not isinstance(tu, dict):
                                    continue

                                u_id = str(tu.get("userId") or tu.get("id") or tu.get("userUuid") or tu.get("uuid") or "")
                                dev_count = tu.get("devicesCount", tu.get("count", 0))

                                if not u_id or dev_count <= 0:
                                    continue

                                # Fetch user info & limits
                                limit = 0
                                udata = {}
                                try:
                                    async with session.get(f"{self.base_url}/api/users/{u_id}", headers=headers) as u_resp:
                                        if u_resp.status == 200:
                                            u_json = await u_resp.json()
                                            udata = u_json.get("response", u_json)
                                            limit = udata.get("hwidDeviceLimit") or udata.get("deviceLimit") or 0
                                except Exception:
                                    pass

                                status = str(udata.get("status") or "").upper()
                                is_active = status == "ACTIVE" or udata.get("disabled") is False

                                if is_active and limit > 0 and dev_count > limit:
                                    unique_ips = []
                                    # Fetch detailed device sessions to extract unique IPs (probe v3.1.0 and v2.x endpoints)
                                    for dev_ep in [f"/api/hwid/devices/{u_id}", f"/api/hwid/devices/{tu.get('userUuid')}"]:
                                        try:
                                            async with session.get(f"{self.base_url}{dev_ep}", headers=headers) as dev_resp:
                                                if dev_resp.status == 200:
                                                    dev_json = await dev_resp.json()
                                                    dev_data = dev_json.get("response", dev_json)
                                                    dev_list = dev_data if isinstance(dev_data, list) else dev_data.get("devices", [])
                                                    if isinstance(dev_list, list):
                                                        unique_ips = list(set(
                                                            d.get("requestIp") or d.get("ip")
                                                            for d in dev_list
                                                            if isinstance(d, dict) and (d.get("requestIp") or d.get("ip"))
                                                        ))
                                                    if unique_ips:
                                                        break
                                        except Exception:
                                            pass

                                    violations.append({
                                        "uuid": u_id,
                                        "user_id": u_id,
                                        "name": udata.get("description") or udata.get("username") or f"user_{u_id}",
                                        "telegram_id": udata.get("telegramId") or "N/A",
                                        "username": udata.get("username") or "N/A",
                                        "limit": limit,
                                        "actual_devices": dev_count,
                                        "unique_ips_count": len(unique_ips),
                                        "ips": unique_ips[:5]
                                    })

            except Exception as e:
                logger.error(f"Error scanning multi-IP violations: {e}")

        return violations

    async def reset_user_traffic(self, user_uuid: str) -> bool:
        """Resets traffic for a user ID/UUID across Remnawave v2.x, v3.0+ and v3.1.0+ API specs."""
        if not self.base_url or not self.token:
            return False

        headers = self.get_headers()
        u_val = int(user_uuid) if str(user_uuid).isdigit() else user_uuid

        endpoints_post_json = [
            (f"/api/users/{user_uuid}/reset-traffic", {}),
            (f"/api/subscriptions/{user_uuid}/reset-traffic", {}),
            ("/api/users/reset-traffic", {"userIds": [u_val] if isinstance(u_val, int) else []}),
            ("/api/users/bulk/reset-traffic", {"userIds": [u_val] if isinstance(u_val, int) else []}),
            ("/api/users/reset-traffic", {"userUuids": [str(user_uuid)]}),
            ("/api/users/reset-traffic", {"userUuid": str(user_uuid)})
        ]

        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            for ep, body in endpoints_post_json:
                try:
                    async with session.post(f"{self.base_url}{ep}", headers=headers, json=body) as resp:
                        if resp.status in (200, 201, 204):
                            return True
                except Exception as e:
                    logger.debug(f"Reset traffic probe {ep} error: {e}")
        return False


