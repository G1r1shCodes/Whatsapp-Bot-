// Global state
let currentTab = 'analytics-tab';
let leadsData = [];
let catalogData = [];
let selectedLead = null;
let productChart = null;
let statusChart = null;

// DOM Elements
const navItems = document.querySelectorAll('.nav-item');
const tabPanels = document.querySelectorAll('.tab-panel');
const pageTitle = document.getElementById('page-title');
const pageSubtitle = document.getElementById('page-subtitle');
const refreshBtn = document.getElementById('refresh-data-btn');

// Toast Helper
function showToast(message, isError = false) {
    const toast = document.getElementById('toast');
    const toastMessage = document.getElementById('toast-message');
    const toastIcon = toast.querySelector('.toast-icon');
    
    toastMessage.textContent = message;
    
    if (isError) {
        toast.classList.add('error');
        toastIcon.className = 'fa-solid fa-circle-xmark toast-icon';
    } else {
        toast.classList.remove('error');
        toastIcon.className = 'fa-solid fa-circle-check toast-icon';
    }
    
    toast.classList.remove('hidden');
    
    setTimeout(() => {
        toast.classList.add('hidden');
    }, 3000);
}

// Format datetime helper
function formatDateTime(isoString) {
    if (!isoString) return '-';
    try {
        const date = new Date(isoString);
        return date.toLocaleString('en-IN', {
            day: '2-digit',
            month: 'short',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            hour12: true
        });
    } catch (e) {
        return isoString;
    }
}

// -------------------------------------------------------------
// Tab Navigation
// -------------------------------------------------------------
navItems.forEach(item => {
    item.addEventListener('click', () => {
        const targetTab = item.getAttribute('data-tab');
        if (currentTab === targetTab) return;
        
        if (!document.startViewTransition) {
            switchTab(targetTab, item);
        } else {
            document.startViewTransition(() => {
                switchTab(targetTab, item);
            });
        }
    });
});

function switchTab(targetTab, activeItem) {
    // Update active class
    navItems.forEach(btn => btn.classList.remove('active'));
    activeItem.classList.add('active');
    
    // Show panel
    tabPanels.forEach(panel => {
        if (panel.id === targetTab) {
            panel.classList.add('active');
        } else {
            panel.classList.remove('active');
        }
    });
    
    currentTab = targetTab;
    updateHeaderMetadata();
    
    // Tab specific actions
    if (targetTab === 'analytics-tab') {
        loadAnalyticsData();
    } else if (targetTab === 'leads-tab') {
        loadLeadsData();
    } else if (targetTab === 'catalog-tab') {
        loadCatalogData();
    } else if (targetTab === 'settings-tab') {
        loadSettingsData();
    }
}

function updateHeaderMetadata() {
    switch (currentTab) {
        case 'analytics-tab':
            pageTitle.textContent = 'Analytics Overview';
            pageSubtitle.textContent = 'Real-time performance and insights';
            break;
        case 'leads-tab':
            pageTitle.textContent = 'Leads Inbox';
            pageSubtitle.textContent = 'Monitor customer inquiries and live chats';
            break;
        case 'catalog-tab':
            pageTitle.textContent = 'Cables Catalog Manager';
            pageSubtitle.textContent = 'Adjust prices and toggle cable stock availability';
            break;
        case 'settings-tab':
            pageTitle.textContent = 'Bot Configuration';
            pageSubtitle.textContent = 'Configure greeting messages and images';
            break;
    }
}

// -------------------------------------------------------------
// 1. Analytics & Charts
// -------------------------------------------------------------
function animateValue(obj, start, end, duration) {
    let startTimestamp = null;
    const step = (timestamp) => {
        if (!startTimestamp) startTimestamp = timestamp;
        const progress = Math.min((timestamp - startTimestamp) / duration, 1);
        // easeOutQuart
        const ease = 1 - Math.pow(1 - progress, 4);
        obj.innerHTML = Math.floor(ease * (end - start) + start);
        if (progress < 1) {
            window.requestAnimationFrame(step);
        }
    };
    window.requestAnimationFrame(step);
}

async function loadAnalyticsData() {
    try {
        const res = await fetch('/api/dashboard/stats');
        const data = await res.json();
        
        // Update Stats Counters with Animation
        animateValue(document.getElementById('stat-total-leads'), 0, data.total_leads || 0, 400);
        animateValue(document.getElementById('stat-new-leads'), 0, data.new_leads || 0, 400);
        animateValue(document.getElementById('stat-quoted-leads'), 0, data.quoted_leads || 0, 400);
        animateValue(document.getElementById('stat-won-leads'), 0, data.won_leads || 0, 400);
        
        // Load Charts
        renderProductChart(data.category_distribution || {});
        renderStatusChart(data);
    } catch (e) {
        console.error('Error fetching analytics stats:', e);
        showToast('Failed to load analytics statistics', true);
    }
}

function renderProductChart(distribution) {
    const ctx = document.getElementById('productChart').getContext('2d');
    
    // Destroy existing chart if it exists
    if (productChart) {
        productChart.destroy();
    }
    
    const labels = Object.keys(distribution);
    const data = Object.values(distribution);
    
    if (labels.length === 0) {
        labels.push('No Data');
        data.push(1);
    }
    
    productChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: [
                    '#06b6d4', // Cyan
                    '#6366f1', // Indigo
                    '#10b981', // Emerald
                    '#a855f7', // Purple
                    '#f59e0b', // Amber
                    '#f43f5e'  // Rose
                ],
                borderWidth: 2,
                borderColor: '#111827'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: '#94a3b8',
                        font: { family: 'Inter', size: 11, weight: '500' },
                        padding: 15
                    }
                }
            },
            cutout: '65%'
        }
    });
}

function renderStatusChart(stats) {
    const ctx = document.getElementById('statusChart').getContext('2d');
    
    if (statusChart) {
        statusChart.destroy();
    }
    
    const leads = leadsData.length ? leadsData : [];
    const counts = {
        'New': stats.new_leads || 0,
        'Contacted': 0,
        'Quoted': stats.quoted_leads || 0,
        'Won': stats.won_leads || 0,
        'Lost': 0
    };
    
    // Count remaining statuses if we have raw data, else fallback to API
    leadsData.forEach(lead => {
        if (lead.status === 'Contacted') counts['Contacted']++;
        if (lead.status === 'Lost') counts['Lost']++;
    });
    
    statusChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['New', 'Contacted', 'Quoted', 'Won', 'Lost'],
            datasets: [{
                label: 'Inquiries',
                data: [counts['New'], counts['Contacted'], counts['Quoted'], counts['Won'], counts['Lost']],
                backgroundColor: [
                    'rgba(245, 158, 11, 0.4)',  // Amber
                    'rgba(99, 102, 241, 0.4)',   // Indigo
                    'rgba(168, 85, 247, 0.4)',  // Purple
                    'rgba(16, 185, 129, 0.4)',  // Emerald
                    'rgba(244, 63, 94, 0.4)'    // Rose
                ],
                borderColor: [
                    '#f59e0b',
                    '#6366f1',
                    '#a855f7',
                    '#10b981',
                    '#f43f5e'
                ],
                borderWidth: 2,
                borderRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#94a3b8', font: { family: 'Inter' }, stepSize: 1 }
                },
                x: {
                    grid: { display: false },
                    ticks: { color: '#94a3b8', font: { family: 'Inter', weight: '600' } }
                }
            }
        }
    });
}

// -------------------------------------------------------------
// 2. Leads Inbox & Chats
// -------------------------------------------------------------
let statusFilter = 'All';
let searchQuery = '';
let searchTimeout = null;

const searchInput = document.getElementById('lead-search-input');
const filterButtons = document.querySelectorAll('.filter-btn');

searchInput.addEventListener('input', (e) => {
    clearTimeout(searchTimeout);
    searchQuery = e.target.value;
    searchTimeout = setTimeout(() => {
        loadLeadsData();
    }, 450);
});

filterButtons.forEach(btn => {
    btn.addEventListener('click', () => {
        filterButtons.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        statusFilter = btn.getAttribute('data-filter');
        loadLeadsData();
    });
});

async function loadLeadsData() {
    const listContainer = document.getElementById('leads-list-container');
    const loadingEl = document.getElementById('leads-list-loading');
    
    loadingEl.style.display = 'block';
    
    try {
        let url = '/api/leads';
        const params = [];
        if (statusFilter !== 'All') params.push(`status=${statusFilter}`);
        if (searchQuery) params.push(`search=${encodeURIComponent(searchQuery)}`);
        
        if (params.length > 0) {
            url += '?' + params.join('&');
        }
        
        const res = await fetch(url);
        leadsData = await res.json();
        
        loadingEl.style.display = 'none';
        listContainer.innerHTML = '';
        
        if (leadsData.length === 0) {
            listContainer.innerHTML = `
                <div class="text-center text-muted" style="padding: 2rem 0;">
                    <i class="fa-solid fa-folder-open" style="font-size: 2rem; margin-bottom: 0.5rem; display: block; opacity: 0.5;"></i>
                    No leads found
                </div>
            `;
            return;
        }
        
        leadsData.forEach(lead => {
            const dateStr = formatDateTime(lead.created_at);
            const statusClass = lead.status.toLowerCase();
            const isActive = selectedLead && selectedLead.id === lead.id ? 'active' : '';
            
            const cardHtml = `
                <div class="lead-item ${isActive}" data-id="${lead.id}">
                    <div class="lead-item-header">
                        <span class="lead-item-name">${lead.name}</span>
                        <span class="status-badge ${statusClass}">${lead.status}</span>
                    </div>
                    <div class="lead-item-body">
                        <span><strong>Company:</strong> ${lead.company || 'Individual'}</span>
                        <span><strong>Product:</strong> ${lead.product_interest}</span>
                    </div>
                    <div class="lead-item-meta">
                        <span><i class="fa-solid fa-phone"></i> +${lead.phone}</span>
                        <span>${dateStr}</span>
                    </div>
                </div>
            `;
            listContainer.insertAdjacentHTML('beforeend', cardHtml);
        });
        
        // Add click events to items
        document.querySelectorAll('.lead-item').forEach(item => {
            item.addEventListener('click', () => {
                const id = parseInt(item.getAttribute('data-id'), 10);
                const lead = leadsData.find(l => l.id === id);
                selectLead(lead);
            });
        });
        
        // Re-highlight if the selected lead is in the list
        if (selectedLead) {
            const currentItem = document.querySelector(`.lead-item[data-id="${selectedLead.id}"]`);
            if (currentItem) currentItem.classList.add('active');
        }
    } catch (e) {
        console.error('Error loading leads:', e);
        loadingEl.style.display = 'none';
        showToast('Failed to load leads list', true);
    }
}

function selectLead(lead) {
    selectedLead = lead;
    
    // Highlight active card
    document.querySelectorAll('.lead-item').forEach(item => item.classList.remove('active'));
    const activeCard = document.querySelector(`.lead-item[data-id="${lead.id}"]`);
    if (activeCard) activeCard.classList.add('active');
    
    // Toggle UI panels
    document.getElementById('detail-empty-state').classList.add('hidden');
    document.getElementById('detail-content-area').classList.remove('hidden');
    
    // Populate details
    document.getElementById('detail-name').textContent = lead.name;
    document.getElementById('detail-company').textContent = lead.company || 'Individual/Personal Use';
    document.getElementById('detail-phone').textContent = `+${lead.phone}`;
    document.getElementById('detail-location').textContent = lead.location || '-';
    document.getElementById('detail-product').textContent = lead.product_interest;
    document.getElementById('detail-qty').textContent = lead.quantity || '-';
    document.getElementById('detail-date').textContent = formatDateTime(lead.created_at);
    
    // Setup Avatar Initials
    const initials = lead.name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase();
    document.getElementById('detail-avatar').textContent = initials;
    
    // Setup status dropdown
    const statusSelect = document.getElementById('lead-status-select');
    statusSelect.value = lead.status;
    
    // Fetch and load chat history
    loadChatHistory(lead.phone);
}

// Update lead status
document.getElementById('lead-status-select').addEventListener('change', async (e) => {
    if (!selectedLead) return;
    
    const newStatus = e.target.value;
    try {
        const res = await fetch(`/api/leads/${selectedLead.id}/status`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: newStatus })
        });
        
        if (res.ok) {
            showToast(`Lead status updated to "${newStatus}"`);
            selectedLead.status = newStatus;
            
            // Reload list and status chart
            loadLeadsData();
            loadAnalyticsData();
        } else {
            showToast('Failed to update lead status', true);
        }
    } catch (err) {
        console.error('Error updating status:', err);
        showToast('Error updating lead status', true);
    }
});

async function loadChatHistory(phone) {
    const chatContainer = document.getElementById('chat-bubbles-container');
    chatContainer.innerHTML = '<div class="text-center text-muted" style="padding: 2rem 0;"><i class="fa-solid fa-spinner fa-spin"></i> Loading messages...</div>';
    
    try {
        const res = await fetch(`/api/leads/${phone}/history`);
        const chats = await res.json();
        
        chatContainer.innerHTML = '';
        
        if (chats.length === 0) {
            chatContainer.innerHTML = '<div class="text-center text-muted" style="padding: 2rem 0;">No chat history found.</div>';
            return;
        }
        
        chats.forEach(chat => {
            const isUser = chat.direction === 'inbound';
            const rowClass = isUser ? 'inbound' : 'outbound';
            const timeStr = new Date(chat.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            
            // Clean text formatting for WhatsApp formatting: *bold* -> <strong>
            let formattedBody = chat.body
                .replace(/\*(.*?)\*/g, '<strong>$1</strong>')
                .replace(/\n/g, '<br>');
                
            const bubbleHtml = `
                <div class="chat-bubble-row ${rowClass}">
                    <div class="chat-bubble">
                        <div class="chat-bubble-body">${formattedBody}</div>
                        <span class="chat-bubble-time">${timeStr}</span>
                    </div>
                </div>
            `;
            chatContainer.insertAdjacentHTML('beforeend', bubbleHtml);
        });
        
        // Auto scroll to bottom
        chatContainer.scrollTop = chatContainer.scrollHeight;
    } catch (e) {
        console.error('Error loading chats:', e);
        chatContainer.innerHTML = '<div class="text-center text-rose-500" style="padding: 2rem 0;">Failed to load chat history.</div>';
    }
}

// -------------------------------------------------------------
// 3. Cables Catalog
// -------------------------------------------------------------
const categorySelect = document.getElementById('category-select');

categorySelect.addEventListener('change', () => {
    loadCatalogData();
});

async function loadCatalogData() {
    const tableBody = document.getElementById('catalog-table-body');
    tableBody.innerHTML = `
        <tr>
            <td colspan="7" class="text-center" style="padding: 3rem 0;">
                <i class="fa-solid fa-spinner fa-spin"></i> Loading catalog...
            </td>
        </tr>
    `;
    
    try {
        const res = await fetch('/api/products');
        catalogData = await res.json();
        
        const filter = categorySelect.value;
        const filteredProducts = filter === 'All' 
            ? catalogData 
            : catalogData.filter(p => p.category === filter);
            
        tableBody.innerHTML = '';
        
        if (filteredProducts.length === 0) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="7" class="text-center text-muted" style="padding: 3rem 0;">
                        No products found
                    </td>
                </tr>
            `;
            return;
        }
        
        filteredProducts.forEach(product => {
            const stockOptions = ['In Stock', 'Out of Stock', 'Custom Only'].map(opt => {
                const selected = product.stock_status === opt ? 'selected' : '';
                return `<option value="${opt}" ${selected}>${opt}</option>`;
            }).join('');
            
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><span class="text-secondary">${product.category}</span></td>
                <td><strong>${product.name}</strong></td>
                <td>${product.conductor}</td>
                <td>${product.size}</td>
                <td>${product.core} core</td>
                <td>
                    <span class="editable-price" data-name="${product.name}">
                        ${product.price_per_meter !== null ? 'INR ' + product.price_per_meter.toFixed(2) : 'N/A'}
                    </span>
                </td>
                <td>
                    <select class="catalog-status-select" data-name="${product.name}">
                        ${stockOptions}
                    </select>
                </td>
            `;
            tableBody.appendChild(tr);
        });
        
        // Add double click & click edit event to price cells
        document.querySelectorAll('.editable-price').forEach(cell => {
            cell.addEventListener('click', function() {
                startEditingPrice(this);
            });
        });
        
        // Add change event to stock selectors
        document.querySelectorAll('.catalog-status-select').forEach(select => {
            select.addEventListener('change', function() {
                updateProductStock(this.getAttribute('data-name'), this.value, this);
            });
        });
    } catch (e) {
        console.error('Error loading catalog:', e);
        tableBody.innerHTML = `
            <tr>
                <td colspan="7" class="text-center text-rose-500" style="padding: 3rem 0;">
                    Failed to load catalog products
                </td>
            </tr>
        `;
    }
}

function startEditingPrice(element) {
    // If already editing, ignore
    if (element.querySelector('input')) return;
    
    const productName = element.getAttribute('data-name');
    const currentPriceText = element.textContent.trim().replace('INR ', '');
    const currentPrice = parseFloat(currentPriceText);
    
    const input = document.createElement('input');
    input.type = 'number';
    input.step = '0.01';
    input.className = 'editable-price-input';
    input.value = isNaN(currentPrice) ? '' : currentPrice;
    
    element.textContent = '';
    element.appendChild(input);
    input.focus();
    input.select();
    
    // Save function
    const savePrice = async () => {
        const newPrice = parseFloat(input.value);
        if (isNaN(newPrice) || newPrice < 0) {
            showToast('Please enter a valid price', true);
            element.textContent = isNaN(currentPrice) ? 'N/A' : `INR ${currentPrice.toFixed(2)}`;
            return;
        }
        
        // Get sibling select value for stock status
        const tr = element.closest('tr');
        const select = tr.querySelector('.catalog-status-select');
        const stockStatus = select.value;
        
        try {
            const res = await fetch(`/api/products/${encodeURIComponent(productName)}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ price: newPrice, stock_status: stockStatus })
            });
            
            if (res.ok) {
                showToast(`Updated price for ${productName} to INR ${newPrice.toFixed(2)}/m`);
                element.textContent = `INR ${newPrice.toFixed(2)}`;
                // Update local model
                const localProd = catalogData.find(p => p.name === productName);
                if (localProd) localProd.price_per_meter = newPrice;
            } else {
                showToast('Failed to update price', true);
                element.textContent = `INR ${currentPrice.toFixed(2)}`;
            }
        } catch (err) {
            console.error('Error updating price:', err);
            showToast('Error saving price change', true);
            element.textContent = `INR ${currentPrice.toFixed(2)}`;
        }
    };
    
    input.addEventListener('blur', savePrice);
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            savePrice();
        } else if (e.key === 'Escape') {
            input.removeEventListener('blur', savePrice);
            element.textContent = `INR ${currentPrice.toFixed(2)}`;
        }
    });
}

async function updateProductStock(productName, stockStatus, selectElement) {
    // Find local price
    const localProd = catalogData.find(p => p.name === productName);
    const price = localProd ? localProd.price_per_meter : 0;
    
    try {
        const res = await fetch(`/api/products/${encodeURIComponent(productName)}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ price: price, stock_status: stockStatus })
        });
        
        if (res.ok) {
            showToast(`Updated stock status for ${productName} to "${stockStatus}"`);
            if (localProd) localProd.stock_status = stockStatus;
        } else {
            showToast('Failed to update stock status', true);
            // Revert value
            if (localProd) selectElement.value = localProd.stock_status;
        }
    } catch (err) {
        console.error('Error updating stock:', err);
        showToast('Error saving stock change', true);
        if (localProd) selectElement.value = localProd.stock_status;
    }
}

// -------------------------------------------------------------
// Global Actions
// -------------------------------------------------------------
refreshBtn.addEventListener('click', () => {
    const originalContent = refreshBtn.innerHTML;
    refreshBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Refreshing...';
    refreshBtn.disabled = true;
    
    Promise.all([
        loadAnalyticsData(),
        currentTab === 'leads-tab' ? loadLeadsData() : Promise.resolve(),
        currentTab === 'catalog-tab' ? loadCatalogData() : Promise.resolve()
    ]).then(() => {
        setTimeout(() => {
            refreshBtn.innerHTML = originalContent;
            refreshBtn.disabled = false;
            showToast('All dashboard data refreshed');
        }, 300);
    }).catch(err => {
        refreshBtn.innerHTML = originalContent;
        refreshBtn.disabled = false;
        showToast('Failed to refresh data', true);
    });
});

// Initial Load
document.addEventListener('DOMContentLoaded', () => {
    // Load analytics tab first
    loadAnalyticsData();
    
    // Fetch leads raw data silently to count statuses for charts correctly
    fetch('/api/leads')
        .then(res => res.json())
        .then(data => {
            leadsData = data;
            loadAnalyticsData(); // Redraw chart once we have total list
        })
        .catch(err => console.warn('Silent lead load failed:', err));
});

// -------------------------------------------------------------
// Settings Tab Logic
// -------------------------------------------------------------
const welcomeImageInput = document.getElementById('welcome-image');
const welcomeTextInput = document.getElementById('welcome-text');
const previewImageName = document.getElementById('preview-image-name');
const previewText = document.getElementById('preview-text');
const saveSettingsBtn = document.getElementById('save-settings-btn');

function updateLivePreview() {
    const imgVal = welcomeImageInput ? (welcomeImageInput.value || 'kdi-logo-white-bg.jpg') : 'kdi-logo-white-bg.jpg';
    const textVal = welcomeTextInput ? (welcomeTextInput.value || 'Hi {profile_name}! \ud83d\udc4b\nWelcome to *KDI Power*!') : '';

    if (previewImageName) previewImageName.textContent = imgVal;

    if (previewText) {
        let formattedText = textVal
            .replace(/{profile_name}/g, 'Rajesh')
            .replace(/\n/g, '<br>')
            .replace(/\*(.*?)\*/g, '<strong>$1</strong>');
        previewText.innerHTML = formattedText;
    }
}

if (welcomeImageInput && welcomeTextInput) {
    welcomeImageInput.addEventListener('input', updateLivePreview);
    welcomeTextInput.addEventListener('input', updateLivePreview);
}

function loadSettingsData() {
    fetch('/api/settings')
        .then(res => res.json())
        .then(data => {
            if (welcomeImageInput && data.welcome_image) welcomeImageInput.value = data.welcome_image;
            if (welcomeTextInput && data.welcome_text) welcomeTextInput.value = data.welcome_text;
            updateLivePreview();
        })
        .catch(err => {
            showToast('Failed to load configuration', true);
            console.error('Settings load error:', err);
        });
}

if (saveSettingsBtn) {
    saveSettingsBtn.addEventListener('click', () => {
        const payload = {
            welcome_image: welcomeImageInput.value.trim(),
            welcome_text: welcomeTextInput.value.trim()
        };

        saveSettingsBtn.disabled = true;
        saveSettingsBtn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Saving...';

        fetch('/api/settings', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        })
        .then(res => {
            if (!res.ok) throw new Error('Network response was not ok');
            return res.json();
        })
        .then(data => {
            showToast('Configuration saved successfully!');
            saveSettingsBtn.disabled = false;
            saveSettingsBtn.innerHTML = '<i class="fa-solid fa-save"></i> Save configuration';
        })
        .catch(err => {
            showToast('Failed to save configuration', true);
            saveSettingsBtn.disabled = false;
            saveSettingsBtn.innerHTML = '<i class="fa-solid fa-save"></i> Save configuration';
        });
    });
}
