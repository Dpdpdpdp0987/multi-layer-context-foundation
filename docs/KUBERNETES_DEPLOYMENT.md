# Kubernetes Deployment Guide

## Overview

Comprehensive production-ready Kubernetes deployment for the Multi-Layer Context Foundation system with autoscaling, service mesh, monitoring, and security.

## Prerequisites

### Required Tools
- Kubernetes cluster (v1.24+)
- kubectl (v1.24+)
- Helm 3 (optional)
- Istio (v1.18+) for service mesh
- cert-manager for TLS certificates

### Cluster Requirements
- Minimum 3 nodes
- 8 CPUs and 16GB RAM per node
- Support for LoadBalancer services
- StorageClass for persistent volumes
- Metrics Server installed
- Prometheus Operator (for monitoring)

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Istio Ingress Gateway                │
│              (TLS Termination, Load Balancing)          │
└────────────────────┬────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
┌───────▼────────┐     ┌─────────▼──────┐
│  MLCF API      │     │   Monitoring   │
│  (3-20 pods)   │     │  (Prometheus)  │
│  - HPA         │     └────────────────┘
│  - VPA         │
│  - PDB         │
└───┬─────────┬──┘
    │         │
    │         │
┌───▼───┐ ┌──▼────┐
│Qdrant │ │ Neo4j │
│(3-10) │ │  (3)  │
│StatefulSet│StatefulSet│
└───────┘ └───────┘
```

## Quick Start

### 1. Create Namespace

```bash
kubectl apply -f k8s/base/namespace.yaml
```

### 2. Configure Secrets

```bash
# Update secrets with your values
kubectl create secret generic mlcf-api-secrets \
  --from-literal=JWT_SECRET_KEY='your-secure-jwt-secret' \
  --from-literal=NEO4J_PASSWORD='your-secure-password' \
  -n mlcf

kubectl create secret generic neo4j-auth \
  --from-literal=NEO4J_AUTH='neo4j/your-secure-password' \
  -n mlcf
```

### 3. Apply ConfigMaps

```bash
kubectl apply -f k8s/base/configmap.yaml
```

### 4. Deploy Storage Classes

```bash
kubectl apply -f k8s/storage/storageclass.yaml
```

### 5. Deploy Databases

```bash
# Deploy Qdrant
kubectl apply -f k8s/deployments/qdrant-statefulset.yaml

# Deploy Neo4j
kubectl apply -f k8s/deployments/neo4j-statefulset.yaml

# Wait for databases to be ready
kubectl wait --for=condition=ready pod -l app=qdrant -n mlcf --timeout=300s
kubectl wait --for=condition=ready pod -l app=neo4j -n mlcf --timeout=300s
```

### 6. Deploy Services

```bash
kubectl apply -f k8s/services/services.yaml
```

### 7. Deploy API

```bash
# Create RBAC
kubectl apply -f k8s/security/rbac.yaml

# Deploy API
kubectl apply -f k8s/deployments/api-deployment.yaml

# Wait for API to be ready
kubectl wait --for=condition=ready pod -l app=mlcf-api -n mlcf --timeout=180s
```

### 8. Configure Autoscaling

```bash
# Horizontal Pod Autoscaler
kubectl apply -f k8s/autoscaling/hpa.yaml

# Vertical Pod Autoscaler (optional)
kubectl apply -f k8s/autoscaling/vpa.yaml

# Pod Disruption Budgets
kubectl apply -f k8s/autoscaling/pdb.yaml
```

### 9. Apply Network Policies

```bash
kubectl apply -f k8s/security/network-policies.yaml
```

### 10. Configure Ingress

**Option A: NGINX Ingress**
```bash
# Update domain in k8s/ingress/ingress.yaml
kubectl apply -f k8s/ingress/ingress.yaml
```

**Option B: Istio Service Mesh**
```bash
# Ensure Istio is installed
istioctl install --set profile=production

# Apply Istio configurations
kubectl apply -f k8s/ingress/istio-gateway.yaml
```

### 11. Setup Monitoring

```bash
# Apply ServiceMonitors
kubectl apply -f k8s/monitoring/servicemonitor.yaml

# Apply Prometheus rules
kubectl apply -f k8s/monitoring/prometheus-rules.yaml

# Apply Grafana dashboard
kubectl apply -f k8s/monitoring/grafana-dashboard.yaml
```

## Verification

### Check Deployments

```bash
# Check all pods
kubectl get pods -n mlcf

# Check services
kubectl get svc -n mlcf

# Check ingress
kubectl get ingress -n mlcf

# Check autoscaling
kubectl get hpa -n mlcf
```

### Test API

```bash
# Port-forward for local testing
kubectl port-forward svc/mlcf-api 8000:80 -n mlcf

# Test health endpoint
curl http://localhost:8000/health

# Or test via ingress (if configured)
curl https://api.mlcf.example.com/health
```

### Check Logs

```bash
# API logs
kubectl logs -f deployment/mlcf-api -n mlcf

# Qdrant logs
kubectl logs -f qdrant-0 -n mlcf

# Neo4j logs
kubectl logs -f neo4j-0 -n mlcf
```

## Configuration

### Environment Variables

Edit `k8s/base/configmap.yaml` to configure:

- API settings (host, port, debug)
- CORS origins
- Rate limiting
- Authentication
- Vector search (Qdrant)
- Graph search (Neo4j)
- Context layers
- Cache settings
- Request limits

### Secrets Management

**Option 1: Kubernetes Secrets (Default)**
```bash
kubectl create secret generic mlcf-api-secrets \
  --from-literal=JWT_SECRET_KEY='...' \
  -n mlcf
```

**Option 2: External Secrets Operator**
```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: mlcf-api-secrets
  namespace: mlcf
spec:\n  secretStoreRef:\n    name: aws-secrets-manager\n  target:\n    name: mlcf-api-secrets\n  data:\n  - secretKey: JWT_SECRET_KEY\n    remoteRef:\n      key: mlcf/jwt-secret\n```

**Option 3: Sealed Secrets**
```bash
kubeseal --format=yaml < secret.yaml > sealed-secret.yaml
kubectl apply -f sealed-secret.yaml
```

## Scaling

### Manual Scaling

```bash
# Scale API
kubectl scale deployment mlcf-api --replicas=5 -n mlcf

# Scale Qdrant
kubectl scale statefulset qdrant --replicas=5 -n mlcf
```

### Autoscaling Configuration

**HPA (Horizontal Pod Autoscaler):**
- API: 3-20 replicas based on CPU/memory/requests
- Qdrant: 3-10 replicas based on CPU/memory
- Automatic scale up/down with stabilization

**VPA (Vertical Pod Autoscaler):**
- Automatically adjusts resource requests/limits
- Configured for all components
- Respects min/max constraints

**PDB (Pod Disruption Budget):**
- Ensures minimum availability during disruptions
- Minimum 2 pods available for each component

## Monitoring

### Prometheus Metrics

Access metrics:
```bash
# Port-forward Prometheus
kubectl port-forward -n monitoring svc/prometheus-k8s 9090:9090

# Open http://localhost:9090
```

**Available Metrics:**
- `http_requests_total` - Request count
- `http_request_duration_seconds` - Request latency
- `container_memory_usage_bytes` - Memory usage
- `container_cpu_usage_seconds_total` - CPU usage

### Grafana Dashboards

Access Grafana:
```bash
# Port-forward Grafana
kubectl port-forward -n monitoring svc/grafana 3000:3000

# Open http://localhost:3000
```

### Alerts

Configured alerts (see `k8s/monitoring/prometheus-rules.yaml`):
- High error rate (>5%)
- High latency (p95 >1s)
- Pod down (<2 replicas)
- High memory usage (>90%)
- High CPU usage (>90%)

## Security

### Network Policies

Network policies restrict traffic:
- API can access Qdrant and Neo4j
- Databases can communicate internally
- No external egress except DNS
- Ingress only from Istio gateway

### RBAC

Service accounts with minimal permissions:
- API can read ConfigMaps and Secrets
- API can list Pods
- No cluster-wide permissions

### Pod Security

- Run as non-root
- Read-only root filesystem
- No privilege escalation
- Drop all capabilities
- Seccomp profile enabled

### TLS/mTLS

**With Istio:**
- Automatic mTLS between services
- TLS termination at gateway
- Certificate rotation

**With cert-manager:**
```bash
# Install cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Create ClusterIssuer
cat <<EOF | kubectl apply -f -
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:\n  name: letsencrypt-prod\nspec:\n  acme:\n    server: https://acme-v02.api.letsencrypt.org/directory\n    email: your-email@example.com\n    privateKeySecretRef:\n      name: letsencrypt-prod\n    solvers:\n    - http01:\n        ingress:\n          class: nginx\nEOF
```

## Backup and Restore

### Qdrant Backup

```bash
# Create snapshot
kubectl exec -it qdrant-0 -n mlcf -- \
  curl -X POST http://localhost:6333/snapshots

# Download snapshot
kubectl cp mlcf/qdrant-0:/qdrant/snapshots/snapshot.tar \
  ./qdrant-backup.tar
```

### Neo4j Backup

```bash
# Backup database
kubectl exec -it neo4j-0 -n mlcf -- \
  neo4j-admin database dump neo4j --to=/backups/neo4j-backup.dump

# Download backup
kubectl cp mlcf/neo4j-0:/backups/neo4j-backup.dump \
  ./neo4j-backup.dump
```

### Restore

```bash
# Restore Qdrant
kubectl cp ./qdrant-backup.tar mlcf/qdrant-0:/qdrant/snapshots/

# Restore Neo4j
kubectl cp ./neo4j-backup.dump mlcf/neo4j-0:/backups/
kubectl exec -it neo4j-0 -n mlcf -- \
  neo4j-admin database load neo4j --from=/backups/neo4j-backup.dump
```

## Troubleshooting

### Pod Not Starting

```bash
# Check pod status
kubectl describe pod <pod-name> -n mlcf

# Check events
kubectl get events -n mlcf --sort-by='.lastTimestamp'

# Check logs
kubectl logs <pod-name> -n mlcf --previous
```

### Database Connection Issues

```bash
# Test Qdrant connectivity
kubectl run -it --rm debug --image=curlimages/curl --restart=Never -n mlcf -- \
  curl http://qdrant-service:6333/

# Test Neo4j connectivity
kubectl run -it --rm debug --image=appropriate/curl --restart=Never -n mlcf -- \
  curl http://neo4j-service:7474/
```

### High Memory/CPU Usage

```bash
# Check resource usage
kubectl top pods -n mlcf

# Check HPA status
kubectl get hpa -n mlcf

# Increase resources if needed
kubectl set resources deployment mlcf-api \
  --requests=cpu=500m,memory=1Gi \
  --limits=cpu=2000m,memory=4Gi \
  -n mlcf
```

### Network Policy Issues

```bash
# Temporarily disable for testing
kubectl delete networkpolicy --all -n mlcf

# Re-enable
kubectl apply -f k8s/security/network-policies.yaml
```

## Upgrade Strategy

### Rolling Update

```bash
# Update image
kubectl set image deployment/mlcf-api \
  api=mlcf-api:v1.1.0 \
  -n mlcf

# Monitor rollout
kubectl rollout status deployment/mlcf-api -n mlcf

# Rollback if needed
kubectl rollout undo deployment/mlcf-api -n mlcf
```

### Blue-Green Deployment

```bash
# Deploy new version with different labels
kubectl apply -f k8s/deployments/api-deployment-v2.yaml

# Switch traffic
kubectl patch service mlcf-api -n mlcf \
  -p '{"spec":{"selector":{"version":"v2"}}}'

# Remove old version
kubectl delete deployment mlcf-api-v1 -n mlcf
```

## Production Checklist

- [ ] Update all secrets in `k8s/base/secrets.yaml`
- [ ] Configure domain in ingress
- [ ] Set up TLS certificates
- [ ] Configure monitoring alerts
- [ ] Set up log aggregation
- [ ] Configure backup schedule
- [ ] Review resource limits
- [ ] Test disaster recovery
- [ ] Document runbooks
- [ ] Set up CI/CD pipeline
- [ ] Configure cost monitoring
- [ ] Review security policies
- [ ] Load testing
- [ ] Chaos engineering tests

## Best Practices

1. **Always use namespaces** for isolation
2. **Set resource requests and limits** for all containers
3. **Use readiness and liveness probes** for health checks
4. **Enable autoscaling** for production workloads
5. **Use pod disruption budgets** to maintain availability
6. **Implement network policies** for security
7. **Use secrets for sensitive data**, never in ConfigMaps
8. **Enable monitoring and alerting** before going live
9. **Test backup and restore** procedures regularly
10. **Use GitOps** for deployment management

## Additional Resources

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Istio Documentation](https://istio.io/latest/docs/)
- [Prometheus Operator](https://prometheus-operator.dev/)
- [cert-manager Documentation](https://cert-manager.io/docs/)
