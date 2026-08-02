#!/usr/bin/env bash
# ==============================================================================
# 🚀 remna-bot — OpenSource Telegram Mini-App & Deployer for Remnawave
# ==============================================================================

set -e

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${CYAN}========================================================================${NC}"
echo -e "${GREEN}🚀 Установка remna-bot (Telegram Mini-App & Admin Suite)${NC}"
echo -e "${CYAN}========================================================================${NC}"

if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}❌ Пожалуйста, запустите скрипт с правами root (sudo).${NC}"
  exit 1
fi

echo -e "${YELLOW}📦 Проверка и установка системных зависимостей (curl, nano, git)...${NC}"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y && apt-get install -y --no-install-recommends curl ca-certificates nano git 2>/dev/null || true

INSTALL_DIR="$(pwd)"

if [ ! -f "$INSTALL_DIR/docker-compose.yml" ]; then
    echo -e "${YELLOW}📥 Клонирование репозитория remna-bot...${NC}"
    if [ -d "$INSTALL_DIR/remna-bot" ]; then
        cd "$INSTALL_DIR/remna-bot" && git pull
    else
        git clone https://github.com/xMentoRx/remna-bot.git "$INSTALL_DIR/remna-bot"
        cd "$INSTALL_DIR/remna-bot"
    fi
    INSTALL_DIR="$(pwd)"
fi
    echo -e "${YELLOW}📝 Заполнение конфигурации бота:${NC}"
    echo ""
    read -p "1. Введите Telegram Bot Token (от @BotFather) [Обязательно]: " BOT_TOKEN
    read -p "2. Введите Telegram Admin ID (ID админа или несколько через запятую) [Обязательно]: " ADMIN_IDS
    echo ""
    echo -e "${CYAN}💡 Настройка группы алертов (можно пропустить и настроить позже в .env):${NC}"
    read -p "3. ID супергруппы/канала для алертов мониторинга (напр. -1001234567890) [Enter - пропустить]: " ALERT_CHAT_ID

    ALERT_TOPIC_ID=""
    if [ -n "$ALERT_CHAT_ID" ]; then
        read -p "4. ID топика/форума в группах (напр. 2 или 0 для общего чата) [Enter - 0]: " ALERT_TOPIC_INPUT
        ALERT_TOPIC_ID="${ALERT_TOPIC_INPUT:-0}"
    fi

    cat <<EOF > "$INSTALL_DIR/.env"
# ==========================================
# 🤖 REMNA-BOT ENVIRONMENT CONFIGURATION
# ==========================================

# Обязательные настройки
BOT_TOKEN=${BOT_TOKEN}
ADMIN_CHAT_IDS=${ADMIN_IDS}

EOF

    if [ -n "$ALERT_CHAT_ID" ]; then
        cat <<EOF >> "$INSTALL_DIR/.env"
# Мониторинг и Алерты
ALERT_CHAT_ID=${ALERT_CHAT_ID}
ALERT_TOPIC_ID=${ALERT_TOPIC_ID}
EOF
    else
        cat <<EOF >> "$INSTALL_DIR/.env"
# Мониторинг и Алерты (Заполните при необходимости)
# ALERT_CHAT_ID=-1001234567890
# ALERT_TOPIC_ID=0
EOF
    fi

    cat <<EOF >> "$INSTALL_DIR/.env"

# Динамически заполняется при первом старте в Telegram MiniApp
API_URL=
API_TOKEN=

# Порт веб-сервера Mini-App
WEBAPP_PORT=8080
WEBAPP_HOST=0.0.0.0
EOF
    echo -e "${GREEN}✅ Файл .env успешно сформирован!${NC}"
fi


echo -e "${YELLOW}📦 Проверка Docker и Docker Compose...${NC}"
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | sh
    systemctl enable --now docker
fi

echo -e "${YELLOW}🚀 Запуск контейнера remna-bot...${NC}"
docker compose up -d --build || docker-compose up -d --build

echo -e "${CYAN}========================================================================${NC}"
echo -e "${GREEN}🎉 remna-bot запущен! Теперь откройте бота в Telegram и отправьте /start${NC}"
echo -e "${CYAN}========================================================================${NC}"
