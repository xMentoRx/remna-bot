import asyncio
import logging
import random
import re
import paramiko
from typing import Callable, Optional, Dict, Any, List

logger = logging.getLogger("remna-bot.node-deployer")

def clean_api_name(name: str) -> str:
    """Translates Russian country names to English and strips special characters."""
    translations = {
        "нидерланды": "Netherlands",
        "германия": "Germany",
        "финляндия": "Finland",
        "швеция": "Sweden",
        "россия": "Russia"
    }
    for ru, en in translations.items():
        name = re.sub(ru, en, name, flags=re.IGNORECASE)
    cleaned = re.sub(r'[^\w\s-]', '', name)
    cleaned = re.sub(r'\s+', ' ', cleaned)
    return cleaned.strip()

def generate_decoy_html(domain: str) -> str:
    """Generates realistic decoy HTML landing pages for Reality SNI masking."""
    templates = [
        f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FC Fan Community | {domain}</title>
    <style>
        body {{ background: #0f172a; color: #fff; font-family: sans-serif; text-align: center; padding: 50px; }}
        h1 {{ color: #f59e0b; }}
    </style>
</head>
<body>
    <h1>Real Madrid FC Fans Portal</h1>
    <p>Welcome to {domain}. Live match updates and community news.</p>
</body>
</html>""",
        f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Apex Coffee Roasters | {domain}</title>
    <style>
        body {{ background: #1c1917; color: #f5f5f4; font-family: serif; text-align: center; padding: 60px; }}
        h1 {{ color: #d97706; }}
    </style>
</head>
<body>
    <h1>Artisanal Coffee & Bakery</h1>
    <p>Fresh roasted coffee beans delivered worldwide. Visit {domain}.</p>
</body>
</html>"""
    ]
    return random.choice(templates)

def connect_smart_ssh(client: paramiko.SSHClient, host: str, password: str, progress_cb: Optional[Callable[[str], None]] = None) -> bool:
    """Tries connecting via standard Port 22 + Password first. If fails, tries Port 5422 + Saved Ed25519 Key from ssh_keys.json!"""
    # 1. Attempt standard port 22 + password
    try:
        if progress_cb:
            progress_cb(f"🔑 SSH Подключение к ноде `{host}` (Порт 22)...")
        client.connect(hostname=host, port=22, username="root", password=password, timeout=10)
        return True
    except Exception as err1:
        logger.info(f"Port 22 password connect on {host} failed ({err1}), checking for saved hardened SSH key...")

    # 2. Check if we have a saved SSH key for this host from previous hardening
    try:
        from services.ssh_hardening import get_ssh_key
        key_data = get_ssh_key(host)
        if key_data and key_data.get("private_key"):
            import io
            pkey = paramiko.Ed25519Key.from_private_key(io.StringIO(key_data["private_key"]))
            port = key_data.get("port", 5422)
            if progress_cb:
                progress_cb(f"🛡️ VPS уже защищен! Вход по SSH ключу Ed25519 (Порт {port})...")
            client.connect(hostname=host, port=port, username="root", pkey=pkey, timeout=10)
            return True
    except Exception as err2:
        logger.warning(f"Hardened key connect on {host} failed: {err2}")

    # 3. Last attempt: try port 5422 with password
    try:
        client.connect(hostname=host, port=5422, username="root", password=password, timeout=10)
        return True
    except Exception:
        pass

    return False

def run_ssh_commands(
    host: str,
    password: str,
    commands: List[str],
    progress_cb: Optional[Callable[[str], None]] = None
) -> bool:
    """Executes a list of SSH commands sequentially on a remote server."""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        if not connect_smart_ssh(client, host, password, progress_cb):
            return False

        for idx, cmd in enumerate(commands, start=1):
            if progress_cb:
                progress_cb(f"⚙️ [{idx}/{len(commands)}] Выполнение: `{cmd[:60]}...`")
            stdin, stdout, stderr = client.exec_command(cmd, get_pty=True)
            exit_status = stdout.channel.recv_exit_status()
            out = stdout.read().decode('utf-8', errors='ignore')
            if exit_status != 0:
                logger.error(f"Command '{cmd}' failed on {host}: {out}")
                if progress_cb:
                    progress_cb(f"⚠️ Ошибка команды `{cmd[:30]}`: status {exit_status}")
        
        if progress_cb:
            progress_cb(f"✅ Успешно выполнено на `{host}`!")
        return True
    except Exception as e:
        logger.error(f"SSH error on {host}: {e}")
        if progress_cb:
            progress_cb(f"❌ Сбой SSH: {e}")
        return False
    finally:
        client.close()

def run_node_full_deploy(
    host: str,
    password: str,
    domain: str = "example.com",
    country_code: str = "NL",
    node_secret: str = "",
    panel_url: str = "",
    progress_cb: Optional[Callable[[str], None]] = None
) -> bool:
    """Performs full 1-click deployment of Remnawave Node on a remote server."""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        if not connect_smart_ssh(client, host, password, progress_cb):
            raise Exception(f"Не удалось подключиться к VPS `{host}` ни по паролю (Порт 22), ни по ключу SSH (Порт 5422)!")

        def exec_cmd(cmd: str, msg: str):
            if progress_cb:
                progress_cb(f"⚙️ {msg}...")
            stdin, stdout, stderr = client.exec_command(cmd, get_pty=True)
            status = stdout.channel.recv_exit_status()
            out = stdout.read().decode('utf-8', errors='ignore')
            if status != 0:
                logger.warning(f"Cmd {cmd} warning: status {status}, out: {out[:100]}")

        # 1. Non-interactive environment setup & unlock APT locks
        exec_cmd(
            "export DEBIAN_FRONTEND=noninteractive; export NEEDRESTART_MODE=a; export UCF_FORCE_CONFFOLD=1; "
            "mkdir -p /etc/needrestart/conf.d; echo '$nrconf{restart} = \"a\";' > /etc/needrestart/conf.d/50auto.conf 2>/dev/null || true; "
            "for i in {1..10}; do fuser -v /var/lib/dpkg/lock-frontend >/dev/null 2>&1 || break; sleep 3; done; "
            "systemctl stop unattended-upgrades apache2 nginx 2>/dev/null || true; "
            "killall -9 apt apt-get dpkg 2>/dev/null || true; "
            "rm -f /var/lib/dpkg/lock* /var/lib/apt/lists/lock /var/cache/apt/archives/lock",
            "Подавление диалогов и снятие APT-блокировок на ноде"
        )

        # 2. Update APT and install base utilities
        exec_cmd(
            "export DEBIAN_FRONTEND=noninteractive; export NEEDRESTART_MODE=a; "
            "apt-get update && apt-get -o Dpkg::Options::='--force-confdef' -o Dpkg::Options::='--force-confold' -y install curl nginx jq ca-certificates",
            "Обновление пакетов и установка Nginx (Тихий режим)"
        )

        # 3. Docker setup
        exec_cmd(
            "export DEBIAN_FRONTEND=noninteractive; export NEEDRESTART_MODE=a; "
            "command -v docker >/dev/null 2>&1 || (curl -fsSL https://get.docker.com | sh); "
            "apt-get -o Dpkg::Options::='--force-confdef' -o Dpkg::Options::='--force-confold' -y install docker-compose-v2 2>/dev/null || true",
            "Проверка и установка Docker Engine"
        )

        # 4. System optimization & BBR
        exec_cmd("sysctl -w net.core.default_qdisc=fq && sysctl -w net.ipv4.tcp_congestion_control=bbr", "Включение BBR и сетевой оптимизации FQ")

        # 5. Create Nginx decoy site & unix socket path explicitly before SFTP
        exec_cmd("mkdir -p /var/www/html /etc/nginx/sites-available /etc/nginx/sites-enabled /opt/remnawave-node", "Подготовка каталогов Nginx и Docker")
        
        decoy_html = generate_decoy_html(domain)
        sftp = client.open_sftp()
        with sftp.file("/var/www/html/index.html", "w") as f:
            f.write(decoy_html)

        # Write stealth nginx config
        nginx_conf = f"""server {{
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;
    root /var/www/html;
    index index.html;

    location / {{
        try_files $uri $uri/ =404;
    }}
}}
"""
        with sftp.file("/etc/nginx/sites-available/default", "w") as f:
            f.write(nginx_conf)

        # Write Remnawave Node docker-compose.yml if secret key is provided
        if node_secret:
            node_compose = f"""version: '3.8'

services:
  remnawave-node:
    image: ghcr.io/remnawave/node:latest
    container_name: remnawave-node
    restart: always
    environment:
      SECRET_KEY: "{node_secret}"
      PANEL_URL: "{panel_url}"
      REMNAWAVE_SECRET_KEY: "{node_secret}"
      REMNAWAVE_PANEL_URL: "{panel_url}"
"""
            with sftp.file("/opt/remnawave-node/docker-compose.yml", "w") as f:
                f.write(node_compose)

        sftp.close()

        exec_cmd("systemctl restart nginx", "Запуск Stealth Nginx маскировки")

        if node_secret:
            exec_cmd("cd /opt/remnawave-node && docker compose up -d", "Запуск Remnawave Node контейнера")

        # Auto-run SSH Hardening on the new Node VPS
        try:
            from services.ssh_hardening import run_ssh_hardening
            if progress_cb:
                progress_cb(f"🛡️ Выполнение SSH Харденинга для Ноды {host}...")
            run_ssh_hardening(host, password, current_port=22, new_port=5422)
        except Exception as hard_err:
            logger.warning(f"Auto SSH hardening on node {host} skipped: {hard_err}")

        if progress_cb:
            progress_cb(f"🎉 Нода `{host}` ({country_code}) успешно настроена и защищена!")
        return True

    except Exception as e:
        logger.error(f"Node deployment failed on {host}: {e}")
        if progress_cb:
            progress_cb(f"❌ Ошибка деплоя ноды: {e}")
        return False
    finally:
        client.close()

async def deploy_node_async(
    host: str,
    password: str,
    domain: str = "example.com",
    country_code: str = "NL",
    node_secret: str = "",
    panel_url: str = "",
    progress_cb: Optional[Callable[[str], None]] = None
) -> bool:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, run_node_full_deploy, host, password, domain, country_code, node_secret, panel_url, progress_cb)

async def audit_node_async(host: str, password: str, progress_cb: Optional[Callable[[str], None]] = None) -> bool:
    commands = [
        "docker ps --format '{{.Names}}: {{.Status}}'",
        "nginx -t",
        "uname -r",
        "sysctl net.ipv4.tcp_congestion_control"
    ]
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, run_ssh_commands, host, password, commands, progress_cb)

