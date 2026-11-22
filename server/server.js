/**
 * DeepGuard AI — Express API Gateway & Proxy (Port 5000)
 *
 * Bridges and proxies client traffic to the FastAPI Python backend (Port 8000),
 * providing seamless cross-origin support, request logging, and unified API access
 * for React Web and Android applications.
 */

const express = require('express');
const cors = require('cors');
const { createProxyMiddleware } = require('http-proxy-middleware');

const app = express();
const PORT = process.env.PORT || 5000;
const FASTAPI_TARGET = process.env.FASTAPI_TARGET || 'http://127.0.0.1:8000';

// Enable CORS for web and Android clients
app.use(cors({
  origin: '*',
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'PATCH'],
  allowedHeaders: ['*'],
  credentials: true
}));

// Request logger
app.use((req, res, next) => {
  const start = Date.now();
  res.on('finish', () => {
    const duration = Date.now() - start;
    console.log(`[Express 5000] ${req.method} ${req.originalUrl} -> ${res.statusCode} (${duration}ms)`);
  });
  next();
});

// Express health check endpoint
app.get('/express/health', (req, res) => {
  res.json({
    status: 'healthy',
    gateway: 'DeepGuard Express API Gateway',
    port: PORT,
    fastapi_target: FASTAPI_TARGET,
    timestamp: new Date().toISOString()
  });
});

// Process level error guards
process.on('uncaughtException', (err) => {
  console.error('[Express Process uncaughtException]:', err.message);
});
process.on('unhandledRejection', (reason, promise) => {
  console.error('[Express Process unhandledRejection]:', reason);
});

// Proxy all requests directly to FastAPI backend
const apiProxy = createProxyMiddleware({
  target: FASTAPI_TARGET,
  changeOrigin: true,
  ws: true, // Support WebSocket proxying for /api/ws
  proxyTimeout: 120000,
  timeout: 120000,
  logLevel: 'warn',
  onError(err, req, res) {
    console.error(`[Express Proxy Error] ${req.method} ${req.url}:`, err.message);
    if (!res.headersSent) {
      res.status(502).json({
        detail: 'FastAPI backend unavailable or unreachable from Express gateway.',
        target: FASTAPI_TARGET,
        error: err.message
      });
    }
  }
});

app.use('/', apiProxy);

const server = app.listen(PORT, '0.0.0.0', () => {
  console.log(`=======================================================`);
  console.log(` DeepGuard AI Express Gateway listening on port ${PORT}`);
  console.log(` Forwarding all traffic to FastAPI at ${FASTAPI_TARGET}`);
  console.log(`=======================================================`);
});

server.keepAliveTimeout = 65000;
server.headersTimeout = 66000;
server.timeout = 120000;

// Handle WebSocket upgrade
server.on('upgrade', apiProxy.upgrade);
