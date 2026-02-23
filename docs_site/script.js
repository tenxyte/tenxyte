
// Tenxyte API Documentation JavaScript

// Tab switching
function switchTab(button, tabId) {
    // Remove active class from all buttons and contents
    const tabButtons = button.parentElement.querySelectorAll('.tab-btn');
    const tabContents = button.parentElement.parentElement.querySelectorAll('.tab-content');
    
    tabButtons.forEach(btn => btn.classList.remove('active'));
    tabContents.forEach(content => content.classList.remove('active'));
    
    // Add active class to clicked button and corresponding content
    button.classList.add('active');
    document.getElementById(tabId).classList.add('active');
}

// Copy code functionality
function copyCode(button) {
    const codeBlock = button.closest('.code-block');
    const code = codeBlock.querySelector('code');
    const text = code.textContent;
    
    navigator.clipboard.writeText(text).then(() => {
        const originalText = button.textContent;
        button.textContent = 'Copied!';
        button.style.background = '#10b981';
        
        setTimeout(() => {
            button.textContent = originalText;
            button.style.background = '';
        }, 2000);
    }).catch(err => {
        console.error('Failed to copy code:', err);
    });
}

// Search functionality
function performSearch() {
    const query = document.getElementById('searchInput').value.toLowerCase();
    if (!query) return;
    
    // Load search index
    fetch('search.json')
        .then(response => response.json())
        .then(data => {
            const results = data.pages.filter(page => 
                page.title.toLowerCase().includes(query) || 
                page.content.toLowerCase().includes(query)
            );
            
            displaySearchResults(results, query);
        })
        .catch(err => console.error('Search failed:', err));
}

function displaySearchResults(results, query) {
    // This would typically show results in a modal or dedicated page
    console.log(`Search results for "${query}":`, results);
    
    // For now, just alert the first result
    if (results.length > 0) {
        alert(`Found ${results.length} results. First result: ${results[0].title}`);
    } else {
        alert(`No results found for "${query}"`);
    }
}

// Smooth scrolling for anchor links
document.addEventListener('DOMContentLoaded', function() {
    const links = document.querySelectorAll('a[href^="#"]');
    links.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
});

// Highlight current navigation item
function highlightCurrentNav() {
    const currentPath = window.location.pathname.split('/').pop();
    const navLinks = document.querySelectorAll('.nav-menu a');
    
    navLinks.forEach(link => {
        const linkPath = link.getAttribute('href');
        if (linkPath === currentPath) {
            link.style.color = 'var(--primary-color)';
            link.style.fontWeight = '600';
        }
    });
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    highlightCurrentNav();
    
    // Add keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        // Ctrl/Cmd + K for search
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            document.getElementById('searchInput').focus();
        }
    });
});

// API request examples (for interactive testing)
function testApiRequest(endpoint, method = 'GET', data = null) {
    const baseUrl = 'https://api.tenxyte.com';
    const url = baseUrl + endpoint;
    
    const options = {
        method: method,
        headers: {
            'Content-Type': 'application/json'
        }
    };
    
    if (data) {
        options.body = JSON.stringify(data);
    }
    
    // This would require CORS to be properly configured
    // For now, just log the request
    console.log('API Request:', { url, method, data });
    alert('API requests are for demonstration only. Use Postman collection for actual testing.');
}
