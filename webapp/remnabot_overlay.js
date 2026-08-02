// Remna-Bot Overlay Engine for Remnawave Panel
(function() {
    console.log("🚀 Remna-Bot Overlay Loaded on Remnawave Panel!");

    function injectOverlayBar() {
        if (document.getElementById("remnabot-overlay-bar")) return;

        const bar = document.createElement("div");
        bar.id = "remnabot-overlay-bar";
        bar.innerHTML = `
            <span class="logo-badge">⚡ Remna-Bot Power-Up</span>
            <button class="overlay-btn" onclick="window.RemnaOverlay.cycleTheme()">🎨 Темы</button>
            <button class="overlay-btn" onclick="window.RemnaOverlay.openHardening()">🛡️ SSH Харденинг</button>
            <button class="overlay-btn" onclick="window.RemnaOverlay.openDeployNode()">🖥️ 1-Click Нода</button>
            <button class="overlay-btn" onclick="window.RemnaOverlay.runSpeedtest()">⚡ 10Gbit Speedtest</button>
        `;
        document.body.appendChild(bar);
    }

    const themes = ["theme-cyberpunk", "theme-emerald", "theme-sunset", "theme-midnight"];
    let currentThemeIdx = 0;

    window.RemnaOverlay = {
        cycleTheme: function() {
            document.body.classList.remove(...themes);
            currentThemeIdx = (currentThemeIdx + 1) % themes.length;
            const nextTheme = themes[currentThemeIdx];
            document.body.classList.add(nextTheme);
            console.log("Theme switched to:", nextTheme);
        },

        openHardening: function() {
            if (window.parent && window.parent.openSshHardeningModal) {
                window.parent.openSshHardeningModal();
            } else {
                alert("🛡️ Откройте бота в Telegram MiniApp для управления SSH Харденингом!");
            }
        },

        openDeployNode: function() {
            if (window.parent && window.parent.openDeployNodeModal) {
                window.parent.openDeployNodeModal();
            } else {
                alert("🖥️ Откройте бота в Telegram MiniApp для 1-Click Деплоя Нод!");
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
