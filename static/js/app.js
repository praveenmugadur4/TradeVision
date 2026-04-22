/**
 * TradeVision — Main Application Controller (Enhanced)
 * Supports: themes, categories, intraday tips, fibonacci, multiple strategies
 */

(() => {
    let currentSymbol = 'RELIANCE.NS';
    let currentPeriod = '1y';
    let currentInterval = '1d';
    let activeIndicators = new Set(['EMA_9', 'EMA_21', 'BB']);
    let indicatorData = null;
    let watchlistCategory = 'large_cap';

    document.addEventListener('DOMContentLoaded', () => {
        initTabs();
        initSearch();
        initTimeframe();
        initIndicatorToggles();
        initAlertForm();
        initWatchlist();
        initThemeToggle();
        initIntraday();
        initTelegram();
        updateClock();
        updateMarketStatus();

        ChartModule.initMainChart('mainChart');
        ChartModule.initRsiChart('rsiChart');
        ChartModule.initMacdChart('macdChart');

        AlertModule.init();
        BacktesterModule.init();

        loadStockData(currentSymbol);

        setInterval(updateClock, 1000);
        setInterval(updateMarketStatus, 60000);
    });

    // ─── Theme Toggle ───
    function initThemeToggle() {
        const btn = document.getElementById('themeToggle');
        const saved = localStorage.getItem('tv_theme') || 'dark';
        applyTheme(saved);

        btn.addEventListener('click', () => {
            const current = document.documentElement.getAttribute('data-theme');
            const next = current === 'dark' ? 'light' : 'dark';
            applyTheme(next);
            localStorage.setItem('tv_theme', next);

            // Re-init charts with new theme
            ChartModule.initMainChart('mainChart');
            ChartModule.initRsiChart('rsiChart');
            ChartModule.initMacdChart('macdChart');
            loadStockData(currentSymbol);
        });
    }

    function applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        const btn = document.getElementById('themeToggle');
        if (btn) btn.textContent = theme === 'dark' ? '☀️' : '🌙';
    }

    // ─── Tab Navigation ───
    function initTabs() {
        const tabs = document.querySelectorAll('.nav-tab');
        tabs.forEach(tab => {
            tab.addEventListener('click', () => {
                tabs.forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
                const targetId = 'content' + tab.dataset.tab.charAt(0).toUpperCase() + tab.dataset.tab.slice(1);
                const target = document.getElementById(targetId);
                if (target) target.classList.add('active');
            });
        });
    }

    // ─── Search ───
    function initSearch() {
        const input = document.getElementById('searchInput');
        const results = document.getElementById('searchResults');
        let debounce = null;

        input.addEventListener('input', () => {
            clearTimeout(debounce);
            const query = input.value.trim();
            if (query.length < 2) { results.classList.remove('active'); return; }

            debounce = setTimeout(async () => {
                try {
                    const res = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
                    const data = await res.json();
                    if (data.length === 0) { results.classList.remove('active'); return; }

                    results.innerHTML = data.map(item => `
                        <div class="search-result-item" data-symbol="${item.symbol}">
                            <div>
                                <span class="symbol">${item.symbol.replace('.NS', '').replace('.BO', '')}</span>
                                <span class="name"> — ${item.name}</span>
                            </div>
                            <div style="display:flex;gap:6px;align-items:center;">
                                <span class="exchange" style="font-size:0.65rem;">${item.category || ''}</span>
                                <span class="exchange">${item.exchange}</span>
                            </div>
                        </div>
                    `).join('');
                    results.classList.add('active');

                    results.querySelectorAll('.search-result-item').forEach(item => {
                        item.addEventListener('click', () => {
                            const symbol = item.dataset.symbol;
                            input.value = '';
                            results.classList.remove('active');
                            currentSymbol = symbol;
                            loadStockData(symbol);
                            document.getElementById('btSymbol').value = symbol;
                            document.getElementById('alertSymbol').value = symbol;
                            document.getElementById('intradaySingleSymbol').value = symbol;
                        });
                    });
                } catch (e) { console.error('Search error:', e); }
            }, 300);
        });

        document.addEventListener('click', (e) => {
            if (!e.target.closest('.header__search')) results.classList.remove('active');
        });

        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                const query = input.value.trim().toUpperCase();
                if (query) {
                    let symbol = query;
                    if (!symbol.endsWith('.NS') && !symbol.endsWith('.BO')) symbol += '.NS';
                    currentSymbol = symbol;
                    input.value = '';
                    results.classList.remove('active');
                    loadStockData(symbol);
                }
            }
        });
    }

    // ─── Timeframe ───
    function initTimeframe() {
        document.querySelectorAll('#timeframeSelector .timeframe-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('#timeframeSelector .timeframe-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                currentPeriod = btn.dataset.period;
                currentInterval = btn.dataset.interval;
                loadStockData(currentSymbol);
            });
        });
    }

    // ─── Indicator Toggles ───
    function initIndicatorToggles() {
        document.querySelectorAll('#indicatorToggles .indicator-toggle').forEach(btn => {
            btn.addEventListener('click', () => {
                const ind = btn.dataset.indicator;
                btn.classList.toggle('active');
                if (btn.classList.contains('active')) activeIndicators.add(ind);
                else activeIndicators.delete(ind);
                applyIndicatorOverlays();
            });
        });
    }

    // ─── Load Stock Data ───
    async function loadStockData(symbol) {
        showToast(`Loading ${symbol.replace('.NS', '')}...`, 'info', 2000);
        try {
            const [marketRes, indicatorRes, signalRes, infoRes] = await Promise.all([
                fetch(`/api/market-data?symbol=${symbol}&period=${currentPeriod}&interval=${currentInterval}`),
                fetch(`/api/indicators?symbol=${symbol}&period=${currentPeriod}&interval=${currentInterval}`),
                fetch(`/api/signals?symbol=${symbol}&period=${currentPeriod}&interval=${currentInterval}`),
                fetch(`/api/stock-info?symbol=${symbol}`),
            ]);

            const marketData = await marketRes.json();
            const indData = await indicatorRes.json();
            const signalData = await signalRes.json();
            const infoData = await infoRes.json();

            indicatorData = indData;
            updateStockInfo(infoData, indData.summary);

            if (marketData.data && marketData.data.length > 0) {
                const candles = marketData.data.map(d => ({ time: d.time, open: d.open, high: d.high, low: d.low, close: d.close }));
                const volumes = marketData.data.map(d => ({ time: d.time, value: d.volume, color: d.close >= d.open ? 'rgba(0, 230, 118, 0.15)' : 'rgba(255, 23, 68, 0.15)' }));
                ChartModule.setMainChartData(candles, volumes);
            }

            applyIndicatorOverlays();
            if (indData.panel_series?.RSI) ChartModule.setRsiData(indData.panel_series.RSI);
            if (indData.panel_series) ChartModule.setMacdData(indData.panel_series.MACD, indData.panel_series.MACD_Signal, indData.panel_series.MACD_Hist);

            updateSignals(signalData);
            updateIndicatorDetails(indData.summary);
            updateFibonacciLevels(indData.summary?.fibonacci);
        } catch (e) {
            console.error('Error loading stock data:', e);
            showToast('Error loading data. Please try again.', 'sell');
        }
    }

    function applyIndicatorOverlays() {
        if (!indicatorData?.overlay_series) return;
        const overlays = indicatorData.overlay_series;
        ['EMA_9', 'EMA_21', 'EMA_50', 'SMA_200', 'Supertrend'].forEach(ind => {
            if (activeIndicators.has(ind) && overlays[ind]) ChartModule.addOverlayIndicator(ind, overlays[ind]);
            else ChartModule.removeOverlayIndicator(ind);
        });
        if (activeIndicators.has('BB') && overlays.BB_Upper && overlays.BB_Mid && overlays.BB_Lower) {
            ChartModule.addBollingerBands(overlays.BB_Upper, overlays.BB_Mid, overlays.BB_Lower);
        } else { ChartModule.removeBollingerBands(); }
    }

    function updateStockInfo(info, summary) {
        document.getElementById('stockName').textContent = info.name || currentSymbol;
        document.getElementById('stockSymbol').textContent = currentSymbol;
        const price = info.currentPrice || summary?.price?.close || 0;
        const prevClose = info.previousClose || 0;
        const change = price - prevClose;
        const changePct = prevClose ? ((change / prevClose) * 100) : 0;
        document.getElementById('stockPrice').textContent = `₹${formatNum(price)}`;
        const changeEl = document.getElementById('stockChange');
        const isPositive = change >= 0;
        changeEl.textContent = `${isPositive ? '+' : ''}${formatNum(change)} (${isPositive ? '+' : ''}${changePct.toFixed(2)}%)`;
        changeEl.className = `stock-info__change ${isPositive ? 'positive' : 'negative'}`;
        document.getElementById('metaDayHigh').textContent = `₹${formatNum(info.dayHigh)}`;
        document.getElementById('metaDayLow').textContent = `₹${formatNum(info.dayLow)}`;
        document.getElementById('meta52High').textContent = `₹${formatNum(info.fiftyTwoWeekHigh)}`;
        document.getElementById('meta52Low').textContent = `₹${formatNum(info.fiftyTwoWeekLow)}`;
        document.getElementById('metaVolume').textContent = formatVolume(info.volume);
        document.getElementById('metaPE').textContent = info.peRatio ? info.peRatio.toFixed(2) : 'N/A';
    }

    function updateSignals(data) {
        const verdict = document.getElementById('signalVerdict');
        verdict.textContent = data.overall_signal ? data.overall_signal.replace('_', ' ') : 'HOLD';
        verdict.className = 'signal-gauge__value ' + getSignalClass(data.overall_signal);
        document.getElementById('signalConfidence').textContent = `Confidence: ${data.confidence || 0}%`;
        document.getElementById('confidenceBarFill').style.width = `${data.confidence || 0}%`;

        const breakdownList = document.getElementById('signalBreakdown');
        if (breakdownList && data.breakdown) {
            breakdownList.innerHTML = data.breakdown.map(item => {
                const badgeClass = item.score > 0 ? 'badge-bullish' : item.score < 0 ? 'badge-bearish' : 'badge-neutral';
                return `<li class="breakdown-item"><div><div class="breakdown-item__name">${item.indicator}</div><div class="breakdown-item__reason">${item.reason}</div></div><span class="breakdown-item__badge ${badgeClass}">${item.score > 0 ? '+' : ''}${item.score}</span></li>`;
            }).join('');
        }

        const srLevels = document.getElementById('srLevels');
        if (srLevels && data.support_resistance) {
            const sr = data.support_resistance;
            srLevels.innerHTML = `
                <div class="sr-level resistance"><div class="sr-level__label">Resistance 2</div><div class="sr-level__value">₹${sr.resistance_2 || '—'}</div></div>
                <div class="sr-level resistance"><div class="sr-level__label">Resistance 1</div><div class="sr-level__value">₹${sr.resistance_1 || '—'}</div></div>
                <div class="sr-level pivot"><div class="sr-level__label">Pivot</div><div class="sr-level__value">₹${sr.pivot || '—'}</div></div>
                <div class="sr-level support"><div class="sr-level__label">Support 1</div><div class="sr-level__value">₹${sr.support_1 || '—'}</div></div>
                <div class="sr-level support"><div class="sr-level__label">Support 2</div><div class="sr-level__value">₹${sr.support_2 || '—'}</div></div>
                <div class="sr-level pivot"><div class="sr-level__label">52W Range</div><div class="sr-level__value" style="font-size:0.75rem;">₹${sr['52w_low'] || '—'} — ₹${sr['52w_high'] || '—'}</div></div>
            `;
        }
    }

    function updateFibonacciLevels(fib) {
        const container = document.getElementById('fibLevels');
        if (!container || !fib) return;
        container.innerHTML = `
            <div class="sr-level fib-ext"><div class="sr-level__label">Extension 161.8%</div><div class="sr-level__value">₹${fib.fib_ext_162 || '—'}</div></div>
            <div class="sr-level fib-ext"><div class="sr-level__label">Extension 127.2%</div><div class="sr-level__value">₹${fib.fib_ext_127 || '—'}</div></div>
            <div class="sr-level resistance"><div class="sr-level__label">0% (High)</div><div class="sr-level__value">₹${fib.fib_0 || '—'}</div></div>
            <div class="sr-level fib"><div class="sr-level__label">23.6%</div><div class="sr-level__value">₹${fib.fib_236 || '—'}</div></div>
            <div class="sr-level fib"><div class="sr-level__label">38.2%</div><div class="sr-level__value">₹${fib.fib_382 || '—'}</div></div>
            <div class="sr-level pivot"><div class="sr-level__label">50%</div><div class="sr-level__value">₹${fib.fib_500 || '—'}</div></div>
            <div class="sr-level fib"><div class="sr-level__label">61.8% (Golden)</div><div class="sr-level__value">₹${fib.fib_618 || '—'}</div></div>
            <div class="sr-level support"><div class="sr-level__label">100% (Low)</div><div class="sr-level__value">₹${fib.fib_100 || '—'}</div></div>
        `;
    }

    function updateIndicatorDetails(summary) {
        const grid = document.getElementById('indicatorsGrid');
        if (!grid || !summary) return;
        grid.innerHTML = `
            <div class="indicator-category"><div class="indicator-category__title">Moving Averages</div>${renderIndicatorRows(summary.movingAverages)}</div>
            <div class="indicator-category"><div class="indicator-category__title">Oscillators</div>${renderIndicatorRows(summary.oscillators)}</div>
            <div class="indicator-category"><div class="indicator-category__title">Volatility & Volume</div>${renderIndicatorRows({ ...summary.volatility, ...summary.volume_indicators })}</div>
        `;
    }

    function renderIndicatorRows(obj) {
        if (!obj) return '';
        return Object.entries(obj).filter(([, v]) => v !== null && v !== undefined).map(([key, value]) => `
            <div class="indicator-row"><span class="indicator-row__name">${key.replace(/_/g, ' ')}</span><span class="indicator-row__value">${typeof value === 'number' ? formatNum(value) : value}</span></div>
        `).join('');
    }

    // ─── Alert Form ───
    function initAlertForm() {
        const form = document.getElementById('alertForm');
        const typeSelect = document.getElementById('alertType');
        const valueGroup = document.getElementById('alertValueGroup');
        typeSelect.addEventListener('change', () => {
            valueGroup.style.display = ['price_above', 'price_below'].includes(typeSelect.value) ? 'flex' : 'none';
        });
        form.addEventListener('submit', (e) => {
            e.preventDefault();
            AlertModule.addAlert({
                symbol: document.getElementById('alertSymbol').value.trim(),
                type: typeSelect.value,
                value: parseFloat(document.getElementById('alertValue').value),
                sound: document.getElementById('alertSound').checked,
                notification: document.getElementById('alertNotification').checked,
            });
        });
        const autoCheck = document.getElementById('alertAutoCheck');
        if (autoCheck) autoCheck.addEventListener('change', () => autoCheck.checked ? AlertModule.startAutoCheck() : AlertModule.stopAutoCheck());
    }

    // ─── Watchlist with Categories ───
    function initWatchlist() {
        document.getElementById('btnScanWatchlist').addEventListener('click', () => scanWatchlist(watchlistCategory));

        document.querySelectorAll('#watchlistCategoryTabs .category-tab').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('#watchlistCategoryTabs .category-tab').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                watchlistCategory = btn.dataset.category;
            });
        });
    }

    async function scanWatchlist(category) {
        const btn = document.getElementById('btnScanWatchlist');
        const grid = document.getElementById('watchlistGrid');
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner" style="width:16px;height:16px;border-width:2px;display:inline-block;"></span> Scanning...';

        grid.innerHTML = `<div class="empty-state" style="grid-column: 1 / -1;"><div class="spinner" style="margin: 0 auto 16px;"></div><div class="empty-state__text">Scanning ${category.replace('_', ' ')} stocks...</div></div>`;

        try {
            const res = await fetch(`/api/multi-signals?category=${category}`);
            const data = await res.json();

            if (data.length === 0) {
                grid.innerHTML = `<div class="empty-state" style="grid-column: 1 / -1;"><div class="empty-state__icon">😕</div><div class="empty-state__text">No data available.</div></div>`;
                return;
            }

            grid.innerHTML = data.map(stock => {
                const isPositive = stock.change_pct >= 0;
                const signalColor = getSignalColor(stock.signal);
                return `
                    <div class="watchlist-card" onclick="window.dispatchEvent(new CustomEvent('selectStock', {detail: '${stock.symbol}'}))">
                        <div class="watchlist-card__header">
                            <span class="watchlist-card__symbol">${stock.name}</span>
                            <span class="watchlist-card__signal" style="background: ${signalColor}20; color: ${signalColor}">${stock.signal.replace('_', ' ')}</span>
                        </div>
                        <div style="display: flex; align-items: baseline; gap: 10px;">
                            <span class="watchlist-card__price">₹${formatNum(stock.price)}</span>
                            <span class="watchlist-card__change" style="color: ${isPositive ? 'var(--accent-green)' : 'var(--accent-red)'}">${isPositive ? '+' : ''}${stock.change_pct}%</span>
                        </div>
                        <div class="watchlist-card__confidence">
                            Confidence: ${stock.confidence}% · ${stock.category}
                            <div class="watchlist-card__confidence-bar"><div class="watchlist-card__confidence-fill" style="width: ${stock.confidence}%; background: ${signalColor}"></div></div>
                        </div>
                    </div>
                `;
            }).join('');
        } catch (e) {
            grid.innerHTML = `<div class="empty-state" style="grid-column: 1 / -1;"><div class="empty-state__icon">❌</div><div class="empty-state__text">Error scanning. Please try again.</div></div>`;
        } finally {
            btn.disabled = false;
            btn.innerHTML = '🔄 Scan';
        }
    }

    window.addEventListener('selectStock', (e) => {
        currentSymbol = e.detail;
        loadStockData(currentSymbol);
        document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
        document.getElementById('tabDashboard').classList.add('active');
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        document.getElementById('contentDashboard').classList.add('active');
    });

    // ─── Intraday Tips ───
    function initIntraday() {
        document.getElementById('btnScanIntraday').addEventListener('click', scanIntraday);
        document.getElementById('btnSingleTip').addEventListener('click', loadSingleTip);
    }

    async function scanIntraday() {
        const btn = document.getElementById('btnScanIntraday');
        const grid = document.getElementById('intradayTipsGrid');
        const category = document.getElementById('intradayCategory').value;

        btn.disabled = true;
        btn.innerHTML = '<span class="spinner" style="width:16px;height:16px;border-width:2px;display:inline-block;"></span> Scanning...';
        grid.innerHTML = `<div class="empty-state" style="grid-column:1/-1;"><div class="spinner" style="margin: 0 auto 16px;"></div><div class="empty-state__text">Analyzing stocks for intraday opportunities...</div></div>`;

        try {
            const res = await fetch(`/api/intraday-scan?category=${category}`);
            const tips = await res.json();

            if (tips.length === 0) {
                grid.innerHTML = `<div class="empty-state" style="grid-column:1/-1;"><div class="empty-state__icon">⏳</div><div class="empty-state__text">No actionable tips found. Market may be sideways.</div></div>`;
                return;
            }

            grid.innerHTML = tips.map(tip => renderTipCard(tip)).join('');
        } catch (e) {
            grid.innerHTML = `<div class="empty-state" style="grid-column:1/-1;"><div class="empty-state__icon">❌</div><div class="empty-state__text">Error scanning. Please try again.</div></div>`;
        } finally {
            btn.disabled = false;
            btn.innerHTML = '⚡ Scan for Tips';
        }
    }

    async function loadSingleTip() {
        const symbol = document.getElementById('intradaySingleSymbol').value.trim();
        const container = document.getElementById('singleTipResult');
        if (!symbol) { showToast('Enter a symbol', 'info'); return; }

        container.innerHTML = `<div style="text-align:center;padding:20px;"><div class="spinner" style="margin:0 auto;"></div></div>`;

        try {
            const res = await fetch(`/api/intraday-tips?symbol=${encodeURIComponent(symbol)}`);
            const tip = await res.json();
            container.innerHTML = renderTipCard(tip);
        } catch (e) {
            container.innerHTML = `<div class="empty-state"><div class="empty-state__text">Error loading analysis</div></div>`;
        }
    }

    function renderTipCard(tip) {
        const actionClass = tip.action === 'BUY' ? 'buy-tip' : tip.action === 'SELL' ? 'sell-tip' : 'wait-tip';
        const actionBadge = tip.action === 'BUY' ? 'buy' : tip.action === 'SELL' ? 'sell' : 'wait';
        return `
            <div class="intraday-tip-card ${actionClass}">
                <div class="tip-card__header">
                    <span class="tip-card__symbol">${(tip.symbol || '').replace('.NS', '')}</span>
                    <span class="tip-card__action ${actionBadge}">${tip.action}</span>
                </div>
                <div class="tip-card__price-row">
                    <span class="tip-card__current-price">₹${formatNum(tip.current_price)}</span>
                    <span class="tip-card__confidence">${tip.confidence}% confidence</span>
                </div>
                ${tip.action !== 'WAIT' ? `
                <div class="tip-card__levels">
                    <div class="tip-level entry"><div class="tip-level__label">Entry</div><div class="tip-level__value">₹${tip.entry_price}</div></div>
                    <div class="tip-level target"><div class="tip-level__label">Target</div><div class="tip-level__value">₹${tip.target}</div></div>
                    <div class="tip-level stoploss"><div class="tip-level__label">Stop Loss</div><div class="tip-level__value">₹${tip.stop_loss}</div></div>
                </div>
                <div style="margin-bottom:8px;"><span class="tip-card__rr">Risk:Reward = 1:${tip.risk_reward}</span></div>
                ` : ''}
                <ul class="tip-card__reasoning">${(tip.reasoning || []).map(r => `<li>${r}</li>`).join('')}</ul>
                <ul class="tip-card__tips">${(tip.tips || []).map(t => `<li>${t}</li>`).join('')}</ul>
            </div>
        `;
    }

    // ─── Telegram Config ───
    async function initTelegram() {
        // Load existing config
        try {
            const res = await fetch('/api/telegram/config');
            const config = await res.json();
            document.getElementById('telegramEnabled').checked = config.enabled;
            document.getElementById('telegramChatId').value = config.chat_id || '';
            const status = document.getElementById('telegramStatus');
            if (config.enabled && config.bot_token_set) {
                status.innerHTML = '🟢 Telegram connected';
                status.style.color = 'var(--accent-green)';
            }
        } catch (e) { /* ignore */ }

        // Save config
        document.getElementById('btnSaveTelegram').addEventListener('click', async () => {
            const botToken = document.getElementById('telegramBotToken').value.trim();
            const chatId = document.getElementById('telegramChatId').value.trim();
            const enabled = document.getElementById('telegramEnabled').checked;
            const status = document.getElementById('telegramStatus');

            if (!botToken && !chatId) {
                status.innerHTML = '⚠️ Please enter Bot Token and Chat ID';
                status.style.color = 'var(--accent-amber)';
                return;
            }

            try {
                const res = await fetch('/api/telegram/config', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ bot_token: botToken, chat_id: chatId, enabled }),
                });
                const result = await res.json();
                status.innerHTML = '✅ Configuration saved!';
                status.style.color = 'var(--accent-green)';
                showToast('Telegram configuration saved', 'info');
            } catch (e) {
                status.innerHTML = '❌ Error saving configuration';
                status.style.color = 'var(--accent-red)';
            }
        });

        // Test message
        document.getElementById('btnTestTelegram').addEventListener('click', async () => {
            const status = document.getElementById('telegramStatus');
            status.innerHTML = '⏳ Sending test message...';
            status.style.color = 'var(--text-muted)';

            try {
                const res = await fetch('/api/telegram/test', { method: 'POST' });
                const result = await res.json();
                if (result.success) {
                    status.innerHTML = '✅ Test message sent! Check your Telegram.';
                    status.style.color = 'var(--accent-green)';
                    showToast('Test message sent to Telegram!', 'buy');
                } else {
                    status.innerHTML = '❌ ' + result.message;
                    status.style.color = 'var(--accent-red)';
                    showToast(result.message, 'sell');
                }
            } catch (e) {
                status.innerHTML = '❌ Error sending test message';
                status.style.color = 'var(--accent-red)';
            }
        });
    }

    // ─── Utilities ───
    function getSignalClass(signal) { return signal ? signal.toLowerCase().replace('_', '-') : 'hold'; }
    function getSignalColor(signal) {
        return { STRONG_BUY: '#00e676', BUY: '#66ffa6', HOLD: '#ffab00', SELL: '#ff6b6b', STRONG_SELL: '#ff1744' }[signal] || '#ffab00';
    }
    function formatNum(num) {
        if (num === undefined || num === null || isNaN(num)) return '—';
        return Number(num).toLocaleString('en-IN', { maximumFractionDigits: 2 });
    }
    function formatVolume(vol) {
        if (!vol) return '—';
        if (vol >= 10000000) return (vol / 10000000).toFixed(2) + ' Cr';
        if (vol >= 100000) return (vol / 100000).toFixed(2) + ' L';
        if (vol >= 1000) return (vol / 1000).toFixed(1) + ' K';
        return vol.toString();
    }
    function updateClock() {
        const el = document.getElementById('currentTime');
        if (el) el.textContent = new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true });
    }
    function updateMarketStatus() {
        const dot = document.getElementById('marketStatusDot');
        const text = document.getElementById('marketStatusText');
        const now = new Date();
        const time = now.getHours() * 60 + now.getMinutes();
        const day = now.getDay();
        const isOpen = day >= 1 && day <= 5 && time >= 555 && time <= 930;
        dot.classList.toggle('closed', !isOpen);
        text.textContent = isOpen ? 'Market Open' : 'Market Closed';
    }
})();
