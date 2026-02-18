/**
 * Tenxyte Device Info Helper — Format v1
 *
 * Format: v=1|os=windows;osv=11|device=desktop|arch=x64|app=tenxyte;appv=1.4.2|runtime=chrome;rtv=122|tz=Africa/Porto-Novo
 *
 * Usage:
 *   import { buildDeviceInfo, parseDeviceInfo } from 'tenxyte/device-info';
 *   const deviceInfo = buildDeviceInfo({ app: 'my-app', appVersion: '1.0.0' });
 *   // => "v=1|os=windows;osv=10|device=desktop|arch=x64|app=my-app;appv=1.0.0|runtime=chrome;rtv=122|tz=Africa/Porto-Novo"
 */

const CURRENT_VERSION = '1';

const VALID_DEVICE_TYPES = new Set(['desktop', 'mobile', 'tablet', 'server', 'bot']);
const VALID_ARCHITECTURES = new Set(['x64', 'arm64', 'arm', 'x86']);

/**
 * Detect OS name and version from navigator.userAgent
 * @returns {{ os: string, osVersion: string }}
 */
function detectOS() {
  const ua = navigator.userAgent;
  let os = 'unknown';
  let osVersion = '';

  if (/Windows/.test(ua)) {
    os = 'windows';
    const match = ua.match(/Windows NT (\d+\.\d+)/);
    if (match) {
      const ntVersionMap = {
        '10.0': '10+',
        '6.3': '8.1',
        '6.2': '8',
        '6.1': '7',
      };
      osVersion = ntVersionMap[match[1]] || match[1];
    }
  } else if (/Android/.test(ua)) {
    os = 'android';
    const match = ua.match(/Android (\d+[\d.]*)/);
    if (match) osVersion = match[1];
  } else if (/iPhone|iPad|iPod/.test(ua)) {
    os = 'ios';
    const match = ua.match(/OS (\d+[_\d]*)/);
    if (match) osVersion = match[1].replace(/_/g, '.');
  } else if (/Mac OS X/.test(ua)) {
    os = 'macos';
    const match = ua.match(/Mac OS X (\d+[_\d.]*)/);
    if (match) osVersion = match[1].replace(/_/g, '.');
  } else if (/Linux/.test(ua)) {
    os = 'linux';
  } else if (/CrOS/.test(ua)) {
    os = 'chromeos';
  }

  return { os, osVersion };
}

/**
 * Detect device type from navigator.userAgent
 * @returns {string} 'desktop' | 'mobile' | 'tablet'
 */
function detectDeviceType() {
  const ua = navigator.userAgent;

  if (/iPad|Android(?!.*Mobile)|Tablet/i.test(ua)) {
    return 'tablet';
  }
  if (/Mobile|iPhone|iPod|Android.*Mobile|webOS|BlackBerry|IEMobile|Opera Mini/i.test(ua)) {
    return 'mobile';
  }
  return 'desktop';
}

/**
 * Detect browser/runtime name and version
 * @returns {{ runtime: string, runtimeVersion: string }}
 */
function detectRuntime() {
  const ua = navigator.userAgent;
  let runtime = 'unknown';
  let runtimeVersion = '';

  // Order matters: check more specific browsers first
  if (/Edg\//.test(ua)) {
    runtime = 'edge';
    const match = ua.match(/Edg\/(\d+)/);
    if (match) runtimeVersion = match[1];
  } else if (/OPR\//.test(ua)) {
    runtime = 'opera';
    const match = ua.match(/OPR\/(\d+)/);
    if (match) runtimeVersion = match[1];
  } else if (/Chrome\//.test(ua) && !/Chromium/.test(ua)) {
    runtime = 'chrome';
    const match = ua.match(/Chrome\/(\d+)/);
    if (match) runtimeVersion = match[1];
  } else if (/Safari\//.test(ua) && !/Chrome/.test(ua)) {
    runtime = 'safari';
    const match = ua.match(/Version\/(\d+[\d.]*)/);
    if (match) runtimeVersion = match[1];
  } else if (/Firefox\//.test(ua)) {
    runtime = 'firefox';
    const match = ua.match(/Firefox\/(\d+)/);
    if (match) runtimeVersion = match[1];
  }

  return { runtime, runtimeVersion };
}

/**
 * Detect CPU architecture (best effort)
 * @returns {string} 'x64' | 'arm64' | 'arm' | 'x86' | ''
 */
function detectArch() {
  const ua = navigator.userAgent;

  if (/x86_64|x86-64|Win64|x64|amd64|AMD64/.test(ua)) return 'x64';
  if (/aarch64|ARM64/.test(ua)) return 'arm64';
  if (/arm|ARM/.test(ua)) return 'arm';
  if (/i[3-6]86|x86|WOW64/.test(ua)) return 'x86';

  // NavigatorUAData API (Chromium 90+)
  if (navigator.userAgentData && navigator.userAgentData.architecture) {
    const arch = navigator.userAgentData.architecture.toLowerCase();
    if (arch === 'x86' && navigator.userAgentData.bitness === '64') return 'x64';
    if (arch === 'arm' && navigator.userAgentData.bitness === '64') return 'arm64';
    return arch;
  }

  return '';
}

/**
 * Build a device_info string from auto-detected + manual values.
 *
 * @param {Object} [options={}]
 * @param {string} [options.app] - Application name
 * @param {string} [options.appVersion] - Application version
 * @param {string} [options.os] - Override OS detection
 * @param {string} [options.osVersion] - Override OS version detection
 * @param {string} [options.device] - Override device type detection
 * @param {string} [options.arch] - Override architecture detection
 * @param {string} [options.runtime] - Override runtime detection
 * @param {string} [options.runtimeVersion] - Override runtime version detection
 * @param {string} [options.timezone] - Override timezone detection
 * @returns {string} Formatted device_info string
 *
 * @example
 * buildDeviceInfo({ app: 'tenxyte', appVersion: '1.4.2' })
 * // => "v=1|os=windows;osv=10+|device=desktop|arch=x64|app=tenxyte;appv=1.4.2|runtime=chrome;rtv=122|tz=Europe/Paris"
 */
function buildDeviceInfo(options = {}) {
  const detected = {
    ...detectOS(),
    device: detectDeviceType(),
    arch: detectArch(),
    ...detectRuntime(),
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || '',
  };

  const os = options.os || detected.os;
  const osVersion = options.osVersion || detected.osVersion;
  const device = options.device || detected.device;
  const arch = options.arch || detected.arch;
  const app = options.app || '';
  const appVersion = options.appVersion || '';
  const runtime = options.runtime || detected.runtime;
  const runtimeVersion = options.runtimeVersion || detected.runtimeVersion;
  const timezone = options.timezone || detected.timezone;

  const parts = [`v=${CURRENT_VERSION}`];

  if (os) {
    let osPart = `os=${os}`;
    if (osVersion) osPart += `;osv=${osVersion}`;
    parts.push(osPart);
  }

  if (device) parts.push(`device=${device}`);
  if (arch) parts.push(`arch=${arch}`);

  if (app) {
    let appPart = `app=${app}`;
    if (appVersion) appPart += `;appv=${appVersion}`;
    parts.push(appPart);
  }

  if (runtime) {
    let rtPart = `runtime=${runtime}`;
    if (runtimeVersion) rtPart += `;rtv=${runtimeVersion}`;
    parts.push(rtPart);
  }

  if (timezone) parts.push(`tz=${timezone}`);

  return parts.join('|');
}

/**
 * Parse a device_info string into an object.
 *
 * @param {string} deviceInfo - Formatted device_info string
 * @returns {Object} Parsed key-value pairs
 *
 * @example
 * parseDeviceInfo('v=1|os=windows;osv=11|device=desktop')
 * // => { v: '1', os: 'windows', osv: '11', device: 'desktop' }
 */
function parseDeviceInfo(deviceInfo) {
  if (!deviceInfo || !deviceInfo.trim()) return {};

  const result = {};
  const categories = deviceInfo.split('|');

  for (const category of categories) {
    const pairs = category.split(';');
    for (const pair of pairs) {
      const eqIndex = pair.indexOf('=');
      if (eqIndex === -1) continue;
      const key = pair.substring(0, eqIndex).trim();
      const value = pair.substring(eqIndex + 1).trim();
      if (key && value) result[key] = value;
    }
  }

  return result;
}

/**
 * Get a human-readable summary of the device info.
 *
 * @param {string} deviceInfo - Formatted device_info string
 * @returns {string} Human-readable summary
 *
 * @example
 * getDeviceSummary('v=1|os=windows;osv=11|device=desktop|runtime=chrome;rtv=122')
 * // => "desktop — windows 11 — chrome 122"
 */
function getDeviceSummary(deviceInfo) {
  const parsed = parseDeviceInfo(deviceInfo);
  if (!Object.keys(parsed).length) return 'Unknown device';

  const parts = [];

  if (parsed.device) parts.push(parsed.device);
  if (parsed.os) {
    parts.push(parsed.osv ? `${parsed.os} ${parsed.osv}` : parsed.os);
  }
  if (parsed.runtime) {
    parts.push(parsed.rtv ? `${parsed.runtime} ${parsed.rtv}` : parsed.runtime);
  }

  return parts.length ? parts.join(' — ') : 'Unknown device';
}

// ESM export
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { buildDeviceInfo, parseDeviceInfo, getDeviceSummary };
}

// Also expose globally for script tags
if (typeof window !== 'undefined') {
  window.TenxyteDeviceInfo = { buildDeviceInfo, parseDeviceInfo, getDeviceSummary };
}
