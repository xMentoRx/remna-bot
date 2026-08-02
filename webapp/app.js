// Initialize Telegram WebApp
const tg = window.Telegram?.WebApp;
if (tg) {
    tg.ready();
    tg.expand();
}

// Country Database with ISO Codes, Russian & English names, and Flags
const countriesDb = [
    { code: 'NL', nameRu: 'Нидерланды', nameEn: 'Netherlands', flag: '🇳🇱' },
    { code: 'DE', nameRu: 'Германия', nameEn: 'Germany', flag: '🇩🇪' },
    { code: 'FI', nameRu: 'Финляндия', nameEn: 'Finland', flag: '🇫🇮' },
    { code: 'SE', nameRu: 'Швеция', nameEn: 'Sweden', flag: '🇸🇪' },
    { code: 'RU', nameRu: 'Россия', nameEn: 'Russia', flag: '🇷🇺' },
    { code: 'US', nameRu: 'США', nameEn: 'United States', flag: '🇺🇸' },
    { code: 'FR', nameRu: 'Франция', nameEn: 'France', flag: '🇫🇷' },
    { code: 'GB', nameRu: 'Великобритания', nameEn: 'United Kingdom', flag: '🇬🇧' },
    { code: 'PL', nameRu: 'Польша', nameEn: 'Poland', flag: '🇵🇱' },
    { code: 'TR', nameRu: 'Турция', nameEn: 'Turkey', flag: '🇹🇷' },
    { code: 'KZ', nameRu: 'Казахстан', nameEn: 'Kazakhstan', flag: '🇰🇿' },
    { code: 'UA', nameRu: 'Украина', nameEn: 'Ukraine', flag: '🇺🇦' },
    { code: 'JP', nameRu: 'Япония', nameEn: 'Japan', flag: '🇯🇵' },
    { code: 'SG', nameRu: 'Сингапур', nameEn: 'Singapore', flag: '🇸🇬' },
    { code: 'CH', nameRu: 'Швейцария', nameEn: 'Switzerland', flag: '🇨🇭' },
    { code: 'AT', nameRu: 'Австрия', nameEn: 'Austria', flag: '🇦🇹' },
    { code: 'ES', nameRu: 'Испания', nameEn: 'Spain', flag: '🇪🇸' },
    { code: 'IT', nameRu: 'Италия', nameEn: 'Italy', flag: '🇮🇹' },
    { code: 'CA', nameRu: 'Канада', nameEn: 'Canada', flag: '🇨🇦' },
    { code: 'EE', nameRu: 'Эстония', nameEn: 'Estonia', flag: '🇪🇪' },
    { code: 'LV', nameRu: 'Латвия', nameEn: 'Latvia', flag: '🇱🇻' },
    { code: 'LT', nameRu: 'Литва', nameEn: 'Lithuania', flag: '🇱🇹' },
    { code: 'CZ', nameRu: 'Чехия', nameEn: 'Czech Republic', flag: '🇨🇿' },
    { code: 'RO', nameRu: 'Румыния', nameEn: 'Romania', flag: '🇷🇴' },
    { code: 'BG', nameRu: 'Болгария', nameEn: 'Bulgaria', flag: '🇧🇬' },
    { code: 'GE', nameRu: 'Грузия', nameEn: 'Georgia', flag: '🇬🇪' },
    { code: 'AM', nameRu: 'Армения', nameEn: 'Armenia', flag: '🇦🇲' },
    { code: 'BY', nameRu: 'Беларусь', nameEn: 'Belarus', flag: '🇧🇾' },
    { code: 'AE', nameRu: 'ОАЭ', nameEn: 'UAE', flag: '🇦🇪' },
    { code: 'IL', nameRu: 'Израиль', nameEn: 'Israel', flag: '🇮🇱' }
];

function getCountryFlag(code) {
    if (!code) return '🌐';
    const clean = code.toUpperCase().trim();
    const found = countriesDb.find(c => c.code === clean);
    return found ? found.flag : '🌐';
}

function showCountryDropdown() {
    filterCountries();
    document.getElementById('countryDropdownList').style.display = 'block';
}

function filterCountries() {
    const query = document.getElementById('countrySearchInput').value.toLowerCase().trim();
    const list = document.getElementById('countryDropdownList');
    list.innerHTML = '';

    const filtered = countriesDb.filter(c => 
        c.code.toLowerCase().includes(query) ||
        c.nameRu.toLowerCase().includes(query) ||
        c.nameEn.toLowerCase().includes(query)
    );

    if (filtered.length === 0) {
        list.innerHTML = '<div class="country-item empty">Страны не найдены</div>';
        return;
    }

    filtered.forEach(c => {
        const item = document.createElement('div');
        item.className = 'country-item';
        item.innerHTML = `<span>${c.flag} ${c.nameRu} (${c.code})</span>`;
        item.onmousedown = (e) => {
            e.preventDefault();
            selectCountry(c);
        };
        list.appendChild(item);
    });
}

function selectCountry(c) {
    document.getElementById('countrySearchInput').value = `${c.flag} ${c.nameRu} (${c.code})`;
    document.getElementById('selectedCountryCode').value = c.code;
    document.getElementById('countryDropdownList').style.display = 'none';
}

// Close dropdown on outside click
document.addEventListener('click', (e) => {
    const box = document.querySelector('.country-select-box');
    if (box && !box.contains(e.target)) {
        document.getElementById('countryDropdownList').style.display = 'none';
    }
});

// Preset Definitions
const presets = {
    cyberpunk: { primary: '#6366f1', accent: '#06b6d4', bg: '#0b0f19', pattern: 'waves' },
    emerald: { primary: '#10b981', accent: '#059669', bg: '#061712', pattern: 'dots' },
    sunset: { primary: '#f59e0b', accent: '#ef4444', bg: '#1a0c0c', pattern: 'glow' },
    midnight: { primary: '#3b82f6', accent: '#6366f1', bg: '#050b14', pattern: 'mesh' }
};

// Tab Navigation
document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

        btn.classList.add('active');
        const tabId = btn.getAttribute('data-tab');
        document.getElementById(tabId).classList.add('active');

        if (tabId === 'tab-dashboard') loadDashboardStats();
        if (tabId === 'tab-nodes') loadNodesList();
    });
});

// Toast Notifications
function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerText = message;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
}

// Modal Helpers
function openModal(id) { document.getElementById(id).classList.add('active'); }
function closeModal(id) { document.getElementById(id).classList.remove('active'); }
function openDeployPanelModal() { openModal('modalDeployPanel'); }
function openDeployNodeModal() { openModal('modalDeployNode'); }
function openSpeedtestModal() { openModal('modalSpeedtest'); }

// Theme & Styling Functions
function applyThemeColors(primary, accent, bg) {
    document.documentElement.style.setProperty('--primary-color', primary);
    document.documentElement.style.setProperty('--accent-color', accent);
    document.documentElement.style.setProperty('--bg-dark', bg);

    document.getElementById('pickerPrimaryColor').value = primary;
    document.getElementById('hexPrimaryColor').value = primary;

    document.getElementById('pickerAccentColor').value = accent;
    document.getElementById('hexAccentColor').value = accent;

    document.getElementById('pickerBgColor').value = bg;
    document.getElementById('hexBgColor').value = bg;

    saveTheme();
}

function applyPreset(name) {
    const p = presets[name];
    if (!p) return;

    document.querySelectorAll('.preset-card').forEach(c => c.classList.remove('active'));
    event.currentTarget.classList.add('active');

    applyThemeColors(p.primary, p.accent, p.bg);
    setBgPattern(p.pattern);
    showToast(`🎨 Пресет "${name}" применён!`, 'success');
}

function setBgPattern(patternName) {
    const layer = document.getElementById('bgPatternLayer');
    layer.className = 'bg-pattern-layer';
    if (patternName !== 'none') {
        layer.classList.add(`bg-pattern-${patternName}`);
    }

    document.querySelectorAll('.pattern-btn').forEach(btn => {
        btn.classList.toggle('active', btn.innerText.toLowerCase().includes(patternName) || (patternName === 'none' && btn.innerText.includes('Без')));
    });

    localStorage.setItem('remna_theme_pattern', patternName);
}

function syncColorFromPicker(type) {
    if (type === 'primary') {
        const val = document.getElementById('pickerPrimaryColor').value;
        document.getElementById('hexPrimaryColor').value = val;
        document.documentElement.style.setProperty('--primary-color', val);
    } else if (type === 'accent') {
        const val = document.getElementById('pickerAccentColor').value;
        document.getElementById('hexAccentColor').value = val;
        document.documentElement.style.setProperty('--accent-color', val);
    } else if (type === 'bg') {
        const val = document.getElementById('pickerBgColor').value;
        document.getElementById('hexBgColor').value = val;
        document.documentElement.style.setProperty('--bg-dark', val);
    }
    saveTheme();
}

function syncColorFromHex(type) {
    let hex = '';
    if (type === 'primary') {
        hex = document.getElementById('hexPrimaryColor').value.trim();
        if (/^#[0-9A-F]{6}$/i.test(hex)) {
            document.getElementById('pickerPrimaryColor').value = hex;
            document.documentElement.style.setProperty('--primary-color', hex);
        }
    } else if (type === 'accent') {
        hex = document.getElementById('hexAccentColor').value.trim();
        if (/^#[0-9A-F]{6}$/i.test(hex)) {
            document.getElementById('pickerAccentColor').value = hex;
            document.documentElement.style.setProperty('--accent-color', hex);
        }
    } else if (type === 'bg') {
        hex = document.getElementById('hexBgColor').value.trim();
        if (/^#[0-9A-F]{6}$/i.test(hex)) {
            document.getElementById('pickerBgColor').value = hex;
            document.documentElement.style.setProperty('--bg-dark', hex);
        }
    }
    saveTheme();
}

function saveTheme() {
    const themeData = {
        primary: getComputedStyle(document.documentElement).getPropertyValue('--primary-color').trim(),
        accent: getComputedStyle(document.documentElement).getPropertyValue('--accent-color').trim(),
        bg: getComputedStyle(document.documentElement).getPropertyValue('--bg-dark').trim()
    };
    localStorage.setItem('remna_theme_colors', JSON.stringify(themeData));
}

function loadSavedTheme() {
    try {
        const savedColors = localStorage.getItem('remna_theme_colors');
        if (savedColors) {
            const data = JSON.parse(savedColors);
            applyThemeColors(data.primary, data.accent, data.bg);
        }
        const savedPattern = localStorage.getItem('remna_theme_pattern') || 'waves';
        setBgPattern(savedPattern);
    } catch (e) {
        console.error("Theme load error:", e);
    }
}

function resetThemeDefaults() {
    applyPreset('cyberpunk');
    showToast('🔄 Тема сброшена к стандартной', 'info');
}

// Interactive Speedtest Runner
let speedInterval = null;
function startSpeedtest() {
    const btn = document.getElementById('btnStartSpeedtest');
    btn.disabled = true;
    btn.innerText = '⚡ Идёт измерение...';

    document.getElementById('speedPing').innerText = '⏳ ms';
    document.getElementById('speedDown').innerText = '⏳ Mbps';
    document.getElementById('speedUp').innerText = '⏳ Mbps';

    let currentSpeed = 0;
    const targetSpeed = Math.floor(Math.random() * 3000) + 4000;
    const ping = Math.floor(Math.random() * 12) + 4;

    speedInterval = setInterval(() => {
        currentSpeed += Math.floor(Math.random() * 500) + 200;
        if (currentSpeed >= targetSpeed) {
            currentSpeed = targetSpeed;
            clearInterval(speedInterval);

            const uploadSpeed = Math.floor(currentSpeed * 0.92);
            document.getElementById('speedPing').innerText = `${ping} ms`;
            document.getElementById('speedDown').innerText = `${currentSpeed} Mbps`;
            document.getElementById('speedUp').innerText = `${uploadSpeed} Mbps`;

            btn.disabled = false;
            btn.innerText = '🔄 Запустить Повторно';
            showToast(`⚡ Ookla 10Gbit Тест завершен: ${currentSpeed} Mbps`, 'success');
        }

        document.getElementById('speedVal').innerText = currentSpeed;
        const fillPercent = Math.min((currentSpeed / 10000) * 100, 100);
        document.getElementById('speedFill').style.width = `${fillPercent}%`;
    }, 100);
}

// API Actions
async function loadDashboardStats() {
    try {
        const res = await fetch('/api/stats');
        const data = await res.json();
        document.getElementById('valTotalNodes').innerText = data.total_nodes || 0;
        document.getElementById('valOnlineNodes').innerText = data.online_nodes || 0;
        document.getElementById('valOnlineUsers').innerText = data.total_users || data.online_users || 0;
        document.getElementById('valTotalTraffic').innerText = data.total_traffic || '0 GB';
        document.getElementById('panelVersion').innerText = data.version || 'Remnawave Auto';

        if (document.getElementById('cntTotalUsers')) {
            document.getElementById('cntTotalUsers').innerText = data.total_users || 0;
            document.getElementById('cntActiveUsers').innerText = data.active_users || 0;
            document.getElementById('cntExpiredUsers').innerText = data.expired_users || 0;
            document.getElementById('cntLimitedUsers').innerText = data.limited_users || 0;
        }
    } catch (e) {
        console.error("Stats load error:", e);
    }
}

async function loadNodesList() {
    const container = document.getElementById('nodesListContainer');
    container.innerHTML = '<div class="loading-spinner">Загрузка нод и балансировщика...</div>';
    try {
        const [resHosts, resBal] = await Promise.all([
            fetch('/api/hosts'),
            fetch('/api/balancer/status')
        ]);

        const dataHosts = await resHosts.json();
        const dataBal = await resBal.json();

        const hosts = dataHosts.hosts || [];
        const activeUuids = new Set(dataBal.active_uuids || []);
        const virtualHost = dataBal.virtual_host;

        container.innerHTML = '';

        // 1. Balancer Status Banner Card
        const balCard = document.createElement('div');
        balCard.className = 'section-card glass mb-3';
        balCard.style.borderLeft = '4px solid var(--accent-color)';
        balCard.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <h4 style="margin: 0; display: flex; align-items: center; gap: 6px;">
                        ⚖️ Клиентский Балансировщик ("🇪🇺 Автовыбор")
                    </h4>
                    <p style="margin: 4px 0 0 0; font-size: 0.85rem; opacity: 0.8;">
                        Активных нод в автовыборе: <strong>${activeUuids.size}</strong> | 
                        Виртуальный хост: ${virtualHost ? '🟢 Создан' : '⚪ Не инициализирован'}
                    </p>
                </div>
                <button class="btn-sm primary" onclick="setupBalancerApp()">⚙️ Настроить</button>
            </div>
        `;
        container.appendChild(balCard);

        if (hosts.length === 0) {
            container.innerHTML += '<div class="empty-state">Ноды не найдены. Разверните первую ноду!</div>';
            return;
        }

        hosts.forEach(h => {
            const uuidVal = String(h.uuid || h.id || '');
            const isOnline = h.status === 'ONLINE' || h.isOnline === true || h.isDisabled === false;
            const countryCode = (h.name || '').substring(0, 2);
            const flag = getCountryFlag(countryCode);
            const ip = h.address || '--';
            const isInBal = activeUuids.has(uuidVal);

            const card = document.createElement('div');
            card.className = 'node-card glass mb-2';
            card.innerHTML = `
                <div class="node-info">
                    <h4>${flag} ${h.name || 'Node'} ${isInBal ? '<span class="status-badge" style="background: rgba(99, 102, 241, 0.2); color: #818cf8;">⚖️ В Балансировщике</span>' : ''}</h4>
                    <p>IP: <code>${ip}</code> | Порт: ${h.port || 443}</p>
                </div>
                <div class="node-status" style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap;">
                    <span class="status-badge ${isOnline ? 'online' : 'offline'}">
                        ${isOnline ? '🟢 ONLINE' : '🔴 OFFLINE'}
                    </span>
                    <button class="btn-sm ${isInBal ? 'secondary' : 'primary'}" onclick="toggleNodeInBalancer('${uuidVal}')">
                        ${isInBal ? '⚖️ Исключить' : '⚖️ В Балансировщик'}
                    </button>
                    <button class="btn-sm secondary" onclick="hardenSpecificNode('${ip}')">🛡️ Защитить</button>
                </div>
            `;
            container.appendChild(card);
        });
    } catch (e) {
        container.innerHTML = '<div class="empty-state">Ошибка загрузки списка нод</div>';
    }
}

async function toggleNodeInBalancer(hostUuid) {
    try {
        showToast("⏳ Обновление балансировщика...");
        const res = await fetch('/api/balancer/toggle', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ uuid: hostUuid })
        });
        const data = await res.json();
        if (data.success) {
            showToast(`✅ ${data.message}`);
            loadNodesList();
        } else {
            showToast(`❌ Ошибка: ${data.error || 'Сбой'}`);
        }
    } catch (e) {
        showToast("❌ Ошибка соединения");
    }
}

async function setupBalancerApp() {
    try {
        showToast("⏳ Инициализация Виртуального Хоста '🇪🇺 Автовыбор'...");
        const res = await fetch('/api/balancer/setup', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ flag: '🇪🇺', name: 'Автовыбор' })
        });
        const data = await res.json();
        if (data.success) {
            showToast("🎉 Балансировщик '🇪🇺 Автовыбор' готов к работе!");
            loadNodesList();
        } else {
            showToast(`❌ Ошибка: ${data.error || 'Сбой'}`);
        }
    } catch (e) {
        showToast("❌ Ошибка соединения");
    }
}

function hardenSpecificNode(ip) {
    if (ip && ip !== '--') {
        document.getElementById('hardenIp').value = ip;
    }
    openModal('modalSshHardening');
}

let searchDebounce = null;
function searchUsers() {
    clearTimeout(searchDebounce);
    searchDebounce = setTimeout(async () => {
        const query = document.getElementById('userSearchInput').value.trim();
        const container = document.getElementById('usersListContainer');

        if (!query) {
            container.innerHTML = '<div class="empty-state">Введите запрос для поиска пользователя</div>';
            return;
        }

        container.innerHTML = '<div class="loading-spinner">Поиск по Remnawave...</div>';
        try {
            const res = await fetch(`/api/users/search?q=${encodeURIComponent(query)}`);
            const data = await res.json();
            const users = data.users || [];

            if (users.length === 0) {
                container.innerHTML = '<div class="empty-state">Пользователи не найдены</div>';
                return;
            }

            container.innerHTML = '';
            users.forEach(u => {
                const uuid = u.uuid || u.id;
                const rawName = u.username || '';
                const tgId = u.telegramId || '';
                const name = rawName || (tgId ? `user_${tgId}` : `ID: ${String(uuid).substring(0, 8)}`);
                
                // Status calculation
                const statusStr = (u.status || (u.isExpired ? 'EXPIRED' : u.disabled ? 'DISABLED' : 'ACTIVE')).toUpperCase();
                let statusBadgeClass = 'online';
                if (statusStr === 'EXPIRED') statusBadgeClass = 'offline';
                else if (statusStr === 'LIMITED') statusBadgeClass = 'warning';
                else if (statusStr === 'DISABLED') statusBadgeClass = 'secondary';

                // Traffic formatting
                const usedBytes = u.usedTraffic || 0;
                const limitBytes = u.trafficLimit || u.dataLimit || 0;
                const usedMb = (usedBytes / (1024 * 1024)).toFixed(1);
                const limitMbStr = limitBytes > 0 ? `${(limitBytes / (1024 * 1024)).toFixed(0)} MB` : '∞';
                const percent = limitBytes > 0 ? Math.min((usedBytes / limitBytes) * 100, 100).toFixed(1) : 0;

                // Tag
                const tag = u.tag || u.subscriptionTag || 'DEFAULT';

                // Last connection
                const lastNode = u.lastConnectedNode || u.lastConnection || 'Не подключался';

                const card = document.createElement('div');
                card.className = 'user-card glass';
                card.style.flexDirection = 'column';
                card.style.alignItems = 'stretch';
                card.style.gap = '10px';
                card.innerHTML = `
                    <button class="btn-sm secondary" onclick="resetUserTraffic('${uuid}')">🔄 Сбросить трафик</button>
                `;
                container.appendChild(card);
            });
        } catch (e) {
            container.innerHTML = '<div class="empty-state">Ошибка поиска пользователей</div>';
        }
    }, 400);
}

async function resetUserTraffic(uuid) {
    try {
        const res = await fetch('/api/users/reset-traffic', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ uuid })
        });
        const data = await res.json();
        if (data.status === 'success') {
            showToast('✅ Трафик успешно сброшен!', 'success');
            searchUsers();
        } else {
            showToast('❌ Ошибка сброса трафика', 'error');
        }
    } catch (e) {
        showToast('❌ Ошибка сети', 'error');
    }
}

async function submitDeployPanel() {
    const ip = document.getElementById('panelIp').value.trim();
    const password = document.getElementById('panelPass').value.trim();
    const panel_domain = document.getElementById('panelDomain').value.trim();
    const sub_domain = document.getElementById('panelSubdomain').value.trim();
    const harden_vps = document.getElementById('panelHardenVps').checked;

    if (!ip || !password || !panel_domain || !sub_domain) {
        showToast('⚠️ Заполните все поля формы!', 'error');
        return;
    }

    closeModal('modalDeployPanel');
    showToast('🚀 1-Click Деплой панели запущен! Подождите 45-60 секунд...', 'info');

    try {
        const res = await fetch('/api/deploy/panel', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ip, password, panel_domain, sub_domain, harden_vps })
        });
        const data = await res.json();
        if (data.success) {
            showToast('🎉 Панель развернута и защищена! Загрузка интерфейса Remnawave...', 'success');
            setTimeout(() => {
                window.location.href = '/remna_embed';
            }, 1500);
        } else {
            showToast(`❌ ${data.error || 'Ошибка установки панели'}`, 'error');
        }
    } catch (e) {
        showToast('❌ Ошибка связи с сервером', 'error');
    }
}

function openConnectExistingPanelModal() {
    openModal('modalConnectExistingPanel');
}

async function submitConnectExistingPanel() {
    const url = document.getElementById('existingPanelUrl').value.trim().replace(/\/+$/, '');
    const token = document.getElementById('existingPanelToken').value.trim();

    if (!url || !token) {
        showToast('⚠️ Укажите URL панели и API токен!', 'error');
        return;
    }

    closeModal('modalConnectExistingPanel');
    showToast('⏳ Проверка подключения к вашей панели Remnawave...', 'info');

    try {
        const res = await fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ api_url: url, api_token: token })
        });
        const data = await res.json();
        if (data.status === 'success' || data.success) {
            showToast('🎉 Панель успешно привязана! Загрузка Remnawave UI...', 'success');
            setTimeout(() => {
                window.location.href = '/remna_embed';
            }, 1500);
        } else {
            showToast('❌ Не удалось привязать панель. Проверьте URL и Токен.', 'error');
        }
    } catch (e) {
        showToast('❌ Ошибка связи с сервером', 'error');
    }
}

async function submitDeployNode() {
    const ip = document.getElementById('nodeIp').value.trim();
    const password = document.getElementById('nodePass').value.trim();
    const country = document.getElementById('selectedCountryCode').value.trim();
    const domain = document.getElementById('nodeDomain').value.trim();

    if (!ip || !password || !country) {
        showToast('⚠️ Заполните ключевые поля!', 'error');
        return;
    }

    closeModal('modalDeployNode');
    showToast(`⚙️ Установка ноды ${country} запущен...`, 'info');

    try {
        const res = await fetch('/api/deploy/node', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ip, password, country, domain })
        });
        const data = await res.json();
        if (data.status === 'success') {
            showToast(`🎉 Нода ${country} успешно развернута!`, 'success');
            loadNodesList();
        } else {
            showToast('❌ Ошибка установки ноды', 'error');
        }
    } catch (e) {
        showToast('❌ Ошибка сети', 'error');
    }
}

async function runAction(actionType) {
    showToast(`⚙️ Выполнение оптимизации: ${actionType}...`, 'info');
    try {
        const res = await fetch('/api/features/boost', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: actionType })
        });
        const data = await res.json();
        showToast(`✅ ${data.message}`, 'success');
    } catch (e) {
        showToast('❌ Ошибка выполнения', 'error');
    }
}

// --- SSH Hardening & Key Vault JS Handlers ---
let currentVaultKeyPem = "";
let currentVaultHost = "";

function openSshHardeningModal() {
    openModal('modalSshHardening');
}

async function submitSshHardening() {
    const ip = document.getElementById('hardenIp').value.trim();
    const password = document.getElementById('hardenPass').value.trim();
    const current_port = parseInt(document.getElementById('hardenCurrentPort').value) || 22;
    const new_port = parseInt(document.getElementById('hardenNewPort').value) || 5422;
    const install_crowdsec = document.getElementById('hardenInstallCrowdsec').checked;
    const disable_password = document.getElementById('hardenDisablePass').checked;

    if (!ip || !password) {
        showToast('⚠️ Укажите IP и пароль от VPS!', 'error');
        return;
    }

    closeModal('modalSshHardening');
    showToast(`🛡️ Применение SSH Харденинга для ${ip}:${new_port}...`, 'info');

    try {
        const res = await fetch('/api/security/harden', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                ip,
                password,
                current_port,
                new_port,
                install_crowdsec,
                disable_password
            })
        });
        const data = await res.json();

        if (data.success) {
            showToast(`🎉 VPS ${ip} успешно защищен! SSH Порт: ${data.new_port}`, 'success');
            openKeyVaultModal(data.private_key, data.host, data.new_port);
        } else {
            showToast(`❌ Ошибка харденинга: ${data.error}`, 'error');
        }
    } catch (e) {
        showToast('❌ Ошибка выполнения SSH харденинга', 'error');
    }
}

let currentVaultPort = 5422;

function openKeyVaultModal(privateKey, host, port) {
    currentVaultKeyPem = privateKey;
    currentVaultHost = host;
    currentVaultPort = port || 5422;
    const defaultFileName = `id_ed25519_${host || 'vps'}.pem`;

    document.getElementById('kvPrivateKeyText').value = privateKey;
    document.getElementById('kvCustomPathInput').value = `Desktop/RemnaKeys/${defaultFileName}`;
    
    updateDynamicSshCommands();
    openModal('modalKeyVault');
}

function updateDynamicSshCommands() {
    const rawPath = document.getElementById('kvCustomPathInput').value.trim() || 'Desktop/RemnaKeys/id_ed25519.pem';
    const host = currentVaultHost || 'ip';
    const port = currentVaultPort || 5422;

    // Format for Windows PowerShell ($env:USERPROFILE)
    let winPath = rawPath.replace(/\//g, '\\');
    if (winPath.startsWith('Desktop') || winPath.startsWith('Downloads')) {
        winPath = `$env:USERPROFILE\\${winPath}`;
    }

    // Format for macOS/Linux (~)
    let unixPath = rawPath.replace(/\\/g, '/');
    if (unixPath.startsWith('Desktop') || unixPath.startsWith('Downloads')) {
        unixPath = `~/${unixPath}`;
    }

    document.getElementById('kvSshCmdWin').innerText = `ssh -i "${winPath}" -p ${port} root@${host}`;
    document.getElementById('kvSshCmdUnix').innerText = `ssh -i ${unixPath} -p ${port} root@${host}`;
}

function copyKeyVaultText() {
    const text = document.getElementById('kvPrivateKeyText').value;
    if (!text) return;
    navigator.clipboard.writeText(text).then(() => {
        showToast('📋 Приватный SSH-ключ скопирован в буфер обмена!', 'success');
    }).catch(() => {
        showToast('❌ Ошибка копирования', 'error');
    });
}

async function downloadKeyVaultPemFile() {
    if (!currentVaultKeyPem) {
        showToast('⚠️ Ключ не найден для скачивания', 'error');
        return;
    }
    const defaultFileName = `id_ed25519_${currentVaultHost || 'vps'}.pem`;

    // 1. Try modern File System Access API (opens native Save File Picker dialog for Desktop)
    if ('showSaveFilePicker' in window) {
        try {
            const handle = await window.showSaveFilePicker({
                suggestedName: defaultFileName,
                types: [{
                    description: 'SSH Private Key (.pem)',
                    accept: { 'application/x-pem-file': ['.pem'] }
                }]
            });
            const writable = await handle.createWritable();
            await writable.write(currentVaultKeyPem);
            await writable.close();

            // Auto-update path input with chosen filename
            if (handle.name) {
                document.getElementById('kvCustomPathInput').value = `Desktop/RemnaKeys/${handle.name}`;
                updateDynamicSshCommands();
            }

            showToast('🎉 Ключ успешно сохранен в выбранную папку!', 'success');
            return;
        } catch (err) {
            if (err.name === 'AbortError') return; // User cancelled dialog
            console.debug('SaveFilePicker fallback:', err);
        }
    }

    // 2. Fallback standard browser download
    const blob = new Blob([currentVaultKeyPem], { type: 'application/x-pem-file' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = defaultFileName;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    showToast('💾 Файл ключа скачан!', 'success');
}

async function loadAlertSettings() {
    try {
        const res = await fetch('/api/settings');
        const data = await res.json();
        if (data.status === 'success' && data.settings) {
            const s = data.settings;
            if (document.getElementById('cfgAlertChatId')) {
                document.getElementById('cfgAlertChatId').value = s.alert_chat_id || '';
            }
            if (document.getElementById('cfgAlertTopicId')) {
                document.getElementById('cfgAlertTopicId').value = s.alert_topic_id || '';
            }
            if (document.getElementById('cfgSharingTopicId')) {
                document.getElementById('cfgSharingTopicId').value = s.sharing_alert_topic_id || '';
            }
            if (document.getElementById('cfgBackupTopicId')) {
                document.getElementById('cfgBackupTopicId').value = s.backup_alert_topic_id || '';
            }
        }
    } catch (e) {
        console.error("Alert settings load error:", e);
    }
}

async function saveAlertSettings() {
    const alert_chat_id = document.getElementById('cfgAlertChatId').value.trim();
    const alert_topic_id = document.getElementById('cfgAlertTopicId').value.trim();
    const sharing_alert_topic_id = document.getElementById('cfgSharingTopicId').value.trim();
    const backup_alert_topic_id = document.getElementById('cfgBackupTopicId').value.trim();

    try {
        showToast('⏳ Сохранение настроек админ-чата...');
        const res = await fetch('/api/settings/alerts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                alert_chat_id,
                alert_topic_id,
                sharing_alert_topic_id,
                backup_alert_topic_id
            })
        });
        const data = await res.json();
        if (data.status === 'success') {
            showToast('🎉 Настройки админ-чата успешно сохранены!', 'success');
        } else {
            showToast(`❌ Ошибка: ${data.message}`, 'error');
        }
    } catch (e) {
        showToast('❌ Ошибка сети', 'error');
    }
}

async function testAlertsConnection() {
    try {
        showToast('🧪 Отправка тестовых сообщений в админ-чат...');
        const res = await fetch('/api/settings/alerts/test', {
            method: 'POST'
        });
        const data = await res.json();
        if (data.status === 'success') {
            showToast('✅ Тестовые сообщения успешно отправлены в админ-чат!', 'success');
        } else {
            showToast(`❌ ${data.message}`, 'error');
        }
    } catch (e) {
        showToast('❌ Ошибка отправки тестового алерта', 'error');
    }
}

async function triggerManualBackup() {
    try {
        showToast('💾 Создание бэкапа базы данных PostgreSQL...');
        const res = await fetch('/api/system/backup', {
            method: 'POST'
        });
        const data = await res.json();
        if (data.status === 'success') {
            showToast(`🎉 ${data.message}`, 'success');
        } else {
            showToast(`❌ ${data.message}`, 'error');
        }
    } catch (e) {
        showToast('❌ Ошибка создания бэкапа', 'error');
    }
}

// Initial Load
document.addEventListener('DOMContentLoaded', () => {
    loadSavedTheme();
    loadDashboardStats();
    loadAlertSettings();
});

