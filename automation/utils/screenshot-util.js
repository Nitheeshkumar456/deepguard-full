/**
 * screenshot-util.js — Captures and indexes device screenshots for pass/fail evidence
 */
const fs = require('fs');
const path = require('path');
const logger = require('./logger');

const SCREENSHOTS_DIR = path.resolve(__dirname, '..', 'screenshots');
if (!fs.existsSync(SCREENSHOTS_DIR)) fs.mkdirSync(SCREENSHOTS_DIR, { recursive: true });

async function captureScreenshot(driver, testId, status = 'PASSED') {
  const sanitizedId = testId.replace(/[^a-zA-Z0-9_-]/g, '_');
  const filename = `${sanitizedId}_${status}_${Date.now()}.png`;
  const filepath = path.join(SCREENSHOTS_DIR, filename);

  try {
    if (driver && driver.takeScreenshot) {
      const data = await driver.takeScreenshot();
      fs.writeFileSync(filepath, data, 'base64');
      logger.info(`Screenshot captured: ${filename}`);
      return filename;
    }
  } catch (err) {
    logger.warn(`Could not capture screenshot for ${testId}: ${err.message}`);
  }
  return null;
}

module.exports = {
  captureScreenshot,
  getScreenshotsDir: () => SCREENSHOTS_DIR
};

