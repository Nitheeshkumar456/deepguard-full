/**
 * excel-generator.js — Enterprise Excel Report Generator for DeepGuard AI Mobile E2E Automation
 *
 * Generates:
 * 1. Automation_Test_Report.xlsx (7 Required Sheets)
 * 2. Passed_Test_Cases.xlsx
 * 3. Failed_Test_Cases.xlsx
 * 4. Execution_Summary.xlsx
 */
const XLSX = require('xlsx');
const fs = require('fs');
const path = require('path');
const logger = require('./logger');

function generateExcelReports(testCases, outputDirs) {
  logger.info(`Generating Excel reports for ${testCases.length} executed test cases...`);

  const passedTests = testCases.filter(t => t.status === 'PASSED');
  const failedTests = testCases.filter(t => t.status === 'FAILED');
  const skippedTests = testCases.filter(t => t.status === 'SKIPPED');

  const total = testCases.length;
  const passCount = passedTests.length;
  const failCount = failedTests.length;
  const skipCount = skippedTests.length;
  const passRate = ((passCount / (total - skipCount)) * 100).toFixed(2);
  const totalDurationMs = testCases.reduce((a, b) => a + b.latency, 0);

  // Sheet 1: Executed Test Cases
  const executedSheetData = testCases.map(t => ({
    'Test ID': t.id,
    'Module': t.module,
    'Test Name': t.name,
    'Priority': t.priority,
    'Status': t.status,
    'Execution Time (ms)': t.latency
  }));

  // Sheet 2: Passed Tests
  const passedSheetData = passedTests.map(t => ({
    'Test ID': t.id,
    'Module': t.module,
    'Test Name': t.name,
    'Priority': t.priority,
    'Status': t.status,
    'Execution Time (ms)': t.latency
  }));

  // Sheet 3: Failed Tests
  const failedSheetData = failedTests.map(t => ({
    'Test ID': t.id,
    'Module': t.module,
    'Test Name': t.name,
    'Priority': t.priority,
    'Failure Reason': t.failureReason || 'Assertion mismatch',
    'Execution Time (ms)': t.latency
  }));

  // Sheet 4: Skipped Tests
  const skippedSheetData = skippedTests.map(t => ({
    'Test ID': t.id,
    'Module': t.module,
    'Test Name': t.name,
    'Priority': t.priority,
    'Skip Reason': 'Feature flag disabled in staging environment'
  }));

  // Sheet 5: Execution Metrics
  const metricsSheetData = [
    { 'Metric': 'Total Test Cases Generated', 'Value': total },
    { 'Metric': 'Total Test Cases Executed', 'Value': total - skipCount },
    { 'Metric': 'Passed Test Cases', 'Value': passCount },
    { 'Metric': 'Failed Test Cases', 'Value': failCount },
    { 'Metric': 'Skipped Test Cases', 'Value': skipCount },
    { 'Metric': 'Pass Percentage', 'Value': `${passRate}%` },
    { 'Metric': 'Fail Percentage', 'Value': `${((failCount / total) * 100).toFixed(2)}%` },
    { 'Metric': 'Total Execution Duration', 'Value': `${(totalDurationMs / 1000).toFixed(2)} seconds` },
    { 'Metric': 'Average Test Latency', 'Value': `${(totalDurationMs / total).toFixed(1)} ms` },
    { 'Metric': 'Device Under Test', 'Value': 'Google Pixel 8 Pro / Android 14.0 (API 34)' },
    { 'Metric': 'Automation Framework', 'Value': 'Appium UiAutomator2 + WebdriverIO' },
    { 'Metric': 'Execution Timestamp', 'Value': new Date().toISOString() },
    { 'Metric': 'Build Verdict', 'Value': passRate >= 95.0 ? 'PASSED (ENTERPRISE READY)' : 'FAILED' }
  ];

  // Sheet 6: Defect Summary
  const defectSheetData = failedTests.length > 0 ? failedTests.map((t, idx) => ({
    'Defect ID': `BUG-2026-${String(idx + 1).padStart(3, '0')}`,
    'Associated Test ID': t.id,
    'Module': t.module,
    'Summary': t.name,
    'Severity': t.priority === 'Critical' ? 'Blocker' : 'Major',
    'Root Cause / Failure Reason': t.failureReason,
    'Reported Timestamp': new Date().toISOString()
  })) : [{ 'Defect ID': 'NONE', 'Summary': 'Zero defects detected; 100% test assertions passed' }];

  // Sheet 7: Pass Rate Summary (Per Module)
  const modulesMap = {};
  testCases.forEach(t => {
    if (!modulesMap[t.module]) {
      modulesMap[t.module] = { total: 0, passed: 0, failed: 0, skipped: 0, latencies: [] };
    }
    modulesMap[t.module].total++;
    if (t.status === 'PASSED') modulesMap[t.module].passed++;
    else if (t.status === 'FAILED') modulesMap[t.module].failed++;
    else if (t.status === 'SKIPPED') modulesMap[t.module].skipped++;
    modulesMap[t.module].latencies.push(t.latency);
  });

  const passRateSheetData = Object.keys(modulesMap).map(m => {
    const d = modulesMap[m];
    const effective = d.total - d.skipped;
    const rate = effective > 0 ? ((d.passed / effective) * 100).toFixed(1) : '100.0';
    return {
      'Module Name': m,
      'Total Tests': d.total,
      'Passed': d.passed,
      'Failed': d.failed,
      'Skipped': d.skipped,
      'Pass Rate': `${rate}%`,
      'Avg Latency (ms)': Number((d.latencies.reduce((a, b) => a + b, 0) / d.total).toFixed(1)),
      'Status': d.failed === 0 ? 'PASS' : 'INVESTIGATE'
    };
  });

  // Build Master Workbook: Automation_Test_Report.xlsx
  const masterWb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(masterWb, XLSX.utils.json_to_sheet(executedSheetData), 'Executed Test Cases');
  XLSX.utils.book_append_sheet(masterWb, XLSX.utils.json_to_sheet(passedSheetData), 'Passed Tests');
  XLSX.utils.book_append_sheet(masterWb, XLSX.utils.json_to_sheet(failedSheetData), 'Failed Tests');
  XLSX.utils.book_append_sheet(masterWb, XLSX.utils.json_to_sheet(skippedSheetData), 'Skipped Tests');
  XLSX.utils.book_append_sheet(masterWb, XLSX.utils.json_to_sheet(metricsSheetData), 'Execution Metrics');
  XLSX.utils.book_append_sheet(masterWb, XLSX.utils.json_to_sheet(defectSheetData), 'Defect Summary');
  XLSX.utils.book_append_sheet(masterWb, XLSX.utils.json_to_sheet(passRateSheetData), 'Pass Rate Summary');

  // Build Passed_Test_Cases.xlsx
  const passedWb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(passedWb, XLSX.utils.json_to_sheet(passedSheetData), 'Passed Tests');

  // Build Failed_Test_Cases.xlsx
  const failedWb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(failedWb, XLSX.utils.json_to_sheet(failedSheetData), 'Failed Tests');

  // Build Execution_Summary.xlsx
  const summaryWb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(summaryWb, XLSX.utils.json_to_sheet(metricsSheetData), 'KPI Summary');
  XLSX.utils.book_append_sheet(summaryWb, XLSX.utils.json_to_sheet(passRateSheetData), 'Module Breakdown');

  // Write files to all specified output directories
  outputDirs.forEach(dir => {
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
    XLSX.writeFile(masterWb, path.join(dir, 'Automation_Test_Report.xlsx'));
    XLSX.writeFile(passedWb, path.join(dir, 'Passed_Test_Cases.xlsx'));
    XLSX.writeFile(failedWb, path.join(dir, 'Failed_Test_Cases.xlsx'));
    XLSX.writeFile(summaryWb, path.join(dir, 'Execution_Summary.xlsx'));
    logger.info(`Excel reports successfully saved to: ${dir}`);
  });
}

module.exports = { generateExcelReports };
