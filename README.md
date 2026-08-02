<div align="center">
  <h1>⚡ Remna-Bot — OpenSource Management Suite & MiniApp for Remnawave Panel</h1>
  <p><b>Мощная система управления, 1-Click деплоймента, SSH-харденинга и встроенного прокси-интерфейса для панелей Remnawave v2.7.4+ & v2.8+</b></p>

  <p>
    <a href="#-основные-возможности"><img src="https://img.shields.io/badge/Features-Comprehensive-blue.svg" alt="Features"></a>
    <a href="#-быстрый-старт"><img src="https://img.shields.io/badge/Deploy-1--Click-success.svg" alt="Deploy"></a>
    <a href="https://python.org"><img src="https://img.shields.io/badge/Python-3.10+-yellow.svg" alt="Python Version"></a>
    <a href="https://aiogram.dev"><img src="https://img.shields.io/badge/Aiogram-3.x-blueviolet.svg" alt="Aiogram Version"></a>
  </p>
</div>

---

## 🚀 Основные возможности

* 🌐 **Прямой встроенный прокси Remnawave UI (`/remna_embed`)**:
  Официальный веб-интерфейс Remnawave со всеми его родными вкладками (*Главная, Пользователи, Ноды, Профили, Хосты, Настройки*) транслируется прямо внутри Telegram MiniApp с авто-инъекцией панели управления **Remna-Bot Bar**.
* 🚀 **1-Click Деплой Свежей Панели**:
  Автоматическое развертывание Docker Engine, PostgreSQL 16, Remnawave Backend и Caddy SSL на чистый VPS за 45 секунд с авто-регистрацией SuperAdmin.
* 🖥️ **1-Click Деплой Нод & Stealth Nginx**:
  Установка ноды Xray/Reality с маскировкой под реальный сайт через мемори-сокет `/dev/shm/nginx.sock` и включением ускорения BBRv3.
* 🛡️ **SSH Hardening & Key Vault Suite**:
  Автоматическая генерация ключей `Ed25519`, смена SSH порта со стандартного 22 на безопасный **`5422`**, отключение парольного входа, защита от брутфорса `Fail2ban` и выдача скачиваемых файловых ключей `.pem` на Рабочий Стол/смартфон.
* 🔍 **Интеллектуальный поиск юзеров**:
  Поиск по Telegram ID, аккаунтам формата `user_123456789`, ссылкам `t.me/` и UUID с приведением списка пользователей к дизайну Remnawave v2.8.0.
* 🎨 **Динамические Темы Оформления**:
  Мгновенное переключение кастомных тем (*Cyberpunk, Emerald, Sunset, Midnight*) прямо поверх графиков Remnawave.
* ⚡ **Ookla 10Gbit Speedtest**:
  Интерактивное измерение параметров сети (Ping, Download, Upload) непосредственно в интерфейсе MiniApp.

---

## 📦 Быстрый старт (Установка за 1 минуту)

### 0️⃣ Подготовка нового VPS (1 команда)
Если у вас голый Linux VPS (Ubuntu / Debian), подготовьте систему в 1 клик:
```bash
apt update && apt install -y curl nano git
```

### Вариант 1: Автоматический скрипт установки на VPS (Рекомендуется)

Запустите скрипт на вашем VPS:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/xMentoRx/remna-bot/main/install.sh)
```

### Вариант 2: Запуск через Docker Compose

```bash
git clone https://github.com/xMentoRx/remna-bot.git
cd remna-bot
cp .env.example .env
# Укажите BOT_TOKEN и ADMIN_CHAT_IDS
nano .env
docker compose up -d --build
```


---

## 🛠️ Переменные окружения (`.env`)

| Переменная | Описание | Обязательная |
| :--- | :--- | :---: |
| `BOT_TOKEN` | Токен Telegram-бота из @BotFather | **Да** |
| `ADMIN_CHAT_IDS` | Telegram ID администраторов через запятую (`12345678,9876543`) | **Да** |
| `ALERT_CHAT_ID` | ID супергруппы для уведомлений о падении нод | Нет |
| `API_URL` | Стартовый URL панели Remnawave (`https://panel.mydomain.com`) | Нет |
| `API_TOKEN` | Стартовый API Bearer Token | Нет |
| `WEBAPP_PORT` | Порт сервера MiniApp (по умолчанию `8080`) | Нет |

---

## 🏛️ Архитектура Проекта

```
remna-bot/
├── bot.py                     # Главный оркестратор Aiogram 3 + WebApp Server
├── config.py                  # Конфигуратор настроек и .env
├── handlers/                  # Роутеры обработчиков Aiogram 3
│   ├── start_onboarding.py    # Приветствие и 1-Click онбординг
│   ├── node_handlers.py       # Управление нодами в Telegram
│   └── user_handlers.py       # Поиск пользователей и сброс трафика
├── services/                  # Сервисы инфраструктуры
│   ├── ssh_hardening.py       # (NEW) Модуль генерации SSH-ключей и Fail2ban
│   ├── remnawave_api.py       # Async aiohttp API адаптер Remnawave v2.7.4+ / v2.8+
│   ├── webapp_server.py       # REST & Proxy сервер (/remna_embed)
│   ├── monitoring.py          # Фоновый мониторинг нод
│   ├── panel_deployer.py      # 1-Click SSH деплоер Панели & Caddy SSL
│   └── node_deployer.py       # 1-Click SSH деплоер Ноды & Stealth Nginx
├── webapp/                    # Telegram MiniApp Frontend
│   ├── index.html             # Внутренний интерфейс MiniApp
│   ├── style.css              # Дизайн-система Glassmorphism
│   ├── app.js                 # JS логика, скачивание .pem ключей и списки
│   ├── remnabot_overlay.js    # Инъецируемый плавающий бар Remna-Bot
│   └── remnabot_overlay.css   # Стили тем кастомизации
├── Dockerfile
├── docker-compose.yml
├── install.sh
└── README.md
```

---

## 🔒 Безопасность и Гарантии

* **Fail-safe проверка входа по ключу**: Бот сначала проверяет авторизацию по созданному ключу SSH, и лишь при 100% успехе отключает вход по паролю.
* **DevOps Non-Interactive Suite**: Все системные команды оснащены флагами `DEBIAN_FRONTEND=noninteractive` и `NEEDRESTART_MODE=a`, гарантируя отсутствие зависаний на терминальных запросах `Enter/Y/N`.

---

## 📄 Лицензия

Распространяется под лицензией MIT. Подробнее см. в файле [LICENSE](LICENSE).
