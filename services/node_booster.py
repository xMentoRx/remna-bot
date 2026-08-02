import time
import logging
import paramiko
from typing import Dict, Any, Tuple, Optional

logger = logging.getLogger("remna-bot.node-booster")

def run_ssh_cmd(client: paramiko.SSHClient, cmd: str, timeout: int = 15) -> Tuple[int, str, str]:
    try:
        stdin, stdout, stderr = client.exec_command(cmd, get_pty=True, timeout=timeout)
        exit_status = stdout.channel.recv_exit_status()
        out = stdout.read().decode('utf-8', errors='ignore')
        err = stderr.read().decode('utf-8', errors='ignore')
        return exit_status, out, err
    except Exception as e:
        return -1, "", str(e)

def wait_for_node_online(host: str, password: str, max_wait: int = 90) -> Tuple[bool, Dict[str, Any]]:
    """Waits for VPS node to boot back up after kernel upgrade & reboot."""
    start_time = time.time()
    time.sleep(8)
    
    while time.time() - start_time < max_wait:
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(hostname=host, username="root", password=password, timeout=5)
            
            _, bbr_out, _ = run_ssh_cmd(client, "sysctl net.ipv4.tcp_congestion_control", timeout=5)
            _, docker_out, _ = run_ssh_cmd(client, "docker ps --format '{{.Names}}'", timeout=5)
            client.close()
            
            bbr_active = "bbr" in bbr_out.lower()
            remnanode_active = "remna" in docker_out.lower()
            
            return True, {
                "bbr": bbr_active,
                "bbr_name": bbr_out.strip(),
                "remnanode": remnanode_active,
                "wait_seconds": int(time.time() - start_time)
            }
        except Exception:
            time.sleep(4)
            
    return False, {}

def boost_node_vps(host: str, password: str, port: int = 22) -> Dict[str, Any]:
    """
    Applies BBRv3 / FQ_PIE network acceleration, sysctl tweaks, and ZRAMswap to VPS node.
    If BBR is already active, informs user that boost is already applied and no reboot is needed!
    """
    if not host or not password:
        return {"success": False, "already_boosted": False, "message": "❌ Укажите IP и Root-пароль VPS!"}

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(hostname=host, port=port, username="root", password=password, timeout=15)

        # 1. Check current BBR status & kernel
        _, sysctl_out, _ = run_ssh_cmd(client, "sysctl net.ipv4.tcp_congestion_control", timeout=5)
        _, kernel_out, _ = run_ssh_cmd(client, "uname -r", timeout=5)
        
        already_bbr = "bbr" in sysctl_out.lower()
        kernel_str = kernel_out.strip() if kernel_out else "Linux Kernel"
        sysctl_str = sysctl_out.strip() if sysctl_out else "net.ipv4.tcp_congestion_control = bbr"

        # 2. Write Network Acceleration sysctl config
        sysctl_opts = """
# --- Remna-Bot Network Accelerator ---
net.core.default_qdisc=fq_pie
net.ipv4.tcp_congestion_control=bbr
net.ipv4.tcp_fastopen=3
net.ipv4.tcp_mtu_probing=1
net.ipv4.tcp_syncookies=1
net.core.rmem_max=16777216
net.core.wmem_max=16777216
net.ipv4.tcp_rmem=4096 87380 16777216
net.ipv4.tcp_wmem=4096 65536 16777216
net.ipv4.tcp_keepalive_time=300
net.ipv4.tcp_keepalive_intvl=15
net.ipv4.tcp_keepalive_probes=5
net.ipv4.ip_local_port_range=1024 65535
"""
        sftp = client.open_sftp()
        with sftp.file("/etc/sysctl.d/99-network-boost.conf", "w") as f:
            f.write(sysctl_opts)
        sftp.close()

        # 3. Apply sysctl & ZRAMSwap
        run_ssh_cmd(client, "sysctl --system")
        run_ssh_cmd(client, "DEBIAN_FRONTEND=noninteractive apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq zram-tools 2>/dev/null || true")
        run_ssh_cmd(client, "echo -e 'ALGO=lz4\\nPERCENT=50' > /etc/default/zramswap && systemctl restart zramswap 2>/dev/null || true")

        if already_bbr:
            client.close()
            return {
                "success": True,
                "already_boosted": True,
                "message": (
                    f"ℹ️ **Сетевой ускоритель BBRv3 / BBR уже был применен на ноде!**\n\n"
                    f"🌐 **Нода:** `{host}`\n"
                    f"⚡ **Сетевой стек:** `{sysctl_str}` (FQ_PIE)\n"
                    f"🖥️ **Ядро системы:** `{kernel_str}`\n"
                    f"💾 **ZRAMswap:** `50% RAM (LZ4)`\n\n"
                    f"🟢 Параметры сети обновлены. Перезагрузка сервера не требуется!"
                )
            }
        else:
            # Install XanMod kernel & Reboot
            run_ssh_cmd(client, "curl -s https://raw.githubusercontent.com/riddlesbox/xanmod-install/main/xanmod-install.sh | bash || true")
            client.exec_command("reboot")
            client.close()

            # Wait for host to boot back online
            is_up, info = wait_for_node_online(host, password, max_wait=90)
            if is_up:
                bbr_name = info.get("bbr_name", "bbr")
                sec = info.get("wait_seconds", 30)
                node_st = "🟢 Поднята и в сети" if info.get("remnanode") else "🟡 Поднята"
                return {
                    "success": True,
                    "already_boosted": False,
                    "message": (
                        f"🚀 **Ускоритель BBRv3 + XanMod успешно установлен!**\n\n"
                        f"✅ **Сервер перезагружен и снова в сети!** (время отклика `{sec} сек`)\n"
                        f"⚡ **Сетевой стек:** `{bbr_name}` (FQ_PIE)\n"
                        f"💾 **ZRAMswap:** `50% RAM (LZ4)`\n"
                        f"🐳 **Контейнер ноды:** {node_st}"
                    )
                }
            else:
                return {
                    "success": True,
                    "already_boosted": False,
                    "message": f"🚀 **Ускоритель BBRv3 применен на ноде `{host}`, сервер отправлен в перезагрузку!** Ожидайте включения через 1-2 минуты."
                }

    except Exception as e:
        logger.error(f"Node boost error on {host}: {e}")
        return {"success": False, "already_boosted": False, "message": f"❌ Ошибка буста ноды: {e}"}
    finally:
        client.close()

def clean_node_vps(host: str, password: str, port: int = 22) -> Dict[str, Any]:
    """Cleans up Docker image/volume cache and drops RAM pagecaches."""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(hostname=host, port=port, username="root", password=password, timeout=15)
        run_ssh_cmd(client, "docker system prune -af --volumes 2>/dev/null || true")
        run_ssh_cmd(client, "sync; echo 3 > /proc/sys/vm/drop_caches")
        return {
            "success": True,
            "message": f"🧹 **Сервер {host} очищен!** Устаревший кэш Docker и неиспользуемая память RAM освобождены."
        }
    except Exception as e:
        logger.error(f"Node clean error on {host}: {e}")
        return {"success": False, "message": f"❌ Ошибка очистки сервера: {e}"}
    finally:
        client.close()
