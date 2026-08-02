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

INSTALL_DIR="$(pwd)"

if [ ! -f "$INSTALL_DIR/.env" ]; then
    echo -e "${YELLOW}📝 Заполнение базовой конфигурации (всего 2 параметра):${NC}"
    echo ""
    read -p "1. Введите Telegram Bot Token (от @BotFather): " BOT_TOKEN
    read -p "2. Введите Telegram Admin ID (свой ID или несколько через запятую): " ADMIN_IDS
    echo ""

    cat <<EOF > "$INSTALL_DIR/.env"
BOT_TOKEN=${BOT_TOKEN}
ADMIN_CHAT_IDS=${ADMIN_IDS}

# Динамически заполняется при первом старте в Telegram
API_URL=
API_TOKEN=

# Порт веб-сервера Mini-App
WEBAPP_PORT=8080
WEBAPP_HOST=0.0.0.0
EOF
    echo -e "${GREEN}✅ Файл .env успешно создан!${NC}"
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
