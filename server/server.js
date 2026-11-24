/**
 * DeepGuard AI — Express API Gateway & Proxy (Port 5000)
 *
 * Bridges and proxies client traffic to the FastAPI Python backend (Port 8000),
 * providing seamless cross-origin support, request logging, and unified API access
 * for React Web and Android applications.
 */

const express = require('express');
const cors = require('cors');
const path = require('path');
const fs = require('fs');
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

// Direct APK download route for mobile QR code scanning
app.get('/download-apk', (req, res) => {
  const distApk = path.resolve(__dirname, '..', 'dist-apk', 'DeepGuard-AI.apk');
  const buildApk = path.resolve(__dirname, '..', 'android', 'app', 'build', 'outputs', 'apk', 'debug', 'app-debug.apk');
  const targetApk = fs.existsSync(distApk) ? distApk : (fs.existsSync(buildApk) ? buildApk : null);

  if (targetApk) {
    res.setHeader('Content-Type', 'application/vnd.android.package-archive');
    res.setHeader('Content-Disposition', 'attachment; filename="DeepGuard-AI.apk"');
    res.sendFile(targetApk);
  } else {
    res.status(404).json({ error: 'APK not found. Please build the Android app first.' });
  }
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

// Serve built web frontend (React SPA)
const webDist = path.resolve(__dirname, '..', 'web', 'dist');
if (fs.existsSync(webDist)) {
  app.use(express.static(webDist));
}

// Proxy API and FastAPI routes
app.use('/api', apiProxy);
app.use('/docs', apiProxy);
app.use('/openapi.json', apiProxy);
app.use('/health', apiProxy);
app.use('/metrics', apiProxy);

// SPA fallback for frontend routes
app.use((req, res, next) => {
  if (req.method === 'GET' && !req.originalUrl.startsWith('/api') && !req.originalUrl.startsWith('/download-apk') && !req.originalUrl.startsWith('/docs') && !req.originalUrl.startsWith('/openapi.json')) {
    const indexPath = path.resolve(webDist, 'index.html');
    if (fs.existsSync(indexPath)) {
      return res.sendFile(indexPath);
    }
  }
  next();
});

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
