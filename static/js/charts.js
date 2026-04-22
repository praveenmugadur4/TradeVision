/**
 * TradeVision — Chart Module
 * TradingView Lightweight Charts integration for candlestick & indicator rendering
 */

const ChartModule = (() => {
    let mainChart = null;
    let candleSeries = null;
    let volumeSeries = null;
    let rsiChart = null;
    let rsiSeries = null;
    let macdChart = null;
    let macdLineSeries = null;
    let macdSignalSeries = null;
    let macdHistSeries = null;
    let equityChart = null;
    let equitySeries = null;

    // Overlay line series references
    const overlaySeries = {};

    const CHART_COLORS = {
        bg: '#0a0e17',
        gridLines: 'rgba(255, 255, 255, 0.03)',
        textColor: '#5a6a80',
        crosshair: '#448aff',
        upColor: '#00e676',
        downColor: '#ff1744',
        wickUp: '#00e676',
        wickDown: '#ff1744',
        volumeUp: 'rgba(0, 230, 118, 0.15)',
        volumeDown: 'rgba(255, 23, 68, 0.15)',
    };

    const INDICATOR_COLORS = {
        EMA_9: '#00d4ff',
        EMA_21: '#b388ff',
        EMA_50: '#ffab00',
        SMA_200: '#ff6b6b',
        BB_Upper: 'rgba(0, 212, 255, 0.4)',
        BB_Mid: 'rgba(0, 212, 255, 0.2)',
        BB_Lower: 'rgba(0, 212, 255, 0.4)',
        Supertrend: '#ff9100',
    };

    function getChartOptions(container) {
        return {
            width: container.clientWidth,
            height: container.clientHeight,
            layout: {
                background: { type: 'solid', color: CHART_COLORS.bg },
                textColor: CHART_COLORS.textColor,
                fontFamily: "'Inter', sans-serif",
                fontSize: 11,
            },
            grid: {
                vertLines: { color: CHART_COLORS.gridLines },
                horzLines: { color: CHART_COLORS.gridLines },
            },
            crosshair: {
                mode: LightweightCharts.CrosshairMode.Normal,
                vertLine: {
                    color: CHART_COLORS.crosshair,
                    width: 1,
                    style: 2,
                    labelBackgroundColor: '#1a2235',
                },
                horzLine: {
                    color: CHART_COLORS.crosshair,
                    width: 1,
                    style: 2,
                    labelBackgroundColor: '#1a2235',
                },
            },
            timeScale: {
                borderColor: 'rgba(255, 255, 255, 0.06)',
                timeVisible: false,
            },
            rightPriceScale: {
                borderColor: 'rgba(255, 255, 255, 0.06)',
            },
        };
    }

    function initMainChart(containerId) {
        const container = document.getElementById(containerId);
        if (!container) return;

        if (mainChart) {
            mainChart.remove();
            mainChart = null;
        }

        // Clear overlay references
        Object.keys(overlaySeries).forEach(k => delete overlaySeries[k]);

        mainChart = LightweightCharts.createChart(container, getChartOptions(container));

        // Candlestick series
        candleSeries = mainChart.addCandlestickSeries({
            upColor: CHART_COLORS.upColor,
            downColor: CHART_COLORS.downColor,
            wickUpColor: CHART_COLORS.wickUp,
            wickDownColor: CHART_COLORS.wickDown,
            borderVisible: false,
        });

        // Volume series
        volumeSeries = mainChart.addHistogramSeries({
            priceFormat: { type: 'volume' },
            priceScaleId: 'volume',
        });

        mainChart.priceScale('volume').applyOptions({
            scaleMargins: { top: 0.85, bottom: 0 },
        });

        // Handle resize
        const resizeObserver = new ResizeObserver(entries => {
            for (const entry of entries) {
                mainChart.applyOptions({
                    width: entry.contentRect.width,
                    height: entry.contentRect.height,
                });
            }
        });
        resizeObserver.observe(container);
    }

    function setMainChartData(candleData, volumeData) {
        if (!candleSeries || !volumeSeries) return;
        candleSeries.setData(candleData);
        volumeSeries.setData(volumeData);
        mainChart.timeScale().fitContent();
    }

    function addOverlayIndicator(name, data, color) {
        if (!mainChart || !data || data.length === 0) return;

        // Remove existing if any
        if (overlaySeries[name]) {
            mainChart.removeSeries(overlaySeries[name]);
            delete overlaySeries[name];
        }

        const series = mainChart.addLineSeries({
            color: color || INDICATOR_COLORS[name] || '#888',
            lineWidth: 1,
            priceLineVisible: false,
            lastValueVisible: false,
            crosshairMarkerVisible: false,
        });

        series.setData(data);
        overlaySeries[name] = series;
    }

    function removeOverlayIndicator(name) {
        if (overlaySeries[name] && mainChart) {
            mainChart.removeSeries(overlaySeries[name]);
            delete overlaySeries[name];
        }
    }

    function addBollingerBands(upperData, midData, lowerData) {
        addOverlayIndicator('BB_Upper', upperData, INDICATOR_COLORS.BB_Upper);
        addOverlayIndicator('BB_Mid', midData, INDICATOR_COLORS.BB_Mid);
        addOverlayIndicator('BB_Lower', lowerData, INDICATOR_COLORS.BB_Lower);
    }

    function removeBollingerBands() {
        removeOverlayIndicator('BB_Upper');
        removeOverlayIndicator('BB_Mid');
        removeOverlayIndicator('BB_Lower');
    }

    // ─── RSI Chart ───
    function initRsiChart(containerId) {
        const container = document.getElementById(containerId);
        if (!container) return;

        if (rsiChart) {
            rsiChart.remove();
            rsiChart = null;
        }

        const opts = getChartOptions(container);
        opts.height = container.clientHeight || 150;

        rsiChart = LightweightCharts.createChart(container, opts);

        rsiSeries = rsiChart.addLineSeries({
            color: '#b388ff',
            lineWidth: 2,
            priceLineVisible: false,
        });

        // Add overbought/oversold levels
        // We'll just draw them as price lines on the series after data is set

        const resizeObserver = new ResizeObserver(entries => {
            for (const entry of entries) {
                rsiChart.applyOptions({ width: entry.contentRect.width });
            }
        });
        resizeObserver.observe(container);
    }

    function setRsiData(data) {
        if (!rsiSeries) return;
        rsiSeries.setData(data);

        // Overbought / Oversold lines
        rsiSeries.createPriceLine({ price: 70, color: 'rgba(255, 23, 68, 0.5)', lineWidth: 1, lineStyle: 2, axisLabelVisible: true, title: 'OB' });
        rsiSeries.createPriceLine({ price: 30, color: 'rgba(0, 230, 118, 0.5)', lineWidth: 1, lineStyle: 2, axisLabelVisible: true, title: 'OS' });

        rsiChart.timeScale().fitContent();
    }

    // ─── MACD Chart ───
    function initMacdChart(containerId) {
        const container = document.getElementById(containerId);
        if (!container) return;

        if (macdChart) {
            macdChart.remove();
            macdChart = null;
        }

        const opts = getChartOptions(container);
        opts.height = container.clientHeight || 150;

        macdChart = LightweightCharts.createChart(container, opts);

        macdLineSeries = macdChart.addLineSeries({
            color: '#00d4ff',
            lineWidth: 2,
            priceLineVisible: false,
            lastValueVisible: false,
        });

        macdSignalSeries = macdChart.addLineSeries({
            color: '#ff6b6b',
            lineWidth: 1,
            priceLineVisible: false,
            lastValueVisible: false,
        });

        macdHistSeries = macdChart.addHistogramSeries({
            priceLineVisible: false,
            lastValueVisible: false,
        });

        const resizeObserver = new ResizeObserver(entries => {
            for (const entry of entries) {
                macdChart.applyOptions({ width: entry.contentRect.width });
            }
        });
        resizeObserver.observe(container);
    }

    function setMacdData(macdData, signalData, histData) {
        if (macdLineSeries && macdData) macdLineSeries.setData(macdData);
        if (macdSignalSeries && signalData) macdSignalSeries.setData(signalData);
        if (macdHistSeries && histData) {
            // Color histogram bars
            const colored = histData.map(d => ({
                ...d,
                color: d.value >= 0 ? 'rgba(0, 230, 118, 0.6)' : 'rgba(255, 23, 68, 0.6)',
            }));
            macdHistSeries.setData(colored);
        }
        if (macdChart) macdChart.timeScale().fitContent();
    }

    // ─── Equity Curve Chart ─── 
    function initEquityChart(containerId) {
        const container = document.getElementById(containerId);
        if (!container) return;

        if (equityChart) {
            equityChart.remove();
            equityChart = null;
        }

        const opts = getChartOptions(container);
        opts.height = container.clientHeight || 300;

        equityChart = LightweightCharts.createChart(container, opts);

        equitySeries = equityChart.addAreaSeries({
            lineColor: '#00d4ff',
            topColor: 'rgba(0, 212, 255, 0.3)',
            bottomColor: 'rgba(0, 212, 255, 0.02)',
            lineWidth: 2,
            priceLineVisible: false,
        });

        const resizeObserver = new ResizeObserver(entries => {
            for (const entry of entries) {
                equityChart.applyOptions({ width: entry.contentRect.width });
            }
        });
        resizeObserver.observe(container);
    }

    function setEquityData(data) {
        if (!equitySeries) return;
        equitySeries.setData(data);
        equityChart.timeScale().fitContent();
    }

    return {
        initMainChart,
        setMainChartData,
        addOverlayIndicator,
        removeOverlayIndicator,
        addBollingerBands,
        removeBollingerBands,
        initRsiChart,
        setRsiData,
        initMacdChart,
        setMacdData,
        initEquityChart,
        setEquityData,
        INDICATOR_COLORS,
    };
})();
