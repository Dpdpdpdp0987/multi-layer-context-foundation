# Kubernetes Quick Reference Guide

## Essential Commands

### Deployment
```bash
# Deploy using Kustomize
kubectl apply -k k8s/overlays/production/

# Deploy using script
cd k8s && ./scripts/deploy.sh

# Validate deployment
./scripts/validate.sh
```

### Monitoring
```bash
# Check pod status
kubectl get pods -n context-foundation

# Check all resources
kubectl get all -n context-foundation

# Watch pod status
kubectl get pods -n context-foundation -w

# Check resource usage
kubectl top pods -n context-foundation
kubectl top nodes
```

### Logs
```bash
# API logs
kubectl logs -f deployment/context-api -n context-foundation

# Specific pod logs
kubectl logs -f <pod-name> -n context-foundation

# Previous pod logs (after crash)
kubectl logs <pod-name> -n context-foundation --previous

# All logs from label selector
kubectl logs -f -l app=context-api -n context-foundation

# Logs from Istio sidecar
kubectl logs <pod-name> -n context-foundation -c istio-proxy
```

### Debugging
```bash
# Describe pod
kubectl describe pod <pod-name> -n context-foundation

# Get pod events
kubectl get events -n context-foundation --sort-by='.lastTimestamp'

# Execute command in pod
kubectl exec -it <pod-name> -n context-foundation -- /bin/bash

# Port forward to pod
kubectl port-forward <pod-name> -n context-foundation 8000:8000

# Check endpoints
kubectl get endpoints -n context-foundation
```

### Scaling
```bash
# Manual scale
kubectl scale deployment/context-api --replicas=5 -n context-foundation

# Get HPA status
kubectl get hpa -n context-foundation

# Describe HPA
kubectl describe hpa context-api -n context-foundation

# Get VPA recommendations
kubectl get vpa -n context-foundation
kubectl describe vpa context-api -n context-foundation
```

### Updates
```bash
# Update image
kubectl set image deployment/context-api \
  api=ghcr.io/dpdpdpdp0987/context-api:v2.0.0 \
  -n context-foundation

# Rollout status
kubectl rollout status deployment/context-api -n context-foundation

# Rollout history
kubectl rollout history deployment/context-api -n context-foundation

# Rollback
kubectl rollout undo deployment/context-api -n context-foundation

# Rollback to specific revision
kubectl rollout undo deployment/context-api --to-revision=2 -n context-foundation

# Restart deployment
kubectl rollout restart deployment/context-api -n context-foundation
```

### Configuration
```bash
# Edit ConfigMap
kubectl edit configmap api-config -n context-foundation

# Edit Secret
kubectl edit secret context-secrets -n context-foundation

# Update ConfigMap from file
kubectl create configmap api-config \
  --from-file=k8s/base/configmaps.yaml \
  -n context-foundation \
  --dry-run=client -o yaml | kubectl apply -f -
```

### Database Operations
```bash
# Qdrant
# Check cluster status
kubectl exec qdrant-0 -n context-foundation -- \
  curl http://localhost:6333/cluster

# Create snapshot
kubectl exec qdrant-0 -n context-foundation -- \
  curl -X POST http://localhost:6333/collections/context_memory/snapshots

# Neo4j
# Check cluster status
kubectl exec neo4j-0 -n context-foundation -- \
  cypher-shell -u neo4j -p <password> "CALL dbms.cluster.overview();"

# Create backup
kubectl exec neo4j-0 -n context-foundation -- \
  neo4j-admin dump --database=neo4j --to=/var/lib/neo4j/import/backup.dump
```

### Istio
```bash
# Get Istio ingress IP
kubectl -n istio-system get service istio-ingressgateway

# Check Istio configuration
istioctl analyze -n context-foundation

# Check mTLS status
istioctl authn tls-check <pod-name>.context-foundation

# View Istio proxy config
istioctl proxy-config routes <pod-name> -n context-foundation
```

### Monitoring
```bash
# Port forward to Prometheus
kubectl port-forward -n monitoring svc/prometheus 9090:9090

# Port forward to Grafana
kubectl port-forward -n monitoring svc/grafana 3000:3000

# Check ServiceMonitor
kubectl get servicemonitor -n context-foundation

# Check PrometheusRule
kubectl get prometheusrule -n context-foundation
```

### Cleanup
```bash
# Delete specific resource
kubectl delete deployment/context-api -n context-foundation

# Delete all resources (careful!)
kubectl delete all --all -n context-foundation

# Delete PVCs (data loss!)
kubectl delete pvc --all -n context-foundation

# Full teardown
./scripts/teardown.sh
```

## API Endpoints

### Health Checks
```bash
# Health endpoint
curl http://localhost:8000/health

# Ready endpoint
curl http://localhost:8000/health/ready

# Via Istio ingress (replace with actual domain/IP)
curl -H "Host: context-api.example.com" http://<INGRESS_IP>/health
```

### API Documentation
```bash
# OpenAPI docs
http://localhost:8000/docs

# ReDoc
http://localhost:8000/redoc

# OpenAPI JSON
http://localhost:8000/openapi.json
```

### API Operations
```bash
# Create memory
curl -X POST http://localhost:8000/api/v1/context/memory \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "content": "Sample context",
    "metadata": {"source": "test"}
  }'

# Search context
curl -X POST http://localhost:8000/api/v1/context/search \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "query": "sample",
    "limit": 10
  }'
```

## Troubleshooting Quick Fixes

### Pods Not Starting
```bash
# Check events
kubectl describe pod <pod-name> -n context-foundation

# Check logs
kubectl logs <pod-name> -n context-foundation

# Common fixes:
# 1. Check secrets exist
kubectl get secret context-secrets -n context-foundation

# 2. Check ConfigMaps exist
kubectl get configmap -n context-foundation

# 3. Check storage
kubectl get pvc -n context-foundation
```

### Network Issues
```bash
# Check NetworkPolicies
kubectl get networkpolicy -n context-foundation

# Test connectivity from pod
kubectl exec -it <api-pod> -n context-foundation -- \
  curl http://qdrant:6333/health

# Check service endpoints
kubectl get endpoints -n context-foundation

# Check Istio sidecar
kubectl get pod <pod-name> -n context-foundation -o jsonpath='{.spec.containers[*].name}'
```

### Performance Issues
```bash
# Check resource usage
kubectl top pods -n context-foundation

# Check HPA status
kubectl get hpa -n context-foundation

# Check for throttling
kubectl describe pod <pod-name> -n context-foundation | grep -i throttl

# Check metrics
kubectl port-forward -n monitoring svc/prometheus 9090:9090
# Then visit: http://localhost:9090
```

### Database Issues
```bash
# Qdrant not forming cluster
kubectl get pods -l app=qdrant -n context-foundation
kubectl logs qdrant-0 -n context-foundation | grep cluster

# Neo4j cluster issues
kubectl exec neo4j-0 -n context-foundation -- \
  cypher-shell -u neo4j -p <password> "CALL dbms.cluster.overview();"

# Storage issues
kubectl get pvc -n context-foundation
kubectl describe pvc <pvc-name> -n context-foundation
```

## Environment Variables

### Set from local file
```bash
# Create secret from .env file
kubectl create secret generic context-secrets \
  --from-env-file=.env \
  -n context-foundation

# Create ConfigMap from file
kubectl create configmap api-config \
  --from-env-file=config.env \
  -n context-foundation
```

### Update single value
```bash
# Update secret value
kubectl patch secret context-secrets -n context-foundation \
  -p '{"stringData":{"JWT_SECRET":"new-secret-value"}}'

# Update ConfigMap value
kubectl patch configmap api-config -n context-foundation \
  -p '{"data":{"LOG_LEVEL":"DEBUG"}}'
```

## Resource Requests/Limits

### View current resources
```bash
# Get pod resources
kubectl get pods -n context-foundation -o=jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.containers[0].resources}{"\n"}{end}'

# Get VPA recommendations
kubectl describe vpa context-api -n context-foundation
```

### Update resources
```bash
# Patch deployment
kubectl patch deployment context-api -n context-foundation \
  -p '{"spec":{"template":{"spec":{"containers":[{"name":"api","resources":{"requests":{"memory":"1Gi","cpu":"1000m"},"limits":{"memory":"2Gi","cpu":"2000m"}}}]}}}}'
```

## Backup & Restore

### Create backups
```bash
# Backup all manifests
kubectl get all,configmap,secret,pvc,networkpolicy -n context-foundation -o yaml > backup.yaml

# Backup specific resources
kubectl get deployment,statefulset,service -n context-foundation -o yaml > workloads-backup.yaml
```

### Restore from backup
```bash
kubectl apply -f backup.yaml
```

## Useful Aliases

Add to `.bashrc` or `.zshrc`:

```bash
alias k='kubectl'
alias kgp='kubectl get pods -n context-foundation'
alias kgs='kubectl get svc -n context-foundation'
alias kgd='kubectl get deployment -n context-foundation'
alias kdp='kubectl describe pod -n context-foundation'
alias klf='kubectl logs -f -n context-foundation'
alias kex='kubectl exec -it -n context-foundation'
alias kctx='kubectl config use-context'
```

## Emergency Procedures

### Complete system restart
```bash
# Scale down API
kubectl scale deployment/context-api --replicas=0 -n context-foundation

# Restart databases (one at a time)
kubectl delete pod qdrant-0 -n context-foundation
kubectl wait --for=condition=ready pod/qdrant-0 -n context-foundation

kubectl delete pod neo4j-0 -n context-foundation
kubectl wait --for=condition=ready pod/neo4j-0 -n context-foundation

# Scale up API
kubectl scale deployment/context-api --replicas=3 -n context-foundation
```

### Force delete stuck resources
```bash
# Force delete pod
kubectl delete pod <pod-name> -n context-foundation --force --grace-period=0

# Remove finalizers
kubectl patch pvc <pvc-name> -n context-foundation -p '{"metadata":{"finalizers":null}}'
```

## Monitoring URLs

After port-forwarding:

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs
- **Qdrant UI**: http://localhost:6333/dashboard (if exposed)

## Common Patterns

### Rolling restart all components
```bash
for deployment in $(kubectl get deployment -n context-foundation -o name); do
  kubectl rollout restart $deployment -n context-foundation
done

for statefulset in $(kubectl get statefulset -n context-foundation -o name); do
  kubectl rollout restart $statefulset -n context-foundation
done
```

### Check all pod logs
```bash
for pod in $(kubectl get pods -n context-foundation -o name); do
  echo "=== $pod ==="
  kubectl logs $pod -n context-foundation --tail=10
done
```

### Export all resources
```bash
kubectl get all,cm,secret,pvc,networkpolicy,hpa,vpa,gateway,virtualservice \
  -n context-foundation -o yaml > full-export.yaml
```

---

**Quick Links:**
- [Full Deployment Guide](./README.md)
- [Troubleshooting Guide](./TROUBLESHOOTING.md)
- [Deployment Checklist](./DEPLOYMENT_CHECKLIST.md)
- [Deployment Summary](./DEPLOYMENT_SUMMARY.md)
