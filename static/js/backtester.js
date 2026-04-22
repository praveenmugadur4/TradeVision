/**
 * TradeVision — Backtester UI Module
 * Handles backtest form, results display, equity curve, and trade log
 */

const BacktesterModule = (() => {
    let selectedPeriod = '2y';

    function init() {
        // Period selector buttons
        const periodBtns = document.querySelectorAll('#btPeriodSelector .period-btn');
        periodBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                periodBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                selectedPeriod = btn.dataset.period;
            });
        });

        // Form submit
        const form = document.getElementById('backtestForm');
        if (form) {
            form.addEventListener('submit', (e) => {
                e.preventDefault();
                runBacktest();
            });
        }
    }

    async function runBacktest() {
        const symbol = document.getElementById('btSymbol').value.trim();
        const capital = parseFloat(document.getElementById('btCapital').value);
        const stopLoss = parseFloat(document.getElementById('btStopLoss').value);
        const takeProfit = parseFloat(document.getElementById('btTakeProfit').value);
        const positionSize = parseFloat(document.getElementById('btPositionSize').value);

        if (!symbol) {
            showToast('Please enter a stock symbol', 'info');
            return;
        }

        const btn = document.getElementById('btnRunBacktest');
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner" style="width:18px;height:18px;border-width:2px;"></span> Running...';

        try {
            const response = await fetch('/api/backtest', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    symbol,
                    period: selectedPeriod,
                    initial_capital: capital,
                    stop_loss: stopLoss,
                    take_profit: takeProfit,
                    position_size: positionSize,
                    strategy: document.getElementById('btStrategy')?.value || 'confluence',
                }),
            });

            const result = await response.json();

            if (result.error) {
                showToast(result.error, 'sell');
                return;
            }

            displayResults(result);
            showToast('Backtest completed successfully!', 'buy');

        } catch (e) {
            console.error('Backtest error:', e);
            showToast('Failed to run backtest. Check console for details.', 'sell');
        } finally {
            btn.disabled = false;
            btn.innerHTML = '⚡ Run Backtest';
        }
    }

    function displayResults(result) {
        const emptyState = document.getElementById('btEmptyState');
        const statsSection = document.getElementById('btStatsSection');

        if (emptyState) emptyState.style.display = 'none';
        if (statsSection) statsSection.style.display = 'block';

        // ─── Stats Grid ───
        const s = result.summary;
        const statsGrid = document.getElementById('btStatsGrid');
        if (statsGrid) {
            const isPositive = s.total_return_pct >= 0;
            statsGrid.innerHTML = `
                <div class="stat-card" style="grid-column: 1 / -1;">
                    <div class="stat-card__label">Strategy</div>
                    <div class="stat-card__value" style="color: var(--accent-cyan); font-size: 1rem;">${s.strategy || 'Confluence'}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-card__label">Total Return</div>
                    <div class="stat-card__value ${isPositive ? 'positive' : 'negative'}">
                        ${isPositive ? '+' : ''}${s.total_return_pct}%
                    </div>
                </div>
                <div class="stat-card">
                    <div class="stat-card__label">P&L (₹)</div>
                    <div class="stat-card__value ${isPositive ? 'positive' : 'negative'}">
                        ${isPositive ? '+' : ''}₹${formatNumber(s.total_return_inr)}
                    </div>
                </div>
                <div class="stat-card">
                    <div class="stat-card__label">Final Value</div>
                    <div class="stat-card__value">₹${formatNumber(s.final_value)}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-card__label">Win Rate</div>
                    <div class="stat-card__value ${s.win_rate >= 50 ? 'positive' : 'negative'}">${s.win_rate}%</div>
                </div>
                <div class="stat-card">
                    <div class="stat-card__label">Total Trades</div>
                    <div class="stat-card__value">${s.total_trades}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-card__label">Profit Factor</div>
                    <div class="stat-card__value">${s.profit_factor}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-card__label">Max Drawdown</div>
                    <div class="stat-card__value negative">-${s.max_drawdown}%</div>
                </div>
                <div class="stat-card">
                    <div class="stat-card__label">Sharpe Ratio</div>
                    <div class="stat-card__value ${s.sharpe_ratio >= 1 ? 'positive' : ''}">${s.sharpe_ratio}</div>
                </div>
            `;
        }

        // ─── Equity Curve ───
        if (result.equity_curve && result.equity_curve.length > 0) {
            ChartModule.initEquityChart('equityChart');
            ChartModule.setEquityData(result.equity_curve);
        }

        // ─── Trade Log ───
        const tradeLogBody = document.getElementById('tradeLogBody');
        if (tradeLogBody && result.trades) {
            tradeLogBody.innerHTML = result.trades.map((t, i) => {
                const isProfit = t.pnl > 0;
                return `
                    <tr>
                        <td>${i + 1}</td>
                        <td>${t.entry_date}</td>
                        <td>${t.exit_date}</td>
                        <td>₹${t.entry_price}</td>
                        <td>₹${t.exit_price}</td>
                        <td>${t.qty}</td>
                        <td class="${isProfit ? 'pnl-positive' : 'pnl-negative'}">
                            ${isProfit ? '+' : ''}₹${t.pnl}
                        </td>
                        <td class="${isProfit ? 'pnl-positive' : 'pnl-negative'}">
                            ${isProfit ? '+' : ''}${t.pnl_pct}%
                        </td>
                        <td>${t.exit_reason}</td>
                    </tr>
                `;
            }).join('');
        }
    }

    function formatNumber(num) {
        if (num === undefined || num === null) return '—';
        return Number(num).toLocaleString('en-IN', { maximumFractionDigits: 2 });
    }

    return {
        init,
        runBacktest,
    };
})();
