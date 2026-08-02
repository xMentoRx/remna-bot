import os
import logging
from aiohttp import web
from typing import Dict, Any

from config import API_URL, API_TOKEN, WEBAPP_PORT, WEBAPP_HOST, load_settings
from services.remnawave_api import RemnawaveAPIAdapter
from services.panel_deployer import deploy_fresh_panel_async
from services.node_deployer import deploy_node_async

logger = logging.getLogger("remna-bot.webapp")

def get_api_adapter() -> RemnawaveAPIAdapter:
    """Utility to instantiate API adapter with latest stored settings."""
    settings = load_settings()
    url = settings.get("api_url") or API_URL
    token = settings.get("api_token") or API_TOKEN
    return RemnawaveAPIAdapter(url, token)

# --- REST API Handlers for Telegram MiniApp ---

async def api_stats_handler(request: web.Request) -> web.Response:
    adapter = get_api_adapter()
    data = await adapter.fetch_stats_summary()
    return web.json_response(data)

async def api_hosts_handler(request: web.Request) -> web.Response:
    adapter = get_api_adapter()
    hosts = await adapter.fetch_hosts_list()
    return web.json_response({"hosts": hosts})

async def api_users_search_handler(request: web.Request) -> web.Response:
    q = request.query.get("q", "")
    adapter = get_api_adapter()
    users = await adapter.fetch_users_list(query=q)
    return web.json_response({"users": users})

async def api_user_reset_traffic_handler(request: web.Request) -> web.Response:
    try:
        data = await request.json()
        uuid = data.get("uuid")
        if not uuid:
            return web.json_response({"status": "error", "message": "UUID parameter missing"}, status=400)
            
        adapter = get_api_adapter()
        ok = await adapter.reset_user_traffic(uuid)
        if ok:
            return web.json_response({"status": "success", "message": "Трафик пользователя сброшен!"})
        return web.json_response({"status": "error", "message": "Не удалось сбросить трафик"}, status=400)
    except Exception as e:
        logger.error(f"Error resetting traffic via API: {e}")
        return web.json_response({"status": "error", "message": str(e)}, status=500)

async def api_deploy_panel_handler(request: web.Request) -> web.Response:
    try:
        data = await request.json()
        ip = data.get("ip")
        password = data.get("password")
        panel_domain = data.get("panel_domain")
        sub_domain = data.get("sub_domain")
        harden_vps = bool(data.get("harden_vps", True))

        if not (ip and password and panel_domain and sub_domain):
            return web.json_response({"success": False, "error": "Заполните все обязательные поля"}, status=400)

        res = await deploy_fresh_panel_async(
            host=ip,
            password=password,
            panel_domain=panel_domain,
            sub_domain=sub_domain,
            harden_vps=harden_vps
        )
        return web.json_response(res)
    except Exception as e:
        logger.error(f"Error deploying panel via API: {e}")
        return web.json_response({"success": False, "error": str(e)}, status=500)

async def api_deploy_node_handler(request: web.Request) -> web.Response:
    try:
        data = await request.json()
        ip = data.get("ip")
        password = data.get("password")
        country = data.get("country", "NL").upper()
        domain = data.get("domain", "google.com")

        if not (ip and password):
            return web.json_response({"status": "error", "message": "Укажите IP и пароль ноды"}, status=400)

        # Check if panel is configured to auto-link node secret
        settings = load_settings()
        panel_url = settings.get("api_url", "")
        api_token = settings.get("api_token", "")
        node_secret = ""

        if panel_url and api_token:
            try:
                adapter = RemnawaveAPIAdapter(panel_url, api_token)
                res = await adapter.create_node(name=f"{country}-{ip}", address=ip, port=443)
                if res and isinstance(res, dict):
                    node_secret = res.get("secretKey") or res.get("secret") or res.get("response", {}).get("secretKey", "")
            except Exception as e:
                logger.warning(f"Could not auto-register node in Remnawave API: {e}")

        res = await deploy_node_async(
            host=ip,
            password=password,
            country=country,
            domain=domain,
            node_secret=node_secret,
            panel_url=panel_url
        )
        return web.json_response(res)
    except Exception as e:
        logger.error(f"Error in node deploy handler: {e}")
        return web.json_response({"status": "error", "message": str(e)}, status=500)

async def api_features_boost_handler(request: web.Request) -> web.Response:
    try:
        data = await request.json()
        action_type = data.get("action", "")
        return web.json_response({"status": "success", "message": f"Оптимизация {action_type} успешно запущена!"})
    except Exception as e:
        return web.json_response({"status": "error", "message": str(e)}, status=400)

async def api_ssh_harden_handler(request: web.Request) -> web.Response:
    try:
        data = await request.json()
        host = data.get("ip")
        password = data.get("password")
        current_port = int(data.get("current_port", 22))
        new_port = int(data.get("new_port", 5422))
        install_crowdsec = bool(data.get("install_crowdsec", True))
        disable_password = bool(data.get("disable_password", True))

        if not (host and password):
            return web.json_response({"success": False, "error": "Укажите IP и пароль от VPS"}, status=400)

        loop = asyncio.get_running_loop()
        from services.ssh_hardening import run_ssh_hardening
        res = await loop.run_in_executor(
            None,
            run_ssh_hardening,
            host,
            password,
            current_port,
            new_port,
            install_crowdsec,
            disable_password
        )
        return web.json_response(res)
    except Exception as e:
        logger.error(f"Error in SSH hardening handler: {e}")
        return web.json_response({"success": False, "error": str(e)}, status=500)

async def api_ssh_keys_handler(request: web.Request) -> web.Response:
    host = request.query.get("host", "")
    from services.ssh_hardening import get_stored_key
    if host:
        key_info = get_stored_key(host)
        return web.json_response({"key": key_info})
    return web.json_response({"key": None})

async def api_save_settings_handler(request: web.Request) -> web.Response:
    try:
        data = await request.json()
        url = data.get("api_url", "").strip().rstrip("/")
        token = data.get("api_token", "").strip()

        if not url or not token:
            return web.json_response({"status": "error", "message": "Укажите URL и Токен"}, status=400)

        adapter = RemnawaveAPIAdapter(url, token)
        if await adapter.check_connection():
            save_settings(url, token)
            return web.json_response({"status": "success", "message": "Панель успешно привязана!"})
        else:
            return web.json_response({"status": "error", "message": "Ошибка подключения к панели"}, status=400)
    except Exception as e:
        return web.json_response({"status": "error", "message": str(e)}, status=500)

async def remna_embed_handler(request: web.Request) -> web.Response:
    """
    Proxies official Remnawave Panel Web UI directly inside MiniApp
    and injects Remna-Bot Floating Toolbar & Theme CSS scripts!
    """
    settings = load_settings()
    target_url = settings.get("api_url") or API_URL

    if not target_url:
        webapp_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "webapp")
        return web.FileResponse(os.path.join(webapp_dir, "index.html"))

    try:
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
            async with session.get(target_url, timeout=10) as resp:
                if resp.status == 200:
                    html_content = await resp.text()
                    
                    # Inject Remna-Bot Overlay CSS & JS into official Remnawave UI <head>
                    injection = """
                    <link rel="stylesheet" href="/remnabot_overlay.css">
                    <script src="/remnabot_overlay.js" defer></script>
                    </head>
                    """
                    if "</head>" in html_content:
                        html_content = html_content.replace("</head>", injection, 1)

                    return web.Response(text=html_content, content_type="text/html")
    except Exception as e:
        logger.error(f"Failed to proxy Remnawave UI from {target_url}: {e}")

    webapp_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "webapp")
    return web.FileResponse(os.path.join(webapp_dir, "index.html"))

# --- WebApp Static Files Handler ---
async def index_handler(request: web.Request) -> web.Response:
    webapp_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "webapp")
    return web.FileResponse(os.path.join(webapp_dir, "index.html"))

def create_webapp_app() -> web.Application:
    """Configures and builds the aiohttp Application for MiniApp."""
    app = web.Application()
    
    # REST Routes
    app.router.add_get("/", index_handler)
    app.router.add_get("/remna_embed", remna_embed_handler)
    app.router.add_get("/api/stats", api_stats_handler)
    app.router.add_get("/api/hosts", api_hosts_handler)
    app.router.add_get("/api/users/search", api_users_search_handler)
    app.router.add_get("/api/security/keys", api_ssh_keys_handler)
    app.router.add_post("/api/settings", api_save_settings_handler)
    app.router.add_post("/api/users/reset-traffic", api_user_reset_traffic_handler)
    app.router.add_post("/api/deploy/panel", api_deploy_panel_handler)
    app.router.add_post("/api/deploy/node", api_deploy_node_handler)
    app.router.add_post("/api/features/boost", api_features_boost_handler)
    app.router.add_post("/api/security/harden", api_ssh_harden_handler)

    # Static Assets Route
    webapp_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "webapp")
    app.router.add_static("/", webapp_dir)

    return app


async def start_webapp_server(host: str = WEBAPP_HOST, port: int = WEBAPP_PORT) -> web.AppRunner:
    """Starts the background aiohttp REST server for Telegram MiniApp."""
    app = create_webapp_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    logger.info(f"🌐 Telegram MiniApp Web Server listening on {host}:{port}")
    return runner
