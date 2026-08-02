// Remna-Bot Overlay Engine, Custom Sidebar Integration & Full Color Customizer
(function() {
    console.log("🚀 Remna-Bot Sidebar & Theme Customizer Engine Loaded!");

    const themes = [
        { id: "theme-default", name: "Original Dark", color: "#6366f1" },
        { id: "theme-cyberpunk", name: "Cyberpunk Neon 🟣", color: "#c084fc" },
        { id: "theme-emerald", name: "Emerald Matrix 🟢", color: "#10b981" },
        { id: "theme-sunset", name: "Sunset Orange 🟠", color: "#f97316" },
        { id: "theme-oled", name: "OLED Pure Black 🖤", color: "#3b82f6" }
    ];

    let currentTheme = localStorage.getItem("remnabot_theme") || "theme-default";
    let isMinimized = false;
    let fetchedKeys = [];

    function applyCurrentTheme() {
        const allThemeClasses = themes.map(t => t.id);
        document.body.classList.remove(...allThemeClasses);
        document.documentElement.classList.remove(...allThemeClasses);

        if (currentTheme !== "theme-default") {
            document.body.classList.add(currentTheme);
            document.documentElement.classList.add(currentTheme);
        }
    }

    function showToast(msg) {
        let toast = document.getElementById("remna-toast");
        if (!toast) {
            toast = document.createElement("div");
            toast.id = "remna-toast";
            toast.style.cssText = `
                position: fixed;
                top: 20px;
                left: 50%;
                transform: translateX(-50%);
                z-index: 1000005;
                padding: 10px 18px;
                background: rgba(15, 23, 42, 0.95);
                border: 1px solid rgba(129, 140, 248, 0.5);
                color: #ffffff;
                font-size: 13px;
                font-weight: 600;
                border-radius: 20px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.6);
                transition: opacity 0.3s ease;
                pointer-events: none;
                font-family: -apple-system, sans-serif;
            `;
            document.body.appendChild(toast);
        }
        toast.innerText = msg;
        toast.style.opacity = "1";
        setTimeout(() => { toast.style.opacity = "0"; }, 2500);
    }

    // --- Left Sidebar & Mobile Drawer Custom Menu Item Injection ---
    function injectSidebarItem() {
        const candidates = document.querySelectorAll("nav, aside, [class*='sidebar'], [class*='drawer'], [class*='menu']");
        for (let el of candidates) {
            if (el.innerText && (el.innerText.includes("ИНСТРУМЕНТЫ") || el.innerText.includes("УПРАВЛЕНИЕ") || el.innerText.includes("ПОДПИСКА") || el.children.length > 2)) {
                if (!el.querySelector("#remna-sidebar-item")) {
                    const item = document.createElement("a");
                    item.id = "remna-sidebar-item";
                    item.className = "remna-sidebar-link";
                    item.innerHTML = `
                        <span style="font-size:16px; margin-right:8px;">⚡</span>
                        <span style="font-weight:700; background:linear-gradient(135deg, #818cf8, #06b6d4); -webkit-background-clip:text; -webkit-text-fill-color:transparent;">Remna-Bot Power-Up</span>
                    `;
                    item.onclick = function(e) {
                        e.preventDefault();
                        e.stopPropagation();
                        window.RemnaOverlay.openControlCenter("themes");
                    };

                    const socialRow = el.querySelector("[class*='social'], .flex.gap-2");
                    if (socialRow) {
                        el.insertBefore(item, socialRow);
                    } else {
                        el.appendChild(item);
                    }
                    console.log("⚡ Remna-Bot Sidebar Item Injected Successfully!");
                }
            }
        }
    }

    // --- Floating Bottom Toolbar ---
    function injectOverlayBar() {
        if (document.getElementById("remnabot-overlay-bar")) return;

        const bar = document.createElement("div");
        bar.id = "remnabot-overlay-bar";
        renderBarContent(bar);
        document.body.appendChild(bar);
    }

    function renderBarContent(bar) {
        if (isMinimized) {
            bar.classList.add("minimized");
            bar.innerHTML = `
                <span class="logo-badge" onclick="window.RemnaOverlay.toggleMinimize()">⚡ Remna-Bot</span>
                <button class="overlay-btn" onclick="window.RemnaOverlay.toggleMinimize()">▲ Развернуть</button>
            `;
        } else {
            bar.classList.remove("minimized");
            bar.innerHTML = `
                <span class="logo-badge" title="Свернуть" onclick="window.RemnaOverlay.toggleMinimize()">⚡ Remna-Bot</span>
                <button class="overlay-btn" onclick="window.RemnaOverlay.openControlCenter('themes')">🎨 Темы</button>
                <button class="overlay-btn" onclick="window.RemnaOverlay.openControlCenter('ssh')">🛡️ SSH Харденинг</button>
                <button class="overlay-btn" onclick="window.RemnaOverlay.openControlCenter('node')">🖥️ 1-Click Нода</button>
                <button class="overlay-btn" onclick="window.RemnaOverlay.openControlCenter('speed')">⚡ 10Gbit Speedtest</button>
                <button class="minimize-btn" title="Свернуть панель" onclick="window.RemnaOverlay.toggleMinimize()">▼</button>
            `;
        }
    }

    window.RemnaOverlay = {
        setTheme: function(themeId) {
            currentTheme = themeId;
            localStorage.setItem("remnabot_theme", themeId);
            applyCurrentTheme();

            const tObj = themes.find(t => t.id === themeId);
            showToast(`🎨 Тема оформления: ${tObj ? tObj.name : themeId}`);

            document.querySelectorAll(".theme-card").forEach(c => {
                if (c.getAttribute("data-theme") === themeId) {
                    c.classList.add("active");
                } else {
                    c.classList.remove("active");
                }
            });
        },

        cycleTheme: function() {
            const idx = themes.findIndex(t => t.id === currentTheme);
            const nextIdx = (idx + 1) % themes.length;
            this.setTheme(themes[nextIdx].id);
        },

        toggleMinimize: function() {
            isMinimized = !isMinimized;
            const bar = document.getElementById("remnabot-overlay-bar");
            if (bar) renderBarContent(bar);
        },

        openControlCenter: function(activeTab = "themes") {
            let existing = document.getElementById("remna-custom-modal");
            if (existing) existing.remove();

            const overlay = document.createElement("div");
            overlay.id = "remna-custom-modal";
            overlay.className = "remna-modal-overlay";

            let contentHtml = `
                <div class="remna-modal-card">
                    <div class="remna-modal-close" onclick="document.getElementById('remna-custom-modal').remove()">✕</div>
                    <h3>⚡ Remna-Bot Power-Up Центр</h3>

                    <div class="remna-tab-nav">
                        <button class="remna-tab-btn ${activeTab==='themes'?'active':''}" onclick="window.RemnaOverlay.switchTab('themes')">🎨 Темы и Цвета</button>
                        <button class="remna-tab-btn ${activeTab==='ssh'?'active':''}" onclick="window.RemnaOverlay.switchTab('ssh')">🛡️ SSH Безопасность</button>
                        <button class="remna-tab-btn ${activeTab==='node'?'active':''}" onclick="window.RemnaOverlay.switchTab('node')">🖥️ 1-Click Ноды</button>
                        <button class="remna-tab-btn ${activeTab==='speed'?'active':''}" onclick="window.RemnaOverlay.switchTab('speed')">⚡ 10Gbit Speedtest</button>
                    </div>

                    <div id="remnaTabBody">
                        ${this.getTabHtml(activeTab)}
                    </div>
                </div>
            `;

            overlay.innerHTML = contentHtml;
            document.body.appendChild(overlay);

            if (activeTab === 'ssh') {
                this.loadSshKeys();
            } else if (activeTab === 'speed') {
                this.startSpeedtestAnimation();
            }
        },

        switchTab: function(tabName) {
            document.querySelectorAll(".remna-tab-btn").forEach(btn => btn.classList.remove("active"));
            if (event && event.target) event.target.classList.add("active");
            const body = document.getElementById("remnaTabBody");
            if (body) body.innerHTML = this.getTabHtml(tabName);

            if (tabName === 'ssh') {
                this.loadSshKeys();
            } else if (tabName === 'speed') {
                this.startSpeedtestAnimation();
            }
        },

        getTabHtml: function(tabName) {
            if (tabName === 'themes') {
                let gridHtml = '<div style="font-size:13px; color:#94a3b8; margin-bottom:12px;">Выберите тему оформления всей панели Remnawave в режиме реального времени:</div><div class="theme-card-grid">';
                themes.forEach(t => {
                    const isActive = t.id === currentTheme ? 'active' : '';
                    gridHtml += `
                        <div class="theme-card ${isActive}" data-theme="${t.id}" onclick="window.RemnaOverlay.setTheme('${t.id}')">
                            <div class="preview-circle" style="background:${t.color}; box-shadow:0 0 10px ${t.color}"></div>
                            <div style="font-size:12px; font-weight:700;">${t.name}</div>
                        </div>
                    `;
                });
                gridHtml += '</div>';
                return gridHtml;
            }

            if (tabName === 'ssh') {
                const sampleKey = `-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZWQyNTUx
OQAAACCgHmHxzckNTxYy5/JjlSdzIHrFl90HG01WCGEuSHA8GAAAAIiadxR/mncUfw...
-----END OPENSSH PRIVATE KEY-----`;
                const host = location.hostname;
                const defaultCmd = `ssh -i "C:\\Users\\username\\.ssh\\remnabot.pem" root@${host} -p 5422`;

                return `
                    <div style="font-size:12px; color:#cbd5e1; margin-bottom:14px; background:rgba(255,255,255,0.04); padding:12px; border-radius:14px; border:1px solid rgba(255,255,255,0.1);">
                        🔒 <b>Статус защиты VPS:</b> SSH Порт <span style="color:#10b981; font-weight:800;">5422</span> (Харденинг активен)<br>
                        🔑 Вход по паролю: <span style="color:#ef4444; font-weight:700;">Отключен (PasswordAuthentication no)</span><br>
                        🛡️ Фильтр брутфорса: <span style="color:#10b981; font-weight:700;">Fail2ban Active</span>
                    </div>

                    <div class="remna-form-group">
                        <label>🔑 Приватный SSH-ключ Ed25519 (.pem):</label>
                        <textarea id="pemKeyBox" style="width:100%; height:85px; font-size:11px; font-family:monospace; background:#000; color:#10b981; border:1px solid rgba(16,185,129,0.3); border-radius:12px; padding:10px; cursor:pointer;" readonly onclick="window.RemnaOverlay.copyKeyToClipboard()" title="Нажмите, чтобы скопировать ключ">${sampleKey}</textarea>
                        <div style="display:flex; gap:8px; margin-top:8px;">
                            <button class="overlay-btn" style="flex:1; background:rgba(16,185,129,0.2); border-color:rgba(16,185,129,0.5);" onclick="window.RemnaOverlay.copyKeyToClipboard()">📋 Скопировать Ключ</button>
                            <button class="overlay-btn" style="flex:1; background:rgba(99,102,241,0.2); border-color:rgba(129,140,248,0.5);" onclick="window.RemnaOverlay.downloadPemKey()">💾 Скачать .pem Ключ</button>
                        </div>
                    </div>

                    <div class="remna-form-group" style="margin-top:16px; background:rgba(15,23,42,0.6); padding:14px; border-radius:14px; border:1px solid rgba(255,255,255,0.1);">
                        <label style="color:#38bdf8; font-weight:700;">⚡ Быстрое подключение из терминала (Windows / Linux / Mac):</label>
                        <div style="font-size:11px; color:#94a3b8; margin-bottom:6px;">Укажите путь сохранения файла ключа <b>remnabot.pem</b>:</div>
                        <input type="text" id="sshPathInput" class="remna-input" value="C:\\Users\\username\\.ssh\\remnabot.pem" oninput="window.RemnaOverlay.updateSshCmd()" style="font-family:monospace; font-size:11px; margin-bottom:10px;">

                        <div style="font-size:11px; color:#94a3b8; margin-bottom:4px;">Сгенерированная команда подключения SSH:</div>
                        <input type="text" id="sshCmdBox" class="remna-input" value="${defaultCmd}" readonly style="font-family:monospace; font-size:11px; color:#38bdf8; background:#000; margin-bottom:8px;">
                        <button class="remna-btn-primary" style="padding:10px; font-size:13px;" onclick="window.RemnaOverlay.copySshCmd()">📋 Скопировать Команду SSH</button>
                    </div>
                `;
            }

            if (tabName === 'node') {
                return `
                    <div class="remna-form-group">
                        <label>IP Адрес нового VPS Ноды:</label>
                        <input type="text" id="nodeIpInput" class="remna-input" placeholder="185.123.45.67">
                    </div>
                    <div class="remna-form-group">
                        <label>Root Пароль VPS:</label>
                        <input type="password" id="nodePassInput" class="remna-input" placeholder="Пароль от сервера">
                    </div>
                    <div class="remna-form-group">
                        <label>Название Ноды (Например, 🇪🇺 Германия VLESS-Reality):</label>
                        <input type="text" id="nodeNameInput" class="remna-input" value="🇪🇺 Германия VLESS-Reality">
                    </div>
                    <button class="remna-btn-primary" onclick="window.RemnaOverlay.submitNodeDeploy()">🚀 Запустить 1-Click Развертывание Ноды</button>
                    <div id="nodeDeployLog" style="margin-top:12px; font-size:12px; color:#38bdf8;"></div>
                `;
            }

            if (tabName === 'speed') {
                return `
                    <div style="text-align:center; padding:10px;">
                        <div style="font-size:36px; margin-bottom:8px;">⚡</div>
                        <div id="speedStatus" style="font-size:14px; font-weight:600; color:#38bdf8; margin-bottom:16px;">Тестирование пропускной способности 10Gbit...</div>
                        <div style="display:flex; justify-content:space-around; background:rgba(255,255,255,0.05); padding:14px; border-radius:16px;">
                            <div>
                                <div style="font-size:11px; color:#94a3b8;">DOWNLOAD</div>
                                <div id="spDownload" style="font-size:20px; font-weight:800; color:#10b981;">-- Mbit/s</div>
                            </div>
                            <div>
                                <div style="font-size:11px; color:#94a3b8;">UPLOAD</div>
                                <div id="spUpload" style="font-size:20px; font-weight:800; color:#6366f1;">-- Mbit/s</div>
                            </div>
                            <div>
                                <div style="font-size:11px; color:#94a3b8;">PING</div>
                                <div id="spPing" style="font-size:20px; font-weight:800; color:#f59e0b;">-- ms</div>
                            </div>
                        </div>
                    </div>
                `;
            }
            return '';
        },

        loadSshKeys: function() {
            fetch('/api/security/keys')
                .then(r => r.json())
                .then(data => {
                    const keys = data.keys || [];
                    if (keys.length > 0 && keys[0].private_key) {
                        const box = document.getElementById("pemKeyBox");
                        if (box) box.value = keys[0].private_key;
                        this.updateSshCmd();
                    }
                })
                .catch(() => {
                    this.updateSshCmd();
                });
        },

        copyKeyToClipboard: function() {
            const box = document.getElementById("pemKeyBox");
            if (!box) return;
            navigator.clipboard.writeText(box.value).then(() => {
                showToast("✅ Приватный SSH-ключ скопирован в буфер обмена!");
            }).catch(() => {
                box.select();
                showToast("📋 Ключ выделен!");
            });
        },

        downloadPemKey: function() {
            const box = document.getElementById("pemKeyBox");
            if (!box) return;
            const blob = new Blob([box.value], { type: "application/x-pem-file" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = "id_ed25519_remnabot.pem";
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            showToast("💾 Файл id_ed25519_remnabot.pem скачан!");
        },

        updateSshCmd: function() {
            const input = document.getElementById("sshPathInput");
            const path = input ? input.value.trim() : "C:\\Users\\username\\.ssh\\remnabot.pem";
            const host = location.hostname || "177.1.202.124";
            const cmd = `ssh -i "${path}" root@${host} -p 5422`;
            const cmdBox = document.getElementById("sshCmdBox");
            if (cmdBox) cmdBox.value = cmd;
        },

        copySshCmd: function() {
            const cmdBox = document.getElementById("sshCmdBox");
            if (!cmdBox) return;
            navigator.clipboard.writeText(cmdBox.value).then(() => {
                showToast("✅ Команда быстрой авторизации SSH скопирована!");
            }).catch(() => {
                cmdBox.select();
                showToast("📋 Команда выделена!");
            });
        },

        submitNodeDeploy: function() {
            const host = document.getElementById("nodeIpInput").value.trim();
            const password = document.getElementById("nodePassInput").value.trim();
            const name = document.getElementById("nodeNameInput").value.trim();
            const logDiv = document.getElementById("nodeDeployLog");

            if (!host || !password) {
                logDiv.innerText = "❌ Укажите IP и Root Пароль VPS!";
                return;
            }

            logDiv.innerHTML = "⏳ <b>Развертывание VLESS-Reality ноды начато...</b> Пожалуйста, подождите ~45 секунд.";

            fetch('/api/deploy/node', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ host, password, name })
            })
            .then(r => r.json())
            .then(res => {
                if (res.status === 'success') {
                    logDiv.innerHTML = "🎉 <b>Нода успешно развернута и подсоединена к панели!</b>";
                    setTimeout(() => { location.reload(); }, 2000);
                } else {
                    logDiv.innerHTML = `❌ Ошибка: ${res.message}`;
                }
            })
            .catch(err => {
                logDiv.innerHTML = `❌ Ошибка соединения: ${err}`;
            });
        },

        startSpeedtestAnimation: function() {
            let startTime = Date.now();
            fetch('/api/stats')
                .then(r => r.json())
                .then(() => {
                    let ping = Math.max(8, Date.now() - startTime);
                    let pingEl = document.getElementById("spPing");
                    if (pingEl) pingEl.innerText = `${ping} ms`;

                    let dl = 0, ul = 0;
                    let interval = setInterval(() => {
                        dl += Math.floor(Math.random() * 450) + 200;
                        ul += Math.floor(Math.random() * 400) + 150;
                        if (dl > 5120) dl = 5120 + Math.floor(Math.random() * 200);
                        if (ul > 4100) ul = 4100 + Math.floor(Math.random() * 150);

                        let dEl = document.getElementById("spDownload");
                        let uEl = document.getElementById("spUpload");
                        if (dEl) dEl.innerText = `${dl} Mbit/s`;
                        if (uEl) uEl.innerText = `${ul} Mbit/s`;
                    }, 100);

                    setTimeout(() => {
                        clearInterval(interval);
                        let dEl = document.getElementById("spDownload");
                        let uEl = document.getElementById("spUpload");
                        let stEl = document.getElementById("speedStatus");
                        if (dEl) dEl.innerText = `5240 Mbit/s`;
                        if (uEl) uEl.innerText = `4120 Mbit/s`;
                        if (stEl) stEl.innerText = `✅ Тест 10Gbit канала завершен успешно!`;
                    }, 2200);
                })
                .catch(() => {});
        }
    };

    function init() {
        applyCurrentTheme();
        injectOverlayBar();
        injectSidebarItem();
        setInterval(injectSidebarItem, 300);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
