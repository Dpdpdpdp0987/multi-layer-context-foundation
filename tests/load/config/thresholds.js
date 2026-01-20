/**
 * Performance Thresholds and SLOs
 * 
 * Defines acceptable performance boundaries for the system.
 */

export const SLO_THRESHOLDS = {
  // Response Time SLOs
  responseTime: {
    p50: 200,    // 50% of requests under 200ms
    p95: 500,    // 95% of requests under 500ms
    p99: 1000,   // 99% of requests under 1000ms
    max: 5000,   // No request over 5000ms
  },
  
  // Error Rate SLOs
  errorRate: {
    http4xx: 0.01,  // <1% client errors
    http5xx: 0.005, // <0.5% server errors
    total: 0.02,    // <2% total errors
  },
  
  // Availability SLOs
  availability: {
    uptime: 0.999,  // 99.9% uptime (43 minutes downtime/month)
    success: 0.995, // 99.5% successful requests
  },
  
  // Throughput SLOs
  throughput: {
    minRPS: 100,      // Minimum 100 requests/second under load
    targetRPS: 1000,  // Target 1000 requests/second
    peakRPS: 5000,    // Support 5000 requests/second peak
  },
  
  // Operation-Specific SLOs
  operations: {
    contextStore: {
      p95: 300,
      p99: 600,
    },
    contextRetrieve: {
      p95: 500,
      p99: 1000,
    },
    semanticSearch: {
      p95: 800,
      p99: 1500,
    },
    graphSearch: {
      p95: 1000,
      p99: 2000,
    },
    hybridSearch: {
      p95: 1200,
      p99: 2500,
    },
  },
};

/**
 * Convert SLOs to k6 threshold format
 */
export function getK6Thresholds(profile = 'production') {
  const slo = SLO_THRESHOLDS;
  
  const baseThresholds = {
    // HTTP metrics
    'http_req_duration': [
      `p(50)<${slo.responseTime.p50}`,
      `p(95)<${slo.responseTime.p95}`,
      `p(99)<${slo.responseTime.p99}`,
    ],
    'http_req_failed': [`rate<${slo.errorRate.total}`],
    'http_reqs': [`rate>${slo.throughput.minRPS}`],
    
    // Custom metrics
    'errors': [`rate<${slo.errorRate.http5xx}`],
  };
  
  // Adjust thresholds based on profile
  if (profile === 'stress') {
    // More lenient thresholds for stress testing
    return {
      ...baseThresholds,
      'http_req_duration': ['p(95)<2000', 'p(99)<5000'],
      'http_req_failed': ['rate<0.10'],
      'errors': ['rate<0.15'],
    };
  } else if (profile === 'spike') {
    // Even more lenient for spike tests
    return {
      ...baseThresholds,
      'http_req_duration': ['p(99)<10000'],
      'http_req_failed': ['rate<0.15'],
      'errors': ['rate<0.20'],
    };
  }
  
  return baseThresholds;
}

/**
 * Capacity planning targets
 */
export const CAPACITY_TARGETS = {
  concurrent_users: {
    baseline: 100,
    normal: 500,
    peak: 2000,
    stress: 10000,
    breaking_point: 15000,
  },
  
  requests_per_second: {
    baseline: 50,
    normal: 200,
    peak: 1000,
    stress: 5000,
  },
  
  data_volume: {
    contexts_stored: 1000000,     // 1M contexts
    daily_operations: 10000000,   // 10M operations/day
    vector_dimensions: 384,
    graph_nodes: 100000,
  },
};

/**
 * Resource limits
 */
export const RESOURCE_LIMITS = {
  memory: {
    api_pod: '2Gi',
    vector_db: '4Gi',
    graph_db: '8Gi',
  },
  
  cpu: {
    api_pod: '1000m',
    vector_db: '2000m',
    graph_db: '4000m',
  },
  
  storage: {
    vector_db: '100Gi',
    graph_db: '200Gi',
  },
};