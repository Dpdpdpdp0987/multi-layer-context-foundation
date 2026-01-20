/**
 * k6 Results Analyzer
 * 
 * Analyzes k6 test results and generates reports.
 * Usage: node analysis/results-analyzer.js <results.json>
 */

const fs = require('fs');
const path = require('path');

class K6ResultsAnalyzer {
  constructor(resultsPath) {
    this.results = JSON.parse(fs.readFileSync(resultsPath, 'utf8'));
    this.metrics = this.results.metrics;
    this.root_group = this.results.root_group;
  }
  
  analyzPerformance() {
    const httpReqDuration = this.metrics['http_req_duration'];
    const httpReqs = this.metrics['http_reqs'];
    
    return {
      totalRequests: httpReqs?.values?.count || 0,
      requestsPerSecond: httpReqs?.values?.rate || 0,
      responseTime: {
        min: httpReqDuration?.values?.min || 0,
        max: httpReqDuration?.values?.max || 0,
        avg: httpReqDuration?.values?.avg || 0,
        p50: httpReqDuration?.values['p(50)'] || 0,
        p90: httpReqDuration?.values['p(90)'] || 0,
        p95: httpReqDuration?.values['p(95)'] || 0,
        p99: httpReqDuration?.values['p(99)'] || 0,
      },
    };
  }
  
  analyzeErrors() {
    const httpReqFailed = this.metrics['http_req_failed'];
    const errors = this.metrics['errors'];
    
    return {
      failedRequests: httpReqFailed?.values?.passes || 0,
      failureRate: httpReqFailed?.values?.rate || 0,
      errorRate: errors?.values?.rate || 0,
      totalErrors: errors?.values?.passes || 0,
    };
  }
  
  analyzeCustomMetrics() {
    const custom = {};
    
    // Context operations
    if (this.metrics['context_store_latency']) {
      custom.contextStore = {
        p95: this.metrics['context_store_latency'].values['p(95)'],
        p99: this.metrics['context_store_latency'].values['p(99)'],
        avg: this.metrics['context_store_latency'].values.avg,
      };
    }
    
    if (this.metrics['context_retrieve_latency']) {
      custom.contextRetrieve = {
        p95: this.metrics['context_retrieve_latency'].values['p(95)'],
        p99: this.metrics['context_retrieve_latency'].values['p(99)'],
        avg: this.metrics['context_retrieve_latency'].values.avg,
      };
    }
    
    // Session metrics
    if (this.metrics['session_duration']) {
      custom.sessionDuration = {
        avg: this.metrics['session_duration'].values.avg,
        p90: this.metrics['session_duration'].values['p(90)'],
      };
    }
    
    if (this.metrics['operations_per_session']) {
      custom.operationsPerSession = {
        avg: this.metrics['operations_per_session'].values.avg,
      };
    }
    
    return custom;
  }
  
  checkThresholds() {
    const thresholds = this.results.thresholds || {};
    const passed = [];
    const failed = [];
    
    for (const [metric, result] of Object.entries(thresholds)) {
      if (result.ok) {
        passed.push(metric);
      } else {
        failed.push({ metric, ...result });
      }
    }
    
    return { passed, failed, allPassed: failed.length === 0 };
  }
  
  generateReport() {
    const performance = this.analyzePerformance();
    const errors = this.analyzeErrors();
    const custom = this.analyzeCustomMetrics();
    const thresholds = this.checkThresholds();
    
    return {
      summary: {
        testDuration: this.results.state?.testRunDurationMs || 0,
        totalRequests: performance.totalRequests,
        requestsPerSecond: performance.requestsPerSecond.toFixed(2),
        avgResponseTime: performance.responseTime.avg.toFixed(2),
        p95ResponseTime: performance.responseTime.p95.toFixed(2),
        errorRate: (errors.errorRate * 100).toFixed(2) + '%',
      },
      performance,
      errors,
      customMetrics: custom,
      thresholds,
      verdict: this.generateVerdict(performance, errors, thresholds),
    };
  }
  
  generateVerdict(performance, errors, thresholds) {
    const verdicts = [];
    
    // Check if all thresholds passed
    if (thresholds.allPassed) {
      verdicts.push('✅ All performance thresholds met');
    } else {
      verdicts.push(`❌ ${thresholds.failed.length} threshold(s) failed`);
      thresholds.failed.forEach(f => {
        verdicts.push(`   - ${f.metric}`);
      });
    }
    
    // Performance assessment
    if (performance.responseTime.p95 < 500) {
      verdicts.push('✅ Excellent response times');
    } else if (performance.responseTime.p95 < 1000) {
      verdicts.push('⚠️  Acceptable response times');
    } else {
      verdicts.push('❌ Poor response times');
    }
    
    // Error rate assessment
    if (errors.errorRate < 0.01) {
      verdicts.push('✅ Excellent error rate');
    } else if (errors.errorRate < 0.05) {
      verdicts.push('⚠️  Acceptable error rate');
    } else {
      verdicts.push('❌ High error rate');
    }
    
    // Throughput assessment
    if (performance.requestsPerSecond > 1000) {
      verdicts.push('✅ Excellent throughput');
    } else if (performance.requestsPerSecond > 100) {
      verdicts.push('⚠️  Acceptable throughput');
    } else {
      verdicts.push('❌ Low throughput');
    }
    
    return verdicts;
  }
  
  printReport() {
    const report = this.generateReport();
    
    console.log('\n' + '='.repeat(80));
    console.log('                    K6 LOAD TEST RESULTS');
    console.log('='.repeat(80) + '\n');
    
    console.log('SUMMARY');
    console.log('-'.repeat(80));
    console.log(`Test Duration:        ${(report.summary.testDuration / 1000).toFixed(2)}s`);
    console.log(`Total Requests:       ${report.summary.totalRequests}`);
    console.log(`Requests/Second:      ${report.summary.requestsPerSecond}`);
    console.log(`Avg Response Time:    ${report.summary.avgResponseTime}ms`);
    console.log(`P95 Response Time:    ${report.summary.p95ResponseTime}ms`);
    console.log(`Error Rate:           ${report.summary.errorRate}`);
    
    console.log('\nDETAILED PERFORMANCE');
    console.log('-'.repeat(80));
    console.log(`Min:    ${report.performance.responseTime.min.toFixed(2)}ms`);
    console.log(`P50:    ${report.performance.responseTime.p50.toFixed(2)}ms`);
    console.log(`P90:    ${report.performance.responseTime.p90.toFixed(2)}ms`);
    console.log(`P95:    ${report.performance.responseTime.p95.toFixed(2)}ms`);
    console.log(`P99:    ${report.performance.responseTime.p99.toFixed(2)}ms`);
    console.log(`Max:    ${report.performance.responseTime.max.toFixed(2)}ms`);
    
    if (Object.keys(report.customMetrics).length > 0) {
      console.log('\nCUSTOM METRICS');
      console.log('-'.repeat(80));
      console.log(JSON.stringify(report.customMetrics, null, 2));
    }
    
    console.log('\nTHRESHOLDS');
    console.log('-'.repeat(80));
    console.log(`Passed: ${report.thresholds.passed.length}`);
    console.log(`Failed: ${report.thresholds.failed.length}`);
    
    if (report.thresholds.failed.length > 0) {
      console.log('\nFailed Thresholds:');
      report.thresholds.failed.forEach(f => {
        console.log(`  ${f.metric}`);
      });
    }
    
    console.log('\nVERDICT');
    console.log('-'.repeat(80));
    report.verdict.forEach(v => console.log(v));
    
    console.log('\n' + '='.repeat(80) + '\n');
    
    return report;
  }
  
  saveReport(outputPath) {
    const report = this.generateReport();
    fs.writeFileSync(outputPath, JSON.stringify(report, null, 2));
    console.log(`Report saved to: ${outputPath}`);
  }
}

// CLI usage
if (require.main === module) {
  const args = process.argv.slice(2);
  
  if (args.length === 0) {
    console.error('Usage: node results-analyzer.js <results.json> [output.json]');
    process.exit(1);
  }
  
  const resultsPath = args[0];
  const outputPath = args[1];
  
  if (!fs.existsSync(resultsPath)) {
    console.error(`File not found: ${resultsPath}`);
    process.exit(1);
  }
  
  const analyzer = new K6ResultsAnalyzer(resultsPath);
  analyzer.printReport();
  
  if (outputPath) {
    analyzer.saveReport(outputPath);
  }
}

module.exports = K6ResultsAnalyzer;