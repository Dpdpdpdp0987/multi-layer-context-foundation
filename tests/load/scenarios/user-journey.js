/**
 * User Journey Test
 * 
 * Simulates realistic user behavior patterns.
 * Scenarios: Research session, Document analysis, Conversation continuation
 */

import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Rate, Trend } from 'k6/metrics';
import { randomString, randomItem } from '../utils/helpers.js';

const errorRate = new Rate('errors');
const sessionDuration = new Trend('session_duration');
const operationsPerSession = new Trend('operations_per_session');

export const options = {
  scenarios: {
    research_session: {
      executor: 'ramping-vus',
      exec: 'researchSession',
      startVUs: 0,
      stages: [
        { duration: '2m', target: 100 },
        { duration: '10m', target: 100 },
        { duration: '2m', target: 0 },
      ],
    },
    document_analysis: {
      executor: 'ramping-vus',
      exec: 'documentAnalysis',
      startVUs: 0,
      startTime: '1m',
      stages: [
        { duration: '2m', target: 50 },
        { duration: '10m', target: 50 },
        { duration: '2m', target: 0 },
      ],
    },
    conversation_continuation: {
      executor: 'ramping-vus',
      exec: 'conversationContinuation',
      startVUs: 0,
      startTime: '2m',
      stages: [
        { duration: '2m', target: 150 },
        { duration: '10m', target: 150 },
        { duration: '2m', target: 0 },
      ],
    },
  },
  thresholds: {
    'http_req_duration': ['p(95)<1000'],
    'errors': ['rate<0.05'],
    'session_duration': ['p(90)<180000'], // 90% of sessions under 3 minutes
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

/**
 * Research Session Journey
 * User conducts research, stores findings, retrieves related information
 */
export function researchSession() {
  const sessionStart = Date.now();
  let operations = 0;
  const conversationId = `research_${__VU}_${Date.now()}`;
  
  group('Initial Search', () => {
    // User starts with broad search
    const searchRes = http.post(
      `${BASE_URL}/api/v1/search/hybrid`,
      JSON.stringify({
        query: 'machine learning best practices',
        max_results: 10,
      }),
      { headers: { 'Content-Type': 'application/json' } }
    );
    
    check(searchRes, { 'initial search ok': (r) => r.status === 200 });
    operations++;
    sleep(2); // Reading results
  });
  
  group('Deep Dive', () => {
    // User explores specific topics
    const topics = [
      'neural network architecture',
      'hyperparameter tuning',
      'model validation techniques',
    ];
    
    for (const topic of topics) {
      const res = http.post(
        `${BASE_URL}/api/v1/context/retrieve`,
        JSON.stringify({
          query: topic,
          max_results: 5,
          conversation_id: conversationId,
        }),
        { headers: { 'Content-Type': 'application/json' } }
      );
      
      check(res, { 'deep dive ok': (r) => r.status === 200 });
      operations++;
      sleep(3); // Reading and thinking
    }
  });
  
  group('Store Findings', () => {
    // User stores their research notes
    const notes = [
      'Key insight about neural networks: Use batch normalization for faster convergence',
      'Hyperparameter tuning: Grid search vs random search vs Bayesian optimization',
      'Cross-validation is essential for model generalization',
    ];
    
    for (const note of notes) {
      const res = http.post(
        `${BASE_URL}/api/v1/context/store`,
        JSON.stringify({
          content: note,
          context_type: 'document',
          metadata: {
            conversation_id: conversationId,
            session_type: 'research',
          },
        }),
        { headers: { 'Content-Type': 'application/json' } }
      );
      
      check(res, { 'store note ok': (r) => r.status === 201 });
      operations++;
      sleep(1);
    }
  });
  
  group('Final Review', () => {
    // User reviews all session content
    const res = http.post(
      `${BASE_URL}/api/v1/context/retrieve`,
      JSON.stringify({
        query: 'research findings',
        conversation_id: conversationId,
        max_results: 20,
      }),
      { headers: { 'Content-Type': 'application/json' } }
    );
    
    check(res, { 'final review ok': (r) => r.status === 200 });
    operations++;
    sleep(5); // Reviewing results
  });
  
  const duration = Date.now() - sessionStart;
  sessionDuration.add(duration);
  operationsPerSession.add(operations);
}

/**
 * Document Analysis Journey
 * User uploads/analyzes document, extracts entities, explores relationships
 */
export function documentAnalysis() {
  const sessionStart = Date.now();
  let operations = 0;
  
  group('Upload Document', () => {
    const document = `
      Python is a high-level programming language developed by Guido van Rossum.
      It is widely used at companies like Google, Netflix, and Spotify.
      Popular frameworks include Django for web development and TensorFlow for machine learning.
      The Python Software Foundation oversees the development of the language.
    `;
    
    const res = http.post(
      `${BASE_URL}/api/v1/context/store`,
      JSON.stringify({
        content: document,
        context_type: 'document',
        metadata: { source: 'user_upload' },
      }),
      { headers: { 'Content-Type': 'application/json' } }
    );
    
    check(res, { 'upload ok': (r) => r.status === 201 });
    operations++;
    sleep(2);
  });
  
  group('Extract Entities', () => {
    const res = http.post(
      `${BASE_URL}/api/v1/graph/extract`,
      JSON.stringify({
        text: 'Python programming language',
      }),
      { headers: { 'Content-Type': 'application/json' } }
    );
    
    check(res, { 'extract ok': (r) => r.status === 200 });
    operations++;
    sleep(3);
  });
  
  group('Explore Relationships', () => {
    const res = http.get(`${BASE_URL}/api/v1/graph/entity/Python/neighborhood?depth=2`);
    
    check(res, { 'explore ok': (r) => r.status === 200 });
    operations++;
    sleep(4);
  });
  
  group('Semantic Search', () => {
    const res = http.post(
      `${BASE_URL}/api/v1/search/semantic`,
      JSON.stringify({
        query: 'programming languages for web development',
        max_results: 10,
      }),
      { headers: { 'Content-Type': 'application/json' } }
    );
    
    check(res, { 'semantic search ok': (r) => r.status === 200 });
    operations++;
    sleep(3);
  });
  
  const duration = Date.now() - sessionStart;
  sessionDuration.add(duration);
  operationsPerSession.add(operations);
}

/**
 * Conversation Continuation Journey
 * User continues previous conversation, builds on context
 */
export function conversationContinuation() {
  const sessionStart = Date.now();
  let operations = 0;
  const conversationId = `conv_${__VU}_${Math.floor(Date.now() / 10000)}`;
  
  group('Resume Conversation', () => {
    // Retrieve conversation history
    const res = http.post(
      `${BASE_URL}/api/v1/context/retrieve`,
      JSON.stringify({
        query: 'previous discussion',
        conversation_id: conversationId,
        max_results: 10,
      }),
      { headers: { 'Content-Type': 'application/json' } }
    );
    
    check(res, { 'resume ok': (r) => r.status === 200 });
    operations++;
    sleep(2);
  });
  
  group('Add Context', () => {
    // User adds new messages to conversation
    const messages = [
      'Following up on our discussion about API design',
      'I think REST is still a good choice for most cases',
      'GraphQL makes sense for complex data requirements',
    ];
    
    for (const message of messages) {
      const res = http.post(
        `${BASE_URL}/api/v1/context/store`,
        JSON.stringify({
          content: message,
          context_type: 'conversation',
          metadata: { conversation_id: conversationId },
        }),
        { headers: { 'Content-Type': 'application/json' } }
      );
      
      check(res, { 'add message ok': (r) => r.status === 201 });
      operations++;
      sleep(1.5);
    }
  });
  
  group('Context-Aware Query', () => {
    const res = http.post(
      `${BASE_URL}/api/v1/context/retrieve`,
      JSON.stringify({
        query: 'API design best practices',
        conversation_id: conversationId,
        max_results: 5,
      }),
      { headers: { 'Content-Type': 'application/json' } }
    );
    
    check(res, { 'context query ok': (r) => r.status === 200 });
    operations++;
    sleep(3);
  });
  
  const duration = Date.now() - sessionStart;
  sessionDuration.add(duration);
  operationsPerSession.add(operations);
}