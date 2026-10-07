const DEFAULT_HOST = 'localhost';
const DEFAULT_PORT = 8080;

const WS_HOST = process.env.WS_HOST || '';
const WS_PORT = parseInt(process.env.WS_PORT || process.env.PORT || String(DEFAULT_PORT), 10);

function getWsUrl(defaultUrl) {
  for (let i = 2; i < process.argv.length; i++) {
    const arg = process.argv[i];
    if (arg === '--ws-url' && process.argv[i + 1]) {
      return process.argv[i + 1];
    }
    if (arg.startsWith('--ws-url=')) {
      return arg.slice('--ws-url='.length);
    }
  }

  if (process.env.WS_URL) {
    return process.env.WS_URL;
  }

  if (defaultUrl) {
    return defaultUrl;
  }

  const host = process.env.WS_HOST || DEFAULT_HOST;
  const port = process.env.WS_PORT || process.env.PORT || DEFAULT_PORT;
  return `ws://${host}:${port}`;
}

module.exports = {
  DEFAULT_HOST,
  DEFAULT_PORT,
  WS_HOST,
  WS_PORT,
  getWsUrl,
};
