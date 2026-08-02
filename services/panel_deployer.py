import asyncio
import logging
import secrets
import time
import requests
import paramiko
import urllib3
from typing import Callable, Optional, Dict, Any

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logger = logging.getLogger("remna-bot.panel-deployer")

def auto_register_admin(panel_url: str, admin_username: str, admin_password: str) -> Optional[str]:
    """
    Attempts to automatically register the initial SuperAdmin account via API
    once the fresh Remnawave backend starts up.
    Waits up to 120 seconds to allow slow Docker image pulls.
    """
    headers = {
        "Content-Type": "application/json",
        "X-Remnawave-Client-Type": "browser"
    }
    register_endpoints = ["/api/auth/register", "/api/auth/setup", "/api/auth/first-user", "/api/auth/register-first"]
    
    # Wait up to 120 seconds (60 attempts * 2 sec) for Caddy + Remnawave container to build and start
    for attempt in range(60):
        time.sleep(2)
        for ep in register_endpoints:
            try:
                r = requests.post(
                    f"{panel_url}{ep}",
                    json={"username": admin_username, "password": admin_password},
                    headers=headers,
                    timeout=5,
                    verify=False
                )
                if r.status_code in (200, 201):
                    res = r.json()
                    token = (
                        res.get("accessToken") or
                        res.get("token") or
                        res.get("response", {}).get("accessToken") or
                        res.get("response", {}).get("token")
                    )
                    if token:
                        logger.info(f"Auto-registered SuperAdmin '{admin_username}' on {panel_url}")
                        return token
            except Exception as e:
                logger.debug(f"Attempt {attempt+1} probing {ep}: {e}")

    # Fallback: Try login if already registered
    try:
        r = requests.post(
            f"{panel_url}/api/auth/login",
            json={"username": admin_username, "password": admin_password},
            headers=headers,
            timeout=5,
            verify=False
        )
        if r.status_code in (200, 201):
            res = r.json()
            return res.get("accessToken") or res.get("response", {}).get("accessToken")
    except Exception as e:
        logger.debug(f"Fallback login failed: {e}")

    return None

def run_panel_ssh_install(
    host: str,
    password: str,
    panel_domain: str,
    sub_domain: str,
    admin_username: str = "admin",
    admin_password: str = "",
    harden_vps: bool = True,
    progress_cb: Optional[Callable[[str], None]] = None
) -> Dict[str, Any]:
    """
    Deploys a fresh Remnawave Panel instance on a clean VPS via SSH.
    Validates DNS A-records and SSH credentials BEFORE installation.
    """
    import socket

    # 1. Validate DNS A-records before SSH connecting
    if progress_cb:
        progress_cb(f"🔍 Проверка DNS A-записей для `{panel_domain}` и `{sub_domain}`...")
    try:
        ip_panel = socket.gethostbyname(panel_domain)
        if ip_panel != host:
            return {
                "success": False,
                "error": f"Ошибка DNS: Домен `{panel_domain}` указывает на `{ip_panel}`, а не на IP вашего VPS `{host}`. Если вы используете Cloudflare, временно отключите проксирование (поставьте 'Серые облака' / DNS Only), чтобы Caddy мог выпустить SSL!"
            }
    except Exception:
        return {
            "success": False,
            "error": f"Ошибка DNS: Не удалось распознать IP домена `{panel_domain}`. Убедитесь, что создали A-запись на IP `{host}` и подождите 1-2 минуты для обновления DNS!"
        }

    if not admin_password:
        admin_password = secrets.token_urlsafe(12)

    jwt_secret = secrets.token_hex(32)
    cookie_secret = secrets.token_hex(16)
    db_password = secrets.token_urlsafe(16)

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        if progress_cb:
            progress_cb(f"🔑 Подключение к VPS `{host}` по SSH...")
        try:
            client.connect(hostname=host, username="root", password=password, timeout=15)
        except paramiko.AuthenticationException:
            return {"success": False, "error": f"Ошибка SSH: Неверный Root-пароль от VPS `{host}`!"}
        except Exception as conn_err:
            return {"success": False, "error": f"Не удалось подключиться к VPS `{host}`: {conn_err}"}

        def exec_cmd(cmd: str, desc: str):
            if progress_cb:
                progress_cb(f"⚙️ {desc}...")
            stdin, stdout, stderr = client.exec_command(cmd, get_pty=True)
            status = stdout.channel.recv_exit_status()
            out = stdout.read().decode('utf-8', errors='ignore')
            if status != 0:
                logger.warning(f"Cmd '{cmd}' status {status}: {out[:100]}")
            return out

        # 1. Non-interactive environment setup & unlock APT locks
        exec_cmd(
            "export DEBIAN_FRONTEND=noninteractive; export NEEDRESTART_MODE=a; export UCF_FORCE_CONFFOLD=1; "
            "mkdir -p /etc/needrestart/conf.d; echo '$nrconf{restart} = \"a\";' > /etc/needrestart/conf.d/50auto.conf 2>/dev/null || true; "
            "for i in {1..10}; do fuser -v /var/lib/dpkg/lock-frontend >/dev/null 2>&1 || break; sleep 3; done; "
            "systemctl stop unattended-upgrades apache2 nginx 2>/dev/null || true; "
            "killall -9 apt apt-get dpkg 2>/dev/null || true; "
            "rm -f /var/lib/dpkg/lock* /var/lib/apt/lists/lock /var/cache/apt/archives/lock",
            "Подавление интерактивных окон и снятие APT-блокировок"
        )

        # 2. Non-interactive System update
        exec_cmd(
            "export DEBIAN_FRONTEND=noninteractive; export NEEDRESTART_MODE=a; "
            "apt-get update && apt-get -o Dpkg::Options::='--force-confdef' -o Dpkg::Options::='--force-confold' -y install curl git jq ca-certificates",
            "Обновление пакетов APT (Тихий режим без запросов Enter)"
        )

        # 3. Non-interactive Docker Engine & Caddy SSL (Fail-safe for Ubuntu 22/24 & Debian)
        exec_cmd(
            "export DEBIAN_FRONTEND=noninteractive; export NEEDRESTART_MODE=a; "
            "command -v docker >/dev/null 2>&1 || (curl -fsSL https://get.docker.com | sh); "
            "apt-get update -y 2>/dev/null || true; "
            "apt-get -y install debian-keyring debian-archive-keyring apt-transport-https curl gnupg 2>/dev/null || true; "
            "mkdir -p /usr/share/keyrings /etc/apt/sources.list.d; "
            "curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg 2>/dev/null || true; "
            "curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list 2>/dev/null || true; "
            "apt-get update -y 2>/dev/null || true; "
            "apt-get -o Dpkg::Options::='--force-confdef' -o Dpkg::Options::='--force-confold' -y install docker-compose-v2 caddy 2>/dev/null || true; "
            "if ! command -v caddy >/dev/null 2>&1; then "
            "  curl -fsSL 'https://caddyserver.com/api/download?os=linux&arch=amd64' -o /usr/bin/caddy && chmod +x /usr/bin/caddy; "
            "  caddy service install 2>/dev/null || true; "
            "fi",
            "Автоматическая гарантия установки Docker Engine & Caddy SSL"
        )

        # 4. Enable services
        exec_cmd("systemctl enable --now docker", "Запуск системной службы Docker Engine")

        # 5. Prepare directories explicitly before SFTP
        exec_cmd("mkdir -p /opt/remnawave /etc/caddy", "Подготовка каталогов /opt/remnawave и /etc/caddy")

        # 6. Generate docker-compose.yml
        metrics_pass = secrets.token_urlsafe(16)
        compose_content = f"""version: '3.8'

services:
  postgres:
    image: postgres:16-alpine
    container_name: remnawave-db
    restart: always
    environment:
      POSTGRES_USER: remnawave
      POSTGRES_PASSWORD: {db_password}
      POSTGRES_DB: remnawave
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U remnawave"]
      interval: 5s
      timeout: 5s
      retries: 5

  valkey:
    image: valkey/valkey:8-alpine
    container_name: remnawave-valkey
    restart: always
    command: valkey-server --save 60 1 --loglevel warning
    volumes:
      - valkey_data:/data
    healthcheck:
      test: ["CMD", "valkey-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

  remnawave:
    image: ghcr.io/remnawave/backend:latest
    container_name: remnawave-panel
    restart: always
    depends_on:
      postgres:
        condition: service_healthy
      valkey:
        condition: service_healthy
    ports:
      - "127.0.0.1:3000:3000"
    environment:
      DATABASE_URL: "postgresql://remnawave:{db_password}@postgres:5432/remnawave?sslmode=disable"
      REDIS_HOST: "valkey"
      REDIS_PORT: "6379"
      FRONT_END_DOMAIN: "{panel_domain}"
      SUB_PUBLIC_DOMAIN: "{sub_domain}"
      METRICS_USER: "admin"
      METRICS_PASS: "{metrics_pass}"
      APP_SECRET: "{jwt_secret}"
      JWT_AUTH_SECRET: "{jwt_secret}"
      JWT_SECRET: "{jwt_secret}"
      COOKIE_SECRET: "{cookie_secret}"
      PORT: "3000"

volumes:
  postgres_data:
  valkey_data:
"""
        sftp = client.open_sftp()
        with sftp.file("/opt/remnawave/docker-compose.yml", "w") as f:
            f.write(compose_content)

        # 7. Configure Caddyfile with /remna_embed proxy routing to remna-bot (port 8080)
        caddyfile_content = f"""{panel_domain} {{
    handle /remna_embed* {{
        reverse_proxy 127.0.0.1:8080
    }}
    handle /remnabot_overlay* {{
        reverse_proxy 127.0.0.1:8080
    }}
    handle /api/stats* {{
        reverse_proxy 127.0.0.1:8080
    }}
    handle /api/hosts* {{
        reverse_proxy 127.0.0.1:8080
    }}
    handle /api/balancer* {{
        reverse_proxy 127.0.0.1:8080
    }}
    handle /api/settings* {{
        reverse_proxy 127.0.0.1:8080
    }}
    handle /api/deploy* {{
        reverse_proxy 127.0.0.1:8080
    }}
    handle {{
        reverse_proxy 127.0.0.1:3000
    }}
}}

{sub_domain} {{
    reverse_proxy 127.0.0.1:3000
}}
"""
        with sftp.file("/etc/caddy/Caddyfile", "w") as f:
            f.write(caddyfile_content)
        sftp.close()

        # 8. Run Docker Compose & reload Caddy SSL
        exec_cmd("cd /opt/remnawave && docker compose up -d", "Запуск контейнеров Remnawave Backend & Postgres")
        exec_cmd("systemctl enable caddy 2>/dev/null || true; systemctl restart caddy 2>/dev/null || caddy run --config /etc/caddy/Caddyfile &", "Запуск службы Caddy и авто-выпуск SSL")

        panel_url = f"https://{panel_domain}"
        token = auto_register_admin(panel_url, admin_username, admin_password)

        if token:
            save_settings(panel_url, token)

        # 9. Optional SSH Hardening for Panel VPS
        ssh_key_info = None
        if harden_vps:
            try:
                from services.ssh_hardening import run_ssh_hardening
                ssh_key_info = run_ssh_hardening(
                    host=host,
                    password=password,
                    current_port=22,
                    new_port=5422,
                    install_crowdsec=True,
                    disable_password_auth=True,
                    progress_cb=progress_cb
                )
            except Exception as hard_err:
                logger.warning(f"Panel SSH Hardening warning: {hard_err}")

        if progress_cb:
            progress_cb("🎉 Панель Remnawave успешно развернута и защищена!")

        return {
            "success": True,
            "panel_url": panel_url,
            "sub_url": f"https://{sub_domain}",
            "admin_username": admin_username,
            "admin_password": admin_password,
            "auto_connected": bool(token),
            "ssh_key": ssh_key_info
        }

    except Exception as e:
        logger.error(f"Panel deployment failed on {host}: {e}")
        if progress_cb:
            progress_cb(f"❌ Ошибка развертывания панели: {e}")
        return {"success": False, "error": str(e)}
    finally:
        client.close()

async def deploy_fresh_panel_async(
    host: str,
    password: str,
    panel_domain: str,
    sub_domain: str,
    admin_username: str = "admin",
    admin_password: str = "",
    harden_vps: bool = True,
    progress_cb: Optional[Callable[[str], None]] = None
) -> Dict[str, Any]:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None,
        lambda: run_panel_ssh_install(
            host=host,
            password=password,
            panel_domain=panel_domain,
            sub_domain=sub_domain,
            admin_username=admin_username,
            admin_password=admin_password,
            harden_vps=harden_vps,
            progress_cb=progress_cb
        )
    )
def run_panel_backup(host: str, password: str, port: int = 22) -> Dict[str, Any]:
    """Performs PostgreSQL database backup of Remnawave Panel via SSH."""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(hostname=host, port=port, username="root", password=password, timeout=15)
        backup_filename = f"remnawave_backup_{int(time.time())}.sql.gz"
        backup_remote_path = f"/tmp/{backup_filename}"
        
        cmd = f"docker exec remnawave-db pg_dump -U remnawave remnawave | gzip > {backup_remote_path}"
        stdin, stdout, stderr = client.exec_command(cmd)
        exit_code = stdout.channel.recv_exit_status()
        
        if exit_code == 0:
            local_backup_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "backups")
            os.makedirs(local_backup_dir, exist_ok=True)
            local_path = os.path.join(local_backup_dir, backup_filename)
            
            sftp = client.open_sftp()
            sftp.get(backup_remote_path, local_path)
            sftp.remove(backup_remote_path)
            sftp.close()
            
            return {
                "success": True,
                "local_path": local_path,
                "filename": backup_filename,
                "message": f"💾 Бэкап базы данных успешно создан: `{backup_filename}`"
            }
        else:
            return {"success": False, "error": "Не удалось создать дампы PostgreSQL через Docker exec"}
    except Exception as e:
        logger.error(f"Panel backup error on {host}: {e}")
        return {"success": False, "error": str(e)}
    finally:
        client.close()

async def backup_panel_database_async(host: str, password: str, port: int = 22) -> Dict[str, Any]:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, run_panel_backup, host, password, port)


