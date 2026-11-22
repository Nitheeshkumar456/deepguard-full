/**
 * BasePage.js — Core Page Object Model class providing reusable interaction primitives
 * for both Appium UiAutomator2 mobile driver and Selenium web driver.
 */
class BasePage {
  constructor(driver) {
    this.driver = driver;
    this.timeout = 10000;
  }

  async waitForElement(selector, timeout = this.timeout) {
    if (this.driver.wait && this.driver.findElement) {
      const { until, By } = require('selenium-webdriver');
      return await this.driver.wait(until.elementLocated(typeof selector === 'string' ? By.css(selector) : selector), timeout);
    } else if (this.driver.$) {
      const el = await this.driver.$(selector);
      await el.waitForDisplayed({ timeout });
      return el;
    }
    return null;
  }

  async tap(selector) {
    const el = await this.waitForElement(selector);
    if (el.click) {
      await el.click();
    } else if (el.touchAction) {
      await el.touchAction('tap');
    }
  }

  async sendKeys(selector, text, clearFirst = true) {
    const el = await this.waitForElement(selector);
    if (clearFirst && el.clear) {
      await el.clear();
    }
    await el.sendKeys(text);
  }

  async getText(selector) {
    const el = await this.waitForElement(selector);
    return await el.getText();
  }

  async isDisplayed(selector) {
    try {
      const el = await this.waitForElement(selector, 3000);
      return await el.isDisplayed();
    } catch {
      return false;
    }
  }

  async hideKeyboard() {
    if (this.driver.hideKeyboard) {
      try {
        await this.driver.hideKeyboard();
      } catch {}
    }
  }

  async takeScreenshot(filepath) {
    if (this.driver.takeScreenshot) {
      const fs = require('fs');
      const data = await this.driver.takeScreenshot();
      fs.writeFileSync(filepath, data, 'base64');
    }
  }
}

module.exports = BasePage;
