/**
 * TradeVision — Alert System Module
 * Browser notifications + sound alerts + auto-polling
 */

const AlertModule = (() => {
    let alerts = [];
    let triggeredAlerts = [];
    let checkInterval = null;
    let alertIdCounter = 1;

    function init() {
        // Load from localStorage
        const saved = localStorage.getItem('tv_alerts');
        if (saved) {
            try {
                const parsed = JSON.parse(saved);
                alerts = parsed.alerts || [];
                triggeredAlerts = parsed.triggered || [];
                alertIdCounter = parsed.counter || 1;
            } catch (e) { /* ignore */ }
        }

        renderAlerts();
        renderTriggeredAlerts();

        // Request notification permission
        if ('Notification' in window && Notification.permission === 'default') {
            Notification.requestPermission();
        }

        // Start auto-checking
        startAutoCheck();
    }

    function save() {
        localStorage.setItem('tv_alerts', JSON.stringify({
            alerts,
            triggered: triggeredAlerts,
            counter: alertIdCounter,
        }));
    }

    function addAlert(config) {
        const alert = {
            id: alertIdCounter++,
            symbol: config.symbol,
            type: config.type,
            value: config.value,
            sound: config.sound,
            notification: config.notification,
            status: 'active',
            createdAt: new Date().toISOString(),
        };

        alerts.push(alert);
        save();
        renderAlerts();
        showToast(`Alert created for ${alert.symbol}`, 'info');
        return alert;
    }

    function removeAlert(id) {
        alerts = alerts.filter(a => a.id !== id);
        save();
        renderAlerts();
    }

    function getAlertTypeLabel(type) {
        const labels = {
            price_above: 'Price Above',
            price_below: 'Price Below',
            signal_buy: 'Buy Signal',
            signal_sell: 'Sell Signal',
            rsi_oversold: 'RSI Oversold',
            rsi_overbought: 'RSI Overbought',
        };
        return labels[type] || type;
    }

    function getAlertDescription(alert) {
        switch (alert.type) {
            case 'price_above': return `Price > ₹${alert.value}`;
            case 'price_below': return `Price < ₹${alert.value}`;
            case 'signal_buy': return 'Buy signal generated';
            case 'signal_sell': return 'Sell signal generated';
            case 'rsi_oversold': return 'RSI drops below 30';
            case 'rsi_overbought': return 'RSI rises above 70';
            default: return alert.type;
        }
    }

    function renderAlerts() {
        const container = document.getElementById('activeAlertsList');
        if (!container) return;

        if (alerts.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state__icon">🔔</div>
                    <div class="empty-state__text">No alerts configured yet</div>
                </div>`;
            return;
        }

        container.innerHTML = alerts.map(alert => `
            <div class="alert-item" data-id="${alert.id}">
                <div class="alert-item__info">
                    <div class="alert-item__symbol">${alert.symbol}</div>
                    <div class="alert-item__condition">${getAlertDescription(alert)}</div>
                </div>
                <span class="alert-item__status active">Active</span>
                <button class="btn-delete" onclick="AlertModule.removeAlert(${alert.id})">✕</button>
            </div>
        `).join('');
    }

    function renderTriggeredAlerts() {
        const container = document.getElementById('triggeredAlertsList');
        if (!container) return;

        if (triggeredAlerts.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state__icon">✅</div>
                    <div class="empty-state__text">No triggered alerts yet</div>
                </div>`;
            return;
        }

        container.innerHTML = triggeredAlerts.slice(-20).reverse().map(alert => `
            <div class="alert-item">
                <div class="alert-item__info">
                    <div class="alert-item__symbol">${alert.symbol}</div>
                    <div class="alert-item__condition">${getAlertDescription(alert)} — Triggered at ${new Date(alert.triggeredAt).toLocaleString()}</div>
                </div>
                <span class="alert-item__status triggered">Triggered</span>
            </div>
        `).join('');
    }

    async function checkAlerts() {
        if (alerts.length === 0) return;

        // Group alerts by symbol to minimize API calls
        const symbolGroups = {};
        alerts.forEach(alert => {
            if (!symbolGroups[alert.symbol]) {
                symbolGroups[alert.symbol] = [];
            }
            symbolGroups[alert.symbol].push(alert);
        });

        for (const [symbol, symbolAlerts] of Object.entries(symbolGroups)) {
            try {
                // Fetch signals (which includes price data)
                const response = await fetch(`/api/signals?symbol=${encodeURIComponent(symbol)}&period=3mo&interval=1d`);
                const signalData = await response.json();

                // Fetch indicator data for RSI
                const indResponse = await fetch(`/api/indicators?symbol=${encodeURIComponent(symbol)}&period=3mo&interval=1d`);
                const indData = await indResponse.json();

                const currentPrice = indData.summary?.price?.close;
                const rsi = indData.summary?.oscillators?.RSI;
                const signal = signalData.overall_signal;

                for (const alert of symbolAlerts) {
                    let triggered = false;

                    switch (alert.type) {
                        case 'price_above':
                            if (currentPrice && currentPrice >= alert.value) triggered = true;
                            break;
                        case 'price_below':
                            if (currentPrice && currentPrice <= alert.value) triggered = true;
                            break;
                        case 'signal_buy':
                            if (signal === 'STRONG_BUY' || signal === 'BUY') triggered = true;
                            break;
                        case 'signal_sell':
                            if (signal === 'STRONG_SELL' || signal === 'SELL') triggered = true;
                            break;
                        case 'rsi_oversold':
                            if (rsi && rsi < 30) triggered = true;
                            break;
                        case 'rsi_overbought':
                            if (rsi && rsi > 70) triggered = true;
                            break;
                    }

                    if (triggered) {
                        triggerAlert(alert, currentPrice);
                    }
                }
            } catch (e) {
                console.error(`Error checking alerts for ${symbol}:`, e);
            }
        }
    }

    function triggerAlert(alert, currentPrice) {
        // Move to triggered
        const triggered = { ...alert, triggeredAt: new Date().toISOString(), price: currentPrice };
        triggeredAlerts.push(triggered);

        // Remove from active
        alerts = alerts.filter(a => a.id !== alert.id);
        save();

        // Play sound
        if (alert.sound) {
            playAlertSound();
        }

        // Browser notification
        if (alert.notification && 'Notification' in window && Notification.permission === 'granted') {
            new Notification(`TradeVision Alert — ${alert.symbol}`, {
                body: `${getAlertDescription(alert)}\nCurrent Price: ₹${currentPrice}`,
                icon: '📊',
            });
        }

        // Show toast
        const isGreen = ['price_above', 'signal_buy', 'rsi_oversold'].includes(alert.type);
        showToast(
            `🔔 Alert Triggered: ${alert.symbol} — ${getAlertDescription(alert)} (₹${currentPrice})`,
            isGreen ? 'buy' : 'sell'
        );

        // Send to Telegram
        try {
            fetch('/api/telegram/send-alert', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ symbol: alert.symbol, type: alert.type, price: currentPrice }),
            });
        } catch (e) { /* Telegram send failed silently */ }

        renderAlerts();
        renderTriggeredAlerts();
    }

    function playAlertSound() {
        try {
            // Generate a simple alert beep using Web Audio API
            const ctx = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = ctx.createOscillator();
            const gainNode = ctx.createGain();

            oscillator.connect(gainNode);
            gainNode.connect(ctx.destination);

            oscillator.frequency.value = 880;
            oscillator.type = 'sine';
            gainNode.gain.setValueAtTime(0.3, ctx.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.5);

            oscillator.start(ctx.currentTime);
            oscillator.stop(ctx.currentTime + 0.5);

            // Second beep
            setTimeout(() => {
                const osc2 = ctx.createOscillator();
                const gain2 = ctx.createGain();
                osc2.connect(gain2);
                gain2.connect(ctx.destination);
                osc2.frequency.value = 1320;
                osc2.type = 'sine';
                gain2.gain.setValueAtTime(0.3, ctx.currentTime);
                gain2.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.5);
                osc2.start(ctx.currentTime);
                osc2.stop(ctx.currentTime + 0.5);
            }, 200);
        } catch (e) {
            console.log('Audio not available');
        }
    }

    function startAutoCheck() {
        const autoCheckEnabled = document.getElementById('alertAutoCheck');
        const intervalSelect = document.getElementById('alertCheckInterval');

        if (checkInterval) {
            clearInterval(checkInterval);
        }

        if (autoCheckEnabled && autoCheckEnabled.checked) {
            const interval = intervalSelect ? parseInt(intervalSelect.value) : 60000;
            checkInterval = setInterval(checkAlerts, interval);
        }
    }

    function stopAutoCheck() {
        if (checkInterval) {
            clearInterval(checkInterval);
            checkInterval = null;
        }
    }

    return {
        init,
        addAlert,
        removeAlert,
        checkAlerts,
        startAutoCheck,
        stopAutoCheck,
        getAlerts: () => alerts,
        getTriggered: () => triggeredAlerts,
    };
})();


// ─── Toast Notification System ───
function showToast(message, type = 'info', duration = 5000) {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const icons = {
        buy: '🟢',
        sell: '🔴',
        info: '💡',
    };

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <span class="toast__icon">${icons[type] || '💡'}</span>
        <span class="toast__message">${message}</span>
        <button class="toast__close" onclick="this.parentElement.remove()">✕</button>
    `;

    container.appendChild(toast);

    setTimeout(() => {
        if (toast.parentElement) {
            toast.style.animation = 'slideInToast 0.3s ease reverse';
            setTimeout(() => toast.remove(), 300);
        }
    }, duration);
}
