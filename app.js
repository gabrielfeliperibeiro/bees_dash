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

// Placeholder for update functions (to be implemented in next task)
function updateDashboard() {
    console.log('Updating dashboard...');
    updateCountryDashboard('ph', dashboardData.ph);
    updateCountryDashboard('vn', dashboardData.vn);
}

function updateCountryDashboard(country, data) {
    console.log(`Updating ${country} dashboard...`, data);
    // TODO: Implement in next task
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
