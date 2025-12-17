// WaveApp Invoice Generator - Frontend JavaScript

document.addEventListener('DOMContentLoaded', function() {
    console.log('WaveApp Invoice Generator loaded');
    
    // Initialize features
    initSelectSearch();
    initFormValidation();
    initAjaxRefresh();
});

/**
 * Add search/filter functionality to select dropdowns
 */
function initSelectSearch() {
    const selects = document.querySelectorAll('select[data-search="true"]');
    
    selects.forEach(select => {
        // Simple filter on keypress (for browsers that support it)
        select.addEventListener('focus', function() {
            this.size = Math.min(this.options.length, 10);
        });
        
        select.addEventListener('blur', function() {
            this.size = 1;
        });
        
        select.addEventListener('change', function() {
            this.size = 1;
        });
    });
}

/**
 * Form validation helpers
 */
function initFormValidation() {
    const forms = document.querySelectorAll('form[data-validate="true"]');
    
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!validateForm(this)) {
                e.preventDefault();
                showError('Please fill in all required fields');
            }
        });
    });
}

function validateForm(form) {
    const requiredFields = form.querySelectorAll('[required]');
    let isValid = true;
    
    requiredFields.forEach(field => {
        if (!field.value || field.value.trim() === '') {
            field.classList.add('error');
            isValid = false;
        } else {
            field.classList.remove('error');
        }
    });
    
    return isValid;
}

/**
 * AJAX refresh functionality for customers and products
 */
function initAjaxRefresh() {
    // Add refresh buttons if they exist
    const refreshCustomersBtn = document.getElementById('refresh-customers');
    const refreshProductsBtn = document.getElementById('refresh-products');
    
    if (refreshCustomersBtn) {
        refreshCustomersBtn.addEventListener('click', function(e) {
            e.preventDefault();
            refreshCustomers();
        });
    }
    
    if (refreshProductsBtn) {
        refreshProductsBtn.addEventListener('click', function(e) {
            e.preventDefault();
            refreshProducts();
        });
    }
}

/**
 * Refresh customers from API
 */
async function refreshCustomers() {
    try {
        showLoading('Refreshing customers...');
        const response = await fetch('/api/customers');
        
        if (!response.ok) {
            throw new Error('Failed to fetch customers');
        }
        
        const customers = await response.json();
        updateCustomerSelects(customers);
        showSuccess(`Loaded ${customers.length} customers`);
    } catch (error) {
        showError('Failed to refresh customers: ' + error.message);
    }
}

/**
 * Refresh products from API
 */
async function refreshProducts() {
    try {
        showLoading('Refreshing services...');
        const response = await fetch('/api/products');
        
        if (!response.ok) {
            throw new Error('Failed to fetch products');
        }
        
        const products = await response.json();
        updateProductSelects(products);
        showSuccess(`Loaded ${products.length} services`);
    } catch (error) {
        showError('Failed to refresh services: ' + error.message);
    }
}

/**
 * Update all customer select dropdowns
 */
function updateCustomerSelects(customers) {
    const selects = document.querySelectorAll('.select-customer');
    
    selects.forEach(select => {
        const currentValue = select.value;
        
        // Clear and rebuild options
        select.innerHTML = '<option value="">Select customer...</option>';
        
        customers.forEach(customer => {
            const option = document.createElement('option');
            option.value = customer.id;
            option.textContent = customer.name;
            if (customer.email) {
                option.textContent += ` (${customer.email})`;
            }
            
            if (customer.id === currentValue) {
                option.selected = true;
            }
            
            select.appendChild(option);
        });
    });
}

/**
 * Update all product select dropdowns
 */
function updateProductSelects(products) {
    const selects = document.querySelectorAll('.select-service');
    
    selects.forEach(select => {
        const currentValue = select.value;
        
        // Clear and rebuild options
        select.innerHTML = '<option value="">Select service...</option>';
        
        products.forEach(product => {
            const option = document.createElement('option');
            option.value = product.id;
            option.textContent = `${product.name} - $${product.price.toFixed(2)}/hr`;
            option.setAttribute('data-price', product.price);
            
            if (product.id === currentValue) {
                option.selected = true;
            }
            
            select.appendChild(option);
        });
    });
}

/**
 * Show loading message
 */
function showLoading(message) {
    // Create or update loading element
    let loader = document.getElementById('global-loader');
    if (!loader) {
        loader = document.createElement('div');
        loader.id = 'global-loader';
        loader.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #667eea;
            color: white;
            padding: 15px 25px;
            border-radius: 8px;
            box-shadow: 0 5px 20px rgba(0,0,0,0.2);
            z-index: 9999;
            display: flex;
            align-items: center;
            gap: 10px;
        `;
        document.body.appendChild(loader);
    }
    
    loader.innerHTML = `
        <div class="spinner"></div>
        <span>${message}</span>
    `;
    loader.style.display = 'flex';
}

/**
 * Show success message
 */
function showSuccess(message) {
    hideLoading();
    showToast(message, 'success');
}

/**
 * Show error message
 */
function showError(message) {
    hideLoading();
    showToast(message, 'error');
}

/**
 * Hide loading indicator
 */
function hideLoading() {
    const loader = document.getElementById('global-loader');
    if (loader) {
        loader.style.display = 'none';
    }
}

/**
 * Show temporary toast notification
 */
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `flash ${type}`;
    toast.textContent = message;
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        min-width: 300px;
        z-index: 9999;
        animation: slideIn 0.3s ease;
    `;
    
    document.body.appendChild(toast);
    
    // Auto-remove after 3 seconds
    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

/**
 * Utility: Format currency
 */
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(amount);
}

/**
 * Utility: Format hours
 */
function formatHours(hours) {
    return hours.toFixed(2) + 'h';
}

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
    
    .error {
        border-color: #fc8181 !important;
    }
`;
document.head.appendChild(style);
