/**
 * SignupPage.js — Page Object Model for DeepGuard AI Signup Screen
 */
const BasePage = require('./BasePage');

class SignupPage extends BasePage {
  constructor(driver) {
    super(driver);
    this.nameInput = 'input[placeholder*="name" i], [accessibilityLabel="Full Name"]';
    this.emailInput = 'input[type="email"], [accessibilityLabel="Email Address"]';
    this.passwordInput = 'input[type="password"], [accessibilityLabel="Password"]';
    this.confirmPasswordInput = 'input[placeholder*="confirm" i], [accessibilityLabel="Confirm Password"]';
    this.createAccountBtn = 'button[type="submit"], [accessibilityLabel="Create Account"]';
    this.loginLink = 'a[href="/login"], [accessibilityLabel="Already have an account? Sign in"]';
  }

  async register(name, email, password, confirmPassword) {
    await this.sendKeys(this.nameInput, name);
    await this.sendKeys(this.emailInput, email);
    await this.sendKeys(this.passwordInput, password);
    await this.sendKeys(this.confirmPasswordInput, confirmPassword);
    await this.tap(this.createAccountBtn);
  }
}

module.exports = SignupPage;
