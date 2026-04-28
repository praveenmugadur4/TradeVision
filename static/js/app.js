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
        initGoldenPicks();
        initMarketPulse();
        initPaperTrading();
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

    // ─── Golden Picks & Weekly Strategy ───
    function initGoldenPicks() {
        document.getElementById('btnScanGolden').addEventListener('click', scanGoldenPicks);
        document.getElementById('btnScanWeekly').addEventListener('click', scanWeeklyPicks);
    }

    async function scanGoldenPicks() {
        const btn = document.getElementById('btnScanGolden');
        const grid = document.getElementById('goldenPicksGrid');
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner" style="width:16px;height:16px;border-width:2px;display:inline-block;"></span> Scanning 40 stocks...';
        grid.innerHTML = `<div class="empty-state" style="grid-column:1/-1;"><div class="spinner" style="margin:0 auto 16px;"></div><div class="empty-state__text">Analyzing CPR + VWAP + 8 indicators across 40 stocks...</div></div>`;

        try {
            const res = await fetch('/api/golden-picks?top=6');
            const picks = await res.json();
            if (picks.length === 0) {
                grid.innerHTML = `<div class="empty-state" style="grid-column:1/-1;"><div class="empty-state__icon">⏳</div><div class="empty-state__text">No golden picks today. Market may be sideways or no stocks meet >80% confidence threshold.</div></div>`;
                return;
            }
            grid.innerHTML = picks.map(p => renderGoldenCard(p)).join('');
        } catch (e) {
            grid.innerHTML = `<div class="empty-state" style="grid-column:1/-1;"><div class="empty-state__icon">❌</div><div class="empty-state__text">Error scanning. Please try again.</div></div>`;
        } finally {
            btn.disabled = false;
            btn.innerHTML = '⚡ Find Golden Picks';
        }
    }

    async function scanWeeklyPicks() {
        const btn = document.getElementById('btnScanWeekly');
        const grid = document.getElementById('weeklyPicksGrid');
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner" style="width:16px;height:16px;border-width:2px;display:inline-block;"></span> Scanning 50 stocks...';
        grid.innerHTML = `<div class="empty-state" style="grid-column:1/-1;"><div class="spinner" style="margin:0 auto 16px;"></div><div class="empty-state__text">Analyzing weekly trends across 50 stocks (1-year data)...</div></div>`;

        try {
            const res = await fetch('/api/weekly-picks?top=6');
            const picks = await res.json();
            if (picks.length === 0) {
                grid.innerHTML = `<div class="empty-state" style="grid-column:1/-1;"><div class="empty-state__icon">⏳</div><div class="empty-state__text">No weekly setups found. Market may not have strong trending stocks right now.</div></div>`;
                return;
            }
            grid.innerHTML = picks.map(p => renderWeeklyCard(p)).join('');
        } catch (e) {
            grid.innerHTML = `<div class="empty-state" style="grid-column:1/-1;"><div class="empty-state__icon">❌</div><div class="empty-state__text">Error scanning. Please try again.</div></div>`;
        } finally {
            btn.disabled = false;
            btn.innerHTML = '📊 Find Weekly Picks';
        }
    }

    function renderGoldenCard(p) {
        const isBuy = p.direction === 'BUY';
        const dirClass = isBuy ? 'buy-tip' : 'sell-tip';
        const dirColor = isBuy ? 'var(--accent-green)' : 'var(--accent-red)';
        return `
            <div class="intraday-tip-card ${dirClass}" onclick="window.dispatchEvent(new CustomEvent('selectStock', {detail: '${p.symbol}'}))" style="cursor:pointer;">
                <div class="tip-card__header">
                    <span class="tip-card__symbol">${p.name}</span>
                    <span class="tip-card__action ${isBuy ? 'buy' : 'sell'}">${p.direction}</span>
                </div>
                <div class="tip-card__price-row">
                    <span class="tip-card__current-price">₹${formatNum(p.price)}</span>
                    <span class="tip-card__confidence" style="color: ${p.confidence >= 85 ? '#FFD700' : dirColor}">${p.confidence}% confidence</span>
                </div>
                <div class="tip-card__levels">
                    <div class="tip-level entry"><div class="tip-level__label">Entry</div><div class="tip-level__value">₹${p.entry}</div></div>
                    <div class="tip-level target"><div class="tip-level__label">Target</div><div class="tip-level__value">₹${p.target}</div></div>
                    <div class="tip-level stoploss"><div class="tip-level__label">Stop Loss</div><div class="tip-level__value">₹${p.stop_loss}</div></div>
                </div>
                <div style="margin: 6px 0 8px;"><span class="tip-card__rr">R:R = 1:${p.risk_reward}</span></div>
                <div style="font-size: 0.72rem; color: var(--text-muted); margin-bottom: 6px;">
                    <b>CPR:</b> TC ₹${p.cpr?.tc || '—'} | Pivot ₹${p.cpr?.pivot || '—'} | BC ₹${p.cpr?.bc || '—'}
                    <span style="margin-left: 6px; color: ${p.cpr?.cpr_type === 'VERY_NARROW' || p.cpr?.cpr_type === 'NARROW' ? '#FFD700' : 'var(--text-muted)'}">[${p.cpr?.cpr_type || ''}]</span>
                </div>
                ${p.analyst ? `<div style="font-size:0.72rem;margin-bottom:4px;"><span style="background:${p.analyst.color};color:#000;padding:2px 6px;border-radius:4px;font-weight:600;">${p.analyst.consensus}</span> <span style="color:var(--text-muted);">${p.analyst.buy}B / ${p.analyst.hold}H / ${p.analyst.sell}S from brokerages</span></div>` : ''}
                ${p.news && p.news.headlines?.length ? `<div style="font-size:0.7rem;margin-bottom:4px;color:${p.news.color};"><b>📰</b> ${p.news.headlines[0].title.substring(0, 80)}${p.news.headlines[0].title.length > 80 ? '...' : ''}</div>` : ''}
                <ul class="tip-card__reasoning">${(p.reasons || []).slice(0, 6).map(r => `<li>${r}</li>`).join('')}</ul>
            </div>
        `;
    }

    function renderWeeklyCard(p) {
        return `
            <div class="intraday-tip-card buy-tip" onclick="window.dispatchEvent(new CustomEvent('selectStock', {detail: '${p.symbol}'}))" style="cursor:pointer;">
                <div class="tip-card__header">
                    <span class="tip-card__symbol">${p.name}</span>
                    <span class="tip-card__action buy">SWING BUY</span>
                </div>
                <div class="tip-card__price-row">
                    <span class="tip-card__current-price">₹${formatNum(p.price)}</span>
                    <span class="tip-card__confidence" style="color: #00E676">${p.confidence}% confidence</span>
                </div>
                <div class="tip-card__levels">
                    <div class="tip-level entry"><div class="tip-level__label">Entry</div><div class="tip-level__value">₹${p.entry}</div></div>
                    <div class="tip-level target"><div class="tip-level__label">Target (+${p.target_pct}%)</div><div class="tip-level__value">₹${p.target}</div></div>
                    <div class="tip-level stoploss"><div class="tip-level__label">Stop Loss</div><div class="tip-level__value">₹${p.stop_loss}</div></div>
                </div>
                <div style="margin: 6px 0;"><span class="tip-card__rr">R:R = 1:${p.risk_reward}</span> &nbsp; <span style="font-size:0.75rem; color:var(--text-muted);">📅 Hold: ${p.holding_period}</span></div>
                <ul class="tip-card__reasoning">${(p.reasons || []).slice(0, 5).map(r => `<li>${r}</li>`).join('')}</ul>
            </div>
        `;
    }

    // ─── Market Pulse ───
    function initMarketPulse() {
        document.getElementById('btnRefreshPulse').addEventListener('click', fetchMarketPulse);
        fetchMarketPulse();
    }

    async function fetchMarketPulse() {
        const card = document.getElementById('marketPulseCard');
        card.style.display = 'block';
        try {
            const res = await fetch('/api/market-pulse');
            const p = await res.json();
            // VIX
            if (p.vix) {
                document.getElementById('pulseVixValue').textContent = p.vix.value;
                document.getElementById('pulseVixValue').style.color = p.vix.color;
                const sign = p.vix.change >= 0 ? '+' : '';
                document.getElementById('pulseVixChange').innerHTML = `<span style="color:${p.vix.change >= 0 ? 'var(--accent-red)' : 'var(--accent-green)'}">${sign}${p.vix.change} (${sign}${p.vix.change_pct}%)</span>`;
                document.getElementById('pulseVixMood').innerHTML = `<span style="color:${p.vix.color}">${p.vix.level}</span> — ${p.vix.mood}`;
            }
            // Nifty
            if (p.nifty) {
                document.getElementById('pulseNiftyValue').textContent = formatNum(p.nifty.value);
                const sign = p.nifty.change >= 0 ? '+' : '';
                document.getElementById('pulseNiftyChange').innerHTML = `<span style="color:${p.nifty.change >= 0 ? 'var(--accent-green)' : 'var(--accent-red)'}">${sign}${p.nifty.change} (${sign}${p.nifty.change_pct}%)</span>`;
                document.getElementById('pulseNiftyTrend').innerHTML = `<span style="color:${p.nifty.color};font-weight:600;">${p.nifty.trend}</span> — ${p.nifty.advice}`;
            }
            // Overall
            document.getElementById('pulseMood').innerHTML = `<span style="color:${p.overall_color}">${p.overall_mood}</span>`;
            document.getElementById('pulseMoodText').innerHTML = `${p.overall_text} <span style="color:var(--text-muted);font-size:0.65rem;">Updated: ${p.timestamp}</span>`;
        } catch (e) {
            console.error('Market pulse error:', e);
        }
    }

    // ─── Paper Trading ───
    let paperRefreshInterval = null;

    function initPaperTrading() {
        document.getElementById('btnStartPaper').addEventListener('click', startPaperTrading);
        document.getElementById('btnRefreshPaper').addEventListener('click', refreshPaperTrades);
        document.getElementById('btnClosePaper').addEventListener('click', closePaperDay);
        // Auto-load existing trades if any
        refreshPaperTrades();
        loadPerformanceStats();
    }

    async function startPaperTrading() {
        const btn = document.getElementById('btnStartPaper');
        const qty = parseInt(document.getElementById('paperQty').value) || 1000;
        const pts = parseFloat(document.getElementById('paperTarget').value) || 2;
        const topN = parseInt(document.getElementById('paperTopN').value) || 5;

        btn.disabled = true;
        btn.innerHTML = '<span class="spinner" style="width:14px;height:14px;border-width:2px;display:inline-block;"></span> Scanning & placing trades...';

        try {
            const res = await fetch('/api/paper-trade/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ quantity: qty, target_points: pts, top_n: topN }),
            });
            const result = await res.json();

            if (result.status === 'started') {
                renderPaperTrades(result.data);
                // Auto-refresh every 60 seconds
                if (paperRefreshInterval) clearInterval(paperRefreshInterval);
                paperRefreshInterval = setInterval(refreshPaperTrades, 60000);
            } else if (result.status === 'already_active') {
                renderPaperTrades(result.data);
            } else {
                document.getElementById('paperTradesBody').innerHTML = '<tr><td colspan="9" style="text-align:center;padding:30px;color:var(--text-muted);">' + result.message + '</td></tr>';
            }
        } catch (e) {
            console.error('Paper trade start error:', e);
        } finally {
            btn.disabled = false;
            btn.innerHTML = '🚀 Start Paper Trading';
        }
    }

    async function refreshPaperTrades() {
        try {
            const res = await fetch('/api/paper-trade/status');
            const data = await res.json();
            if (data && data.trades && data.trades.length > 0) {
                renderPaperTrades(data);
            }
        } catch (e) {
            console.error('Paper trade refresh error:', e);
        }
    }

    async function closePaperDay() {
        if (!confirm('Close all active trades at current price? This will finalize today\'s P&L.')) return;
        try {
            const res = await fetch('/api/paper-trade/close', { method: 'POST' });
            const result = await res.json();
            if (result.data) renderPaperTrades(result.data);
            if (paperRefreshInterval) clearInterval(paperRefreshInterval);
            loadPerformanceStats();
        } catch (e) {
            console.error('Paper trade close error:', e);
        }
    }

    function renderPaperTrades(data) {
        const s = data.summary || {};
        const pnl = s.total_pnl || 0;
        const pnlColor = pnl >= 0 ? 'var(--accent-green)' : 'var(--accent-red)';

        // Summary cards
        document.getElementById('paperTotalPnl').innerHTML = `<span style="color:${pnlColor}">₹${pnl.toLocaleString('en-IN')}</span>`;
        document.getElementById('paperActive').textContent = s.active || 0;
        document.getElementById('paperTargetHit').textContent = s.target_hit || 0;
        document.getElementById('paperSlHit').textContent = s.sl_hit || 0;
        document.getElementById('paperWinRate').textContent = (s.win_rate || 0) + '%';

        // Table
        const tbody = document.getElementById('paperTradesBody');
        if (!data.trades || data.trades.length === 0) {
            tbody.innerHTML = '<tr><td colspan="9" style="text-align:center;padding:30px;color:var(--text-muted);">No trades yet</td></tr>';
            return;
        }

        tbody.innerHTML = data.trades.map(t => {
            const tPnl = t.pnl || 0;
            const tColor = tPnl >= 0 ? 'var(--accent-green)' : 'var(--accent-red)';
            const dirColor = t.direction === 'BUY' ? 'var(--accent-green)' : 'var(--accent-red)';
            let statusBadge = '';
            if (t.status === 'TARGET_HIT') statusBadge = '<span style="background:#00E676;color:#000;padding:2px 8px;border-radius:4px;font-weight:600;font-size:0.7rem;">🎯 HIT</span>';
            else if (t.status === 'SL_HIT') statusBadge = '<span style="background:#FF1744;color:#fff;padding:2px 8px;border-radius:4px;font-weight:600;font-size:0.7rem;">🛑 SL</span>';
            else if (t.status === 'CLOSED') statusBadge = '<span style="background:#FFD740;color:#000;padding:2px 8px;border-radius:4px;font-weight:600;font-size:0.7rem;">⏹ CLOSED</span>';
            else statusBadge = '<span style="background:var(--accent-blue);color:#fff;padding:2px 8px;border-radius:4px;font-weight:600;font-size:0.7rem;">⚡ LIVE</span>';

            return `<tr style="border-bottom:1px solid var(--border);">
                <td style="padding:10px 12px;font-weight:600;">${t.name}</td>
                <td style="padding:10px 8px;color:${dirColor};font-weight:600;">${t.direction}</td>
                <td style="padding:10px 8px;font-family:var(--font-mono);">₹${t.entry_price}</td>
                <td style="padding:10px 8px;font-family:var(--font-mono);color:var(--accent-green);">₹${t.target_price}</td>
                <td style="padding:10px 8px;font-family:var(--font-mono);color:var(--accent-red);">₹${t.stop_loss}</td>
                <td style="padding:10px 8px;font-family:var(--font-mono);font-weight:600;">₹${t.current_price}</td>
                <td style="padding:10px 8px;">${t.quantity}</td>
                <td style="padding:10px 8px;font-family:var(--font-mono);font-weight:700;color:${tColor};">${tPnl >= 0 ? '+' : ''}₹${tPnl.toLocaleString('en-IN')}</td>
                <td style="padding:10px 8px;">${statusBadge}</td>
            </tr>`;
        }).join('');
    }

    async function loadPerformanceStats() {
        try {
            const res = await fetch('/api/paper-trade/performance');
            const stats = await res.json();
            const el = document.getElementById('paperPerformance');

            if (!stats || stats.total_days === 0) {
                el.innerHTML = '<div style="color:var(--text-muted);text-align:center;padding:20px;">No trading history yet. Start paper trading and close the day to see performance.</div>';
                return;
            }

            const pnlColor = stats.total_pnl >= 0 ? 'var(--accent-green)' : 'var(--accent-red)';
            el.innerHTML = `
                <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px;">
                    <div style="background:var(--bg-primary);padding:12px;border-radius:var(--radius-sm);text-align:center;">
                        <div style="font-size:0.68rem;color:var(--text-muted);">Total Days</div>
                        <div style="font-size:1.2rem;font-weight:700;">${stats.total_days}</div>
                    </div>
                    <div style="background:var(--bg-primary);padding:12px;border-radius:var(--radius-sm);text-align:center;">
                        <div style="font-size:0.68rem;color:var(--text-muted);">Total P&L</div>
                        <div style="font-size:1.2rem;font-weight:700;color:${pnlColor};">₹${stats.total_pnl?.toLocaleString('en-IN')}</div>
                    </div>
                    <div style="background:var(--bg-primary);padding:12px;border-radius:var(--radius-sm);text-align:center;">
                        <div style="font-size:0.68rem;color:var(--text-muted);">Avg Daily P&L</div>
                        <div style="font-size:1.2rem;font-weight:700;">₹${stats.avg_daily_pnl?.toLocaleString('en-IN')}</div>
                    </div>
                    <div style="background:var(--bg-primary);padding:12px;border-radius:var(--radius-sm);text-align:center;">
                        <div style="font-size:0.68rem;color:var(--text-muted);">Win Rate</div>
                        <div style="font-size:1.2rem;font-weight:700;color:${stats.win_rate > 50 ? 'var(--accent-green)' : 'var(--accent-red)'}">${stats.win_rate}%</div>
                    </div>
                    <div style="background:var(--bg-primary);padding:12px;border-radius:var(--radius-sm);text-align:center;">
                        <div style="font-size:0.68rem;color:var(--text-muted);">Day Win Rate</div>
                        <div style="font-size:1.2rem;font-weight:700;">${stats.day_win_rate}%</div>
                        <div style="font-size:0.65rem;color:var(--text-muted);">${stats.winning_days}W / ${stats.losing_days}L</div>
                    </div>
                    <div style="background:var(--bg-primary);padding:12px;border-radius:var(--radius-sm);text-align:center;">
                        <div style="font-size:0.68rem;color:var(--text-muted);">Target Hit %</div>
                        <div style="font-size:1.2rem;font-weight:700;">${stats.target_hit_rate}%</div>
                    </div>
                    <div style="background:var(--bg-primary);padding:12px;border-radius:var(--radius-sm);text-align:center;">
                        <div style="font-size:0.68rem;color:var(--text-muted);">Best Day</div>
                        <div style="font-size:1.2rem;font-weight:700;color:var(--accent-green);">₹${stats.best_day?.toLocaleString('en-IN')}</div>
                    </div>
                    <div style="background:var(--bg-primary);padding:12px;border-radius:var(--radius-sm);text-align:center;">
                        <div style="font-size:0.68rem;color:var(--text-muted);">Worst Day</div>
                        <div style="font-size:1.2rem;font-weight:700;color:var(--accent-red);">₹${stats.worst_day?.toLocaleString('en-IN')}</div>
                    </div>
                </div>
            `;
        } catch (e) {
            console.error('Performance stats error:', e);
        }
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
