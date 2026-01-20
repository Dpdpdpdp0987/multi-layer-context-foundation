/**
 * Stress Test
 * 
 * Pushes the system beyond normal operational capacity.
 * Tests: 10k+ concurrent users, high throughput, system limits
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend, Counter, Gauge } from 'k6/metrics';
import { randomString, randomItem } from '../utils/helpers.js';

// Custom metrics
const errorRate = new Rate('errors');
const activeUsers = new Gauge('active_users');
const throughput = new Counter('throughput');
const p95Latency = new Trend('p95_latency');

// Stress test configuration
export const options = {
  stages: [
    { duration: '5m', target: 1000 },   // Ramp to 1k users
    { duration: '5m', target: 5000 },   // Ramp to 5k users
    { duration: '5m', target: 10000 },  // Ramp to 10k users
    { duration: '10m', target: 10000 }, // Stay at 10k users
    { duration: '5m', target: 15000 },  // Push beyond - find breaking point
    { duration: '10m', target: 15000 }, // Sustain peak load
    { duration: '5m', target: 0 },      // Ramp down
  ],
  thresholds: {
    'http_req_duration': ['p(95)<2000', 'p(99)<5000'],
    'http_req_failed': ['rate<0.05'],
    'errors': ['rate<0.10'],
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

export default function () {
  activeUsers.add(__VU);
  
  const operations = [
    storeContext,
    retrieveContext,
    hybridSearch,
    batchStore,
  ];
  
  // Random operation selection
  const operation = randomItem(operations);
  const start = Date.now();
  
  const success = operation();
  
  const latency = Date.now() - start;
  p95Latency.add(latency);
  
  if (!success) {
    errorRate.add(1);
  } else {
    throughput.add(1);
  }
  
  // Minimal sleep to maximize load
  sleep(Math.random() * 0.5);
}

function storeContext() {
  const payload = JSON.stringify({
    content: `Stress test context: ${randomString(500)}`,
    context_type: 'document',
    metadata: {
      vu: __VU,
      iteration: __ITER,
      timestamp: Date.now(),
    },
  });
  
  const res = http.post(
    `${BASE_URL}/api/v1/context/store`,
    payload,
    { headers: { 'Content-Type': 'application/json' } }
  );
  
  return check(res, {
    'store successful': (r) => r.status === 201,
  });
}

function retrieveContext() {
  const payload = JSON.stringify({
    query: `query ${randomString(20)}`,
    max_results: 10,
    strategy: 'hybrid',
  });
  
  const res = http.post(
    `${BASE_URL}/api/v1/context/retrieve`,
    payload,
    { headers: { 'Content-Type': 'application/json' } }
  );
  
  return check(res, {
    'retrieve successful': (r) => r.status === 200,
  });
}

function hybridSearch() {
  const payload = JSON.stringify({
    query: randomString(30),
    max_results: 5,
    strategy: 'hybrid',
  });
  
  const res = http.post(
    `${BASE_URL}/api/v1/search/hybrid`,
    payload,
    { headers: { 'Content-Type': 'application/json' } }
  );
  
  return check(res, {
    'search successful': (r) => r.status === 200,
  });
}

function batchStore() {
  const items = [];
  for (let i = 0; i < 5; i++) {
    items.push({
      content: `Batch item ${i}: ${randomString(200)}`,
      context_type: 'document',
    });
  }
  
  const payload = JSON.stringify({ items });
  
  const res = http.post(
    `${BASE_URL}/api/v1/context/batch`,
    payload,
    { headers: { 'Content-Type': 'application/json' } }
  );
  
  return check(res, {
    'batch successful': (r) => r.status === 201,
  });
}