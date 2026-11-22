/**
 * environment.config.js — DeepGuard AI Multi-Modal Automation Environment Configuration
 */
module.exports = {
  env: process.env.NODE_ENV || 'staging',
  fastapiUrl: process.env.FASTAPI_URL || 'http://127.0.0.1:8000',
  expressGatewayUrl: process.env.GATEWAY_URL || 'http://127.0.0.1:5000',
  webFrontendUrl: process.env.WEB_URL || 'http://127.0.0.1:5173',
  endpoints: {
    health: '/',
    expressHealth: '/express/health',
    login: '/api/auth/login',
    register: '/api/auth/register',
    me: '/api/auth/me',
    analyzeImage: '/api/analyze/image',
    analyzeVideo: '/api/analyze/video',
    analyzeAudio: '/api/analyze/audio',
    history: '/api/history',
    cases: '/api/cases',
    notifications: '/api/notifications'
  }
};
