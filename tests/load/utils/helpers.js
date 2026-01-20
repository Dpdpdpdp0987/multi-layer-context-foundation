/**
 * Helper utilities for k6 tests
 */

/**
 * Generate random string of specified length
 */
export function randomString(length) {
  const chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
  let result = '';
  for (let i = 0; i < length; i++) {
    result += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return result;
}

/**
 * Select random item from array
 */
export function randomItem(array) {
  return array[Math.floor(Math.random() * array.length)];
}

/**
 * Generate random integer between min and max (inclusive)
 */
export function randomInt(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

/**
 * Generate realistic text content
 */
export function generateRealisticText(category) {
  const templates = {
    technical: [
      'Implementing microservices architecture with Docker and Kubernetes',
      'Database optimization strategies for high-throughput applications',
      'Machine learning model deployment using MLOps best practices',
      'API security patterns: OAuth2, JWT, and API keys',
      'Continuous integration and deployment pipelines with GitHub Actions',
    ],
    conversation: [
      'I think we should consider the trade-offs between consistency and performance',
      'Based on our previous discussion, the modular approach makes more sense',
      'Can you explain the benefits of using this pattern over the alternatives?',
      'Let me share what I learned from implementing this in production',
      'That's a good point, we should also consider the scalability implications',
    ],
    document: [
      'This document outlines the system architecture and design decisions',
      'Requirements gathering revealed several key user needs and constraints',
      'Performance benchmarks show significant improvement over the baseline',
      'The implementation follows industry best practices and coding standards',
      'Testing strategy includes unit tests, integration tests, and e2e tests',
    ],
  };
  
  const categoryTemplates = templates[category] || templates.technical;
  return randomItem(categoryTemplates);
}

/**
 * Generate test user data
 */
export function generateUserData() {
  return {
    id: `user_${randomString(8)}`,
    name: randomItem(['Alice', 'Bob', 'Charlie', 'Diana', 'Eve']),
    role: randomItem(['developer', 'researcher', 'analyst', 'manager']),
  };
}

/**
 * Sleep with jitter to simulate human behavior
 */
export function sleepWithJitter(baseSeconds, jitterPercent = 0.3) {
  const jitter = baseSeconds * jitterPercent;
  const actualSleep = baseSeconds + (Math.random() * jitter * 2 - jitter);
  return Math.max(0.1, actualSleep);
}

/**
 * Format bytes to human readable
 */
export function formatBytes(bytes) {
  const sizes = ['B', 'KB', 'MB', 'GB'];
  if (bytes === 0) return '0 B';
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
}

/**
 * Calculate percentile from array
 */
export function percentile(arr, p) {
  if (arr.length === 0) return 0;
  const sorted = arr.slice().sort((a, b) => a - b);
  const index = Math.ceil(arr.length * p / 100) - 1;
  return sorted[index];
}