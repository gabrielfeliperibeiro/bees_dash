// Configuration
const CONFIG = {
    dataFiles: {
        ph: 'data/ph.json',
        vn: 'data/vn.json'
    },
    refreshInterval: 5 * 60 * 1000, // 5 minutes
    retryAttempts: 3,
    retryDelays: [0, 10000, 20000], // 0s, 10s, 20s (total 30s window)
    staleThresholds: {
        warning: 10 * 60 * 1000, // 10 minutes
        error: 30 * 60 * 1000 // 30 minutes
    }
};

// Global state
let dashboardData = {
    ph: null,
    vn: null
};

let charts = {
    ph: { gmv: null, orders: null },
    vn: { gmv: null, orders: null }
};

/**
 * Fetch data with retry logic (3 attempts within 30 seconds)
 */
async function fetchWithRetry(url, attemptNumber = 0) {
    try {
        if (attemptNumber > 0) {
            await new Promise(resolve => setTimeout(resolve, CONFIG.retryDelays[attemptNumber]));
        }

        console.log(`Fetching ${url} (attempt ${attemptNumber + 1}/${CONFIG.retryAttempts})`);

        const response = await fetch(url + '?t=' + Date.now()); // Cache busting

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        console.log(`Successfully fetched ${url}`);
        return data;

    } catch (error) {
        console.error(`Fetch attempt ${attemptNumber + 1} failed for ${url}:`, error);

        if (attemptNumber < CONFIG.retryAttempts - 1) {
            return fetchWithRetry(url, attemptNumber + 1);
        } else {
            throw new Error(`Failed to fetch ${url} after ${CONFIG.retryAttempts} attempts`);
        }
    }
}

/**
 * Load data for both countries
 */
async function loadDashboardData() {
    try {
        console.log('Loading dashboard data...');

        // Fetch both countries in parallel
        const [phData, vnData] = await Promise.all([
            fetchWithRetry(CONFIG.dataFiles.ph),
            fetchWithRetry(CONFIG.dataFiles.vn)
        ]);

        dashboardData.ph = phData;
        dashboardData.vn = vnData;

        console.log('Dashboard data loaded successfully');

        // Update UI
        updateDashboard();
        updateStatusIndicator();

    } catch (error) {
        console.error('Failed to load dashboard data:', error);
        showError('Unable to load dashboard data. Please try again.');
    }
}

/**
 * Update status indicator based on data freshness
 */
function updateStatusIndicator() {
    const statusIndicator = document.getElementById('statusIndicator');
    const lastUpdatedEl = document.getElementById('lastUpdated');

    // Use PH data timestamp (both should be the same)
    const lastUpdated = dashboardData.ph?.last_updated;

    if (!lastUpdated) {
        lastUpdatedEl.textContent = 'No data';
        return;
    }

    const lastUpdateTime = new Date(lastUpdated);
    const now = new Date();
    const timeDiff = now - lastUpdateTime;

    // Update last updated text
    lastUpdatedEl.textContent = `Updated ${formatTimeAgo(lastUpdateTime)}`;

    // Update status indicator
    const statusDot = statusIndicator.querySelector('.status-dot');
    const statusText = statusIndicator.querySelector('.status-text');

    if (timeDiff < CONFIG.staleThresholds.warning) {
        // Green - Fresh data
        statusIndicator.style.background = 'rgba(16, 185, 129, 0.1)';
        statusDot.style.background = '#10b981';
        statusText.style.color = '#10b981';
        statusText.textContent = 'Live';
    } else if (timeDiff < CONFIG.staleThresholds.error) {
        // Yellow - Slightly stale
        statusIndicator.style.background = 'rgba(245, 158, 11, 0.1)';
        statusDot.style.background = '#f59e0b';
        statusText.style.color = '#f59e0b';
        statusText.textContent = 'Delayed';
    } else {
        // Red - Very stale
        statusIndicator.style.background = 'rgba(239, 68, 68, 0.1)';
        statusDot.style.background = '#ef4444';
        statusText.style.color = '#ef4444';
        statusText.textContent = 'Stale';
    }
}

/**
 * Format time difference in human-readable format
 */
function formatTimeAgo(date) {
    const seconds = Math.floor((new Date() - date) / 1000);

    if (seconds < 60) return 'just now';
    if (seconds < 120) return '1 min ago';
    if (seconds < 3600) return `${Math.floor(seconds / 60)} mins ago`;
    if (seconds < 7200) return '1 hour ago';
    if (seconds < 86400) return `${Math.floor(seconds / 3600)} hours ago`;

    return date.toLocaleString();
}

/**
 * Show error message
 */
function showError(message) {
    console.error(message);
    // TODO: Add visual error display
    alert(message);
}

/**
 * Format number with commas
 */
function formatNumber(num, decimals = 0) {
    if (num === null || num === undefined) return '-';
    return num.toLocaleString('en-US', {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals
    });
}

/**
 * Calculate percentage change
 */
function calculateChange(current, previous) {
    if (!previous || previous === 0) return 0;
    return ((current - previous) / previous) * 100;
}

/**
 * Format percentage change with sign
 */
function formatChangePercent(change) {
    const sign = change > 0 ? '+' : '';
    return `${sign}${change.toFixed(1)}%`;
}

/**
 * Get change class (positive/negative/neutral)
 */
function getChangeClass(change) {
    if (change > 0) return 'positive';
    if (change < 0) return 'negative';
    return 'neutral';
}

/**
 * Update dashboard for both countries
 */
function updateDashboard() {
    console.log('Updating dashboard...');
    updateCountryDashboard('ph', dashboardData.ph);
    updateCountryDashboard('vn', dashboardData.vn);
}

/**
 * Update dashboard for a country
 */
function updateCountryDashboard(country, data) {
    if (!data) {
        console.warn(`No data for ${country}`);
        return;
    }

    updateMetricCards(country, data);
    updateComparisonTable(country, data);
    updateCharts(country, data);
}

/**
 * Update metric cards
 */
function updateMetricCards(country, data) {
    const today = data.today;
    const lastWeek = data.same_day_last_week;

    // Helper to update a metric card
    const updateCard = (metric, value, decimals = 0) => {
        const valueEl = document.getElementById(`${country}-${metric}`);
        const changeEl = document.getElementById(`${country}-${metric}-change`);

        if (!valueEl || !changeEl) return;

        // Update value
        valueEl.textContent = formatNumber(today[value], decimals);

        // Calculate and update change
        const change = calculateChange(today[value], lastWeek[value]);
        changeEl.textContent = formatChangePercent(change);
        changeEl.className = 'metric-change ' + getChangeClass(change);
    };

    // Update hero metrics
    updateCard('gmv', 'total_gmv', 2);
    updateCard('orders', 'orders', 0);
    updateCard('aov', 'aov', 2);

    // Update secondary metrics
    updateCard('buyers', 'unique_buyers', 0);
    updateCard('frequency', 'frequency', 2);
    updateCard('gmv-poc', 'gmv_per_poc', 2);
}

/**
 * Update comparison table
 */
function updateComparisonTable(country, data) {
    const tableId = `${country}-comparison-table`;
    const tbody = document.querySelector(`#${tableId} tbody`);

    if (!tbody) return;

    const today = data.today;
    const lastWeek = data.same_day_last_week;
    const mtd = data.mtd;

    const metrics = [
        { label: 'GMV', key: 'total_gmv', decimals: 2 },
        { label: 'Orders', key: 'orders', decimals: 0 },
        { label: 'Buyers', key: 'unique_buyers', decimals: 0 },
        { label: 'AOV', key: 'aov', decimals: 2 },
        { label: 'Frequency', key: 'frequency', decimals: 2 },
        { label: 'GMV/POCs', key: 'gmv_per_poc', decimals: 2 }
    ];

    tbody.innerHTML = metrics.map(metric => {
        const todayValue = today[metric.key];
        const lastWeekValue = lastWeek[metric.key];
        const mtdValue = mtd[metric.key];
        const change = calculateChange(todayValue, lastWeekValue);

        return `
            <tr>
                <td><strong>${metric.label}</strong></td>
                <td>${formatNumber(todayValue, metric.decimals)}</td>
                <td>${formatNumber(lastWeekValue, metric.decimals)}</td>
                <td class="change-cell ${getChangeClass(change)}">${formatChangePercent(change)}</td>
                <td>${formatNumber(mtdValue, metric.decimals)}</td>
            </tr>
        `;
    }).join('');
}

/**
 * Update charts
 */
function updateCharts(country, data) {
    const dailyHistory = data.daily_history || [];
    const movingAverages = data.moving_averages || {};

    // Prepare data (last 30 days)
    const last30Days = dailyHistory.slice(-30);
    const dates = last30Days.map(d => {
        const date = new Date(d.date);
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    });

    // GMV data
    const gmvData = last30Days.map(d => d.total_gmv);
    const gmvMA7 = new Array(last30Days.length).fill(movingAverages.ma_7d?.gmv || 0);
    const gmvMA30 = new Array(last30Days.length).fill(movingAverages.ma_30d?.gmv || 0);

    // Orders data
    const ordersData = last30Days.map(d => d.orders);
    const ordersMA7 = new Array(last30Days.length).fill(movingAverages.ma_7d?.orders || 0);
    const ordersMA30 = new Array(last30Days.length).fill(movingAverages.ma_30d?.orders || 0);

    // Create or update GMV chart
    updateChart(
        `${country}-gmv-chart`,
        charts[country].gmv,
        dates,
        gmvData,
        gmvMA7,
        gmvMA30,
        'GMV'
    );

    // Create or update Orders chart
    updateChart(
        `${country}-orders-chart`,
        charts[country].orders,
        dates,
        ordersData,
        ordersMA7,
        ordersMA30,
        'Orders'
    );
}

/**
 * Create or update a chart
 */
function updateChart(canvasId, existingChart, labels, data, ma7, ma30, label) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;

    const chartData = {
        labels: labels,
        datasets: [
            {
                label: label,
                data: data,
                borderColor: '#8b5cf6',
                backgroundColor: 'rgba(139, 92, 246, 0.1)',
                borderWidth: 2,
                tension: 0.4,
                fill: true,
                pointRadius: 0,
                pointHoverRadius: 4
            },
            {
                label: '7-day MA',
                data: ma7,
                borderColor: '#3b82f6',
                borderWidth: 2,
                borderDash: [5, 5],
                tension: 0.4,
                fill: false,
                pointRadius: 0
            },
            {
                label: '30-day MA',
                data: ma30,
                borderColor: '#10b981',
                borderWidth: 2,
                borderDash: [5, 5],
                tension: 0.4,
                fill: false,
                pointRadius: 0
            }
        ]
    };

    const chartOptions = {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
            legend: {
                display: true,
                position: 'top',
                labels: {
                    color: '#a0a0a0',
                    font: { size: 11 },
                    usePointStyle: true
                }
            },
            tooltip: {
                mode: 'index',
                intersect: false,
                backgroundColor: '#252525',
                titleColor: '#ffffff',
                bodyColor: '#a0a0a0',
                borderColor: '#333333',
                borderWidth: 1
            }
        },
        scales: {
            x: {
                grid: {
                    color: '#333333',
                    drawBorder: false
                },
                ticks: {
                    color: '#a0a0a0',
                    font: { size: 10 }
                }
            },
            y: {
                grid: {
                    color: '#333333',
                    drawBorder: false
                },
                ticks: {
                    color: '#a0a0a0',
                    font: { size: 10 },
                    callback: function(value) {
                        return formatNumber(value, 0);
                    }
                }
            }
        },
        interaction: {
            mode: 'nearest',
            axis: 'x',
            intersect: false
        }
    };

    // Destroy existing chart if it exists
    if (existingChart) {
        existingChart.destroy();
    }

    // Create new chart
    const country = canvasId.split('-')[0];
    const chartType = canvasId.includes('gmv') ? 'gmv' : 'orders';
    charts[country][chartType] = new Chart(ctx, {
        type: 'line',
        data: chartData,
        options: chartOptions
    });
}

// Initialize dashboard on page load
document.addEventListener('DOMContentLoaded', () => {
    console.log('Dashboard initializing...');
    loadDashboardData();

    // Set up auto-refresh
    setInterval(() => {
        console.log('Auto-refreshing dashboard...');
        loadDashboardData();
    }, CONFIG.refreshInterval);
});
