/* ============================================================================
   BEES ANALYTICS DASHBOARD - APPLICATION LOGIC
   Production-Grade JavaScript for Real-Time Dashboard
   ============================================================================ */

// Configuration
const CONFIG = {
    dataFiles: {
        ph: 'data/ph.json',
        vn: 'data/vn.json'
    },
    refreshInterval: 2 * 60 * 1000, // 2 minutes
    staleThresholds: {
        warning: 5 * 60 * 1000, // 5 minutes
        error: 15 * 60 * 1000 // 15 minutes
    }
};

// Global state
let dashboardData = {
    ph: null,
    vn: null
};

let charts = {
    revenue: null,
    orders: null
};

/* ============================================================================
   DATA FETCHING & LOADING
   ============================================================================ */

async function fetchData(url) {
    try {
        const response = await fetch(url + '?t=' + Date.now(), {
            cache: 'no-store'
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error(`Failed to fetch ${url}:`, error);
        return null;
    }
}

async function loadDashboardData() {
    try {
        console.log('Loading dashboard data...');

        // Fetch both countries in parallel
        const [phData, vnData] = await Promise.all([
            fetchData(CONFIG.dataFiles.ph),
            fetchData(CONFIG.dataFiles.vn)
        ]);

        if (phData) dashboardData.ph = phData;
        if (vnData) dashboardData.vn = vnData;

        // Update UI
        updateKPICards();
        updateCharts();
        updateDataTable();
        updateStatusIndicator();

        console.log('Dashboard data loaded successfully');
    } catch (error) {
        console.error('Failed to load dashboard data:', error);
    }
}

/* ============================================================================
   KPI CARDS UPDATE
   ============================================================================ */

function updateKPICards() {
    if (!dashboardData.ph || !dashboardData.vn) return;

    const countries = [
        { code: 'ph', data: dashboardData.ph, name: 'Philippines' },
        { code: 'vn', data: dashboardData.vn, name: 'Vietnam' }
    ];

    countries.forEach(({ code, data }) => {
        if (!data.today) return;

        const today = data.today;
        const lastWeek = data.same_day_last_week || {};

        // Update GMV
        updateKPI(`${code}-gmv`, today.total_gmv_usd, lastWeek.total_gmv_usd, true);

        // Update Orders
        updateKPI(`${code}-orders`, today.orders, lastWeek.orders, false);
    });
}

function updateKPI(elementId, currentValue, previousValue, isCurrency) {
    const valueEl = document.getElementById(elementId);
    const trendEl = document.getElementById(elementId + '-trend');

    if (!valueEl || !trendEl) return;

    // Format value
    const formattedValue = isCurrency
        ? formatCurrency(currentValue)
        : formatNumber(currentValue);

    // Animate number count-up
    animateValue(valueEl, 0, currentValue, 800, isCurrency);

    // Calculate trend
    if (previousValue && previousValue > 0) {
        const change = currentValue - previousValue;
        const percentChange = (change / previousValue) * 100;
        const isPositive = change >= 0;

        trendEl.className = 'kpi-trend ' + (isPositive ? 'positive' : 'negative');

        const arrow = isPositive ? '↑' : '↓';
        const sign = isPositive ? '+' : '';

        trendEl.innerHTML = `
            <span class="trend-indicator">${arrow}</span>
            <span class="trend-value">${sign}${percentChange.toFixed(1)}%</span>
            <span class="trend-text">vs last week</span>
        `;
    }
}

function animateValue(element, start, end, duration, isCurrency) {
    const startTime = Date.now();
    const range = end - start;

    function update() {
        const now = Date.now();
        const progress = Math.min((now - startTime) / duration, 1);

        // Easing function (ease-out)
        const easeOut = 1 - Math.pow(1 - progress, 3);
        const currentValue = start + (range * easeOut);

        element.textContent = isCurrency
            ? formatCurrency(currentValue)
            : formatNumber(Math.round(currentValue));

        if (progress < 1) {
            requestAnimationFrame(update);
        }
    }

    requestAnimationFrame(update);
}

/* ============================================================================
   CHARTS INITIALIZATION & UPDATE
   ============================================================================ */

function initializeCharts() {
    const chartDefaults = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                display: true,
                position: 'top',
                labels: {
                    color: '#A0A0A0',
                    font: {
                        family: 'Inter',
                        size: 12
                    },
                    usePointStyle: true,
                    padding: 16
                }
            },
            tooltip: {
                backgroundColor: '#1A1A1A',
                titleColor: '#FFFFFF',
                bodyColor: '#A0A0A0',
                borderColor: '#2A2A2A',
                borderWidth: 1,
                padding: 12,
                displayColors: true,
                callbacks: {
                    label: function(context) {
                        let label = context.dataset.label || '';
                        if (label) {
                            label += ': ';
                        }
                        if (context.parsed.y !== null) {
                            if (context.dataset.isCurrency) {
                                label += formatCurrency(context.parsed.y);
                            } else {
                                label += formatNumber(context.parsed.y);
                            }
                        }
                        return label;
                    }
                }
            }
        },
        scales: {
            x: {
                grid: {
                    color: 'rgba(255, 255, 255, 0.05)',
                    drawBorder: false
                },
                ticks: {
                    color: '#A0A0A0',
                    font: {
                        size: 11
                    }
                }
            },
            y: {
                grid: {
                    color: 'rgba(255, 255, 255, 0.05)',
                    drawBorder: false
                },
                ticks: {
                    color: '#A0A0A0',
                    font: {
                        size: 11
                    },
                    callback: function(value) {
                        return formatNumber(value);
                    }
                }
            }
        }
    };

    // Revenue Chart
    const revenueCtx = document.getElementById('revenueChart');
    if (revenueCtx) {
        charts.revenue = new Chart(revenueCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'Philippines',
                        data: [],
                        borderColor: '#F5E003',
                        backgroundColor: 'rgba(245, 224, 3, 0.1)',
                        borderWidth: 2,
                        tension: 0.4,
                        fill: true,
                        isCurrency: true
                    },
                    {
                        label: 'Vietnam',
                        data: [],
                        borderColor: '#3B82F6',
                        backgroundColor: 'rgba(59, 130, 246, 0.1)',
                        borderWidth: 2,
                        tension: 0.4,
                        fill: true,
                        isCurrency: true
                    }
                ]
            },
            options: chartDefaults
        });
    }

    // Orders Chart
    const ordersCtx = document.getElementById('ordersChart');
    if (ordersCtx) {
        charts.orders = new Chart(ordersCtx, {
            type: 'bar',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'Philippines',
                        data: [],
                        backgroundColor: '#F5E003',
                        borderRadius: 6,
                        isCurrency: false
                    },
                    {
                        label: 'Vietnam',
                        data: [],
                        backgroundColor: '#3B82F6',
                        borderRadius: 6,
                        isCurrency: false
                    }
                ]
            },
            options: chartDefaults
        });
    }
}

function updateCharts() {
    if (!dashboardData.ph || !dashboardData.vn) return;

    const phHistory = dashboardData.ph.daily_history || [];
    const vnHistory = dashboardData.vn.daily_history || [];

    // Get last 15 days
    const days = phHistory.slice(-15);
    const labels = days.map(d => formatDate(d.date));

    // Update Revenue Chart
    if (charts.revenue) {
        charts.revenue.data.labels = labels;
        charts.revenue.data.datasets[0].data = days.map(d => d.total_gmv_usd);
        charts.revenue.data.datasets[1].data = vnHistory.slice(-15).map(d => d.total_gmv_usd);
        charts.revenue.update('none');
    }

    // Update Orders Chart
    if (charts.orders) {
        charts.orders.data.labels = labels;
        charts.orders.data.datasets[0].data = days.map(d => d.orders);
        charts.orders.data.datasets[1].data = vnHistory.slice(-15).map(d => d.orders);
        charts.orders.update('none');
    }
}

/* ============================================================================
   DATA TABLE UPDATE
   ============================================================================ */

function updateDataTable() {
    const tbody = document.getElementById('dataTableBody');
    if (!tbody || !dashboardData.ph || !dashboardData.vn) return;

    const countries = [
        { name: 'Philippines 🇵🇭', data: dashboardData.ph.today },
        { name: 'Vietnam 🇻🇳', data: dashboardData.vn.today }
    ];

    tbody.innerHTML = countries.map(({ name, data }) => `
        <tr>
            <td><strong>${name}</strong></td>
            <td>${formatCurrency(data.total_gmv_usd)}</td>
            <td>${formatNumber(data.orders)}</td>
            <td>${formatCurrency(data.aov_usd)}</td>
            <td>${formatNumber(data.unique_buyers)}</td>
            <td>${data.frequency.toFixed(2)}x</td>
        </tr>
    `).join('');
}

/* ============================================================================
   STATUS INDICATOR
   ============================================================================ */

function updateStatusIndicator() {
    const indicator = document.getElementById('statusIndicator');
    const lastUpdatedEl = document.getElementById('lastUpdated');

    if (!indicator || !lastUpdatedEl) return;

    const data = dashboardData.ph || dashboardData.vn;
    if (!data || !data.last_updated) return;

    const lastUpdated = new Date(data.last_updated);
    const now = new Date();
    const diff = now - lastUpdated;

    // Update status class
    indicator.classList.remove('delayed', 'stale');
    let statusText = 'Live';

    if (diff > CONFIG.staleThresholds.error) {
        indicator.classList.add('stale');
        statusText = 'Stale';
    } else if (diff > CONFIG.staleThresholds.warning) {
        indicator.classList.add('delayed');
        statusText = 'Delayed';
    }

    indicator.querySelector('.status-text').textContent = statusText;

    // Update timestamp
    lastUpdatedEl.textContent = `Updated ${formatTimeAgo(lastUpdated)}`;
}

/* ============================================================================
   UI INTERACTIONS
   ============================================================================ */

// Theme Toggle
function initializeThemeToggle() {
    const toggle = document.getElementById('themeToggle');
    if (!toggle) return;

    const savedTheme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);

    toggle.addEventListener('click', () => {
        const current = document.documentElement.getAttribute('data-theme');
        const next = current === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', next);
        localStorage.setItem('theme', next);
    });
}

// Sidebar Toggle
function initializeSidebarToggle() {
    const toggle = document.getElementById('sidebarToggle');
    const mobileToggle = document.getElementById('mobileMenuToggle');
    const sidebar = document.getElementById('sidebar');

    [toggle, mobileToggle].forEach(btn => {
        if (btn) {
            btn.addEventListener('click', () => {
                sidebar?.classList.toggle('open');
            });
        }
    });
}

// Refresh Button
function initializeRefreshButton() {
    const refreshBtn = document.getElementById('refreshBtn');
    if (!refreshBtn) return;

    refreshBtn.addEventListener('click', async () => {
        refreshBtn.classList.add('refreshing');
        refreshBtn.disabled = true;

        await loadDashboardData();

        setTimeout(() => {
            refreshBtn.classList.remove('refreshing');
            refreshBtn.disabled = false;
        }, 500);
    });
}

// Logout
function logout() {
    sessionStorage.removeItem('authenticated');
    window.location.href = 'login.html';
}

// Time Range Selector
function initializeTimeRangeSelector() {
    const buttons = document.querySelectorAll('.time-btn');

    buttons.forEach(btn => {
        btn.addEventListener('click', () => {
            const range = btn.dataset.range;
            const parent = btn.closest('.chart-container');

            // Update active state
            parent.querySelectorAll('.time-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            // Filter chart data based on range
            // (Implementation depends on your specific requirements)
        });
    });
}

/* ============================================================================
   FORMATTING UTILITIES
   ============================================================================ */

function formatCurrency(value) {
    if (value === null || value === undefined) return '$0';
    return '$' + value.toLocaleString('en-US', {
        minimumFractionDigits: 0,
        maximumFractionDigits: 2
    });
}

function formatNumber(value) {
    if (value === null || value === undefined) return '0';
    return value.toLocaleString('en-US');
}

function formatDate(dateStr) {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric'
    });
}

function formatTimeAgo(date) {
    const diff = Date.now() - date;
    const minutes = Math.floor(diff / 60000);

    if (minutes < 1) return 'just now';
    if (minutes === 1) return '1 min ago';
    if (minutes < 60) return `${minutes} mins ago`;

    const hours = Math.floor(minutes / 60);
    if (hours === 1) return '1 hour ago';
    if (hours < 24) return `${hours} hours ago`;

    const days = Math.floor(hours / 24);
    if (days === 1) return '1 day ago';
    return `${days} days ago`;
}

/* ============================================================================
   INITIALIZATION
   ============================================================================ */

async function initializeDashboard() {
    console.log('Initializing BEES Analytics Dashboard...');

    // Initialize UI components
    initializeThemeToggle();
    initializeSidebarToggle();
    initializeRefreshButton();
    initializeTimeRangeSelector();

    // Initialize charts
    initializeCharts();

    // Load initial data
    await loadDashboardData();

    // Setup auto-refresh
    setInterval(() => {
        loadDashboardData();
    }, CONFIG.refreshInterval);

    // Setup status update interval
    setInterval(() => {
        updateStatusIndicator();
    }, 30000); // Every 30 seconds

    // Add logout button handler
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', logout);
    }

    console.log('Dashboard initialized successfully');
}

// Start the application when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeDashboard);
} else {
    initializeDashboard();
}
