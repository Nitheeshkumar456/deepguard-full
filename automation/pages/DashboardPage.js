/**
 * DashboardPage.js — Page Object Model for DeepGuard AI Home / Dashboard Screen
 */
const BasePage = require('./BasePage');

class DashboardPage extends BasePage {
  constructor(driver) {
    super(driver);
    this.welcomeText = 'h1, [accessibilityLabel="Dashboard Welcome"]';
    this.quickScanBtn = 'button:has-text("New Analysis"), [accessibilityLabel="New Analysis Button"]';
    this.recentScansList = 'div[data-testid="recent-scans"], [accessibilityLabel="Recent Analyses List"]';
    this.logoutBtn = 'button:has-text("Logout"), [accessibilityLabel="Sign Out"]';
    this.navHistory = 'a[href="/history"], [accessibilityLabel="History Tab"]';
    this.navAnalyze = 'a[href="/analyze"], [accessibilityLabel="Analyze Tab"]';
  }

  async isAtDashboard() {
    return await this.isDisplayed(this.welcomeText);
  }

  async clickNewAnalysis() {
    await this.tap(this.quickScanBtn);
  }

  async logout() {
    await this.tap(this.logoutBtn);
  }
}

module.exports = DashboardPage;
