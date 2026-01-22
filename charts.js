/* ============================================================================
   BEES CHARTS PAGE - Analytics and Channel Distribution
   Google-Quality Code: Clean, Performant, Reliable
   ============================================================================ */

// Configuration
const CONFIG = {
    dataFiles: {
        ph: 'data/ph.json',
        vn: 'data/vn.json'
    },
    refreshInterval: 2 * 60 * 1000, // 2 minutes
    staleThresholds: {
        warning: 5 * 60 * 1000,
        error: 15 * 60 * 1000
    }
};

// Global state
const state = {
    data: {
        ph: null,
        vn: null
    },
    lastFetch: null,
    refreshTimer: null,
    statusTimer: null,
    charts: {
        ph: { gmv: null, orders: null },
        vn: { gmv: null, orders: null }
    }
};

/* ============================================================================
   DATA FETCHING
   ============================================================================ */

async function fetchJSON(url) {
    const response = await fetch(url + '?t=' + Date.now(), {
        cache: 'no-store',
        headers: {
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache'
        }
    });
    if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    return response.json();
}

async function loadDashboardData() {
    try {
        console.log('[DATA] Loading charts data...');
        const [phData, vnData] = await Promise.all([
            fetchJSON(CONFIG.dataFiles.ph),
            fetchJSON(CONFIG.dataFiles.vn)
        ]);
        state.data.ph = phData;
        state.data.vn = vnData;
        state.lastFetch = Date.now();
        console.log('[DATA] Data loaded successfully');
        updateUI();
        return true;
    } catch (error) {
        console.error('[ERROR] Failed to load data:', error);
        return false;
    }
}

/* ============================================================================
   CHARTS CREATION
   ============================================================================ */

function createGMVChart(country, data) {
    const canvasId = `${country}-gmv-chart`;
    const canvas = document.getElementById(canvasId);

    if (!canvas || !data || !data.daily_history) return;

    if (state.charts[country].gmv) {
        state.charts[country].gmv.destroy();
    }

    const history = data.daily_history.slice().reverse();
    const dates = history.map(d => {
        const date = new Date(d.date);
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    });
    const gmvData = history.map(d => d.total_gmv_usd);

    const ma7 = data.moving_averages?.ma_7d?.gmv || 0;
    const ma15 = data.moving_averages?.ma_15d?.gmv || 0;

    const ctx = canvas.getContext('2d');
    state.charts[country].gmv = new Chart(ctx, {
        type: 'line',
        data: {
            labels: dates,
            datasets: [
                {
                    label: 'GMV (USD)',
                    data: gmvData,
                    borderColor: '#F5E003',
                    backgroundColor: 'rgba(245, 224, 3, 0.1)',
                    borderWidth: 3,
                    tension: 0.4,
                    fill: true
                },
                {
                    label: '7-Day MA',
                    data: Array(dates.length).fill(ma7),
                    borderColor: 'rgba(245, 224, 3, 0.5)',
                    borderWidth: 2,
                    borderDash: [5, 5],
                    pointRadius: 0
                },
                {
                    label: '15-Day MA',
                    data: Array(dates.length).fill(ma15),
                    borderColor: 'rgba(245, 224, 3, 0.3)',
                    borderWidth: 2,
                    borderDash: [10, 5],
                    pointRadius: 0
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: { color: '#FFFFFF', font: { size: 12 } }
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.9)',
                    titleColor: '#F5E003',
                    bodyColor: '#FFFFFF',
                    callbacks: {
                        label: (context) => {
                            return context.dataset.label + ': $' +
                                context.parsed.y.toLocaleString('en-US', { maximumFractionDigits: 0 });
                        }
                    }
                }
            },
            scales: {
                x: {
                    ticks: { color: 'rgba(255, 255, 255, 0.7)' },
                    grid: { color: 'rgba(255, 255, 255, 0.1)' }
                },
                y: {
                    ticks: {
                        color: '#F5E003',
                        callback: (value) => '$' + (value / 1000).toFixed(0) + 'K'
                    },
                    grid: { color: 'rgba(245, 224, 3, 0.1)' }
                }
            }
        }
    });
}

function createOrdersChart(country, data) {
    const canvasId = `${country}-orders-chart`;
    const canvas = document.getElementById(canvasId);

    if (!canvas || !data || !data.daily_history) return;

    if (state.charts[country].orders) {
        state.charts[country].orders.destroy();
    }

    const history = data.daily_history.slice().reverse();
    const dates = history.map(d => {
        const date = new Date(d.date);
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    });
    const ordersData = history.map(d => d.orders);

    const ctx = canvas.getContext('2d');
    state.charts[country].orders = new Chart(ctx, {
        type: 'line',
        data: {
            labels: dates,
            datasets: [
                {
                    label: 'Orders',
                    data: ordersData,
                    borderColor: '#10B981',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    borderWidth: 3,
                    tension: 0.4,
                    fill: true
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: { color: '#FFFFFF', font: { size: 12 } }
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.9)',
                    titleColor: '#10B981',
                    bodyColor: '#FFFFFF'
                }
            },
            scales: {
                x: {
                    ticks: { color: 'rgba(255, 255, 255, 0.7)' },
                    grid: { color: 'rgba(255, 255, 255, 0.1)' }
                },
                y: {
                    ticks: { color: '#10B981' },
                    grid: { color: 'rgba(16, 185, 129, 0.1)' }
                }
            }
        }
    });
}

/* ============================================================================
   CHANNEL BREAKDOWN
   ============================================================================ */

function updateChannelBreakdown(country, data) {
    if (!data || !data.channel_breakdown_mtd) return;

    const mtd = data.channel_breakdown_mtd;

    // Customer channel
    const customerGmv = document.getElementById(`${country}-channel-customer-gmv`);
    const customerOrders = document.getElementById(`${country}-channel-customer-orders`);
    const customerPercent = document.getElementById(`${country}-channel-customer-percent`);
    const customerBar = document.getElementById(`${country}-channel-customer-bar`);

    if (customerGmv) customerGmv.textContent = '$' + mtd.customer.gmv_usd.toLocaleString('en-US', { maximumFractionDigits: 0 });
    if (customerOrders) customerOrders.textContent = mtd.customer.orders.toLocaleString('en-US');
    if (customerPercent) customerPercent.textContent = mtd.customer.gmv_percent.toFixed(1) + '%';
    if (customerBar) customerBar.style.width = mtd.customer.gmv_percent + '%';

    // CX_TLP channel
    const cxGmv = document.getElementById(`${country}-channel-cx-tlp-gmv`);
    const cxOrders = document.getElementById(`${country}-channel-cx-tlp-orders`);
    const cxPercent = document.getElementById(`${country}-channel-cx-tlp-percent`);
    const cxBar = document.getElementById(`${country}-channel-cx-tlp-bar`);

    if (cxGmv) cxGmv.textContent = '$' + mtd.cx_tlp.gmv_usd.toLocaleString('en-US', { maximumFractionDigits: 0 });
    if (cxOrders) cxOrders.textContent = mtd.cx_tlp.orders.toLocaleString('en-US');
    if (cxPercent) cxPercent.textContent = mtd.cx_tlp.gmv_percent.toFixed(1) + '%';
    if (cxBar) cxBar.style.width = mtd.cx_tlp.gmv_percent + '%';
}

/* ============================================================================
   COMPARISON TABLE
   ============================================================================ */

function updateComparisonTable(country, data) {
    if (!data) return;

    const tableBody = document.querySelector(`#${country}-comparison-table tbody`);
    if (!tableBody) return;

    const today = data.today || {};
    const lastWeek = data.same_day_last_week || {};
    const mtd = data.mtd || {};

    const metrics = [
        { label: 'GMV (USD)', key: 'total_gmv_usd', isCurrency: true },
        { label: 'Orders', key: 'orders', isCurrency: false },
        { label: 'AOV (USD)', key: 'aov_usd', isCurrency: true },
        { label: 'Buyers', key: 'unique_buyers', isCurrency: false },
        { label: 'Frequency', key: 'frequency', isCurrency: false, decimals: 2 },
        { label: 'GMV/POC (USD)', key: 'gmv_per_poc_usd', isCurrency: true }
    ];

    tableBody.innerHTML = metrics.map(metric => {
        const todayVal = today[metric.key] || 0;
        const lastWeekVal = lastWeek[metric.key] || 0;
        const mtdVal = mtd[metric.key] || 0;
        const diff = todayVal - lastWeekVal;
        const changePercent = lastWeekVal !== 0 ? (diff / lastWeekVal) * 100 : 0;

        const formatValue = (val) => {
            if (metric.isCurrency) {
                return '$' + val.toLocaleString('en-US', { maximumFractionDigits: metric.decimals || 0 });
            }
            return val.toLocaleString('en-US', { maximumFractionDigits: metric.decimals || 0 });
        };

        const changeClass = diff >= 0 ? 'positive' : 'negative';
        const arrow = diff >= 0 ? '▲' : '▼';

        return `
            <tr>
                <td>${metric.label}</td>
                <td>${formatValue(todayVal)}</td>
                <td>${formatValue(lastWeekVal)}</td>
                <td class="${changeClass}">${arrow} ${formatValue(Math.abs(diff))}</td>
                <td class="${changeClass}">${changePercent.toFixed(1)}%</td>
                <td>${formatValue(mtdVal)}</td>
            </tr>
        `;
    }).join('');
}

/* ============================================================================
   STATUS INDICATOR
   ============================================================================ */

function updateStatusIndicator() {
    const indicator = document.getElementById('statusIndicator');
    const lastUpdatedEl = document.getElementById('lastUpdated');

    if (!indicator || !lastUpdatedEl) return;

    const data = state.data.ph || state.data.vn;
    if (!data || !data.last_updated) {
        lastUpdatedEl.textContent = 'No data';
        return;
    }

    const lastUpdated = new Date(data.last_updated);
    const now = new Date();
    const diff = now - lastUpdated;

    lastUpdatedEl.textContent = `Updated ${formatTimeAgo(lastUpdated)}`;

    indicator.classList.remove('delayed', 'stale');

    if (diff > CONFIG.staleThresholds.error) {
        indicator.classList.add('stale');
        indicator.querySelector('.status-text').textContent = 'Stale';
    } else if (diff > CONFIG.staleThresholds.warning) {
        indicator.classList.add('delayed');
        indicator.querySelector('.status-text').textContent = 'Delayed';
    } else {
        indicator.querySelector('.status-text').textContent = 'Live';
    }
}

function formatTimeAgo(date) {
    const seconds = Math.floor((new Date() - date) / 1000);
    if (seconds < 60) return 'just now';
    if (seconds < 120) return '1 min ago';
    if (seconds < 3600) return `${Math.floor(seconds / 60)} mins ago`;
    if (seconds < 7200) return '1 hour ago';
    if (seconds < 86400) return `${Math.floor(seconds / 3600)} hours ago`;
    return date.toLocaleString();
}

/* ============================================================================
   UI UPDATE
   ============================================================================ */

function updateUI() {
    console.log('[UI] Updating charts page...');

    // Update Philippines
    createGMVChart('ph', state.data.ph);
    createOrdersChart('ph', state.data.ph);
    updateChannelBreakdown('ph', state.data.ph);
    updateComparisonTable('ph', state.data.ph);

    // Update Vietnam
    createGMVChart('vn', state.data.vn);
    createOrdersChart('vn', state.data.vn);
    updateChannelBreakdown('vn', state.data.vn);
    updateComparisonTable('vn', state.data.vn);

    updateStatusIndicator();

    console.log('[UI] Charts page updated successfully');
}

/* ============================================================================
   USER INTERACTIONS
   ============================================================================ */

async function refreshData() {
    const btn = document.getElementById('refreshBtn');
    if (!btn) return;

    console.log('[UI] Manual refresh triggered');

    btn.classList.add('refreshing');
    btn.disabled = true;

    await loadDashboardData();

    setTimeout(() => {
        btn.classList.remove('refreshing');
        btn.disabled = false;
    }, 1000);
}

function logout() {
    sessionStorage.removeItem('authenticated');
    window.location.href = 'login.html';
}

/* ============================================================================
   INITIALIZATION
   ============================================================================ */

async function initialize() {
    console.log('[INIT] Initializing Charts Page...');

    const success = await loadDashboardData();

    if (success) {
        state.refreshTimer = setInterval(() => {
            console.log('[AUTO] Auto-refresh triggered');
            loadDashboardData();
        }, CONFIG.refreshInterval);

        state.statusTimer = setInterval(() => {
            updateStatusIndicator();
        }, 30000);

        console.log('[INIT] Charts page initialized successfully');
    } else {
        console.error('[INIT] Failed to initialize charts page');
    }
}

// Start when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initialize);
} else {
    initialize();
}

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (state.refreshTimer) clearInterval(state.refreshTimer);
    if (state.statusTimer) clearInterval(state.statusTimer);
});

// Expose functions to global scope for onclick handlers
window.refreshData = refreshData;
window.logout = logout;
