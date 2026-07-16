// Global application state
let rawFlatsList = [];
let currentFilters = {
    location: 'all',
    rooms: 'all',
    search: '',
    sortBy: 'price-asc'
};
let statusInterval = null;
let logsInterval = null;

// DOM Elements
const btnScan = document.getElementById('btn-scan');
const statusDot = document.getElementById('status-dot');
const statusMsg = document.getElementById('status-msg');
const lastScanned = document.getElementById('last-scanned');
const resultsCount = document.getElementById('results-count');
const propertiesGrid = document.getElementById('properties-grid');
const searchInput = document.getElementById('search-input');
const sortSelect = document.getElementById('sort-select');

// Stats Counters
const statClifton = document.getElementById('stat-clifton');
const statChowk = document.getElementById('stat-chowk');
const statBudget = document.getElementById('stat-budget');

// Drawer elements
const logDrawer = document.getElementById('log-drawer');
const drawerToggle = document.getElementById('drawer-toggle');
const logConsole = document.getElementById('log-console');

// Initialize Dashboard
document.addEventListener('DOMContentLoaded', () => {
    initApp();
    setupEventListeners();
});

function initApp() {
    loadFlatsData();
    checkScraperStatus();
    
    // Poll status frequently (every 3 seconds)
    statusInterval = setInterval(checkScraperStatus, 3000);
}

function setupEventListeners() {
    // Scan Trigger Button
    btnScan.addEventListener('click', triggerScraper);

    // Location Tabs Filter
    document.querySelectorAll('#filter-location .tab-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('#filter-location .tab-btn').forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            currentFilters.location = e.target.getAttribute('data-value');
            applyFiltersAndRender();
        });
    });

    // Rooms Tabs Filter
    document.querySelectorAll('#filter-rooms .tab-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('#filter-rooms .tab-btn').forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            currentFilters.rooms = e.target.getAttribute('data-value');
            applyFiltersAndRender();
        });
    });

    // Search input keyword filtering
    searchInput.addEventListener('input', (e) => {
        currentFilters.search = e.target.value.toLowerCase().strip ? e.target.value.toLowerCase().trim() : e.target.value.toLowerCase();
        applyFiltersAndRender();
    });

    // Sorting select box
    sortSelect.addEventListener('change', (e) => {
        currentFilters.sortBy = e.target.value;
        applyFiltersAndRender();
    });

    // Log Drawer toggling
    drawerToggle.addEventListener('click', () => {
        logDrawer.classList.toggle('open');
        if (logDrawer.classList.contains('open')) {
            updateLogs();
            // Poll logs while open
            logsInterval = setInterval(updateLogs, 2000);
        } else {
            if (logsInterval) {
                clearInterval(logsInterval);
                logsInterval = null;
            }
        }
    });
}

// Fetch lists from backend
async function loadFlatsData(wasJustScanned = false) {
    try {
        const response = await fetch('/api/flats');
        const data = await response.json();
        if (Array.isArray(data)) {
            rawFlatsList = data;
            updateStatsCounters(data);
            applyFiltersAndRender();

            if (wasJustScanned) {
                if (data.length === 0) {
                    showToast("Scan completed: No flats were found. Try adjusting your search filters or budget.", "warning");
                } else {
                    showToast(`Scan completed successfully! Found ${data.length} matching properties.`, "success");
                }
            }
        } else {
            showEmptyState("Could not read property database.");
        }
    } catch (error) {
        console.error("Error loading flats data:", error);
        showEmptyState("Failed to connect to the backend server.");
    }
}

// Stats computations
function updateStatsCounters(data) {
    const cliftonCount = data.filter(f => f.area === "Clifton").length;
    const chowkCount = data.filter(f => f.area === "Pakistan Chowk").length;
    
    // Compute average rent
    let avgRent = 0;
    if (data.length > 0) {
        const total = data.reduce((sum, item) => sum + item.price, 0);
        avgRent = Math.round(total / data.length);
    }
    
    statClifton.textContent = cliftonCount;
    statChowk.textContent = chowkCount;
    statBudget.textContent = avgRent > 0 ? `PKR ${avgRent.toLocaleString()}` : "0";
}

// Trigger background scraper
async function triggerScraper() {
    try {
        btnScan.disabled = true;
        const response = await fetch('/api/scrape', { method: 'POST' });
        const resData = await response.json();
        
        statusMsg.textContent = "Scan requested...";
        statusDot.className = "status-indicator running";
        
        // Open log drawer to show progress
        if (!logDrawer.classList.contains('open')) {
            drawerToggle.click();
        }
        
        setTimeout(checkScraperStatus, 1000);
    } catch (error) {
        console.error("Error triggering scan:", error);
        btnScan.disabled = false;
    }
}

// Check scraper state in background
async function checkScraperStatus() {
    try {
        const response = await fetch('/api/status');
        const status = await response.json();
        
        lastScanned.textContent = status.last_run || "Never";
        statusMsg.textContent = status.status_message || "Idle";
        
        if (status.is_running) {
            btnScan.disabled = true;
            btnScan.classList.add('running');
            statusDot.className = "status-indicator running";
            
            // Auto update logs if drawer is open
            if (logDrawer.classList.contains('open')) {
                updateLogs();
            }
        } else {
            // If it just stopped running, reload the property data with scan notification flag
            if (btnScan.disabled && btnScan.classList.contains('running')) {
                loadFlatsData(true);
            }
            btnScan.disabled = false;
            btnScan.classList.remove('running');
            
            if (status.status_message.includes("Error")) {
                statusDot.className = "status-indicator error";
            } else if (status.last_run !== "Never") {
                statusDot.className = "status-indicator success";
            } else {
                statusDot.className = "status-indicator";
            }
        }
    } catch (error) {
        console.error("Error checking status:", error);
    }
}

// Show animated toast notification
function showToast(message, type = 'info') {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container';
        document.body.appendChild(container);
    }
    
    const toast = document.createElement('div');
    toast.className = `toast-notification ${type}`;
    toast.innerHTML = `
        <span class="toast-icon">${type === 'success' ? '✅' : type === 'warning' ? '⚠️' : type === 'error' ? '❌' : 'ℹ️'}</span>
        <span class="toast-message">${message}</span>
        <span class="toast-close">&times;</span>
    `;
    container.appendChild(toast);
    
    // Add click handler to close
    toast.querySelector('.toast-close').addEventListener('click', () => {
        toast.classList.add('fade-out');
        setTimeout(() => toast.remove(), 300);
    });
    
    // Auto remove after 6 seconds
    setTimeout(() => {
        if (toast.parentNode) {
            toast.classList.add('fade-out');
            setTimeout(() => toast.remove(), 300);
        }
    }, 6000);
}

// Fetch logs
async function updateLogs() {
    try {
        const response = await fetch('/api/logs');
        const data = await response.json();
        if (data.logs) {
            logConsole.textContent = data.logs;
            // Scroll to bottom of logs
            const drawerContent = document.querySelector('.drawer-content');
            drawerContent.scrollTop = drawerContent.scrollHeight;
        }
    } catch (error) {
        console.error("Error fetching logs:", error);
    }
}

// Apply searches, filters, and sorting client-side
function applyFiltersAndRender() {
    let filteredList = [...rawFlatsList];

    // Filter by Location
    if (currentFilters.location !== 'all') {
        filteredList = filteredList.filter(flat => flat.area === currentFilters.location);
    }

    // Filter by Rooms
    if (currentFilters.rooms !== 'all') {
        const requiredRooms = parseInt(currentFilters.rooms);
        filteredList = filteredList.filter(flat => flat.rooms === requiredRooms);
    }

    // Filter by Keyword Search input
    if (currentFilters.search) {
        filteredList = filteredList.filter(flat => {
            return flat.title.toLowerCase().includes(currentFilters.search) || 
                   flat.location.toLowerCase().includes(currentFilters.search) ||
                   flat.source.toLowerCase().includes(currentFilters.search);
        });
    }

    // Sort listings
    if (currentFilters.sortBy === 'price-asc') {
        filteredList.sort((a, b) => a.price - b.price);
    } else if (currentFilters.sortBy === 'price-desc') {
        filteredList.sort((a, b) => b.price - a.price);
    } else if (currentFilters.sortBy === 'rooms-desc') {
        filteredList.sort((a, b) => b.rooms - a.rooms);
    } else if (currentFilters.sortBy === 'date-desc') {
        filteredList.sort((a, b) => new Date(b.date) - new Date(a.date));
    }

    renderFlatsGrid(filteredList);
}

// Render property grid dynamically
function renderFlatsGrid(flats) {
    resultsCount.textContent = flats.length;
    propertiesGrid.innerHTML = '';

    if (flats.length === 0) {
        showEmptyState("No matching flats found. Try running a new property scan or widening filters.");
        return;
    }

    flats.forEach(flat => {
        const card = document.createElement('div');
        card.className = 'flat-card';
        
        const sourceClass = flat.source.toLowerCase();
        
        card.innerHTML = `
            <div class="card-img-container">
                <img src="${flat.image}" alt="Flat Image" onerror="this.onerror=null;this.src='https://via.placeholder.com/300x200?text=Listing+Image';">
                <span class="source-badge ${sourceClass}">${flat.source}</span>
                <span class="area-badge">${flat.area}</span>
            </div>
            <div class="card-details">
                <div class="price-tag">${flat.price_str}</div>
                <h3 class="flat-title" title="${flat.title}">${flat.title}</h3>
                <div class="flat-meta-info">
                    <span class="loc-text" title="${flat.location}">📍 ${flat.location}</span>
                    <span class="rooms-badge">🛏️ ${flat.rooms} Rooms</span>
                </div>
            </div>
            <div class="card-actions">
                <a href="${flat.link}" target="_blank" class="btn btn-view-listing">View Original Ad</a>
            </div>
        `;
        
        propertiesGrid.appendChild(card);
    });
}

function showEmptyState(message) {
    propertiesGrid.innerHTML = `
        <div class="empty-placeholder">
            <span style="font-size: 3rem; margin-bottom: 1rem;">🔍</span>
            <p>${message}</p>
        </div>
    `;
}
