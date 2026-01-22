/* ============================================================================
   BEES DASHBOARD - DATA MANAGEMENT
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
        warning: 5 * 60 * 1000,  // 5 minutes
        error: 15 * 60 * 1000    // 15 minutes
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
    statusTimer: null
};

/* ============================================================================
   DATA FETCHING - Robust with error handling
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
        console.log('[DATA] Loading dashboard data...');

        // Fetch both countries in parallel
        const [phData, vnData] = await Promise.all([
            fetchJSON(CONFIG.dataFiles.ph),
            fetchJSON(CONFIG.dataFiles.vn)
        ]);

        // Update state
        state.data.ph = phData;
        state.data.vn = vnData;
        state.lastFetch = Date.now();

        console.log('[DATA] Data loaded successfully');
        console.log('[DATA] PH:', phData.today);
        console.log('[DATA] VN:', vnData.today);

        // Update UI
        updateUI();

        return true;
    } catch (error) {
        console.error('[ERROR] Failed to load data:', error);
        return false;
    }
}

/* ============================================================================
   UI UPDATE - Simple, direct DOM manipulation
   ============================================================================ */

function updateUI() {
    console.log('[UI] Updating UI...');

    updateCountry('ph', state.data.ph);
    updateCountry('vn', state.data.vn);
    updateStatusIndicator();

    console.log('[UI] UI updated successfully');
}

function updateCountry(country, data) {
    if (!data || !data.today) {
        console.warn(`[UI] No data for ${country}`);
        return;
    }

    const today = data.today;
    const lastWeek = data.same_day_last_week || {};

    console.log(`[UI] Updating ${country.toUpperCase()}:`, today);

    // Update GMV
    updateMetric(country, 'gmv',
        today.total_gmv_usd,
        lastWeek.total_gmv_usd,
        true);

    // Update Orders
    updateMetric(country, 'orders',
        today.orders,
        lastWeek.orders,
        false);

    // Update AOV
    updateMetric(country, 'aov',
        today.aov_usd,
        lastWeek.aov_usd,
        true);

    // Update Buyers
    updateMetric(country, 'buyers',
        today.unique_buyers,
        lastWeek.unique_buyers,
        false);

    // Update Frequency
    updateMetric(country, 'frequency',
        today.frequency,
        lastWeek.frequency,
        false,
        2);

    // Update GMV/POCs
    updateMetric(country, 'gmv-poc',
        today.gmv_per_poc_usd,
        lastWeek.gmv_per_poc_usd,
        true);
}

function updateMetric(country, metricName, currentValue, previousValue, isCurrency, decimals = 0) {
    const valueEl = document.getElementById(`${country}-${metricName}`);
    const changeEl = document.getElementById(`${country}-${metricName}-change`);

    if (!valueEl) {
        console.warn(`[UI] Element not found: ${country}-${metricName}`);
        return;
    }

    // Format and display value
    const formattedValue = formatValue(currentValue, isCurrency, decimals);
    valueEl.textContent = formattedValue;

    // Calculate and display change
    if (changeEl && previousValue !== undefined && previousValue !== null) {
        const change = currentValue - previousValue;
        const changePercent = previousValue !== 0 ? (change / previousValue) * 100 : 0;

        // Format change text
        const arrow = change >= 0 ? '▲' : '▼';
        const sign = change >= 0 ? '+' : '';
        const changeText = `${arrow} ${sign}${changePercent.toFixed(1)}%`;

        changeEl.textContent = changeText;
        changeEl.className = 'metric-change ' + (change >= 0 ? 'positive' : 'negative');
    }
}

function formatValue(value, isCurrency, decimals = 0) {
    if (value === null || value === undefined || isNaN(value)) {
        return isCurrency ? '$0' : '0';
    }

    const formatted = value.toLocaleString('en-US', {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals
    });

    return isCurrency ? `$${formatted}` : formatted;
}

/* ============================================================================
   STATUS INDICATOR - Real-time freshness monitoring
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

    // Update timestamp
    lastUpdatedEl.textContent = `Updated ${formatTimeAgo(lastUpdated)}`;

    // Update status class
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
   USER INTERACTIONS
   ============================================================================ */

async function refreshData() {
    const btn = document.getElementById('refreshBtn');
    if (!btn) return;

    console.log('[UI] Manual refresh triggered');

    // Show loading state
    btn.classList.add('refreshing');
    btn.disabled = true;

    // Load data
    await loadDashboardData();

    // Reset button after animation
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
   INITIALIZATION & AUTO-REFRESH
   ============================================================================ */

async function initialize() {
    console.log('[INIT] Initializing BEES Dashboard...');

    // Load initial data
    const success = await loadDashboardData();

    if (success) {
        // Setup auto-refresh
        state.refreshTimer = setInterval(() => {
            console.log('[AUTO] Auto-refresh triggered');
            loadDashboardData();
        }, CONFIG.refreshInterval);

        // Setup status update interval
        state.statusTimer = setInterval(() => {
            updateStatusIndicator();
        }, 30000); // Every 30 seconds

        console.log('[INIT] Dashboard initialized successfully');
        console.log(`[INIT] Auto-refresh every ${CONFIG.refreshInterval / 1000}s`);
    } else {
        console.error('[INIT] Failed to initialize dashboard');
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
