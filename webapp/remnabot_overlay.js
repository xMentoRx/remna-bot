// Remna-Bot Overlay Engine & Live Theme Customizer for Remnawave Panel
(function() {
    console.log("🚀 Remna-Bot Power-Up Overlay Engine Loaded!");

    const themes = [
        { id: "theme-default", name: "Remnawave Original" },
        { id: "theme-cyberpunk", name: "Cyberpunk Neon 🟣" },
        { id: "theme-emerald", name: "Emerald Matrix 🟢" },
        { id: "theme-sunset", name: "Sunset Orange 🟠" },
        { id: "theme-oled", name: "OLED Pure Black 🖤" }
    ];
    let currentThemeIdx = 0;
    let isMinimized = false;

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
                z-index: 1000000;
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
                <button class="overlay-btn" onclick="window.RemnaOverlay.cycleTheme()">🎨 Темы</button>
                <button class="overlay-btn" onclick="window.RemnaOverlay.openHardening()">🛡️ SSH Харденинг</button>
                <button class="overlay-btn" onclick="window.RemnaOverlay.openDeployNode()">🖥️ 1-Click Нода</button>
                <button class="overlay-btn" onclick="window.RemnaOverlay.runSpeedtest()">⚡ 10Gbit Speedtest</button>
                <button class="minimize-btn" title="Свернуть панель" onclick="window.RemnaOverlay.toggleMinimize()">▼</button>
            `;
        }
    }

    window.RemnaOverlay = {
        cycleTheme: function() {
            const allThemeClasses = themes.map(t => t.id);
            document.body.classList.remove(...allThemeClasses);
            document.documentElement.classList.remove(...allThemeClasses);

            currentThemeIdx = (currentThemeIdx + 1) % themes.length;
            const nextTheme = themes[currentThemeIdx];

            if (nextTheme.id !== "theme-default") {
                document.body.classList.add(nextTheme.id);
                document.documentElement.classList.add(nextTheme.id);
            }

            showToast(`🎨 Тема оформление: ${nextTheme.name}`);
        },

        toggleMinimize: function() {
            isMinimized = !isMinimized;
            const bar = document.getElementById("remnabot-overlay-bar");
            if (bar) renderBarContent(bar);
        },

        openHardening: function() {
            if (window.parent && window.parent.openSshHardeningModal) {
                window.parent.openSshHardeningModal();
            } else {
                alert("🛡️ Управление SSH Харденингом доступно в Telegram MiniApp!");
            }
        },

        openDeployNode: function() {
            if (window.parent && window.parent.openDeployNodeModal) {
                window.parent.openDeployNodeModal();
            } else {
                alert("🖥️ 1-Click Развертывание нод доступно в Telegram MiniApp!");
            }
        },

        runSpeedtest: function() {
            if (window.parent && window.parent.openSpeedtestModal) {
                window.parent.openSpeedtestModal();
            } else {
                alert("⚡ Ookla 10Gbit Speedtest доступен в Telegram MiniApp!");
            }
        }
    };

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", injectOverlayBar);
    } else {
        injectOverlayBar();
    }
})();
