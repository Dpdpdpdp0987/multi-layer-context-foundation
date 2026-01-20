# Kubernetes Deployment Troubleshooting Guide

## Table of Contents

1. [Pod Issues](#pod-issues)
2. [Network Issues](#network-issues)
3. [Storage Issues](#storage-issues)
4. [Database Issues](#database-issues)
5. [Autoscaling Issues](#autoscaling-issues)
6. [Istio Issues](#istio-issues)
7. [Monitoring Issues](#monitoring-issues)
8. [Performance Issues](#performance-issues)

## Pod Issues

### Pods Stuck in Pending State

**Symptoms**: Pods remain in `Pending` state

**Diagnosis**:
```bash
kubectl describe pod <pod-name> -n context-foundation
```

**Common Causes & Solutions**:

1. **Insufficient Resources**
   ```bash
   # Check node resources
   kubectl top nodes
   kubectl describe nodes
   ```
   Solution: Add more nodes or reduce resource requests

2. **PVC Not Bound**
   ```bash
   kubectl get pvc -n context-foundation
   ```
   Solution: Check storage class and provisioner

3. **Pod Scheduling Constraints**
   ```bash
   kubectl get pod <pod-name> -n context-foundation -o yaml | grep -A 10 affinity
   ```
   Solution: Relax affinity/anti-affinity rules or add matching nodes

### Pods in CrashLoopBackOff

**Symptoms**: Pods continuously restart

**Diagnosis**:
```bash
kubectl logs <pod-name> -n context-foundation
kubectl logs <pod-name> -n context-foundation --previous
```

**Common Causes & Solutions**:

1. **Application Error**
   - Check logs for error messages
   - Verify environment variables and secrets
   - Check database connectivity

2. **Liveness Probe Failing**
   ```bash
   kubectl describe pod <pod-name> -n context-foundation | grep -A 5 Liveness
   ```
   Solution: Adjust probe timing or fix application health endpoint

3. **Missing Dependencies**
   - Verify all required ConfigMaps and Secrets exist
   - Check database services are running

### Pods Not Ready

**Symptoms**: Pods running but not passing readiness checks

**Diagnosis**:
```bash
kubectl describe pod <pod-name> -n context-foundation | grep -A 5 Readiness
kubectl exec <pod-name> -n context-foundation -- curl localhost:8000/health/ready
```

**Solutions**:
1. Check readiness probe configuration
2. Verify application startup time vs initialDelaySeconds
3. Check dependencies (databases) are ready

## Network Issues

### Cannot Access API from Outside

**Diagnosis**:
```bash
# Check Istio Gateway
kubectl get gateway -n context-foundation
kubectl describe gateway context-gateway -n context-foundation

# Check VirtualService
kubectl get virtualservice -n context-foundation

# Check Istio Ingress Gateway
kubectl get svc -n istio-system
kubectl get pods -n istio-system
```

**Solutions**:
1. Verify DNS points to Istio Ingress Gateway external IP
2. Check TLS certificate is valid
3. Verify Gateway and VirtualService configuration
4. Check Istio sidecar injection: `kubectl get pod <pod-name> -n context-foundation -o jsonpath='{.spec.containers[*].name}'`

### Inter-Pod Communication Failing

**Diagnosis**:
```bash
# Check NetworkPolicies
kubectl get networkpolicy -n context-foundation

# Test connectivity from API pod to Qdrant
kubectl exec -it deployment/context-api -n context-foundation -- \
  curl -v http://qdrant:6333/health

# Test Neo4j connectivity
kubectl exec -it deployment/context-api -n context-foundation -- \
  curl -v http://neo4j:7474
```

**Solutions**:
1. Verify NetworkPolicy allows traffic
2. Check Service endpoints: `kubectl get endpoints -n context-foundation`
3. Verify DNS resolution: `kubectl exec -it <pod> -n context-foundation -- nslookup qdrant`
4. Check Istio mTLS configuration

### DNS Resolution Issues

**Diagnosis**:
```bash
kubectl exec -it deployment/context-api -n context-foundation -- nslookup qdrant
kubectl exec -it deployment/context-api -n context-foundation -- cat /etc/resolv.conf
```

**Solutions**:
1. Check CoreDNS pods: `kubectl get pods -n kube-system -l k8s-app=kube-dns`
2. Verify service exists: `kubectl get svc -n context-foundation`
3. Check NetworkPolicy doesn't block DNS

## Storage Issues

### PVC Stuck in Pending

**Diagnosis**:
```bash
kubectl get pvc -n context-foundation
kubectl describe pvc <pvc-name> -n context-foundation
kubectl get storageclass
```

**Solutions**:
1. Verify StorageClass exists and is correct
2. Check storage provisioner is running
3. Verify cloud provider credentials and permissions
4. Check for node affinity issues with `WaitForFirstConsumer`

### Disk Space Issues

**Diagnosis**:
```bash
# Check PVC usage
kubectl exec -it <pod-name> -n context-foundation -- df -h

# Check Prometheus metrics
kubectl port-forward -n monitoring svc/prometheus 9090:9090
# Query: kubelet_volume_stats_used_bytes / kubelet_volume_stats_capacity_bytes
```

**Solutions**:
1. Expand PVC (if allowVolumeExpansion: true):
   ```bash
   kubectl patch pvc <pvc-name> -n context-foundation -p '{"spec":{"resources":{"requests":{"storage":"200Gi"}}}}'
   ```
2. Clean up old data
3. Create backups and restore to larger volume

## Database Issues

### Qdrant Cluster Not Forming

**Diagnosis**:
```bash
# Check pod status
kubectl get pods -l app=qdrant -n context-foundation

# Check logs
kubectl logs qdrant-0 -n context-foundation

# Check cluster status
kubectl exec qdrant-0 -n context-foundation -- \
  curl http://localhost:6333/cluster

# Check headless service
kubectl get svc qdrant-headless -n context-foundation
kubectl get endpoints qdrant-headless -n context-foundation
```

**Solutions**:
1. Verify headless service has endpoints for all pods
2. Check NetworkPolicy allows p2p port (6335)
3. Verify pod DNS names are resolvable
4. Check logs for connection errors

### Neo4j Cluster Issues

**Diagnosis**:
```bash
# Check cluster status
kubectl exec neo4j-0 -n context-foundation -- \
  cypher-shell -u neo4j -p <password> "CALL dbms.cluster.overview();"

# Check logs
kubectl logs neo4j-0 -n context-foundation | grep -i cluster

# Verify cluster ports
kubectl get svc neo4j-headless -n context-foundation
```

**Solutions**:
1. Verify initial discovery members are correct
2. Check NetworkPolicy allows cluster ports (5000, 6000, 7000)
3. Ensure minimum cluster size requirements are met
4. Check for split-brain scenarios

### Connection Pool Exhaustion

**Symptoms**: API reports "too many connections" or timeout errors

**Diagnosis**:
```bash
# Check API logs
kubectl logs deployment/context-api -n context-foundation | grep -i "connection"

# Check database connection metrics
kubectl exec qdrant-0 -n context-foundation -- \
  curl http://localhost:6333/metrics | grep connection
```

**Solutions**:
1. Increase connection pool size in API configuration
2. Scale API horizontally
3. Check for connection leaks in application code
4. Tune database max connections

## Autoscaling Issues

### HPA Not Scaling

**Diagnosis**:
```bash
# Check HPA status
kubectl get hpa -n context-foundation
kubectl describe hpa context-api -n context-foundation

# Check metrics-server
kubectl get apiservice v1beta1.metrics.k8s.io -o yaml
kubectl top nodes
kubectl top pods -n context-foundation
```

**Solutions**:
1. Verify metrics-server is running: `kubectl get pods -n kube-system | grep metrics-server`
2. Check pod resource requests are set
3. Verify custom metrics (if used) are available
4. Check HPA events: `kubectl describe hpa context-api -n context-foundation`

### VPA Not Updating Resources

**Diagnosis**:
```bash
kubectl get vpa -n context-foundation
kubectl describe vpa context-api -n context-foundation
```

**Solutions**:
1. Verify VPA admission controller is running
2. Check updateMode is set correctly (Auto/Recreate/Off)
3. Verify resource policy constraints
4. Check VPA recommender logs

### Pods Scaling Too Aggressively

**Solutions**:
1. Adjust HPA stabilization window
2. Tune scaleDown/scaleUp policies
3. Adjust target utilization thresholds
4. Implement pod disruption budgets

## Istio Issues

### Sidecar Not Injected

**Diagnosis**:
```bash
# Check namespace label
kubectl get namespace context-foundation --show-labels

# Check pod for sidecar
kubectl get pod <pod-name> -n context-foundation -o jsonpath='{.spec.containers[*].name}'
```

**Solutions**:
```bash
# Label namespace
kubectl label namespace context-foundation istio-injection=enabled

# Restart pods
kubectl rollout restart deployment/context-api -n context-foundation
```

### mTLS Issues

**Diagnosis**:
```bash
# Check PeerAuthentication
kubectl get peerauthentication -n context-foundation

# Check DestinationRule
kubectl get destinationrule -n context-foundation

# Test mTLS status
istioctl authn tls-check <pod-name>.<namespace> qdrant.context-foundation.svc.cluster.local
```

**Solutions**:
1. Verify PeerAuthentication policy
2. Check DestinationRule tls settings
3. Ensure both services have sidecars

### Traffic Routing Issues

**Diagnosis**:
```bash
# Check VirtualService
kubectl get virtualservice -n context-foundation -o yaml

# Check Gateway
kubectl get gateway -n context-foundation -o yaml

# Check Istio config
istioctl analyze -n context-foundation
```

**Solutions**:
1. Verify host matching in VirtualService
2. Check Gateway selector matches Istio ingress
3. Use istioctl analyze for configuration issues

## Monitoring Issues

### Prometheus Not Scraping Metrics

**Diagnosis**:
```bash
# Check ServiceMonitor
kubectl get servicemonitor -n context-foundation

# Access Prometheus UI and check targets
kubectl port-forward -n monitoring svc/prometheus 9090:9090
# Navigate to Status > Targets
```

**Solutions**:
1. Verify ServiceMonitor selector matches service labels
2. Check prometheus.io annotations on pods
3. Verify NetworkPolicy allows Prometheus access
4. Check service has correct port name

### Alerts Not Firing

**Diagnosis**:
```bash
# Check PrometheusRule
kubectl get prometheusrule -n context-foundation

# Check Prometheus UI
kubectl port-forward -n monitoring svc/prometheus 9090:9090
# Navigate to Alerts
```

**Solutions**:
1. Verify PrometheusRule is loaded
2. Check alert expressions are correct
3. Verify metrics are being collected
4. Check Alertmanager configuration

### Grafana Dashboard Not Showing Data

**Solutions**:
1. Verify Prometheus datasource is configured
2. Check metric names match dashboard queries
3. Verify time range
4. Check Prometheus is collecting metrics

## Performance Issues

### High API Latency

**Diagnosis**:
```bash
# Check metrics
kubectl port-forward -n monitoring svc/prometheus 9090:9090
# Query: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Check logs for slow operations
kubectl logs deployment/context-api -n context-foundation | grep -i "slow"

# Check resource usage
kubectl top pods -n context-foundation
```

**Solutions**:
1. Scale API horizontally
2. Increase resource limits
3. Optimize database queries
4. Add caching
5. Review connection pool settings

### Database Performance Issues

**For Qdrant**:
```bash
# Check search performance metrics
kubectl exec qdrant-0 -n context-foundation -- \
  curl http://localhost:6333/metrics | grep search_duration

# Check resource usage
kubectl top pod qdrant-0 -n context-foundation
```

Solutions:
1. Increase MAX_SEARCH_THREADS
2. Tune HNSW parameters
3. Add more replicas
4. Increase resource limits

**For Neo4j**:
```bash
# Check query performance
kubectl exec neo4j-0 -n context-foundation -- \
  cypher-shell -u neo4j -p <password> "CALL dbms.listQueries();"

# Check memory usage
kubectl exec neo4j-0 -n context-foundation -- \
  cypher-shell -u neo4j -p <password> "CALL dbms.queryJmx('java.lang:type=Memory');"
```

Solutions:
1. Add indexes
2. Increase heap size
3. Tune page cache
4. Optimize queries
5. Add more cluster members

### Resource Exhaustion

**Diagnosis**:
```bash
# Check resource usage
kubectl top pods -n context-foundation
kubectl top nodes

# Check for OOMKilled
kubectl get pods -n context-foundation -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.containerStatuses[*].lastState.terminated.reason}{"\n"}{end}'
```

**Solutions**:
1. Increase memory limits
2. Use VPA recommendations
3. Add more nodes
4. Optimize application memory usage

## Emergency Procedures

### Complete System Restart

```bash
# Scale down API
kubectl scale deployment/context-api --replicas=0 -n context-foundation

# Restart databases (one at a time)
kubectl delete pod qdrant-0 -n context-foundation
kubectl wait --for=condition=ready pod qdrant-0 -n context-foundation

kubectl delete pod neo4j-0 -n context-foundation
kubectl wait --for=condition=ready pod neo4j-0 -n context-foundation

# Scale up API
kubectl scale deployment/context-api --replicas=3 -n context-foundation
```

### Rollback Deployment

```bash
# View rollout history
kubectl rollout history deployment/context-api -n context-foundation

# Rollback to previous version
kubectl rollout undo deployment/context-api -n context-foundation

# Rollback to specific revision
kubectl rollout undo deployment/context-api --to-revision=2 -n context-foundation
```

### Emergency Database Recovery

See [DATABASE_RECOVERY.md](./DATABASE_RECOVERY.md) for detailed recovery procedures.

## Getting Help

If these troubleshooting steps don't resolve your issue:

1. Collect diagnostic information:
   ```bash
   kubectl get all -n context-foundation -o yaml > diagnostic-all.yaml
   kubectl describe pods -n context-foundation > diagnostic-pods.txt
   kubectl logs --tail=1000 -n context-foundation --all-containers > diagnostic-logs.txt
   ```

2. Check Kubernetes events:
   ```bash
   kubectl get events -n context-foundation --sort-by='.lastTimestamp'
   ```

3. Create a GitHub issue with:
   - Description of the problem
   - Steps to reproduce
   - Relevant logs and configurations
   - Kubernetes version and cluster information
