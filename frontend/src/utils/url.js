/**
 * Derives the WebSocket relay URL from environment variables or browser location.
 * Fallback to current host port 8080.
 *
 * @param {string | undefined} envUrl - Optional explicit URL (e.g. import.meta.env.VITE_WS_URL)
 * @param {Location | { protocol?: string, hostname?: string } | undefined} loc - Optional location object
 * @returns {string} Fully qualified ws:// or wss:// URL
 */
export function deriveWsUrl(envUrl, loc) {
  if (envUrl && typeof envUrl === 'string' && envUrl.trim().length > 0) {
    return envUrl.trim();
  }

  const locationObj = loc || (typeof window !== 'undefined' ? window.location : undefined);

  if (locationObj && locationObj.hostname) {
    const isSecure = locationObj.protocol === 'https:';
    const proto = isSecure ? 'wss:' : 'ws:';
    const host = locationObj.hostname || 'localhost';
    return `${proto}//${host}:8080`;
  }

  return 'ws://localhost:8080';
}
