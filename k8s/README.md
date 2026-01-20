# Kubernetes Deployment Guide

Comprehensive Kubernetes deployment for the Multi-Layer Context Foundation system with production-ready configurations including autoscaling, service mesh, monitoring, and security.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Istio Ingress Gateway                   │
│                   (TLS Termination & Routing)               │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                      Context API (3+ pods)                   │
│              HPA: 3-20 replicas based on load               │
│         Health Checks, Metrics, Security Context            │
└──────┬─────────────────────────────────┬───────────────────┘
       │                                 │
       ▼                                 ▼
┌─────────────────┐            ┌──────────────────────┐
│  Qdrant Cluster │            │   Neo4j Cluster      │
│   (3 replicas)  │            │    (3 replicas)      │
│  Vector Search  │            │   Graph Database     │
│   100Gi SSD     │            │     200Gi SSD        │
└─────────────────┘            └──────────────────────┘
```

## Components

### Core Services
- **Context API**: FastAPI application (3-20 replicas with HPA)
- **Qdrant**: Vector database cluster (3 replicas)
- **Neo4j**: Graph database cluster (3 replicas)

### Infrastructure
- **Istio Service Mesh**: mTLS, traffic management, observability
- **Prometheus**: Metrics collection and alerting
- **Grafana**: Visualization and dashboards
- **HPA/VPA**: Horizontal and vertical pod autoscaling

### Security
- **Network Policies**: Zero-trust networking
- **Pod Security Policies**: Restricted execution
- **RBAC**: Fine-grained access control
- **Secret Management**: Encrypted secrets

## Prerequisites

1. **Kubernetes Cluster**: v1.24+
   ```bash
   kubectl version --short
   ```

2. **Istio**: v1.19+
   ```bash
   istioctl version
   ```

3. **Prometheus Operator** (for monitoring)
   ```bash
   kubectl get crd servicemonitors.monitoring.coreos.com
   ```

4. **Metrics Server** (for HPA)
   ```bash
   kubectl get deployment metrics-server -n kube-system
   ```

5. **VPA** (optional, for vertical autoscaling)
   ```bash
   kubectl get crd verticalpodautoscalers.autoscaling.k8s.io
   ```

6. **Storage Class**: fast-ssd and standard storage classes
   ```bash
   kubectl get storageclass
   ```

## Quick Start

### 1. Setup Namespace and Base Configuration

```bash
# Create namespace
kubectl apply -f k8s/base/namespace.yaml

# Label namespace for Istio injection
kubectl label namespace context-foundation istio-injection=enabled

# Apply ConfigMaps and Secrets
kubectl apply -f k8s/base/configmaps.yaml

# IMPORTANT: Update secrets before applying!
# Edit k8s/base/secrets.yaml with real values, then:
kubectl apply -f k8s/base/secrets.yaml
```

### 2. Deploy Storage

```bash
# Create storage classes (adjust for your cloud provider)
kubectl apply -f k8s/storage/storage-class.yaml

# Create backup PVC
kubectl apply -f k8s/storage/backup-pvc.yaml
```

### 3. Deploy Security Policies

```bash
# Apply RBAC
kubectl apply -f k8s/security/rbac.yaml

# Apply Pod Security Policies
kubectl apply -f k8s/security/pod-security-policy.yaml

# Apply Network Policies
kubectl apply -f k8s/security/network-policy.yaml
```

### 4. Deploy Databases

```bash
# Deploy Qdrant
kubectl apply -f k8s/statefulsets/qdrant-statefulset.yaml
kubectl apply -f k8s/services/qdrant-service.yaml

# Wait for Qdrant to be ready
kubectl wait --for=condition=ready pod -l app=qdrant -n context-foundation --timeout=300s

# Deploy Neo4j
kubectl apply -f k8s/statefulsets/neo4j-statefulset.yaml
kubectl apply -f k8s/services/neo4j-service.yaml

# Wait for Neo4j to be ready
kubectl wait --for=condition=ready pod -l app=neo4j -n context-foundation --timeout=600s
```

### 5. Deploy API

```bash
# Deploy API
kubectl apply -f k8s/deployments/api-deployment.yaml
kubectl apply -f k8s/services/api-service.yaml

# Wait for API to be ready
kubectl wait --for=condition=ready pod -l app=context-api -n context-foundation --timeout=300s
```

### 6. Deploy Istio Configuration

```bash
# Apply Istio Gateway and VirtualService
kubectl apply -f k8s/istio/gateway.yaml
kubectl apply -f k8s/istio/virtual-service.yaml
kubectl apply -f k8s/istio/destination-rule.yaml

# Apply security policies
kubectl apply -f k8s/istio/peer-authentication.yaml
kubectl apply -f k8s/istio/authorization-policy.yaml
```

### 7. Deploy Autoscaling

```bash
# Apply HPA for API
kubectl apply -f k8s/autoscaling/api-hpa.yaml

# Apply VPA (if installed)
kubectl apply -f k8s/autoscaling/api-vpa.yaml
kubectl apply -f k8s/autoscaling/qdrant-vpa.yaml
kubectl apply -f k8s/autoscaling/neo4j-vpa.yaml
```

### 8. Deploy Monitoring

```bash
# Apply ServiceMonitors
kubectl apply -f k8s/monitoring/service-monitor.yaml

# Apply Prometheus rules
kubectl apply -f k8s/monitoring/prometheus-rules.yaml

# Apply Grafana dashboard
kubectl apply -f k8s/monitoring/grafana-dashboard.yaml
```

## Verification

### Check Deployment Status

```bash
# Check all resources
kubectl get all -n context-foundation

# Check pod status
kubectl get pods -n context-foundation

# Check services
kubectl get svc -n context-foundation

# Check PVCs
kubectl get pvc -n context-foundation
```

### Test API Endpoint

```bash
# Get Istio Ingress Gateway external IP
export INGRESS_HOST=$(kubectl -n istio-system get service istio-ingressgateway -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

# Test health endpoint (update host header to match your domain)
curl -H "Host: context-api.example.com" http://$INGRESS_HOST/health

# Test API documentation
curl -H "Host: context-api.example.com" http://$INGRESS_HOST/docs
```

### Check Logs

```bash
# API logs
kubectl logs -f deployment/context-api -n context-foundation

# Qdrant logs
kubectl logs -f statefulset/qdrant -n context-foundation

# Neo4j logs
kubectl logs -f statefulset/neo4j -n context-foundation

# Istio sidecar logs
kubectl logs -f deployment/context-api -n context-foundation -c istio-proxy
```

### Monitor Resources

```bash
# Watch HPA status
kubectl get hpa -n context-foundation -w

# Check resource usage
kubectl top pods -n context-foundation
kubectl top nodes

# View events
kubectl get events -n context-foundation --sort-by='.lastTimestamp'
```

## Configuration

### Update ConfigMaps

```bash
# Edit ConfigMap
kubectl edit configmap api-config -n context-foundation

# Or apply updated file
kubectl apply -f k8s/base/configmaps.yaml

# Restart API pods to pick up changes
kubectl rollout restart deployment/context-api -n context-foundation
```

### Update Secrets

```bash
# Update secret (base64 encoded)
kubectl create secret generic context-secrets \
  --from-literal=NEO4J_PASSWORD='new-password' \
  --from-literal=JWT_SECRET='new-secret' \
  -n context-foundation \
  --dry-run=client -o yaml | kubectl apply -f -

# Restart pods to use new secrets
kubectl rollout restart deployment/context-api -n context-foundation
```

### Scale Resources

```bash
# Manually scale API (overrides HPA min/max temporarily)
kubectl scale deployment/context-api --replicas=5 -n context-foundation

# Update HPA limits
kubectl edit hpa context-api -n context-foundation
```

## Maintenance

### Rolling Updates

```bash
# Update API image
kubectl set image deployment/context-api \
  api=ghcr.io/dpdpdpdp0987/context-api:v2.0.0 \
  -n context-foundation

# Watch rollout status
kubectl rollout status deployment/context-api -n context-foundation

# Rollback if needed
kubectl rollout undo deployment/context-api -n context-foundation
```

### Database Backups

```bash
# Qdrant snapshot
kubectl exec -it qdrant-0 -n context-foundation -- \
  curl -X POST http://localhost:6333/collections/context_memory/snapshots

# Neo4j backup
kubectl exec -it neo4j-0 -n context-foundation -- \
  neo4j-admin dump --database=neo4j --to=/var/lib/neo4j/import/backup.dump
```

### Certificate Rotation

```bash
# Update TLS certificate secret
kubectl create secret tls context-api-tls \
  --cert=path/to/tls.crt \
  --key=path/to/tls.key \
  -n istio-system \
  --dry-run=client -o yaml | kubectl apply -f -
```

## Monitoring & Alerting

### Access Grafana Dashboard

1. Port-forward to Grafana:
   ```bash
   kubectl port-forward -n monitoring svc/grafana 3000:3000
   ```

2. Open browser: http://localhost:3000
3. Import dashboard from `k8s/monitoring/grafana-dashboard.yaml`

### View Prometheus Alerts

```bash
# Port-forward to Prometheus
kubectl port-forward -n monitoring svc/prometheus 9090:9090

# Open browser: http://localhost:9090/alerts
```

### Check ServiceMonitor Status

```bash
# List ServiceMonitors
kubectl get servicemonitor -n context-foundation

# Check Prometheus targets
# Access Prometheus UI and navigate to Status > Targets
```

## Troubleshooting

See [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) for detailed troubleshooting guides.

### Common Issues

1. **Pods not starting**: Check events and logs
   ```bash
   kubectl describe pod <pod-name> -n context-foundation
   kubectl logs <pod-name> -n context-foundation
   ```

2. **Network connectivity issues**: Verify NetworkPolicies
   ```bash
   kubectl get networkpolicy -n context-foundation
   ```

3. **Database cluster not forming**: Check headless service and StatefulSet
   ```bash
   kubectl get svc -n context-foundation
   kubectl get endpoints -n context-foundation
   ```

4. **HPA not scaling**: Verify metrics-server
   ```bash
   kubectl get apiservice v1beta1.metrics.k8s.io -o yaml
   kubectl top nodes
   ```

## Production Checklist

- [ ] Update all secrets with production values
- [ ] Configure proper DNS for ingress
- [ ] Set up TLS certificates
- [ ] Configure backup jobs
- [ ] Set up log aggregation (ELK/Loki)
- [ ] Configure alerting (PagerDuty/Slack)
- [ ] Review resource limits and requests
- [ ] Test disaster recovery procedures
- [ ] Set up monitoring dashboards
- [ ] Configure pod disruption budgets
- [ ] Review and adjust HPA/VPA settings
- [ ] Set up network policies for zero-trust
- [ ] Enable audit logging
- [ ] Configure image pull secrets for private registries
- [ ] Set up GitOps (ArgoCD/Flux) for continuous deployment

## Security Considerations

1. **Secret Management**: Use external secret management (e.g., HashiCorp Vault, AWS Secrets Manager)
2. **Image Scanning**: Scan images for vulnerabilities before deployment
3. **Network Policies**: Enforce zero-trust networking
4. **RBAC**: Follow principle of least privilege
5. **mTLS**: Enabled via Istio for all inter-service communication
6. **Pod Security**: Run as non-root, read-only root filesystem where possible
7. **Audit Logging**: Enable Kubernetes audit logging
8. **Certificate Management**: Use cert-manager for automated certificate rotation

## Performance Tuning

### API
- Adjust worker processes based on CPU cores
- Tune connection pools for Qdrant and Neo4j
- Configure request timeouts appropriately
- Enable response caching where applicable

### Qdrant
- Adjust `MAX_SEARCH_THREADS` based on workload
- Monitor and tune HNSW parameters
- Configure appropriate replica count for redundancy

### Neo4j
- Tune page cache and heap sizes based on data size
- Configure appropriate JVM settings
- Monitor query performance and add indexes

## Cost Optimization

1. **Right-size resources**: Use VPA recommendations
2. **Spot instances**: Use for non-critical workloads
3. **Storage tiering**: Use different storage classes
4. **HPA configuration**: Set appropriate min/max replicas
5. **Resource requests**: Set accurate requests to avoid over-provisioning

## Support

For issues and questions:
- Create an issue on GitHub
- Check the troubleshooting guide
- Review logs and metrics in Grafana

## License

MIT License - See LICENSE file for details
