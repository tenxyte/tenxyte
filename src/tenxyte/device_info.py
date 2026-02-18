"""
Device Info Helper — Format v1

Format: v=1|os=windows;osv=11|device=desktop|arch=x64|app=tenxyte;appv=1.4.2|runtime=chrome;rtv=122|tz=Africa/Porto-Novo

Séparateurs:
    - '|' sépare les catégories
    - ';' sépare les sous-clés dans une catégorie
    - '=' sépare clé/valeur

Catégories supportées (v1):
    - v       : version du format (obligatoire)
    - os      : système d'exploitation (os, osv)
    - device  : type d'appareil (desktop, mobile, tablet, server, bot)
    - arch    : architecture (x64, arm64, arm, x86)
    - app     : application (app, appv)
    - runtime : runtime/client (runtime, rtv)
    - tz      : timezone
"""
import re
import logging

logger = logging.getLogger('tenxyte')

CURRENT_VERSION = '1'

VALID_DEVICE_TYPES = {'desktop', 'mobile', 'tablet', 'server', 'bot', 'api-client'}
VALID_ARCHITECTURES = {'x64', 'arm64', 'arm', 'x86'}

# Catégories et leurs sous-clés autorisées
CATEGORY_KEYS = {
    'v': {'v'},
    'os': {'os', 'osv'},
    'device': {'device'},
    'arch': {'arch'},
    'app': {'app', 'appv'},
    'runtime': {'runtime', 'rtv'},
    'tz': {'tz'},
}

# Clé principale de chaque catégorie (utilisée pour identifier la catégorie)
CATEGORY_PRIMARY = {
    'v': 'v',
    'os': 'os',
    'device': 'device',
    'arch': 'arch',
    'app': 'app',
    'runtime': 'runtime',
    'tz': 'tz',
}

# Regex pour valider les valeurs (pas de caractères spéciaux du format)
VALUE_PATTERN = re.compile(r'^[a-zA-Z0-9._\-/: ]+$')


def build_device_info(
    os: str = None,
    os_version: str = None,
    device: str = None,
    arch: str = None,
    app: str = None,
    app_version: str = None,
    runtime: str = None,
    runtime_version: str = None,
    timezone: str = None,
    version: str = CURRENT_VERSION
) -> str:
    """
    Construit une string device_info au format v1.

    Args:
        os: Système d'exploitation (ex: 'windows', 'android', 'ios', 'linux', 'macos')
        os_version: Version de l'OS (ex: '11', '14', 'ubuntu22.04')
        device: Type d'appareil ('desktop', 'mobile', 'tablet', 'server', 'bot')
        arch: Architecture ('x64', 'arm64', 'arm', 'x86')
        app: Nom de l'application (ex: 'tenxyte', 'tenxyte-api')
        app_version: Version de l'application (ex: '1.4.2')
        runtime: Runtime/client (ex: 'chrome', 'firefox', 'safari', 'node', 'webview')
        runtime_version: Version du runtime (ex: '122', '20.11')
        timezone: Timezone (ex: 'Africa/Porto-Novo', 'Europe/Paris')
        version: Version du format (défaut: '1')

    Returns:
        String device_info formatée

    Examples:
        >>> build_device_info(os='windows', os_version='11', device='desktop', arch='x64',
        ...     app='tenxyte', app_version='1.4.2', runtime='chrome', runtime_version='122',
        ...     timezone='Africa/Porto-Novo')
        'v=1|os=windows;osv=11|device=desktop|arch=x64|app=tenxyte;appv=1.4.2|runtime=chrome;rtv=122|tz=Africa/Porto-Novo'
    """
    parts = [f'v={version}']

    if os:
        os_part = f'os={os}'
        if os_version:
            os_part += f';osv={os_version}'
        parts.append(os_part)

    if device:
        if device.lower() not in VALID_DEVICE_TYPES:
            logger.warning(f"[DeviceInfo] Unknown device type: {device}")
        parts.append(f'device={device.lower()}')

    if arch:
        if arch.lower() not in VALID_ARCHITECTURES:
            logger.warning(f"[DeviceInfo] Unknown architecture: {arch}")
        parts.append(f'arch={arch.lower()}')

    if app:
        app_part = f'app={app}'
        if app_version:
            app_part += f';appv={app_version}'
        parts.append(app_part)

    if runtime:
        rt_part = f'runtime={runtime}'
        if runtime_version:
            rt_part += f';rtv={runtime_version}'
        parts.append(rt_part)

    if timezone:
        parts.append(f'tz={timezone}')

    return '|'.join(parts)


def parse_device_info(device_info: str) -> dict:
    """
    Parse une string device_info au format v1 en dictionnaire.

    Args:
        device_info: String au format 'v=1|os=windows;osv=11|device=desktop|...'

    Returns:
        Dictionnaire avec toutes les clés extraites.

    Examples:
        >>> parse_device_info('v=1|os=windows;osv=11|device=desktop|arch=x64')
        {'v': '1', 'os': 'windows', 'osv': '11', 'device': 'desktop', 'arch': 'x64'}

        >>> parse_device_info('')
        {}
    """
    if not device_info or not device_info.strip():
        return {}

    result = {}
    categories = device_info.split('|')

    for category in categories:
        pairs = category.split(';')
        for pair in pairs:
            if '=' not in pair:
                continue
            key, _, value = pair.partition('=')
            key = key.strip()
            value = value.strip()
            if key and value:
                result[key] = value

    return result


def validate_device_info(device_info: str) -> tuple:
    """
    Valide une string device_info.

    Args:
        device_info: String à valider

    Returns:
        Tuple (is_valid: bool, errors: list[str])

    Examples:
        >>> validate_device_info('v=1|os=windows;osv=11|device=desktop')
        (True, [])

        >>> validate_device_info('os=windows')
        (False, ['Missing version field (v=1)'])
    """
    errors = []

    if not device_info or not device_info.strip():
        return True, []  # Vide est valide (optionnel)

    parsed = parse_device_info(device_info)

    if 'v' not in parsed:
        errors.append('Missing version field (v=1)')
    elif parsed['v'] != CURRENT_VERSION:
        errors.append(f"Unsupported version: {parsed['v']} (expected {CURRENT_VERSION})")

    if 'device' in parsed and parsed['device'] not in VALID_DEVICE_TYPES:
        errors.append(f"Invalid device type: {parsed['device']}. Must be one of: {', '.join(sorted(VALID_DEVICE_TYPES))}")

    if 'arch' in parsed and parsed['arch'] not in VALID_ARCHITECTURES:
        errors.append(f"Invalid architecture: {parsed['arch']}. Must be one of: {', '.join(sorted(VALID_ARCHITECTURES))}")

    # Vérifier les valeurs pour les caractères interdits
    for key, value in parsed.items():
        if not VALUE_PATTERN.match(value):
            errors.append(f"Invalid characters in {key}={value}")

    return len(errors) == 0, errors


def get_device_summary(device_info: str) -> str:
    """
    Retourne un résumé lisible du device_info pour affichage.

    Args:
        device_info: String au format v1

    Returns:
        Résumé lisible (ex: 'desktop — windows 11 — chrome 122')

    Examples:
        >>> get_device_summary('v=1|os=windows;osv=11|device=desktop|runtime=chrome;rtv=122')
        'desktop — windows 11 — chrome 122'

        >>> get_device_summary('')
        'Unknown device'
    """
    parsed = parse_device_info(device_info)

    if not parsed:
        return 'Unknown device'

    parts = []

    # Device type
    if 'device' in parsed:
        parts.append(parsed['device'])

    # OS
    if 'os' in parsed:
        os_str = parsed['os']
        if 'osv' in parsed:
            os_str += f" {parsed['osv']}"
        parts.append(os_str)

    # Runtime
    if 'runtime' in parsed:
        rt_str = parsed['runtime']
        if 'rtv' in parsed:
            rt_str += f" {parsed['rtv']}"
        parts.append(rt_str)

    # App
    if 'app' in parsed and not parts:
        app_str = parsed['app']
        if 'appv' in parsed:
            app_str += f" {parsed['appv']}"
        parts.append(app_str)

    return ' — '.join(parts) if parts else 'Unknown device'


def devices_match(device_info_a: str, device_info_b: str) -> bool:
    """
    Compare deux device_info pour déterminer s'ils représentent le même appareil.
    Compare sur les clés stables : os, device, arch, app, runtime.
    Ignore les versions et la timezone.

    Args:
        device_info_a: Première string device_info
        device_info_b: Deuxième string device_info

    Returns:
        True si les deux device_info représentent le même appareil

    Examples:
        >>> devices_match(
        ...     'v=1|os=windows;osv=11|device=desktop|runtime=chrome;rtv=122',
        ...     'v=1|os=windows;osv=11|device=desktop|runtime=chrome;rtv=123'
        ... )
        True
    """
    if not device_info_a and not device_info_b:
        return True
    if not device_info_a or not device_info_b:
        return False

    a = parse_device_info(device_info_a)
    b = parse_device_info(device_info_b)

    # Clés d'identité du device (sans versions)
    identity_keys = ['os', 'device', 'arch', 'app', 'runtime']

    return all(a.get(k) == b.get(k) for k in identity_keys)


def build_device_info_from_user_agent(user_agent: str) -> str:
    """
    Construit un device_info basique à partir d'un User-Agent HTTP.
    Utilisé comme fallback quand le client n'envoie pas de device_info.

    Args:
        user_agent: String User-Agent HTTP

    Returns:
        String device_info au format v1 (best effort)

    Examples:
        >>> build_device_info_from_user_agent(
        ...     'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0'
        ... )
        'v=1|os=windows;osv=10.0|device=desktop|arch=x64|runtime=chrome;rtv=122'
    """
    if not user_agent or not user_agent.strip():
        return ''

    ua = user_agent

    # OS detection
    os_name = None
    os_version = None

    if 'Windows' in ua:
        os_name = 'windows'
        m = re.search(r'Windows NT ([\d.]+)', ua)
        if m:
            os_version = m.group(1)
    elif 'Android' in ua:
        os_name = 'android'
        m = re.search(r'Android ([\d.]+)', ua)
        if m:
            os_version = m.group(1)
    elif 'iPhone' in ua or 'iPad' in ua or 'iPod' in ua:
        os_name = 'ios'
        m = re.search(r'OS ([\d_]+)', ua)
        if m:
            os_version = m.group(1).replace('_', '.')
    elif 'Mac OS X' in ua:
        os_name = 'macos'
        m = re.search(r'Mac OS X ([\d_.]+)', ua)
        if m:
            os_version = m.group(1).replace('_', '.')
    elif 'Linux' in ua:
        os_name = 'linux'
    elif 'CrOS' in ua:
        os_name = 'chromeos'

    # Device type detection
    device = 'desktop'
    if re.search(r'iPad|Android(?!.*Mobile)|Tablet', ua, re.I):
        device = 'tablet'
    elif re.search(r'Mobile|iPhone|iPod|Android.*Mobile|webOS|BlackBerry|IEMobile|Opera Mini', ua, re.I):
        device = 'mobile'
    elif re.search(r'bot|crawl|spider|slurp', ua, re.I):
        device = 'bot'

    # Architecture detection
    arch = None
    if re.search(r'x86_64|x86-64|Win64|x64|amd64|AMD64', ua):
        arch = 'x64'
    elif re.search(r'aarch64|ARM64', ua):
        arch = 'arm64'
    elif re.search(r'arm|ARM', ua):
        arch = 'arm'
    elif re.search(r'i[3-6]86|WOW64', ua):
        arch = 'x86'

    # Runtime detection
    runtime = None
    runtime_version = None

    if 'PostmanRuntime' in ua:
        runtime = 'postman'
        m = re.search(r'PostmanRuntime/([\d.]+)', ua)
        if m:
            runtime_version = m.group(1)
        device = 'api-client'
    elif ua.startswith('curl/'):
        runtime = 'curl'
        m = re.search(r'curl/([\d.]+)', ua)
        if m:
            runtime_version = m.group(1)
        device = 'api-client'
    elif 'insomnia' in ua.lower():
        runtime = 'insomnia'
        m = re.search(r'insomnia/([\d.]+)', ua, re.I)
        if m:
            runtime_version = m.group(1)
        device = 'api-client'
    elif 'httpie' in ua.lower():
        runtime = 'httpie'
        m = re.search(r'HTTPie/([\d.]+)', ua, re.I)
        if m:
            runtime_version = m.group(1)
        device = 'api-client'
    elif 'Edg/' in ua:
        runtime = 'edge'
        m = re.search(r'Edg/([\d]+)', ua)
        if m:
            runtime_version = m.group(1)
    elif 'OPR/' in ua:
        runtime = 'opera'
        m = re.search(r'OPR/([\d]+)', ua)
        if m:
            runtime_version = m.group(1)
    elif 'Chrome/' in ua and 'Chromium' not in ua:
        runtime = 'chrome'
        m = re.search(r'Chrome/([\d]+)', ua)
        if m:
            runtime_version = m.group(1)
    elif 'Safari/' in ua and 'Chrome' not in ua:
        runtime = 'safari'
        m = re.search(r'Version/([\d.]+)', ua)
        if m:
            runtime_version = m.group(1)
    elif 'Firefox/' in ua:
        runtime = 'firefox'
        m = re.search(r'Firefox/([\d]+)', ua)
        if m:
            runtime_version = m.group(1)

    return build_device_info(
        os=os_name,
        os_version=os_version,
        device=device,
        arch=arch,
        runtime=runtime,
        runtime_version=runtime_version,
    )
