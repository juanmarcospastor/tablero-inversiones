const bitcoinChartRoot = document.querySelector("[data-bitcoin-chart]");

if (bitcoinChartRoot) {
    const btcCanvas = document.getElementById("btcRealtimeChart");
    const btcStatus = bitcoinChartRoot.querySelector("[data-btc-status]");
    const btcPrice = bitcoinChartRoot.querySelector("[data-btc-price]");
    const btcUpdated = bitcoinChartRoot.querySelector("[data-btc-updated]");
    const btcRangeButtons = bitcoinChartRoot.querySelectorAll("[data-btc-range]");
    const arsFormatter = new Intl.NumberFormat("es-AR", {
        style: "currency",
        currency: "ARS",
        maximumFractionDigits: 0,
    });

    let btcChart;
    let currentBtcRange = "1";

    const rangeLabels = {
        1: "1 dia",
        30: "1 mes",
        365: "1 anio",
        max: "todo el historial",
    };

    function formatBtcDate(timestamp, range) {
        const options = range === "1"
            ? { hour: "2-digit", minute: "2-digit" }
            : { day: "2-digit", month: "short", year: range === "365" || range === "max" ? "2-digit" : undefined };

        return new Intl.DateTimeFormat("es-AR", options).format(new Date(timestamp));
    }

    function setBtcLoading(range) {
        btcStatus.textContent = `Cargando ${rangeLabels[range]} desde CoinGecko...`;
        btcRangeButtons.forEach((button) => {
            button.disabled = true;
            button.classList.toggle("active", button.dataset.btcRange === range);
        });
    }

    function setBtcReady() {
        btcRangeButtons.forEach((button) => {
            button.disabled = false;
        });
    }

    async function loadBitcoinChart(range) {
        currentBtcRange = range;
        setBtcLoading(range);

        try {
            const url = new URL("https://api.coingecko.com/api/v3/coins/bitcoin/market_chart");
            url.searchParams.set("vs_currency", "ars");
            url.searchParams.set("days", range);
            url.searchParams.set("precision", "2");

            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`CoinGecko respondio ${response.status}`);
            }

            const data = await response.json();
            const prices = Array.isArray(data.prices) ? data.prices : [];

            if (!prices.length) {
                throw new Error("La API no devolvio precios.");
            }

            const labels = prices.map(([timestamp]) => formatBtcDate(timestamp, range));
            const values = prices.map(([, price]) => price);
            const latest = prices[prices.length - 1];
            const latestDate = new Date(latest[0]);

            btcPrice.textContent = arsFormatter.format(latest[1]);
            btcUpdated.textContent = latestDate.toLocaleString("es-AR", {
                day: "2-digit",
                month: "2-digit",
                hour: "2-digit",
                minute: "2-digit",
            });

            if (btcChart) {
                btcChart.data.labels = labels;
                btcChart.data.datasets[0].data = values;
                btcChart.update();
            } else {
                btcChart = new Chart(btcCanvas, {
                    type: "line",
                    data: {
                        labels,
                        datasets: [{
                            label: "BTC/ARS",
                            data: values,
                            borderColor: "#f7931a",
                            backgroundColor: "rgba(247, 147, 26, 0.12)",
                            pointRadius: 0,
                            borderWidth: 2,
                            tension: 0.25,
                            fill: true,
                        }],
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        interaction: {
                            mode: "index",
                            intersect: false,
                        },
                        plugins: {
                            legend: { display: false },
                            tooltip: {
                                callbacks: {
                                    label: (context) => arsFormatter.format(context.parsed.y),
                                },
                            },
                        },
                        scales: {
                            x: {
                                ticks: { maxTicksLimit: 5 },
                                grid: { display: false },
                            },
                            y: {
                                ticks: {
                                    maxTicksLimit: 5,
                                    callback: (value) => arsFormatter.format(value),
                                },
                            },
                        },
                    },
                });
            }

            btcStatus.textContent = `BTC/ARS actualizado desde CoinGecko (${rangeLabels[range]}).`;
        } catch (error) {
            btcStatus.textContent = `No se pudo cargar Bitcoin realtime: ${error.message}`;
        } finally {
            setBtcReady();
        }
    }

    btcRangeButtons.forEach((button) => {
        button.addEventListener("click", () => {
            const range = button.dataset.btcRange;
            if (range !== currentBtcRange) {
                loadBitcoinChart(range);
            }
        });
    });

    loadBitcoinChart(currentBtcRange);
}

const stockChartRoot = document.querySelector("[data-stock-chart]");

if (stockChartRoot) {
    const stockCanvas = document.getElementById("nvdaRealtimeChart");
    const stockStatus = stockChartRoot.querySelector("[data-stock-status]");
    const stockPrice = stockChartRoot.querySelector("[data-stock-price]");
    const stockUpdated = stockChartRoot.querySelector("[data-stock-updated]");
    const stockRangeButtons = stockChartRoot.querySelectorAll("[data-stock-range]");
    const arsFormatter = new Intl.NumberFormat("es-AR", {
        style: "currency",
        currency: "ARS",
        maximumFractionDigits: 0,
    });

    let stockChart;
    let currentStockRange = "1";

    const stockRangeLabels = {
        1: "1 dia",
        30: "1 mes",
        365: "1 anio",
        max: "todo el historial",
    };

    function formatStockDate(timestamp, range) {
        const options = range === "1"
            ? { hour: "2-digit", minute: "2-digit" }
            : { day: "2-digit", month: "short", year: range === "365" || range === "max" ? "2-digit" : undefined };

        return new Intl.DateTimeFormat("es-AR", options).format(new Date(timestamp));
    }

    function setStockLoading(range) {
        stockStatus.textContent = `Cargando ${stockRangeLabels[range]} desde Yahoo Finance...`;
        stockRangeButtons.forEach((button) => {
            button.disabled = true;
            button.classList.toggle("active", button.dataset.stockRange === range);
        });
    }

    function setStockReady() {
        stockRangeButtons.forEach((button) => {
            button.disabled = false;
        });
    }

    async function loadStockChart(range) {
        currentStockRange = range;
        setStockLoading(range);

        try {
            const url = new URL("/api/nvda/chart", window.location.origin);
            url.searchParams.set("range", range);

            const response = await fetch(url);
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.error || `API local respondio ${response.status}`);
            }

            const prices = Array.isArray(data.prices) ? data.prices : [];
            if (!prices.length) {
                throw new Error("La API local no devolvio precios.");
            }

            const labels = prices.map(([timestamp]) => formatStockDate(timestamp, range));
            const values = prices.map(([, price]) => price);
            const latest = prices[prices.length - 1];
            const latestDate = new Date(latest[0]);

            stockPrice.textContent = arsFormatter.format(latest[1]);
            stockUpdated.textContent = latestDate.toLocaleString("es-AR", {
                day: "2-digit",
                month: "2-digit",
                hour: "2-digit",
                minute: "2-digit",
            });

            if (stockChart) {
                stockChart.data.labels = labels;
                stockChart.data.datasets[0].data = values;
                stockChart.update();
            } else {
                stockChart = new Chart(stockCanvas, {
                    type: "line",
                    data: {
                        labels,
                        datasets: [{
                            label: "NVDA/ARS",
                            data: values,
                            borderColor: "#4f46e5",
                            backgroundColor: "rgba(79, 70, 229, 0.12)",
                            pointRadius: 0,
                            borderWidth: 2,
                            tension: 0.25,
                            fill: true,
                        }],
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        interaction: {
                            mode: "index",
                            intersect: false,
                        },
                        plugins: {
                            legend: { display: false },
                            tooltip: {
                                callbacks: {
                                    label: (context) => arsFormatter.format(context.parsed.y),
                                },
                            },
                        },
                        scales: {
                            x: {
                                ticks: { maxTicksLimit: 5 },
                                grid: { display: false },
                            },
                            y: {
                                ticks: {
                                    maxTicksLimit: 5,
                                    callback: (value) => arsFormatter.format(value),
                                },
                            },
                        },
                    },
                });
            }

            stockStatus.textContent = `NVDA/ARS actualizado desde Yahoo Finance (${stockRangeLabels[range]}).`;
        } catch (error) {
            stockStatus.textContent = `No se pudo cargar NVIDIA CEDEAR realtime: ${error.message}`;
        } finally {
            setStockReady();
        }
    }

    stockRangeButtons.forEach((button) => {
        button.addEventListener("click", () => {
            const range = button.dataset.stockRange;
            if (range !== currentStockRange) {
                loadStockChart(range);
            }
        });
    });

    loadStockChart(currentStockRange);
}
