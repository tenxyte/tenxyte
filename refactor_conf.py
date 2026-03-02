import os
import re

input_file = r'c:\Users\bobop\Documents\own\tenxyte\src\tenxyte\conf.py'
output_dir = r'c:\Users\bobop\Documents\own\tenxyte\src\tenxyte\conf'

with open(input_file, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Grab presets
preset_match = re.search(r'(SECURE_MODE_PRESETS\s*=\s*\{.*?\nVALID_SECURE_MODES\s*=\s*list\(SECURE_MODE_PRESETS\.keys\(\)\))', content, re.DOTALL)
presets_code = preset_match.group(1) if preset_match else ""

# 2. Grab class initial part
class_match = re.search(r'class TenxyteSettings:.*?(def __init__.*?)(?=\n    # =)', content, re.DOTALL)
base_init_code = class_match.group(1) if class_match else ""

# 3. Find _get method
_get_method = re.search(r'    def _get\(self, name, default=None\):.*?(?=\n    @property|\n    # ==)', content, re.DOTALL)
get_code = _get_method.group(0) if _get_method else ""

# 4. Grab all properties
# A property starts with "\n    @property" and goes until the next "\n    @property" or end of class
properties_code = content[content.find('    @property'):content.find('auth_settings =')]

# We'll put them in logical buckets based on names.
buckets = {
    'base': [],
    'jwt': [],
    'auth': [],
    'security': [],
    'social': [],
    'communication': [],
    'modules': [],
    'airs': []
}

props = re.split(r'(?=\n    @property)', properties_code)
for p in props:
    if not p.strip(): continue
    # extract name
    m = re.search(r'def ([A-Z0-9_]+)\(', p)
    if not m:
        buckets['base'].append(p)
        continue
    name = m.group(1)
    
    if 'JWT' in name or name in ['TOKEN_BLACKLIST_ENABLED', 'REFRESH_TOKEN_ROTATION']:
        buckets['jwt'].append(p)
    elif 'TOTP' in name or 'OTP' in name or 'PASSWORD' in name or name in ['BACKUP_CODES_COUNT', 'ACCOUNT_LOCKOUT_ENABLED', 'MAX_LOGIN_ATTEMPTS', 'LOCKOUT_DURATION_MINUTES']:
        buckets['auth'].append(p)
    elif 'CORS' in name or 'SECURITY' in name or 'BREACH' in name or 'RATE_LIMIT' in name or 'SESSION' in name or 'DEVICE' in name or 'TRUSTED_PROXIES' in name or 'AUDIT' in name or name in ['ALLOW_MULTIPLE_SESSIONS_PER_DEVICE']:
        buckets['security'].append(p)
    elif 'GOOGLE' in name or 'GITHUB' in name or 'MICROSOFT' in name or 'FACEBOOK' in name or 'MAGIC' in name or 'WEBAUTHN' in name or 'SOCIAL' in name:
        buckets['social'].append(p)
    elif 'EMAIL' in name or 'SMS' in name or 'TWILIO' in name or 'NGH' in name or 'SENDGRID' in name:
        buckets['communication'].append(p)
    elif 'RBAC' in name or 'ORGS' in name or 'ORGANIZATION' in name or name in ['APPLICATION_AUTH_ENABLED', 'API_KEY_HEADER', 'API_SECRET_HEADER']:
        buckets['modules'].append(p)
    elif 'AIRS' in name or 'AGENT' in name:
        buckets['airs'].append(p)
    else:
        buckets['base'].append(p)

file_contents = {
    'presets.py': f"from django.conf import settings\n\n{presets_code}\n",
}

for bucket, p_list in buckets.items():
    if bucket == 'base':
        file_contents['base.py'] = f"""from django.conf import settings
from .presets import SECURE_MODE_PRESETS
import warnings
from django.core.exceptions import ImproperlyConfigured

class BaseSettingsMixin:
{get_code}
{"".join(p_list)}
"""
    else:
        file_contents[f'{bucket}.py'] = f"""from django.conf import settings

class {bucket.capitalize()}SettingsMixin:
{"".join(p_list)}
"""

# Create __init__.py
imports = []
mixins = []
for bucket in buckets.keys():
    if bucket == 'base':
        imports.append("from .base import BaseSettingsMixin")
        mixins.append("BaseSettingsMixin")
    else:
        imports.append(f"from .{bucket} import {bucket.capitalize()}SettingsMixin")
        mixins.append(f"{bucket.capitalize()}SettingsMixin")

imports.append("from .presets import SECURE_MODE_PRESETS, VALID_SECURE_MODES")

init_code = f"""\"\"\"
Configuration settings pour Tenxyte (Module factorisé).
\"\"\"
{chr(10).join(imports)}

class TenxyteSettings(
{chr(10).join(['    ' + m + ',' for m in mixins])}
):
    \"\"\"
    Configuration consolidée de Tenxyte.
    \"\"\"
{base_init_code.replace('class TenxyteSettings:', '')}

auth_settings = TenxyteSettings()

# Rétrocompatibilité absolue : exposer aussi l'instance dans le module parent
# Note: si quelqu'un importe du code depuis src/tenxyte/conf.py, ça pointera vers __init__.py
"""

file_contents['__init__.py'] = init_code

# Save all
for filename, content in file_contents.items():
    path = os.path.join(output_dir, filename)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

print("Files generated properly mapped.")
