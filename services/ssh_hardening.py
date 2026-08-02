import os
import json
import logging
import io
import paramiko
from typing import Dict, Any, Tuple, Optional, List

logger = logging.getLogger("remna-bot.ssh-hardening")
KEYS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "ssh_keys.json")

def generate_ed25519_keypair(comment: str = "remna-bot-key") -> Tuple[str, str]:
    """
    Generates a new Ed25519 SSH private/public keypair in memory.
    Returns (private_key_pem_str, public_key_ssh_str).
    """
    from cryptography.hazmat.primitives.asymmetric import ed25519
    from cryptography.hazmat.primitives import serialization

    key = ed25519.Ed25519PrivateKey.generate()
    private_key_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.OpenSSH,
        encryption_algorithm=serialization.NoEncryption()
    ).decode('utf-8')

    public_ssh_bytes = key.public_key().public_bytes(
        encoding=serialization.Encoding.OpenSSH,
        format=serialization.PublicFormat.OpenSSH
    ).decode('utf-8')

    public_key_ssh = f"{public_ssh_bytes} {comment}"
    return private_key_pem, public_key_ssh

def save_stored_key(host: str, private_key_pem: str, public_key_ssh: str, port: int) -> Dict[str, Any]:
    """Stores key credentials for a host IP in data/ssh_keys.json."""
    os.makedirs(os.path.dirname(KEYS_FILE), exist_ok=True)
    data = {}
    if os.path.exists(KEYS_FILE):
        try:
            with open(KEYS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}

    entry = {
        "host": host,
        "port": port,
        "private_key": private_key_pem,
        "public_key": public_key_ssh
    }
    data[host] = entry

    try:
        with open(KEYS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Failed to save SSH key entry: {e}")

    return entry

def get_stored_key(host: str) -> Optional[Dict[str, Any]]:
    """Retrieves key credentials for a host IP."""
    if os.path.exists(KEYS_FILE):
        try:
            with open(KEYS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get(host)
        except Exception:
            pass
    return None

def get_all_stored_keys() -> List[Dict[str, Any]]:
    """Returns a list of all stored SSH key entries."""
    if os.path.exists(KEYS_FILE):
        try:
            with open(KEYS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return list(data.values())
        except Exception:
            pass
    return []

def run_ssh_hardening(
    host: str,
    password: str,
    current_port: int = 22,
    new_port: int = 5422,
    install_crowdsec: bool = True,
    disable_password_auth: bool = True,
    progress_cb: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Performs 1-Click SSH Hardening on a target VPS:
    1. Generates Ed25519 SSH Keypair.
    2. Injects public key into /root/.ssh/authorized_keys.
    3. Verifies key authentication BEFORE modifying SSH config.
    4. Shifts SSH port to new_port (default 5422).
    5. Disables PasswordAuthentication if enabled.
    6. Installs Fail2ban / CrowdSec for bruteforce protection.
    7. Restarts SSH service safely.
    """
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        if progress_cb:
            progress_cb(f"🔑 Подключение к `{host}:{current_port}` по SSH...")
        client.connect(hostname=host, port=current_port, username="root", password=password, timeout=15)

        # 1. Generate Keypair
        if progress_cb:
            progress_cb("🔐 Генерация парного SSH-ключа (Ed25519)...")
        private_pem, public_ssh = generate_ed25519_keypair(comment=f"remna-bot-{host}")

        def exec_cmd(cmd: str, msg: str):
            if progress_cb:
                progress_cb(f"⚙️ {msg}...")
            stdin, stdout, stderr = client.exec_command(cmd, get_pty=True)
            status = stdout.channel.recv_exit_status()
            out = stdout.read().decode('utf-8', errors='ignore')
            return status, out

        # 2. Inject public key into authorized_keys
        exec_cmd("mkdir -p /root/.ssh && chmod 700 /root/.ssh", "Подготовка каталога /root/.ssh")
        sftp = client.open_sftp()
        try:
            current_auth = ""
            try:
                with sftp.file("/root/.ssh/authorized_keys", "r") as f:
                    current_auth = f.read().decode('utf-8', errors='ignore')
            except Exception:
                pass
            
            if public_ssh not in current_auth:
                updated_auth = current_auth.strip() + f"\n{public_ssh}\n"
                with sftp.file("/root/.ssh/authorized_keys", "w") as f:
                    f.write(updated_auth)
        finally:
            sftp.close()

        exec_cmd("chmod 600 /root/.ssh/authorized_keys", "Настройка прав доступаauthorized_keys")

        # 3. Configure Firewall to open new_port
        exec_cmd(f"command -v ufw >/dev/null 2>&1 && ufw allow {new_port}/tcp || true", f"Открытие порта {new_port} в UFW")
        exec_cmd(f"command -v iptables >/dev/null 2>&1 && iptables -A INPUT -p tcp --dport {new_port} -j ACCEPT || true", f"Открытие порта {new_port} в iptables")

        # 4. Probe SSH Key Connection BEFORE hardening config
        if progress_cb:
            progress_cb("🧪 Проверка валидности входа по созданному SSH-ключу...")
            
        probe_key = paramiko.Ed25519Key.from_private_key(io.StringIO(private_pem))
        probe_client = paramiko.SSHClient()
        probe_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            probe_client.connect(hostname=host, port=current_port, username="root", pkey=probe_key, timeout=10)
            probe_client.close()
            logger.info(f"SSH Key Probe successful on {host}")
        except Exception as probe_err:
            logger.error(f"SSH Key Probe failed: {probe_err}")
            return {
                "success": False,
                "error": f"Проверка входа по SSH-ключу не удалась: {probe_err}. Настройки не изменены во избежание блокировки."
            }

        # 5. Optional CrowdSec / Fail2ban installation
        if install_crowdsec:
            exec_cmd(
                "export DEBIAN_FRONTEND=noninteractive; export NEEDRESTART_MODE=a; "
                "apt-get update && apt-get -o Dpkg::Options::='--force-confdef' -o Dpkg::Options::='--force-confold' -y install fail2ban 2>/dev/null || true",
                "Установка Fail2ban в тихом режиме"
            )
            exec_cmd("systemctl enable --now fail2ban 2>/dev/null || true", "Запуск службы Fail2ban")

        # 6. Apply SSHd Configuration changes
        sshd_conf = f"""
# --- Remna-Bot Hardening ---
Port {new_port}
PubkeyAuthentication yes
"""
        if disable_password_auth:
            sshd_conf += "PasswordAuthentication no\n"

        sftp = client.open_sftp()
        with sftp.file("/etc/ssh/sshd_config.d/remna_hardening.conf", "w") as f:
            f.write(sshd_conf)
        sftp.close()

        # Update main sshd_config Port if sshd_config.d is not included
        exec_cmd(
            f"grep -q 'Port ' /etc/ssh/sshd_config && sed -i 's/^#\\?Port .*/Port {new_port}/' /etc/ssh/sshd_config || echo 'Port {new_port}' >> /etc/ssh/sshd_config",
            f"Перенос порта SSH на {new_port}"
        )
        if disable_password_auth:
            exec_cmd("sed -i 's/^#\\?PasswordAuthentication .*/PasswordAuthentication no/' /etc/ssh/sshd_config", "Отключение входа по паролю")

        # 7. Restart SSH Service
        exec_cmd("systemctl restart sshd 2>/dev/null || systemctl restart ssh 2>/dev/null", "Перезапуск службы SSH")

        # Save to stored keys
        stored = save_stored_key(host, private_pem, public_ssh, new_port)

        if progress_cb:
            progress_cb(f"🎉 Успешно! SSH защищен: порт {new_port}, вход по паролю отключен!")

        return {
            "success": True,
            "host": host,
            "new_port": new_port,
            "private_key": private_pem,
            "public_key": public_ssh,
            "ssh_command": f"ssh -i id_ed25519.pem -p {new_port} root@{host}"
        }

    except Exception as e:
        logger.error(f"SSH Hardening failed for {host}: {e}")
        if progress_cb:
            progress_cb(f"❌ Ошибка SSH Харденинга: {e}")
        return {"success": False, "error": str(e)}
    finally:
        client.close()
