'use strict';

/**
 * DeepGuard AI – Selenium E2E Tests
 * Framework : Selenium WebDriver 4.x + Mocha + Chai
 * Target    : http://localhost:5174
 *
 * Run: npx mocha tests/login-tests.js --timeout 30000 --reporter spec
 *
 * Prerequisites:
 *   1. npm install  (in selenium-tests/)
 *   2. ChromeDriver matching your Chrome version
 *   3. DeepGuard AI web dev server running on port 5174
 *   4. A test account:  TEST_EMAIL / TEST_PASSWORD (set as env vars or below)
 */

const { Builder, By, until, Key } = require('selenium-webdriver');
const chrome  = require('selenium-webdriver/chrome');
const { expect } = require('chai');

// ─── Config ────────────────────────────────────────────────────────────────
const BASE    = process.env.BASE_URL   || 'http://localhost:5174';
const EMAIL   = process.env.TEST_EMAIL || 'testuser@deepguard.ai';
const PASS    = process.env.TEST_PASS  || 'Test@1234';
const TIMEOUT = 10_000; // ms

// ─── Driver factory ────────────────────────────────────────────────────────
function buildDriver() {
  const opts = new chrome.Options()
    .addArguments('--headless=new', '--no-sandbox', '--disable-dev-shm-usage', '--window-size=1280,900');
  return new Builder().forBrowser('chrome').setChromeOptions(opts).build();
}

// ─── Helpers ───────────────────────────────────────────────────────────────
async function go(driver, path) { await driver.get(`${BASE}${path}`); }
async function find(driver, css) { return driver.wait(until.elementLocated(By.css(css)), TIMEOUT); }
async function findXp(driver, xp) { return driver.wait(until.elementLocated(By.xpath(xp)), TIMEOUT); }
async function type(driver, css, text) { const el = await find(driver, css); await el.clear(); await el.sendKeys(text); }
async function click(driver, css) { const el = await find(driver, css); await el.click(); }
async function text(driver, css) { return (await find(driver, css)).getText(); }
async function isPresent(driver, css) {
  try { await driver.findElement(By.css(css)); return true; } catch { return false; }
}
async function loginAs(driver, email = EMAIL, password = PASS) {
  await go(driver, '/login');
  await type(driver, 'input[aria-label="Email address"]', email);
  await type(driver, 'input[aria-label="Password"]', password);
  await click(driver, 'button[type="submit"]');
  await driver.wait(until.urlContains('/dashboard'), TIMEOUT);
}

// ══════════════════════════════════════════════════════════════════════════════
// SUITE 1 – Landing Page
// ══════════════════════════════════════════════════════════════════════════════
describe('Landing Page', function () {
  this.timeout(30_000);
  let driver;
  before(async () => { driver = buildDriver(); });
  after(async () => { if (driver) await driver.quit(); });

  it('TC001 – page loads under 3 seconds', async () => {
    const t0 = Date.now();
    await go(driver, '/');
    await find(driver, 'nav');
    expect(Date.now() - t0).to.be.below(3000);
  });

  it('TC002 – hero headline visible', async () => {
    await go(driver, '/');
    const h = await text(driver, 'h2');
    expect(h).to.include('Detect Synthetic Media');
  });

  it('TC003 – navbar brand logo renders', async () => {
    expect(await isPresent(driver, 'nav h1')).to.be.true;
  });

  it('TC004 – Sign In button navigates to /login', async () => {
    await go(driver, '/');
    await click(driver, 'a[href="/login"]');
    await driver.wait(until.urlContains('/login'), TIMEOUT);
    expect(await driver.getCurrentUrl()).to.include('/login');
  });

  it('TC005 – footer copyright text present', async () => {
    await go(driver, '/');
    const f = await text(driver, 'footer');
    expect(f).to.include('2026 DeepGuard AI');
  });

  it('TC006 – features section has 3 cards', async () => {
    await go(driver, '/');
    const cards = await driver.findElements(By.css('#features .grid > div'));
    expect(cards.length).to.equal(3);
  });

  it('TC007 – security section visible', async () => {
    await go(driver, '/');
    expect(await isPresent(driver, '#security')).to.be.true;
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// SUITE 2 – Login
// ══════════════════════════════════════════════════════════════════════════════
describe('Login Page', function () {
  this.timeout(30_000);
  let driver;
  before(async () => { driver = buildDriver(); });
  after(async () => { if (driver) await driver.quit(); });
  beforeEach(async () => { await go(driver, '/login'); });

  it('TC019 – login page loads', async () => {
    await find(driver, 'form');
    expect(await driver.getCurrentUrl()).to.include('/login');
  });

  it('TC020 – email input present', async () => {
    expect(await isPresent(driver, 'input[aria-label="Email address"]')).to.be.true;
  });

  it('TC021 – password input present', async () => {
    expect(await isPresent(driver, 'input[aria-label="Password"]')).to.be.true;
  });

  it('TC022 – Sign In button present', async () => {
    const btn = await find(driver, 'button[type="submit"]');
    expect(await btn.getText()).to.include('Sign In');
  });

  it('TC023 – empty form shows error', async () => {
    await click(driver, 'button[type="submit"]');
    const err = await text(driver, '[class*="red"]');
    expect(err).to.include('Please enter both email and password');
  });

  it('TC026 – invalid email format shows error', async () => {
    await type(driver, 'input[aria-label="Email address"]', 'notanemail');
    await type(driver, 'input[aria-label="Password"]', 'password123');
    await click(driver, 'button[type="submit"]');
    const err = await text(driver, '[class*="red"]');
    expect(err).to.include('valid email');
  });

  it('TC027 – password < 8 chars shows error', async () => {
    await type(driver, 'input[aria-label="Email address"]', 'user@test.com');
    await type(driver, 'input[aria-label="Password"]', 'abc');
    await click(driver, 'button[type="submit"]');
    const err = await text(driver, '[class*="red"]');
    expect(err).to.include('8 characters');
  });

  it('TC028 – valid credentials redirect to /dashboard', async () => {
    await loginAs(driver);
    expect(await driver.getCurrentUrl()).to.include('/dashboard');
  });

  it('TC029 – wrong credentials shows error', async () => {
    await type(driver, 'input[aria-label="Email address"]', 'wrong@test.com');
    await type(driver, 'input[aria-label="Password"]', 'WrongPass1!');
    await click(driver, 'button[type="submit"]');
    const err = await text(driver, '[class*="red"]');
    expect(err.length).to.be.above(0);
  });

  it('TC030 – show/hide password toggle works', async () => {
    const pwInput = await find(driver, 'input[aria-label="Password"]');
    expect(await pwInput.getAttribute('type')).to.equal('password');
    await click(driver, '[aria-label="Show password"]');
    expect(await pwInput.getAttribute('type')).to.equal('text');
    await click(driver, '[aria-label="Hide password"]');
    expect(await pwInput.getAttribute('type')).to.equal('password');
  });

  it('TC032 – forgot password link navigates to /forgot-password', async () => {
    await click(driver, 'a[href="/forgot-password"]');
    await driver.wait(until.urlContains('/forgot-password'), TIMEOUT);
    expect(await driver.getCurrentUrl()).to.include('/forgot-password');
  });

  it('TC033 – create account link navigates to /signup', async () => {
    await go(driver, '/login');
    await click(driver, 'a[href="/signup"]');
    await driver.wait(until.urlContains('/signup'), TIMEOUT);
    expect(await driver.getCurrentUrl()).to.include('/signup');
  });

  it('TC038 – pressing Enter submits form', async () => {
    await type(driver, 'input[aria-label="Email address"]', '');
    const pw = await find(driver, 'input[aria-label="Password"]');
    await pw.sendKeys(Key.ENTER);
    const err = await find(driver, '[class*="red"]');
    expect(await err.getText()).to.have.length.above(0);
  });

  it('TC039 – SQL injection in email handled', async () => {
    await type(driver, 'input[aria-label="Email address"]', "' OR 1=1 --");
    await type(driver, 'input[aria-label="Password"]', 'password123');
    await click(driver, 'button[type="submit"]');
    // Should show validation error, not crash
    const err = await find(driver, '[class*="red"]');
    expect(await err.getText()).to.have.length.above(0);
  });

  it('TC043 – authenticated user redirected away from /login', async () => {
    await loginAs(driver);
    await go(driver, '/login');
    await driver.wait(until.urlContains('/dashboard'), TIMEOUT);
    expect(await driver.getCurrentUrl()).to.include('/dashboard');
  });

  it('TC050 – multiple rapid clicks handled', async () => {
    await type(driver, 'input[aria-label="Email address"]', EMAIL);
    await type(driver, 'input[aria-label="Password"]', PASS);
    const btn = await find(driver, 'button[type="submit"]');
    await btn.click(); await btn.click(); await btn.click();
    // Button should be disabled after first click
    expect(await btn.getAttribute('disabled')).to.not.be.null;
  });

  it('TC052 – whitespace-only email shows error', async () => {
    await type(driver, 'input[aria-label="Email address"]', '   ');
    await type(driver, 'input[aria-label="Password"]', 'password123');
    await click(driver, 'button[type="submit"]');
    const err = await text(driver, '[class*="red"]');
    expect(err).to.include('valid email');
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// SUITE 3 – Signup
// ══════════════════════════════════════════════════════════════════════════════
describe('Signup Page', function () {
  this.timeout(30_000);
  let driver;
  before(async () => { driver = buildDriver(); });
  after(async () => { if (driver) await driver.quit(); });
  beforeEach(async () => { await go(driver, '/signup'); });

  it('TC056 – signup page loads', async () => {
    await find(driver, 'form');
    expect(await driver.getCurrentUrl()).to.include('/signup');
  });

  it('TC061 – empty form shows validation errors', async () => {
    await click(driver, 'button[type="submit"]');
    const errors = await driver.findElements(By.css('[class*="red"]'));
    expect(errors.length).to.be.above(0);
  });

  it('TC062 – mismatched passwords shows error', async () => {
    await type(driver, 'input[name="name"], input[placeholder*="name" i]', 'Test User');
    await type(driver, 'input[type="email"]', 'newuser@test.com');
    const pws = await driver.findElements(By.css('input[type="password"]'));
    await pws[0].sendKeys('Password1!');
    await pws[1].sendKeys('Different2!');
    await click(driver, 'button[type="submit"]');
    const err = await find(driver, '[class*="red"]');
    expect(await err.getText()).to.include('match');
  });

  it('TC068 – sign in link navigates to /login', async () => {
    await click(driver, 'a[href="/login"]');
    await driver.wait(until.urlContains('/login'), TIMEOUT);
    expect(await driver.getCurrentUrl()).to.include('/login');
  });

  it('TC077 – authenticated user redirected from /signup', async () => {
    await loginAs(driver);
    await go(driver, '/signup');
    await driver.wait(until.urlContains('/dashboard'), TIMEOUT);
    expect(await driver.getCurrentUrl()).to.include('/dashboard');
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// SUITE 4 – Forgot Password
// ══════════════════════════════════════════════════════════════════════════════
describe('Forgot Password Page', function () {
  this.timeout(30_000);
  let driver;
  before(async () => { driver = buildDriver(); });
  after(async () => { if (driver) await driver.quit(); });

  it('TC083 – page loads at /forgot-password', async () => {
    await go(driver, '/forgot-password');
    await find(driver, 'form');
    expect(await driver.getCurrentUrl()).to.include('/forgot-password');
  });

  it('TC085 – empty email shows error', async () => {
    await go(driver, '/forgot-password');
    await click(driver, 'button[type="submit"]');
    const err = await find(driver, '[class*="red"]');
    expect(await err.getText()).to.have.length.above(0);
  });

  it('TC086 – invalid email shows error', async () => {
    await go(driver, '/forgot-password');
    await type(driver, 'input[type="email"]', 'invalidemail');
    await click(driver, 'button[type="submit"]');
    const err = await find(driver, '[class*="red"]');
    expect(await err.getText()).to.include('valid email');
  });

  it('TC088 – back to login link present', async () => {
    await go(driver, '/forgot-password');
    expect(await isPresent(driver, 'a[href="/login"]')).to.be.true;
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// SUITE 5 – Dashboard (authenticated)
// ══════════════════════════════════════════════════════════════════════════════
describe('Dashboard', function () {
  this.timeout(30_000);
  let driver;
  before(async () => {
    driver = buildDriver();
    await loginAs(driver);
  });
  after(async () => { if (driver) await driver.quit(); });

  it('TC128 – dashboard loads', async () => {
    await go(driver, '/dashboard');
    expect(await driver.getCurrentUrl()).to.include('/dashboard');
  });

  it('TC129 – unauthenticated access redirects to /login', async () => {
    const d2 = buildDriver();
    try {
      await go(d2, '/dashboard');
      await d2.wait(until.urlContains('/login'), TIMEOUT);
      expect(await d2.getCurrentUrl()).to.include('/login');
    } finally { await d2.quit(); }
  });

  it('TC130 – sidebar visible', async () => {
    await go(driver, '/dashboard');
    expect(await isPresent(driver, 'aside, [class*="sidebar" i]')).to.be.true;
  });

  it('TC131 – topbar visible', async () => {
    expect(await isPresent(driver, 'header, [class*="topbar" i]')).to.be.true;
  });

  it('TC134 – navigate to Analyze from sidebar', async () => {
    await click(driver, 'a[href="/analyze"]');
    await driver.wait(until.urlContains('/analyze'), TIMEOUT);
    expect(await driver.getCurrentUrl()).to.include('/analyze');
  });

  it('TC135 – navigate to History from sidebar', async () => {
    await click(driver, 'a[href="/history"]');
    await driver.wait(until.urlContains('/history'), TIMEOUT);
    expect(await driver.getCurrentUrl()).to.include('/history');
  });

  it('TC136 – navigate to Cases from sidebar', async () => {
    await click(driver, 'a[href="/cases"]');
    await driver.wait(until.urlContains('/cases'), TIMEOUT);
    expect(await driver.getCurrentUrl()).to.include('/cases');
  });

  it('TC139 – navigate to Settings from sidebar', async () => {
    await click(driver, 'a[href="/settings"]');
    await driver.wait(until.urlContains('/settings'), TIMEOUT);
    expect(await driver.getCurrentUrl()).to.include('/settings');
  });

  it('TC140 – navigate to Subscription from sidebar', async () => {
    await click(driver, 'a[href="/subscription"]');
    await driver.wait(until.urlContains('/subscription'), TIMEOUT);
    expect(await driver.getCurrentUrl()).to.include('/subscription');
  });

  it('TC141 – navigate to Help from sidebar', async () => {
    await click(driver, 'a[href="/help"]');
    await driver.wait(until.urlContains('/help'), TIMEOUT);
    expect(await driver.getCurrentUrl()).to.include('/help');
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// SUITE 6 – Analyze
// ══════════════════════════════════════════════════════════════════════════════
describe('Analyze Page', function () {
  this.timeout(30_000);
  let driver;
  before(async () => {
    driver = buildDriver();
    await loginAs(driver);
  });
  after(async () => { if (driver) await driver.quit(); });

  it('TC155 – analyze page loads', async () => {
    await go(driver, '/analyze');
    expect(await driver.getCurrentUrl()).to.include('/analyze');
  });

  it('TC156 – file upload area visible', async () => {
    await go(driver, '/analyze');
    expect(await isPresent(driver, 'input[type="file"], [class*="drop" i], [class*="upload" i]')).to.be.true;
  });

  it('TC176 – analyze page requires auth', async () => {
    const d2 = buildDriver();
    try {
      await go(d2, '/analyze');
      await d2.wait(until.urlContains('/login'), TIMEOUT);
      expect(await d2.getCurrentUrl()).to.include('/login');
    } finally { await d2.quit(); }
  });

  it('TC178 – submit without file shows error', async () => {
    await go(driver, '/analyze');
    try {
      await click(driver, 'button[type="submit"]');
      const err = await find(driver, '[class*="red"]');
      expect(await err.getText()).to.have.length.above(0);
    } catch {
      // Button may be disabled — also acceptable
      const btn = await find(driver, 'button[type="submit"]');
      expect(await btn.getAttribute('disabled')).to.not.be.null;
    }
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// SUITE 7 – Profile
// ══════════════════════════════════════════════════════════════════════════════
describe('Profile Page', function () {
  this.timeout(30_000);
  let driver;
  before(async () => {
    driver = buildDriver();
    await loginAs(driver);
  });
  after(async () => { if (driver) await driver.quit(); });

  it('TC277 – profile page loads', async () => {
    await go(driver, '/profile');
    expect(await driver.getCurrentUrl()).to.include('/profile');
  });

  it('TC287 – profile requires auth', async () => {
    const d2 = buildDriver();
    try {
      await go(d2, '/profile');
      await d2.wait(until.urlContains('/login'), TIMEOUT);
      expect(await d2.getCurrentUrl()).to.include('/login');
    } finally { await d2.quit(); }
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// SUITE 8 – Settings
// ══════════════════════════════════════════════════════════════════════════════
describe('Settings Page', function () {
  this.timeout(30_000);
  let driver;
  before(async () => {
    driver = buildDriver();
    await loginAs(driver);
  });
  after(async () => { if (driver) await driver.quit(); });

  it('TC293 – settings page loads', async () => {
    await go(driver, '/settings');
    expect(await driver.getCurrentUrl()).to.include('/settings');
  });

  it('TC304 – settings requires auth', async () => {
    const d2 = buildDriver();
    try {
      await go(d2, '/settings');
      await d2.wait(until.urlContains('/login'), TIMEOUT);
      expect(await d2.getCurrentUrl()).to.include('/login');
    } finally { await d2.quit(); }
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// SUITE 9 – History
// ══════════════════════════════════════════════════════════════════════════════
describe('History Page', function () {
  this.timeout(30_000);
  let driver;
  before(async () => {
    driver = buildDriver();
    await loginAs(driver);
  });
  after(async () => { if (driver) await driver.quit(); });

  it('TC185 – history page loads', async () => {
    await go(driver, '/history');
    expect(await driver.getCurrentUrl()).to.include('/history');
  });

  it('TC197 – history requires auth', async () => {
    const d2 = buildDriver();
    try {
      await go(d2, '/history');
      await d2.wait(until.urlContains('/login'), TIMEOUT);
      expect(await d2.getCurrentUrl()).to.include('/login');
    } finally { await d2.quit(); }
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// SUITE 10 – Cases
// ══════════════════════════════════════════════════════════════════════════════
describe('Cases Page', function () {
  this.timeout(30_000);
  let driver;
  before(async () => {
    driver = buildDriver();
    await loginAs(driver);
  });
  after(async () => { if (driver) await driver.quit(); });

  it('TC205 – cases page loads', async () => {
    await go(driver, '/cases');
    expect(await driver.getCurrentUrl()).to.include('/cases');
  });

  it('TC216 – cases requires auth', async () => {
    const d2 = buildDriver();
    try {
      await go(d2, '/cases');
      await d2.wait(until.urlContains('/login'), TIMEOUT);
      expect(await d2.getCurrentUrl()).to.include('/login');
    } finally { await d2.quit(); }
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// SUITE 11 – Notifications
// ══════════════════════════════════════════════════════════════════════════════
describe('Notifications Page', function () {
  this.timeout(30_000);
  let driver;
  before(async () => {
    driver = buildDriver();
    await loginAs(driver);
  });
  after(async () => { if (driver) await driver.quit(); });

  it('TC323 – notifications page loads', async () => {
    await go(driver, '/notifications');
    expect(await driver.getCurrentUrl()).to.include('/notifications');
  });

  it('TC331 – notifications requires auth', async () => {
    const d2 = buildDriver();
    try {
      await go(d2, '/notifications');
      await d2.wait(until.urlContains('/login'), TIMEOUT);
      expect(await d2.getCurrentUrl()).to.include('/login');
    } finally { await d2.quit(); }
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// SUITE 12 – Subscription
// ══════════════════════════════════════════════════════════════════════════════
describe('Subscription Page', function () {
  this.timeout(30_000);
  let driver;
  before(async () => {
    driver = buildDriver();
    await loginAs(driver);
  });
  after(async () => { if (driver) await driver.quit(); });

  it('TC310 – subscription page loads', async () => {
    await go(driver, '/subscription');
    expect(await driver.getCurrentUrl()).to.include('/subscription');
  });

  it('TC319 – subscription requires auth', async () => {
    const d2 = buildDriver();
    try {
      await go(d2, '/subscription');
      await d2.wait(until.urlContains('/login'), TIMEOUT);
      expect(await d2.getCurrentUrl()).to.include('/login');
    } finally { await d2.quit(); }
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// SUITE 13 – Help
// ══════════════════════════════════════════════════════════════════════════════
describe('Help Page', function () {
  this.timeout(30_000);
  let driver;
  before(async () => {
    driver = buildDriver();
    await loginAs(driver);
  });
  after(async () => { if (driver) await driver.quit(); });

  it('TC334 – help page loads', async () => {
    await go(driver, '/help');
    expect(await driver.getCurrentUrl()).to.include('/help');
  });

  it('TC340 – help requires auth', async () => {
    const d2 = buildDriver();
    try {
      await go(d2, '/help');
      await d2.wait(until.urlContains('/login'), TIMEOUT);
      expect(await d2.getCurrentUrl()).to.include('/login');
    } finally { await d2.quit(); }
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// SUITE 14 – Compare Media
// ══════════════════════════════════════════════════════════════════════════════
describe('Compare Media Page', function () {
  this.timeout(30_000);
  let driver;
  before(async () => {
    driver = buildDriver();
    await loginAs(driver);
  });
  after(async () => { if (driver) await driver.quit(); });

  it('TC262 – compare page loads', async () => {
    await go(driver, '/compare');
    expect(await driver.getCurrentUrl()).to.include('/compare');
  });

  it('TC273 – compare requires auth', async () => {
    const d2 = buildDriver();
    try {
      await go(d2, '/compare');
      await d2.wait(until.urlContains('/login'), TIMEOUT);
      expect(await d2.getCurrentUrl()).to.include('/login');
    } finally { await d2.quit(); }
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// SUITE 15 – Navigation & Auth Guards
// ══════════════════════════════════════════════════════════════════════════════
describe('Navigation & Auth Guards', function () {
  this.timeout(30_000);
  let driver;
  before(async () => { driver = buildDriver(); });
  after(async () => { if (driver) await driver.quit(); });

  it('TC345 – /dashboard redirects guest to /login', async () => {
    await go(driver, '/dashboard');
    await driver.wait(until.urlContains('/login'), TIMEOUT);
    expect(await driver.getCurrentUrl()).to.include('/login');
  });

  it('TC346 – /analyze redirects guest to /login', async () => {
    await go(driver, '/analyze');
    await driver.wait(until.urlContains('/login'), TIMEOUT);
    expect(await driver.getCurrentUrl()).to.include('/login');
  });

  it('TC347 – /history redirects guest to /login', async () => {
    await go(driver, '/history');
    await driver.wait(until.urlContains('/login'), TIMEOUT);
    expect(await driver.getCurrentUrl()).to.include('/login');
  });

  it('TC349 – unknown route redirects to /', async () => {
    await go(driver, '/this-does-not-exist-xyz');
    await driver.wait(until.urlIs(`${BASE}/`), TIMEOUT);
    expect(await driver.getCurrentUrl()).to.equal(`${BASE}/`);
  });

  it('TC356 – /detect alias redirects to /analyze', async () => {
    const d2 = buildDriver();
    try {
      await loginAs(d2);
      await go(d2, '/detect');
      await d2.wait(until.urlContains('/analyze'), TIMEOUT);
      expect(await d2.getCurrentUrl()).to.include('/analyze');
    } finally { await d2.quit(); }
  });

  it('TC352 – refresh while authenticated keeps session', async () => {
    const d2 = buildDriver();
    try {
      await loginAs(d2);
      await d2.navigate().refresh();
      await d2.wait(until.urlContains('/dashboard'), TIMEOUT);
      expect(await d2.getCurrentUrl()).to.include('/dashboard');
    } finally { await d2.quit(); }
  });
});
