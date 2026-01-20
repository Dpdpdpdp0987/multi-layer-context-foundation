/**
 * Baseline Load Test
 * 
 * Validates basic system performance with moderate load.
 * Tests: Health checks, basic context operations, simple retrieval
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';
import { randomString, randomItem } from '../utils/helpers.js';

// Custom metrics
const errorRate = new Rate('errors');
const contextStoreLatency = new Trend('context_store_latency');
const contextRetrieveLatency = new Trend('context_retrieve_latency');
const requestCount = new Counter('request_count');

// Configuration
export const options = {
  stages: [
    { duration: '2m', target: 50 },   // Ramp up to 50 users
    { duration: '5m', target: 50 },   // Stay at 50 users
    { duration: '2m', target: 100 },  // Ramp to 100 users
    { duration: '5m', target: 100 },  // Stay at 100 users
    { duration: '2m', target: 0 },    // Ramp down
  ],
  thresholds: {
    'http_req_duration': ['p(95)<500', 'p(99)<1000'],
    'http_req_failed': ['rate<0.01'],
    'errors': ['rate<0.05'],
    'context_store_latency': ['p(95)<300'],
    'context_retrieve_latency': ['p(95)<500'],
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

const contextTypes = ['conversation', 'document', 'code', 'task'];
const queries = [
  'machine learning algorithms',
  'database optimization',
  'python best practices',
  'api design patterns',
  'microservices architecture',
];

export default function () {
  // Health check
  const healthRes = http.get(`${BASE_URL}/health/simple`);
  check(healthRes, {
    'health check status is 200': (r) => r.status === 200,
  });
  requestCount.add(1);
  
  // Store context
  const storePayload = JSON.stringify({
    content: `Test context: ${randomString(100)}`,
    context_type: randomItem(contextTypes),
    metadata: {
      test: true,
      timestamp: Date.now(),
      user: `user_${__VU}`,
    },
  });
  
  const storeStart = Date.now();
  const storeRes = http.post(
    `${BASE_URL}/api/v1/context/store`,
    storePayload,
    {
      headers: { 'Content-Type': 'application/json' },
    }
  );
  
  const storeLatency = Date.now() - storeStart;
  contextStoreLatency.add(storeLatency);
  requestCount.add(1);
  
  const storeSuccess = check(storeRes, {
    'store status is 201': (r) => r.status === 201,
    'store has context id': (r) => JSON.parse(r.body).id !== undefined,
  });
  
  if (!storeSuccess) {
    errorRate.add(1);
  }
  
  sleep(1);
  
  // Retrieve context
  const retrievePayload = JSON.stringify({
    query: randomItem(queries),
    max_results: 5,
    strategy: 'hybrid',
  });
  
  const retrieveStart = Date.now();
  const retrieveRes = http.post(
    `${BASE_URL}/api/v1/context/retrieve`,
    retrievePayload,
    {
      headers: { 'Content-Type': 'application/json' },
    }
  );
  
  const retrieveLatency = Date.now() - retrieveStart;
  contextRetrieveLatency.add(retrieveLatency);
  requestCount.add(1);
  
  const retrieveSuccess = check(retrieveRes, {
    'retrieve status is 200': (r) => r.status === 200,
    'retrieve has results': (r) => JSON.parse(r.body).results !== undefined,
  });
  
  if (!retrieveSuccess) {
    errorRate.add(1);
  }
  
  sleep(2);
}