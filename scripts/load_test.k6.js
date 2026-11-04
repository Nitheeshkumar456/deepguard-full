// load_test.k6.js - Baseline load test using k6
// Run with: k6 run -e API_URL=<your_api_url> scripts/load_test.k6.js
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

export const options = {
  stages: [
    { duration: '1m', target: 100 }, // 100 virtual users for 1 minute
  ],
  thresholds: {
    http_req_duration: ['p(95)<1500'], // 95% of requests should be <1500ms
    'checks': ['rate>0.95'], // 95% of checks must pass
  },
};

// Custom metric to track request success rate
const successRate = new Rate('success_rate');

export default function () {
  const baseUrl = __ENV.API_URL || 'http://localhost:8000'; // default fallback
  // Example endpoint – adjust to your API's health or ping endpoint
  const res = http.get(`${baseUrl}/health`);

  const checkRes = check(res, {
    'status is 200': (r) => r.status === 200,
  });

  successRate.add(checkRes);
  // Simulate think time
  sleep(0.1);
}

export function handleSummary(data) {
  // Generate a simple text summary with RPS and response times
  const summary = `\n=== Load Test Summary ===\n` +
    `Requests: ${data.metrics.http_reqs.count}\n` +
    `Requests per second: ${data.metrics.http_reqs.rate.toFixed(2)} req/sec\n` +
    `Average response time: ${data.metrics.http_req_duration.mean.toFixed(2)} ms\n` +
    `Min response time: ${data.metrics.http_req_duration.min.toFixed(2)} ms\n` +
    `Max response time: ${data.metrics.http_req_duration.max.toFixed(2)} ms\n` +
    `95th percentile: ${data.metrics.http_req_duration.p95.toFixed(2)} ms\n` +
    `Success rate: ${(data.metrics.success_rate.rate * 100).toFixed(2)}%\n`;

  return {
    'stdout': summary,
    // Optionally write to a file in the reports folder
    'reports/load_test_summary.txt': summary,
  };
}
