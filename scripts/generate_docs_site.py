#!/usr/bin/env python3
"""
Documentation Site Generator

This script generates a static documentation website from the OpenAPI specification:
1. Creates HTML documentation pages
2. Generates interactive API explorer
3. Includes code examples in multiple languages
4. Creates responsive design
5. Generates search index
"""

import json
import sys
import os
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
import base64

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class DocumentationSiteGenerator:
    """Generates static documentation website."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.schema_file = self.project_root / 'openapi_schema_optimized.json'
        self.output_dir = self.project_root / 'docs_site'
        self.schema = {}
        
    def generate_site(self) -> bool:
        """Generate the complete documentation site."""
        print("🌐 Generating documentation website...")
        
        # Load schema
        self.schema = self.load_schema()
        if not self.schema:
            return False
        
        # Create output directory
        self.output_dir.mkdir(exist_ok=True)
        
        # Generate components
        self.generate_index_page()
        self.generate_api_reference()
        self.generate_examples_page()
        self.generate_authentication_guide()
        self.generate_migration_guide()
        self.generate_assets()
        self.generate_search_index()
        
        print(f"📁 Documentation site generated in: {self.output_dir}")
        return True
    
    def load_schema(self) -> Dict:
        """Load OpenAPI schema."""
        if not self.schema_file.exists():
            # Try original schema if optimized doesn't exist
            self.schema_file = self.project_root / 'openapi_schema.json'
        
        if not self.schema_file.exists():
            print(f"❌ Schema file not found")
            return {}
        
        try:
            with open(self.schema_file, 'r', encoding='utf-8') as f:
                schema = json.load(f)
            print(f"📋 Loaded schema from: {self.schema_file}")
            return schema
        except Exception as e:
            print(f"❌ Failed to load schema: {e}")
            return {}
    
    def generate_index_page(self):
        """Generate the main index page."""
        html_content = self.get_html_template(
            title="Tenxyte API Documentation",
            description="Comprehensive API documentation for the Tenxyte authentication and authorization system",
            content=self.get_index_content()
        )
        
        with open(self.output_dir / 'index.html', 'w', encoding='utf-8') as f:
            f.write(html_content)
    
    def get_index_content(self) -> str:
        """Get index page content."""
        return f"""
        <div class="hero-section">
            <h1 class="hero-title">Tenxyte API Documentation</h1>
            <p class="hero-subtitle">
                Enhanced DRF Spectacular Documentation for Authentication, Authorization, and Multi-tenant Management
            </p>
            <div class="hero-actions">
                <a href="api-reference.html" class="btn btn-primary">API Reference</a>
                <a href="examples.html" class="btn btn-secondary">Code Examples</a>
                <a href="authentication.html" class="btn btn-outline">Authentication Guide</a>
            </div>
        </div>
        
        <div class="features-section">
            <h2>Key Features</h2>
            <div class="features-grid">
                <div class="feature-card">
                    <div class="feature-icon">🔐</div>
                    <h3>Advanced Authentication</h3>
                    <p>JWT tokens, 2FA, magic links, WebAuthn, and social authentication</p>
                </div>
                <div class="feature-card">
                    <div class="feature-icon">🏢</div>
                    <h3>Multi-tenant Support</h3>
                    <p>Organization management, role-based access control, and hierarchical permissions</p>
                </div>
                <div class="feature-card">
                    <div class="feature-icon">🔒</div>
                    <h3>Security & Privacy</h3>
                    <p>GDPR compliance, device management, audit logging, and account deletion flows</p>
                </div>
                <div class="feature-card">
                    <div class="feature-icon">📊</div>
                    <h3>Admin Dashboard</h3>
                    <p>Comprehensive admin tools, analytics, and organization management</p>
                </div>
            </div>
        </div>
        
        <div class="quick-start-section">
            <h2>Quick Start</h2>
            <div class="code-block">
                <div class="code-header">
                    <span>bash</span>
                    <button class="copy-btn" onclick="copyCode(this)">Copy</button>
                </div>
                <pre><code># Login to get access token
curl -X POST https://api.tenxyte.com/api/auth/login/email/ \\
  -H "Content-Type: application/json" \\
  -d '{{
    "email": "user@example.com",
    "password": "your-password"
  }}'

# Use token for authenticated requests
curl -X GET https://api.tenxyte.com/api/auth/me/ \\
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"</code></pre>
            </div>
        </div>
        
        <div class="stats-section">
            <h2>API Statistics</h2>
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-number">{len(self.schema.get('paths', {}))}</div>
                    <div class="stat-label">Endpoints</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{len(self.schema.get('components', {}).get('schemas', {}))}</div>
                    <div class="stat-label">Schemas</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">8</div>
                    <div class="stat-label">Authentication Methods</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">100%</div>
                    <div class="stat-label">Documentation Coverage</div>
                </div>
            </div>
        </div>
        """
    
    def generate_api_reference(self):
        """Generate API reference page."""
        paths = self.schema.get('paths', {})
        content = "<div class='api-reference'>"
        
        # Group paths by category
        categories = self.categorize_paths(paths)
        
        for category, category_paths in categories.items():
            content += f"<div class='api-category'>"
            content += f"<h2 id='{category.lower().replace(' ', '-')}'>{category}</h2>"
            
            for path, methods in category_paths:
                content += f"<div class='api-endpoint'>"
                content += f"<h3 id='endpoint-{path.replace('/', '-').strip('-')}'>{path}</h3>"
                
                for method, operation in methods.items():
                    if method.upper() in ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']:
                        content += self.generate_method_section(method.upper(), operation, path)
                
                content += f"</div>"
            content += f"</div>"
        
        content += "</div>"
        
        html_content = self.get_html_template(
            title="API Reference - Tenxyte API",
            description="Complete API reference with all endpoints, parameters, and responses",
            content=content
        )
        
        with open(self.output_dir / 'api-reference.html', 'w', encoding='utf-8') as f:
            f.write(html_content)
    
    def categorize_paths(self, paths: Dict) -> Dict[str, List]:
        """Categorize paths by functionality."""
        categories = {
            'Authentication': [],
            'User Management': [],
            'Organizations': [],
            'Security': [],
            'Admin': [],
            'Applications': [],
            'Other': []
        }
        
        for path, path_item in paths.items():
            methods = []
            for method, operation in path_item.items():
                if method.upper() in ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']:
                    methods.append((method, operation))
            
            if methods:
                if '/auth/login' in path or '/auth/register' in path or '/auth/refresh' in path or '/auth/logout' in path:
                    categories['Authentication'].append((path, methods))
                elif '/auth/me' in path:
                    categories['User Management'].append((path, methods))
                elif '/organizations' in path:
                    categories['Organizations'].append((path, methods))
                elif '/admin' in path or '/dashboard' in path:
                    categories['Admin'].append((path, methods))
                elif '/applications' in path:
                    categories['Applications'].append((path, methods))
                elif '/auth/' in path:
                    categories['Security'].append((path, methods))
                else:
                    categories['Other'].append((path, methods))
        
        return {k: v for k, v in categories.items() if v}
    
    def generate_method_section(self, method: str, operation: Dict, path: str) -> str:
        """Generate method documentation section."""
        content = f"<div class='method-section method-{method.lower()}'>"
        content += f"<div class='method-header'>"
        content += f"<span class='method-badge method-{method.lower()}'>{method}</span>"
        content += f"<h4>{operation.get('summary', 'No summary')}</h4>"
        content += f"</div>"
        
        if operation.get('description'):
            content += f"<p class='method-description'>{operation['description']}</p>"
        
        # Parameters
        if operation.get('parameters'):
            content += f"<div class='parameters-section'>"
            content += f"<h5>Parameters</h5>"
            content += f"<table class='parameters-table'>"
            content += f"<thead><tr><th>Name</th><th>Type</th><th>Required</th><th>Description</th></tr></thead>"
            content += f"<tbody>"
            
            for param in operation['parameters']:
                content += f"<tr>"
                content += f"<td><code>{param.get('name', '')}</code></td>"
                content += f"<td>{param.get('type', param.get('schema', {}).get('type', 'string'))}</td>"
                content += f"<td>{'Yes' if param.get('required', False) else 'No'}</td>"
                content += f"<td>{param.get('description', '')}</td>"
                content += f"</tr>"
            
            content += f"</tbody></table></div>"
        
        # Request body
        if operation.get('requestBody'):
            content += f"<div class='request-body-section'>"
            content += f"<h5>Request Body</h5>"
            
            request_body = operation['requestBody']
            if 'content' in request_body:
                for content_type, content_spec in request_body['content'].items():
                    content += f"<div class='content-type'>"
                    content += f"<h6>Content-Type: {content_type}</h6>"
                    
                    if 'schema' in content_spec:
                        content += f"<div class='schema-example'>"
                        content += f"<pre><code>{json.dumps(content_spec['schema'], indent=2)}</code></pre>"
                        content += f"</div>"
                    
                    if 'example' in content_spec:
                        content += f"<div class='example-section'>"
                        content += f"<h6>Example:</h6>"
                        content += f"<div class='code-block'>"
                        content += f"<pre><code>{json.dumps(content_spec['example'], indent=2)}</code></pre>"
                        content += f"</div></div>"
                    
                    content += f"</div>"
            
            content += f"</div>"
        
        # Responses
        if operation.get('responses'):
            content += f"<div class='responses-section'>"
            content += f"<h5>Responses</h5>"
            
            for status_code, response in operation['responses'].items():
                content += f"<div class='response-item'>"
                content += f"<h6>HTTP {status_code} - {response.get('description', '')}</h6>"
                
                if 'content' in response:
                    for content_type, content_spec in response['content'].items():
                        if 'schema' in content_spec:
                            content += f"<div class='response-schema'>"
                            content += f"<pre><code>{json.dumps(content_spec['schema'], indent=2)}</code></pre>"
                            content += f"</div>"
                        
                        if 'example' in content_spec:
                            content += f"<div class='response-example'>"
                            content += f"<h6>Example:</h6>"
                            content += f"<div class='code-block'>"
                            content += f"<pre><code>{json.dumps(content_spec['example'], indent=2)}</code></pre>"
                            content += f"</div></div>"
                
                content += f"</div>"
            
            content += f"</div>"
        
        content += f"</div>"
        return content
    
    def generate_examples_page(self):
        """Generate code examples page."""
        content = """
        <div class="examples-page">
            <h1>Code Examples</h1>
            <p>Practical examples for integrating with the Tenxyte API in various programming languages.</p>
            
            <div class="example-sections">
                <div class="example-section">
                    <h2>Authentication</h2>
                    <div class="example-tabs">
                        <div class="tab-buttons">
                            <button class="tab-btn active" onclick="switchTab(this, 'auth-python')">Python</button>
                            <button class="tab-btn" onclick="switchTab(this, 'auth-javascript')">JavaScript</button>
                            <button class="tab-btn" onclick="switchTab(this, 'auth-curl')">cURL</button>
                        </div>
                        
                        <div class="tab-content active" id="auth-python">
                            <div class="code-block">
                                <div class="code-header">
                                    <span>Python (requests)</span>
                                    <button class="copy-btn" onclick="copyCode(this)">Copy</button>
                                </div>
                                <pre><code>import requests

# Login
response = requests.post('https://api.tenxyte.com/api/auth/login/email/', json={
    'email': 'user@example.com',
    'password': 'your-password'
})

if response.ok:
    data = response.json()
    access_token = data['access']
    
    # Use token for authenticated requests
    headers = {'Authorization': f'Bearer {access_token}'}
    profile = requests.get('https://api.tenxyte.com/api/auth/me/', headers=headers)
    print(profile.json())</code></pre>
                            </div>
                        </div>
                        
                        <div class="tab-content" id="auth-javascript">
                            <div class="code-block">
                                <div class="code-header">
                                    <span>JavaScript (fetch)</span>
                                    <button class="copy-btn" onclick="copyCode(this)">Copy</button>
                                </div>
                                <pre><code>// Login
const response = await fetch('https://api.tenxyte.com/api/auth/login/email/', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        email: 'user@example.com',
        password: 'your-password'
    })
});

const data = await response.json();
const accessToken = data.access;

// Use token for authenticated requests
const profile = await fetch('https://api.tenxyte.com/api/auth/me/', {
    headers: {
        'Authorization': `Bearer ${accessToken}`
    }
});

console.log(await profile.json());</code></pre>
                            </div>
                        </div>
                        
                        <div class="tab-content" id="auth-curl">
                            <div class="code-block">
                                <div class="code-header">
                                    <span>cURL</span>
                                    <button class="copy-btn" onclick="copyCode(this)">Copy</button>
                                </div>
                                <pre><code># Login
curl -X POST https://api.tenxyte.com/api/auth/login/email/ \\
  -H "Content-Type: application/json" \\
  -d '{
    "email": "user@example.com",
    "password": "your-password"
  }'

# Use token for authenticated requests
curl -X GET https://api.tenxyte.com/api/auth/me/ \\
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"</code></pre>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="example-section">
                    <h2>Multi-tenant Requests</h2>
                    <div class="code-block">
                        <div class="code-header">
                            <span>Python - Organization Context</span>
                            <button class="copy-btn" onclick="copyCode(this)">Copy</button>
                        </div>
                        <pre><code>import requests

# Headers with organization context
headers = {
    'Authorization': 'Bearer YOUR_ACCESS_TOKEN',
    'X-Org-Slug': 'acme-corp'
}

# List organization members
response = requests.get(
    'https://api.tenxyte.com/api/auth/organizations/acme-corp/members/',
    headers=headers
)

members = response.json()
print(f"Found {len(members)} members")</code></pre>
                    </div>
                </div>
                
                <div class="example-section">
                    <h2>Error Handling</h2>
                    <div class="code-block">
                        <div class="code-header">
                            <span>Python - Error Handling</span>
                            <button class="copy-btn" onclick="copyCode(this)">Copy</button>
                        </div>
                        <pre><code>import requests
from requests.exceptions import HTTPError

def make_api_request(url, headers=None, json_data=None):
    try:
        response = requests.post(url, headers=headers, json=json_data)
        response.raise_for_status()
        return response.json()
    
    except HTTPError as e:
        error_data = e.response.json()
        error_code = error_data.get('code')
        error_message = error_data.get('error')
        
        if error_code == 'RATE_LIMITED':
            retry_after = e.response.headers.get('Retry-After', 60)
            print(f"Rate limited. Retry after {retry_after} seconds")
        elif error_code == 'INVALID_CREDENTIALS':
            print("Invalid email or password")
        elif error_code == 'ACCOUNT_LOCKED':
            print("Account is temporarily locked")
        else:
            print(f"Error: {error_message}")
        
        return None

# Usage
login_data = {
    'email': 'user@example.com',
    'password': 'your-password'
}

result = make_api_request(
    'https://api.tenxyte.com/api/auth/login/email/',
    json_data=login_data
)</code></pre>
                    </div>
                </div>
            </div>
        </div>
        """
        
        html_content = self.get_html_template(
            title="Code Examples - Tenxyte API",
            description="Practical code examples for integrating with the Tenxyte API",
            content=content
        )
        
        with open(self.output_dir / 'examples.html', 'w', encoding='utf-8') as f:
            f.write(html_content)
    
    def generate_authentication_guide(self):
        """Generate authentication guide page."""
        content = """
        <div class="auth-guide">
            <h1>Authentication Guide</h1>
            <p>Complete guide to authentication methods and security features in the Tenxyte API.</p>
            
            <div class="guide-sections">
                <div class="guide-section">
                    <h2>JWT Token Authentication</h2>
                    <p>The Tenxyte API uses JWT (JSON Web Tokens) for authentication. Here's how it works:</p>
                    
                    <ol class="guide-steps">
                        <li>Send your credentials to the login endpoint</li>
                        <li>Receive access and refresh tokens</li>
                        <li>Include the access token in the Authorization header</li>
                        <li>Refresh the token when it expires</li>
                    </ol>
                    
                    <div class="code-block">
                        <div class="code-header">
                            <span>Token Usage</span>
                            <button class="copy-btn" onclick="copyCode(this)">Copy</button>
                        </div>
                        <pre><code># Include token in requests
curl -X GET https://api.tenxyte.com/api/auth/me/ \\
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."</code></pre>
                    </div>
                </div>
                
                <div class="guide-section">
                    <h2>Two-Factor Authentication (2FA)</h2>
                    <p>Enable 2FA for enhanced security:</p>
                    
                    <div class="code-block">
                        <div class="code-header">
                            <span>Setup 2FA</span>
                            <button class="copy-btn" onclick="copyCode(this)">Copy</button>
                        </div>
                        <pre><code># 1. Setup 2FA
curl -X POST https://api.tenxyte.com/api/auth/2fa/setup/ \\
  -H "Authorization: Bearer YOUR_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{"password": "your-password"}'

# 2. Verify with TOTP app
curl -X POST https://api.tenxyte.com/api/auth/2fa/confirm/ \\
  -H "Authorization: Bearer YOUR_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{"code": "123456"}'</code></pre>
                    </div>
                </div>
                
                <div class="guide-section">
                    <h2>Multi-tenant Authentication</h2>
                    <p>For organization-specific requests, include the X-Org-Slug header:</p>
                    
                    <div class="code-block">
                        <div class="code-header">
                            <span>Multi-tenant Request</span>
                            <button class="copy-btn" onclick="copyCode(this)">Copy</button>
                        </div>
                        <pre><code>curl -X GET https://api.tenxyte.com/api/auth/organizations/members/ \\
  -H "Authorization: Bearer YOUR_TOKEN" \\
  -H "X-Org-Slug: acme-corp"</code></pre>
                    </div>
                </div>
                
                <div class="guide-section">
                    <h2>Security Best Practices</h2>
                    <ul class="best-practices">
                        <li>Always use HTTPS for API requests</li>
                        <li>Store tokens securely (never in localStorage)</li>
                        <li>Implement token refresh before expiry</li>
                        <li>Use 2FA for sensitive operations</li>
                        <li>Validate organization context in multi-tenant apps</li>
                        <li>Handle rate limiting gracefully</li>
                        <li>Log out properly to invalidate tokens</li>
                    </ul>
                </div>
            </div>
        </div>
        """
        
        html_content = self.get_html_template(
            title="Authentication Guide - Tenxyte API",
            description="Complete guide to authentication methods and security features",
            content=content
        )
        
        with open(self.output_dir / 'authentication.html', 'w', encoding='utf-8') as f:
            f.write(html_content)
    
    def generate_migration_guide(self):
        """Generate migration guide page."""
        # Load migration guide content if it exists
        migration_file = self.project_root / 'docs' / 'MIGRATION_GUIDE.md'
        content = "<div class='migration-guide'>"
        content += "<h1>Migration Guide</h1>"
        content += "<p>Guide for migrating from the old API documentation to the new enhanced version.</p>"
        
        if migration_file.exists():
            try:
                with open(migration_file, 'r', encoding='utf-8') as f:
                    md_content = f.read()
                # Convert markdown to basic HTML (simplified)
                content += self.markdown_to_html(md_content)
            except Exception as e:
                content += f"<p>Error loading migration guide: {e}</p>"
        else:
            content += "<p>Migration guide not found. Please refer to the MIGRATION_GUIDE.md file.</p>"
        
        content += "</div>"
        
        html_content = self.get_html_template(
            title="Migration Guide - Tenxyte API",
            description="Guide for migrating to the new API documentation",
            content=content
        )
        
        with open(self.output_dir / 'migration.html', 'w', encoding='utf-8') as f:
            f.write(html_content)
    
    def markdown_to_html(self, md_content: str) -> str:
        """Simple markdown to HTML converter."""
        html = md_content
        
        # Headers
        import re
        html = re.sub(r'^# (.*?)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.*?)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^### (.*?)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
        
        # Bold and italic
        html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html)
        html = re.sub(r'\*(.*?)\*', r'<em>\1</em>', html)
        
        # Code blocks
        html = re.sub(r'```(.*?)```', r'<pre><code>\1</code></pre>', html, flags=re.DOTALL)
        html = re.sub(r'`(.*?)`', r'<code>\1</code>', html)
        
        # Links
        html = re.sub(r'\[(.*?)\]\((.*?)\)', r'<a href="\2">\1</a>', html)
        
        # Lists
        html = re.sub(r'^- (.*?)$', r'<li>\1</li>', html, flags=re.MULTILINE)
        html = re.sub(r'(<li>.*?</li>)', r'<ul>\1</ul>', html, flags=re.DOTALL)
        
        # Paragraphs
        lines = html.split('\n')
        in_paragraph = False
        result = []
        
        for line in lines:
            line = line.strip()
            if not line:
                if in_paragraph:
                    result.append('</p>')
                    in_paragraph = False
                continue
            
            if line.startswith('<') or line.startswith('```'):
                if in_paragraph:
                    result.append('</p>')
                    in_paragraph = False
                result.append(line)
            else:
                if not in_paragraph:
                    result.append('<p>')
                    in_paragraph = True
                result.append(line)
        
        if in_paragraph:
            result.append('</p>')
        
        return '\n'.join(result)
    
    def generate_assets(self):
        """Generate CSS and JavaScript assets."""
        # Generate CSS
        css_content = self.get_css_styles()
        with open(self.output_dir / 'styles.css', 'w', encoding='utf-8') as f:
            f.write(css_content)
        
        # Generate JavaScript
        js_content = self.get_javascript_code()
        with open(self.output_dir / 'script.js', 'w', encoding='utf-8') as f:
            f.write(js_content)
    
    def generate_search_index(self):
        """Generate search index for the documentation."""
        search_index = {
            "pages": [
                {
                    "title": "API Reference",
                    "url": "api-reference.html",
                    "content": "Complete API reference with all endpoints"
                },
                {
                    "title": "Code Examples",
                    "url": "examples.html",
                    "content": "Practical code examples for integration"
                },
                {
                    "title": "Authentication Guide",
                    "url": "authentication.html",
                    "content": "Authentication methods and security features"
                },
                {
                    "title": "Migration Guide",
                    "url": "migration.html",
                    "content": "Migration guide for API documentation"
                }
            ]
        }
        
        with open(self.output_dir / 'search.json', 'w', encoding='utf-8') as f:
            json.dump(search_index, f, indent=2)
    
    def get_html_template(self, title: str, description: str, content: str) -> str:
        """Get complete HTML template."""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <meta name="description" content="{description}">
    <link rel="stylesheet" href="styles.css">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
</head>
<body>
    <header class="header">
        <nav class="nav">
            <div class="nav-container">
                <div class="nav-brand">
                    <h1>Tenxyte API</h1>
                </div>
                <ul class="nav-menu">
                    <li><a href="index.html">Home</a></li>
                    <li><a href="api-reference.html">API Reference</a></li>
                    <li><a href="examples.html">Examples</a></li>
                    <li><a href="authentication.html">Authentication</a></li>
                    <li><a href="migration.html">Migration</a></li>
                </ul>
                <div class="search-box">
                    <input type="text" placeholder="Search documentation..." id="searchInput">
                    <button onclick="performSearch()">🔍</button>
                </div>
            </div>
        </nav>
    </header>
    
    <main class="main">
        <div class="container">
            {content}
        </div>
    </main>
    
    <footer class="footer">
        <div class="container">
            <p>&copy; 2024 Tenxyte. Enhanced DRF Spectacular Documentation.</p>
            <div class="footer-links">
                <a href="https://github.com/tenxyte/tenxyte">GitHub</a>
                <a href="https://api.tenxyte.com/api/docs/">Swagger UI</a>
                <a href="https://api.tenxyte.com/api/redoc/">ReDoc</a>
            </div>
        </div>
    </footer>
    
    <script src="script.js"></script>
</body>
</html>"""
    
    def get_css_styles(self) -> str:
        """Get CSS styles for the documentation site."""
        return """
/* Tenxyte API Documentation Styles */
:root {
    --primary-color: #2563eb;
    --primary-hover: #1d4ed8;
    --secondary-color: #64748b;
    --success-color: #10b981;
    --warning-color: #f59e0b;
    --error-color: #ef4444;
    --background-color: #ffffff;
    --surface-color: #f8fafc;
    --text-color: #1e293b;
    --text-muted: #64748b;
    --border-color: #e2e8f0;
    --code-bg: #f1f5f9;
    --font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: var(--font-family);
    line-height: 1.6;
    color: var(--text-color);
    background-color: var(--background-color);
}

.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 20px;
}

/* Header */
.header {
    background: white;
    border-bottom: 1px solid var(--border-color);
    position: sticky;
    top: 0;
    z-index: 100;
}

.nav-container {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 1rem 2rem;
    max-width: 1200px;
    margin: 0 auto;
}

.nav-brand h1 {
    color: var(--primary-color);
    font-size: 1.5rem;
    font-weight: 700;
}

.nav-menu {
    display: flex;
    list-style: none;
    gap: 2rem;
}

.nav-menu a {
    text-decoration: none;
    color: var(--text-color);
    font-weight: 500;
    transition: color 0.2s;
}

.nav-menu a:hover {
    color: var(--primary-color);
}

.search-box {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.search-box input {
    padding: 0.5rem 1rem;
    border: 1px solid var(--border-color);
    border-radius: 6px;
    font-size: 0.875rem;
}

.search-box button {
    background: none;
    border: none;
    cursor: pointer;
    padding: 0.5rem;
}

/* Main Content */
.main {
    min-height: calc(100vh - 80px);
    padding: 2rem 0;
}

/* Hero Section */
.hero-section {
    text-align: center;
    padding: 4rem 0;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border-radius: 12px;
    margin-bottom: 3rem;
}

.hero-title {
    font-size: 3rem;
    font-weight: 700;
    margin-bottom: 1rem;
}

.hero-subtitle {
    font-size: 1.25rem;
    margin-bottom: 2rem;
    opacity: 0.9;
}

.hero-actions {
    display: flex;
    gap: 1rem;
    justify-content: center;
    flex-wrap: wrap;
}

.btn {
    padding: 0.75rem 1.5rem;
    border-radius: 6px;
    text-decoration: none;
    font-weight: 500;
    transition: all 0.2s;
    display: inline-block;
}

.btn-primary {
    background: var(--primary-color);
    color: white;
}

.btn-primary:hover {
    background: var(--primary-hover);
}

.btn-secondary {
    background: var(--secondary-color);
    color: white;
}

.btn-outline {
    background: transparent;
    color: white;
    border: 2px solid white;
}

.btn-outline:hover {
    background: white;
    color: var(--primary-color);
}

/* Features Section */
.features-section {
    margin-bottom: 3rem;
}

.features-section h2 {
    text-align: center;
    margin-bottom: 2rem;
    font-size: 2rem;
}

.features-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 2rem;
}

.feature-card {
    background: var(--surface-color);
    padding: 2rem;
    border-radius: 8px;
    text-align: center;
    border: 1px solid var(--border-color);
}

.feature-icon {
    font-size: 3rem;
    margin-bottom: 1rem;
}

.feature-card h3 {
    margin-bottom: 1rem;
    color: var(--text-color);
}

/* Code Blocks */
.code-block {
    background: var(--code-bg);
    border: 1px solid var(--border-color);
    border-radius: 6px;
    margin: 1rem 0;
    overflow: hidden;
}

.code-header {
    background: var(--surface-color);
    padding: 0.75rem 1rem;
    border-bottom: 1px solid var(--border-color);
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.code-header span {
    font-family: monospace;
    font-size: 0.875rem;
    color: var(--text-muted);
}

.copy-btn {
    background: var(--primary-color);
    color: white;
    border: none;
    padding: 0.25rem 0.75rem;
    border-radius: 4px;
    font-size: 0.75rem;
    cursor: pointer;
}

.copy-btn:hover {
    background: var(--primary-hover);
}

.code-block pre {
    padding: 1rem;
    overflow-x: auto;
    margin: 0;
    font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
    font-size: 0.875rem;
    line-height: 1.5;
}

/* API Reference */
.api-category {
    margin-bottom: 3rem;
}

.api-category h2 {
    margin-bottom: 1.5rem;
    color: var(--text-color);
    border-bottom: 2px solid var(--primary-color);
    padding-bottom: 0.5rem;
}

.api-endpoint {
    background: white;
    border: 1px solid var(--border-color);
    border-radius: 8px;
    padding: 1.5rem;
    margin-bottom: 1.5rem;
}

.api-endpoint h3 {
    color: var(--text-color);
    margin-bottom: 1rem;
    font-family: monospace;
    background: var(--code-bg);
    padding: 0.5rem 1rem;
    border-radius: 4px;
}

.method-section {
    margin-bottom: 1.5rem;
}

.method-header {
    display: flex;
    align-items: center;
    gap: 1rem;
    margin-bottom: 1rem;
}

.method-badge {
    padding: 0.25rem 0.75rem;
    border-radius: 4px;
    font-weight: 600;
    font-size: 0.875rem;
    text-transform: uppercase;
}

.method-get { background: #10b981; color: white; }
.method-post { background: #3b82f6; color: white; }
.method-put { background: #f59e0b; color: white; }
.method-patch { background: #8b5cf6; color: white; }
.method-delete { background: #ef4444; color: white; }

.method-description {
    color: var(--text-muted);
    margin-bottom: 1rem;
}

/* Tables */
.parameters-table {
    width: 100%;
    border-collapse: collapse;
    margin: 1rem 0;
}

.parameters-table th,
.parameters-table td {
    padding: 0.75rem;
    text-align: left;
    border-bottom: 1px solid var(--border-color);
}

.parameters-table th {
    background: var(--surface-color);
    font-weight: 600;
}

/* Examples */
.example-sections {
    display: flex;
    flex-direction: column;
    gap: 3rem;
}

.example-section h2 {
    margin-bottom: 1.5rem;
    color: var(--text-color);
}

.example-tabs {
    border: 1px solid var(--border-color);
    border-radius: 8px;
    overflow: hidden;
}

.tab-buttons {
    display: flex;
    background: var(--surface-color);
    border-bottom: 1px solid var(--border-color);
}

.tab-btn {
    padding: 1rem 1.5rem;
    border: none;
    background: none;
    cursor: pointer;
    font-weight: 500;
    transition: background 0.2s;
}

.tab-btn.active {
    background: white;
    border-bottom: 2px solid var(--primary-color);
}

.tab-content {
    display: none;
    padding: 1.5rem;
}

.tab-content.active {
    display: block;
}

/* Stats */
.stats-section {
    margin-bottom: 3rem;
}

.stats-section h2 {
    text-align: center;
    margin-bottom: 2rem;
}

.stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 2rem;
}

.stat-card {
    background: var(--surface-color);
    padding: 2rem;
    border-radius: 8px;
    text-align: center;
    border: 1px solid var(--border-color);
}

.stat-number {
    font-size: 2.5rem;
    font-weight: 700;
    color: var(--primary-color);
    margin-bottom: 0.5rem;
}

.stat-label {
    color: var(--text-muted);
    font-weight: 500;
}

/* Footer */
.footer {
    background: var(--surface-color);
    border-top: 1px solid var(--border-color);
    padding: 2rem 0;
    margin-top: 4rem;
}

.footer .container {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 1rem;
}

.footer-links {
    display: flex;
    gap: 2rem;
}

.footer-links a {
    color: var(--text-muted);
    text-decoration: none;
    transition: color 0.2s;
}

.footer-links a:hover {
    color: var(--primary-color);
}

/* Responsive */
@media (max-width: 768px) {
    .nav-container {
        flex-direction: column;
        gap: 1rem;
    }
    
    .nav-menu {
        flex-wrap: wrap;
        justify-content: center;
    }
    
    .hero-title {
        font-size: 2rem;
    }
    
    .hero-actions {
        flex-direction: column;
        align-items: center;
    }
    
    .features-grid {
        grid-template-columns: 1fr;
    }
    
    .stats-grid {
        grid-template-columns: repeat(2, 1fr);
    }
    
    .footer .container {
        flex-direction: column;
        text-align: center;
    }
}
"""
    
    def get_javascript_code(self) -> str:
        """Get JavaScript code for interactivity."""
        return """
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
"""


def main():
    """Main documentation site generator."""
    generator = DocumentationSiteGenerator()
    success = generator.generate_site()
    
    if success:
        print(f"\n🌐 DOCUMENTATION SITE GENERATED SUCCESSFULLY!")
        print(f"\n📁 Location: {generator.output_dir}")
        print(f"\n📋 FILES CREATED:")
        print(f"   - index.html (Main page)")
        print(f"   - api-reference.html (API documentation)")
        print(f"   - examples.html (Code examples)")
        print(f"   - authentication.html (Authentication guide)")
        print(f"   - migration.html (Migration guide)")
        print(f"   - styles.css (Styling)")
        print(f"   - script.js (Interactivity)")
        print(f"   - search.json (Search index)")
        
        print(f"\n🚀 NEXT STEPS:")
        print(f"   1. Open {generator.output_dir}/index.html in your browser")
        print(f"   2. Deploy the files to a static hosting service")
        print(f"   3. Customize the styling and content as needed")
        
        sys.exit(0)
    else:
        print(f"\n❌ Failed to generate documentation site")
        sys.exit(1)


if __name__ == '__main__':
    main()
