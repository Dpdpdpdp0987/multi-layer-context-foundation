/**
 * Soak Test (Endurance Test)
 * 
 * Tests system stability over extended period.
 * Validates: Memory leaks, resource exhaustion, stability
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';
import { randomString, randomItem } from '../utils/helpers.js';

const errorRate = new Rate('errors');
const memoryTrend = new Trend('memory_usage');
const latencyDrift = new Trend('latency_drift');
const totalRequests = new Counter('total_requests');

export const options = {
  stages: [
    { duration: '5m', target: 500 },     // Ramp to moderate load
    { duration: '4h', target: 500 },     // Maintain for 4 hours
    { duration: '5m', target: 0 },       // Ramp down
  ],
  thresholds: {
    'http_req_duration': ['p(95)<1000', 'p(99)<2000'],
    'http_req_failed': ['rate<0.02'],
    'errors': ['rate<0.05'],
    'latency_drift': ['p(95)<2000'], // Ensure latency doesn't drift up
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

let baselineLatency = 0;
let requestCount = 0;

export default function () {
  // Mix of operations to simulate real usage
  const operations = [
    () => storeContext(),
    () => retrieveContext(),
    () => searchSemantic(),
    () => healthCheck(),
  ];
  
  const weights = [0.3, 0.5, 0.15, 0.05]; // Weighted operation selection
  const operation = weightedRandom(operations, weights);
  
  const start = Date.now();
  const success = operation();
  const latency = Date.now() - start;
  
  totalRequests.add(1);
  requestCount++;
  
  // Calculate latency drift
  if (requestCount === 100) {
    baselineLatency = latency;
  } else if (requestCount > 100) {
    latencyDrift.add(latency - baselineLatency);
  }
  
  if (!success) {
    errorRate.add(1);
  }
  
  // Check metrics endpoint periodically
  if (requestCount % 1000 === 0) {
    checkMetrics();
  }
  
  sleep(Math.random() * 2 + 1); // 1-3 seconds
}

function storeContext() {
  const payload = JSON.stringify({
    content: `Soak test content: ${randomString(300)}`,
    context_type: 'document',
    metadata: {
      timestamp: Date.now(),
      iteration: __ITER,
    },
  });
  
  const res = http.post(
    `${BASE_URL}/api/v1/context/store`,
    payload,
    { headers: { 'Content-Type': 'application/json' } }
  );
  
  return check(res, { 'store ok': (r) => r.status === 201 });
}

function retrieveContext() {
  const payload = JSON.stringify({
    query: `soak test query ${randomString(15)}`,
    max_results: 10,
    strategy: 'hybrid',
  });
  
  const res = http.post(
    `${BASE_URL}/api/v1/context/retrieve`,
    payload,
    { headers: { 'Content-Type': 'application/json' } }
  );
  
  return check(res, { 'retrieve ok': (r) => r.status === 200 });
}

function searchSemantic() {
  const payload = JSON.stringify({
    query: randomString(20),
    max_results: 5,
  });
  
  const res = http.post(
    `${BASE_URL}/api/v1/search/semantic`,
    payload,
    { headers: { 'Content-Type': 'application/json' } }
  );
  
  return check(res, { 'search ok': (r) => r.status === 200 });
}

function healthCheck() {
  const res = http.get(`${BASE_URL}/health/detailed`);
  return check(res, { 'health ok': (r) => r.status === 200 });
}

function checkMetrics() {
  const res = http.get(`${BASE_URL}/metrics`);
  
  if (res.status === 200) {
    // Parse memory metrics if available
    const memoryMatch = res.body.match(/memory_usage_bytes{type="rss"} ([0-9]+)/);
    if (memoryMatch) {
      memoryTrend.add(parseInt(memoryMatch[1]));
    }
  }
}

function weightedRandom(items, weights) {
  const total = weights.reduce((sum, w) => sum + w, 0);
  const random = Math.random() * total;
  
  let cumulative = 0;
  for (let i = 0; i < items.length; i++) {
    cumulative += weights[i];
    if (random < cumulative) {
      return items[i];
    }
  }
  
  return items[0];
}