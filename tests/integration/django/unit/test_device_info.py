from tenxyte.device_info import (
    build_device_info,
    parse_device_info,
    validate_device_info,
    get_device_summary,
    devices_match,
    build_device_info_from_user_agent
)

def test_build_device_info():
    assert build_device_info(os='windows', os_version='11', device='desktop', arch='x64',
                             app='tenxyte', app_version='1.4.2', runtime='chrome', runtime_version='122',
                             timezone='Africa/Porto-Novo') == 'v=1|os=windows;osv=11|device=desktop|arch=x64|app=tenxyte;appv=1.4.2|runtime=chrome;rtv=122|tz=Africa/Porto-Novo'

    # With missing optional parts
    assert build_device_info(os='linux', device='server') == 'v=1|os=linux|device=server'

def test_build_device_info_invalid_types(caplog):
    build_device_info(device='unsupported_type', arch='unsupported_arch')
    assert "Unknown device type: unsupported_type" in caplog.text
    assert "Unknown architecture: unsupported_arch" in caplog.text

def test_parse_device_info():
    info = 'v=1|os=windows;osv=11|device=desktop|arch=x64'
    parsed = parse_device_info(info)
    assert parsed == {'v': '1', 'os': 'windows', 'osv': '11', 'device': 'desktop', 'arch': 'x64'}

    assert parse_device_info('') == {}
    assert parse_device_info('   ') == {}

    # Malformed strings
    assert parse_device_info('v=1|os') == {'v': '1'}  # Ignored no equals sign

def test_validate_device_info():
    is_valid, errors = validate_device_info('v=1|os=windows;osv=11|device=desktop')
    assert is_valid is True
    assert errors == []

    is_valid, errors = validate_device_info('')
    assert is_valid is True
    assert errors == []

    is_valid, errors = validate_device_info('os=windows')
    assert is_valid is False
    assert 'Missing version field (v=1)' in errors

    is_valid, errors = validate_device_info('v=2|os=windows')
    assert is_valid is False
    assert 'Unsupported version: 2 (expected 1)' in errors

    is_valid, errors = validate_device_info('v=1|device=supercomputer')
    assert is_valid is False
    assert 'Invalid device type: supercomputer' in errors[0]

    is_valid, errors = validate_device_info('v=1|arch=mips')
    assert is_valid is False
    assert 'Invalid architecture: mips' in errors[0]

    is_valid, errors = validate_device_info('v=1|os=win$$dows')
    assert is_valid is False
    assert 'Invalid characters in os=win$$dows' in errors

def test_get_device_summary():
    assert get_device_summary('v=1|os=windows;osv=11|device=desktop|runtime=chrome;rtv=122') == 'desktop — windows 11 — chrome 122'
    assert get_device_summary('v=1|device=mobile|os=ios') == 'mobile — ios'
    assert get_device_summary('v=1|app=tenxyte;appv=1.0') == 'tenxyte 1.0'
    assert get_device_summary('') == 'Unknown device'

def test_devices_match():
    assert devices_match(
        'v=1|os=windows;osv=11|device=desktop|runtime=chrome;rtv=122',
        'v=1|os=windows;osv=11|device=desktop|runtime=chrome;rtv=123'
    ) is True
    
    assert devices_match('', '') is True
    assert devices_match('v=1|os=windows', '') is False

    assert devices_match(
        'v=1|os=windows',
        'v=1|os=linux'
    ) is False

def test_build_device_info_from_user_agent():
    assert build_device_info_from_user_agent('') == ''
    
    # Windows Desktop Chrome
    ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0'
    assert build_device_info_from_user_agent(ua) == 'v=1|os=windows;osv=10.0|device=desktop|arch=x64|runtime=chrome;rtv=122'

    # Android Mobile
    ua = 'Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 Chrome/122.0.0.0 Mobile'
    assert build_device_info_from_user_agent(ua) == 'v=1|os=android;osv=14|device=mobile|runtime=chrome;rtv=122'

    # iOS Mobile Safari
    ua = 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_3_1 like Mac OS X) AppleWebKit/605.1.15'
    assert build_device_info_from_user_agent(ua) == 'v=1|os=ios;osv=17.3.1|device=mobile'

    # macOS Desktop Safari
    ua = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Version/17.3.1 Safari/605.1.15'
    res = build_device_info_from_user_agent(ua)
    assert res == 'v=1|os=macos;osv=10.15.7|device=desktop|runtime=safari;rtv=17.3.1'

    # Linux Desktop Firefox
    ua = 'Mozilla/5.0 (X11; Linux x86_64; rv:123.0) Gecko/20100101 Firefox/123.0'
    res = build_device_info_from_user_agent(ua)
    assert res == 'v=1|os=linux|device=desktop|arch=x64|runtime=firefox;rtv=123'

    # Edge Desktop
    ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0'
    res = build_device_info_from_user_agent(ua)
    assert res == 'v=1|os=windows;osv=10.0|device=desktop|arch=x64|runtime=edge;rtv=122'

    # Opera Desktop
    ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/121.0.0.0 Safari/537.36 OPR/107.0.0.0'
    res = build_device_info_from_user_agent(ua)
    assert res == 'v=1|os=windows;osv=10.0|device=desktop|arch=x64|runtime=opera;rtv=107'

    # ChromeOS 
    ua = 'Mozilla/5.0 (X11; CrOS x86_64 14541.0.0) AppleWebKit/537.36 Chrome/122.0.0.0'
    res = build_device_info_from_user_agent(ua)
    assert res == 'v=1|os=chromeos|device=desktop|arch=x64|runtime=chrome;rtv=122'

    # iPad Tablet
    ua = 'Mozilla/5.0 (iPad; CPU OS 16_3_1 like Mac OS X) AppleWebKit/605.1.15'
    res = build_device_info_from_user_agent(ua)
    assert res == 'v=1|os=ios;osv=16.3.1|device=tablet'

    # Android Tablet
    ua = 'Mozilla/5.0 (Linux; Android 13; SM-X900) AppleWebKit/537.36 Chrome/119.0.0.0'
    res = build_device_info_from_user_agent(ua)
    assert res == 'v=1|os=android;osv=13|device=tablet|runtime=chrome;rtv=119'

    # API Clients
    assert build_device_info_from_user_agent('PostmanRuntime/7.36.3') == 'v=1|device=api-client|runtime=postman;rtv=7.36.3'
    assert build_device_info_from_user_agent('curl/8.4.0') == 'v=1|device=api-client|runtime=curl;rtv=8.4.0'
    assert build_device_info_from_user_agent('insomnia/8.6.0') == 'v=1|device=api-client|runtime=insomnia;rtv=8.6.0'
    assert build_device_info_from_user_agent('HTTPie/3.2.2') == 'v=1|device=api-client|runtime=httpie;rtv=3.2.2'

    # Bot
    assert build_device_info_from_user_agent('Googlebot/2.1 (+http://www.google.com/bot.html)') == 'v=1|device=bot'

    # ARM64
    assert build_device_info_from_user_agent('Mozilla/5.0 (Macintosh; ARM64 Mac OS X 10_15_7)') == 'v=1|os=macos;osv=10.15.7|device=desktop|arch=arm64'
    assert build_device_info_from_user_agent('Mozilla/5.0 (Linux; arm)') == 'v=1|os=linux|device=desktop|arch=arm'
    assert build_device_info_from_user_agent('Mozilla/5.0 (Windows NT 10.0; WOW64)') == 'v=1|os=windows;osv=10.0|device=desktop|arch=x86'
