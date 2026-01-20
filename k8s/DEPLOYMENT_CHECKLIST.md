# Deployment Checklist

Use this checklist to ensure all necessary steps are completed before and after deployment.

## Pre-Deployment

### Infrastructure
- [ ] Kubernetes cluster provisioned (v1.24+)
- [ ] kubectl configured and working
- [ ] Cluster has sufficient resources:
  - [ ] CPU: Minimum 12 cores available
  - [ ] Memory: Minimum 32 GB available
  - [ ] Storage: Fast SSD storage class available
- [ ] Metrics Server installed and running
- [ ] Istio installed (v1.19+)
  - [ ] istioctl version verified
  - [ ] Istio ingress gateway deployed
  - [ ] External IP assigned to ingress gateway
- [ ] Prometheus Operator installed (optional)
- [ ] VPA installed (optional)

### Configuration
- [ ] Secrets file updated with real values:
  - [ ] NEO4J_PASSWORD (strong password)
  - [ ] NEO4J_AUTH (neo4j/<password>)
  - [ ] JWT_SECRET (random 32+ character string)
  - [ ] API_KEY (random API key)
- [ ] ConfigMaps reviewed and customized:
  - [ ] Environment set correctly
  - [ ] Log level appropriate for environment
  - [ ] Database connection settings verified
  - [ ] Resource limits adjusted for workload
- [ ] DNS configured:
  - [ ] Domain name registered
  - [ ] DNS A record created pointing to Istio ingress IP
- [ ] TLS certificates obtained:
  - [ ] Certificate files (.crt, .key) ready
  - [ ] Certificate validity verified
  - [ ] Certificate matches domain name
- [ ] Container images:
  - [ ] Images built and pushed to registry
  - [ ] Image tags updated in manifests
  - [ ] Image pull secrets configured (if private registry)

### Storage
- [ ] Storage classes verified:
  - [ ] fast-ssd storage class available
  - [ ] standard storage class available
  - [ ] Storage provisioner working
- [ ] Storage quotas checked
- [ ] Backup strategy defined:
  - [ ] Backup schedule determined
  - [ ] Backup retention policy set
  - [ ] Restore procedure tested

### Security
- [ ] RBAC policies reviewed
- [ ] Network policies reviewed
- [ ] Pod security policies reviewed
- [ ] Service account permissions verified
- [ ] Secret encryption at rest enabled
- [ ] Audit logging configured

### Monitoring & Alerting
- [ ] Prometheus configured
- [ ] Grafana configured
- [ ] Alert destinations configured:
  - [ ] Slack/Teams webhook (if applicable)
  - [ ] PagerDuty integration (if applicable)
  - [ ] Email notifications (if applicable)
- [ ] Dashboard imported
- [ ] Alert thresholds reviewed

## Deployment

### Initial Deployment
- [ ] Namespace created
- [ ] Istio injection enabled on namespace
- [ ] ConfigMaps applied
- [ ] Secrets applied
- [ ] Storage classes created
- [ ] RBAC roles created
- [ ] Pod security policies created
- [ ] Network policies created

### Database Deployment
- [ ] Qdrant StatefulSet deployed
- [ ] Qdrant Service created
- [ ] Qdrant pods running (minimum 2)
- [ ] Qdrant cluster formed
- [ ] Qdrant health check passing
- [ ] Neo4j StatefulSet deployed
- [ ] Neo4j Service created
- [ ] Neo4j pods running (minimum 2)
- [ ] Neo4j cluster formed
- [ ] Neo4j cluster leader elected
- [ ] Neo4j health check passing

### API Deployment
- [ ] API Deployment created
- [ ] API Service created
- [ ] API pods running (minimum 2)
- [ ] API health check passing
- [ ] API can connect to Qdrant
- [ ] API can connect to Neo4j

### Istio Configuration
- [ ] Gateway created
- [ ] VirtualService created
- [ ] DestinationRule created
- [ ] PeerAuthentication configured
- [ ] AuthorizationPolicy configured
- [ ] mTLS enabled and working

### Autoscaling
- [ ] HPA created for API
- [ ] HPA metrics available
- [ ] VPA created for all components (if applicable)
- [ ] VPA recommendations visible

### Monitoring
- [ ] ServiceMonitors created
- [ ] Prometheus scraping metrics
- [ ] PrometheusRules created
- [ ] Grafana dashboard imported
- [ ] Alerts firing correctly

## Post-Deployment Verification

### Functional Testing
- [ ] API health endpoint responding: `/health`
- [ ] API ready endpoint responding: `/health/ready`
- [ ] API documentation accessible: `/docs`
- [ ] API endpoints tested:
  - [ ] POST /api/v1/context/memory - Create memory
  - [ ] GET /api/v1/context/memory/{id} - Retrieve memory
  - [ ] POST /api/v1/context/search - Search contexts
  - [ ] GET /api/v1/graph/relationships - Get relationships
- [ ] Authentication working
- [ ] Authorization working
- [ ] CORS configuration working

### Performance Testing
- [ ] Load test performed
- [ ] Response times acceptable (< 500ms p95)
- [ ] Throughput meets requirements
- [ ] Error rate acceptable (< 0.1%)
- [ ] Autoscaling triggers at expected load

### Database Verification
- [ ] Qdrant collections created
- [ ] Vector search working
- [ ] Qdrant snapshots configured
- [ ] Neo4j database accessible
- [ ] Graph queries working
- [ ] Neo4j backups configured

### Security Verification
- [ ] Network policies blocking unauthorized traffic
- [ ] mTLS enforced between services
- [ ] Pods running as non-root
- [ ] Read-only root filesystem (where applicable)
- [ ] Secrets not exposed in logs
- [ ] External access requires authentication

### Monitoring Verification
- [ ] Metrics visible in Prometheus
- [ ] Grafana dashboard showing data
- [ ] Test alert fired successfully
- [ ] Alert notifications received
- [ ] Logs aggregated (if using ELK/Loki)

### Operational Readiness
- [ ] Runbook created
- [ ] On-call rotation defined
- [ ] Escalation procedures documented
- [ ] Disaster recovery tested
- [ ] Backup/restore tested
- [ ] Rollback procedure tested

## Ongoing Operations

### Daily
- [ ] Check pod status
- [ ] Review error logs
- [ ] Check alert status
- [ ] Monitor resource usage

### Weekly
- [ ] Review performance metrics
- [ ] Check disk usage
- [ ] Verify backup success
- [ ] Update dependencies (if needed)
- [ ] Review security advisories

### Monthly
- [ ] Test disaster recovery
- [ ] Review and update documentation
- [ ] Capacity planning review
- [ ] Cost optimization review
- [ ] Security audit

## Rollback Procedure

If issues are encountered:

1. [ ] Identify issue and impact
2. [ ] Decide: fix forward or rollback
3. [ ] If rollback:
   - [ ] Scale down new version
   - [ ] Rollback deployment: `kubectl rollout undo deployment/context-api -n context-foundation`
   - [ ] Verify old version working
   - [ ] Document issue for future reference

## Emergency Contacts

- **On-call Engineer**: [Insert contact]
- **Platform Team Lead**: [Insert contact]
- **Infrastructure Support**: [Insert contact]
- **Cloud Provider Support**: [Insert contact]

## Documentation References

- Deployment Guide: [k8s/README.md](./README.md)
- Troubleshooting Guide: [k8s/TROUBLESHOOTING.md](./TROUBLESHOOTING.md)
- API Documentation: `/docs` endpoint
- Runbook: [Insert link]
- Architecture Diagram: [Insert link]

## Sign-off

- [ ] Deployment completed by: _________________ Date: _________
- [ ] Reviewed by: _________________ Date: _________
- [ ] Approved for production by: _________________ Date: _________

---

## Environment-Specific Notes

### Development
- Reduced resource limits
- Single replica for databases
- Debug logging enabled
- No autoscaling

### Staging
- Similar to production but smaller scale
- 2 replicas minimum
- Used for integration testing
- Automated deployments from main branch

### Production
- Full resource allocation
- 3+ replicas minimum
- Autoscaling enabled
- Manual approval required for deployment
- Blue/green deployment strategy
