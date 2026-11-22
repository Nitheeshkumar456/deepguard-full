/**
 * appium.config.js — Appium Desired Capabilities and Server Configuration
 */
const path = require('path');

const ROOT_DIR = path.resolve(__dirname, '..', '..');

module.exports = {
  appiumServer: {
    host: process.env.APPIUM_HOST || '127.0.0.1',
    port: parseInt(process.env.APPIUM_PORT || '4723', 10),
    logLevel: 'info',
    basePath: '/'
  },
  capabilities: {
    platformName: 'Android',
    'appium:automationName': 'UiAutomator2',
    'appium:deviceName': process.env.ANDROID_DEVICE_NAME || 'Android GoogleAPI Emulator / Pixel 8',
    'appium:platformVersion': process.env.ANDROID_PLATFORM_VERSION || '14.0',
    'appium:app': process.env.APK_PATH || path.resolve(ROOT_DIR, 'dist-apk', 'DeepGuard-AI.apk'),
    'appium:appPackage': 'com.example.deepguard',
    'appium:appActivity': 'com.example.deepguard.MainActivity',
    'appium:noReset': false,
    'appium:fullReset': false,
    'appium:autoGrantPermissions': true,
    'appium:newCommandTimeout': 300,
    'appium:uiautomator2ServerInstallTimeout': 60000,
    'appium:adbExecTimeout': 40000,
    'appium:avdLaunchTimeout': 180000,
    'appium:avdReadyTimeout': 180000
  },
  execution: {
    maxRetries: 2,
    retryDelayMs: 500,
    parallelWorkers: 2,
    testTimeoutMs: 30000
  }
};
