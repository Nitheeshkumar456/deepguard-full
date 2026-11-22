/**
 * AnalyzePage.js — Page Object Model for DeepGuard AI Media Upload & Forensic Analysis Screen
 */
const BasePage = require('./BasePage');

class AnalyzePage extends BasePage {
  constructor(driver) {
    super(driver);
    this.tabImage = 'button:has-text("Image"), [accessibilityLabel="Image Tab"]';
    this.tabVideo = 'button:has-text("Video"), [accessibilityLabel="Video Tab"]';
    this.tabAudio = 'button:has-text("Audio"), [accessibilityLabel="Audio Tab"]';
    this.fileDropzone = 'div[data-testid="dropzone"], [accessibilityLabel="File Upload Dropzone"]';
    this.startScanBtn = 'button:has-text("Run Forensic Scan"), [accessibilityLabel="Start Analysis Button"]';
    this.progressBar = 'div[role="progressbar"], [accessibilityLabel="Analysis Progress"]';
    this.verdictBadge = 'span[data-testid="verdict"], [accessibilityLabel="Verdict Result"]';
  }

  async selectModality(type) {
    if (type === 'image') await this.tap(this.tabImage);
    else if (type === 'video') await this.tap(this.tabVideo);
    else if (type === 'audio') await this.tap(this.tabAudio);
  }

  async runAnalysis() {
    await this.tap(this.startScanBtn);
  }

  async getVerdict() {
    return await this.getText(this.verdictBadge);
  }
}

module.exports = AnalyzePage;

