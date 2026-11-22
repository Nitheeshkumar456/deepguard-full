/**
 * LoginPage.js — Page Object Model for DeepGuard AI Login Screen
 */
const BasePage = require('./BasePage');

class LoginPage extends BasePage {
  constructor(driver) {
    super(driver);
    // Selectors supporting both Android Composable semantics & Web DOM
    this.emailInput = 'input[type="email"], input[aria-label="Email address"], [accessibilityLabel="Email Address"]';
    this.passwordInput = 'input[type="password"], input[aria-label="Password"], [accessibilityLabel="Password"]';
    this.submitButton = 'button[type="submit"], [accessibilityLabel="Sign In"]';
    this.togglePasswordButton = 'button[aria-label*="password"], [accessibilityLabel="Toggle password visibility"]';
    this.errorBanner = 'div.bg-red-500\\/10 span, [accessibilityLabel="Error Message"]';
    this.forgotPasswordLink = 'a[href="/forgot-password"], [accessibilityLabel="Forgot Password?"]';
    this.signupLink = 'a[href="/signup"], [accessibilityLabel="Don\'t have an account? Sign up"]';
  }

  async enterEmail(email) {
    await this.sendKeys(this.emailInput, email);
  }

  async enterPassword(password) {
    await this.sendKeys(this.passwordInput, password);
  }

  async clickSignIn() {
    await this.tap(this.submitButton);
  }

  async togglePasswordVisibility() {
    await this.tap(this.togglePasswordButton);
  }

  async getErrorMessage() {
    return await this.getText(this.errorBanner);
  }

  async login(email, password) {
    await this.enterEmail(email);
    await this.enterPassword(password);
    await this.clickSignIn();
  }
}

module.exports = LoginPage;

