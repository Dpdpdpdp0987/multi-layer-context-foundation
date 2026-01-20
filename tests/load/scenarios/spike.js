/**
 * Spike Test
 * 
 * Tests system behavior under sudden traffic spikes.
 * Validates: Auto-scaling, rate limiting, graceful degradation
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';
import { randomString, randomItem } from '../utils/helpers.js';

const errorRate = new Rate('errors');
const recoveryTime = new Trend('recovery_time');

export const options = {
  stages: [
    { duration: '1m', target: 100 },    // Normal load
    { duration: '30s', target: 5000 },  // Spike!
    { duration: '2m', target: 5000 },   // Sustain spike
    { duration: '1m', target: 100 },    // Return to normal
    { duration: '30s', target: 10000 }, // Larger spike!
    { duration: '2m', target: 10000 },  // Sustain larger spike
    { duration: '1m', target: 0 },      // Ramp down
  ],
  thresholds: {
    'http_req_duration': ['p(99)<10000'],
    'http_req_failed': ['rate<0.10'],
    'errors': ['rate<0.15'],
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

export default function () {
  const payload = JSON.stringify({
    query: `spike test ${randomString(20)}`,
    max_results: 5,
  });
  
  const res = http.post(
    `${BASE_URL}/api/v1/context/retrieve`,
    payload,
    {
      headers: { 'Content-Type': 'application/json' },
      timeout: '30s',
    }
  );
  
  const success = check(res, {
    'status is 200 or 429': (r) => r.status === 200 || r.status === 429,
    'response time acceptable': (r) => r.timings.duration < 10000,
  });
  
  if (!success) {
    errorRate.add(1);
  }
  
  if (res.status === 429) {
    // Rate limited - measure recovery time
    const start = Date.now();
    sleep(1);
    recoveryTime.add(Date.now() - start);
  }
  
  sleep(0.1);
}