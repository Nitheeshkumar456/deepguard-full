/**
 * retry-handler.js — Automatic retry mechanism for flaky or transient network checks
 */
const logger = require('./logger');

async function withRetry(actionFn, retries = 2, delayMs = 500, context = 'Operation') {
  let attempt = 0;
  while (attempt <= retries) {
    try {
      return await actionFn();
    } catch (err) {
      attempt++;
      if (attempt > retries) {
        logger.error(`${context} failed after ${retries} retries: ${err.message}`);
        throw err;
      }
      logger.warn(`${context} attempt ${attempt} failed: ${err.message}. Retrying in ${delayMs}ms...`);
      await new Promise(r => setTimeout(r, delayMs));
    }
  }
}

module.exports = { withRetry };
