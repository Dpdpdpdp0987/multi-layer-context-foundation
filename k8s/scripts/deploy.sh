#!/bin/bash

# Multi-Layer Context Foundation - Kubernetes Deployment Script
# This script automates the deployment of all components

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
NAMESPACE="context-foundation"
TIMEOUT=600

echo -e "${GREEN}Starting Multi-Layer Context Foundation Deployment${NC}"

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
echo -e "\n${YELLOW}Checking prerequisites...${NC}"

if ! command_exists kubectl; then
    echo -e "${RED}Error: kubectl not found${NC}"
    exit 1
fi

if ! command_exists istioctl; then
    echo -e "${YELLOW}Warning: istioctl not found. Istio features may not work.${NC}"
fi

# Check Kubernetes connection
if ! kubectl cluster-info &>/dev/null; then
    echo -e "${RED}Error: Cannot connect to Kubernetes cluster${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Prerequisites checked${NC}"

# Step 1: Create namespace
echo -e "\n${YELLOW}Step 1: Creating namespace...${NC}"
kubectl apply -f k8s/base/namespace.yaml
kubectl label namespace $NAMESPACE istio-injection=enabled --overwrite
echo -e "${GREEN}✓ Namespace created${NC}"

# Step 2: Apply base configuration
echo -e "\n${YELLOW}Step 2: Applying base configuration...${NC}"
kubectl apply -f k8s/base/configmaps.yaml

# Check if secrets exist
if kubectl get secret context-secrets -n $NAMESPACE &>/dev/null; then
    echo -e "${GREEN}✓ Secrets already exist${NC}"
else
    echo -e "${RED}Warning: Secrets not found. Please create secrets manually:${NC}"
    echo -e "${YELLOW}kubectl apply -f k8s/base/secrets.yaml${NC}"
    read -p "Press enter to continue after creating secrets..."
fi

echo -e "${GREEN}✓ Base configuration applied${NC}"

# Step 3: Deploy storage
echo -e "\n${YELLOW}Step 3: Deploying storage...${NC}"
kubectl apply -f k8s/storage/storage-class.yaml
kubectl apply -f k8s/storage/backup-pvc.yaml
echo -e "${GREEN}✓ Storage deployed${NC}"

# Step 4: Deploy security policies
echo -e "\n${YELLOW}Step 4: Deploying security policies...${NC}"
kubectl apply -f k8s/security/rbac.yaml
kubectl apply -f k8s/security/pod-security-policy.yaml 2>/dev/null || echo "PSP not supported, skipping..."
kubectl apply -f k8s/security/network-policy.yaml
echo -e "${GREEN}✓ Security policies deployed${NC}"

# Step 5: Deploy Qdrant
echo -e "\n${YELLOW}Step 5: Deploying Qdrant...${NC}"
kubectl apply -f k8s/services/qdrant-service.yaml
kubectl apply -f k8s/statefulsets/qdrant-statefulset.yaml

echo "Waiting for Qdrant pods to be ready..."
kubectl wait --for=condition=ready pod -l app=qdrant -n $NAMESPACE --timeout=${TIMEOUT}s || {
    echo -e "${RED}Error: Qdrant pods failed to start. Check logs with:${NC}"
    echo "kubectl logs -l app=qdrant -n $NAMESPACE"
    exit 1
}
echo -e "${GREEN}✓ Qdrant deployed${NC}"

# Step 6: Deploy Neo4j
echo -e "\n${YELLOW}Step 6: Deploying Neo4j...${NC}"
kubectl apply -f k8s/services/neo4j-service.yaml
kubectl apply -f k8s/statefulsets/neo4j-statefulset.yaml

echo "Waiting for Neo4j pods to be ready..."
kubectl wait --for=condition=ready pod -l app=neo4j -n $NAMESPACE --timeout=${TIMEOUT}s || {
    echo -e "${RED}Error: Neo4j pods failed to start. Check logs with:${NC}"
    echo "kubectl logs -l app=neo4j -n $NAMESPACE"
    exit 1
}
echo -e "${GREEN}✓ Neo4j deployed${NC}"

# Step 7: Deploy API
echo -e "\n${YELLOW}Step 7: Deploying API...${NC}"
kubectl apply -f k8s/services/api-service.yaml
kubectl apply -f k8s/deployments/api-deployment.yaml

echo "Waiting for API pods to be ready..."
kubectl wait --for=condition=ready pod -l app=context-api -n $NAMESPACE --timeout=${TIMEOUT}s || {
    echo -e "${RED}Error: API pods failed to start. Check logs with:${NC}"
    echo "kubectl logs -l app=context-api -n $NAMESPACE"
    exit 1
}
echo -e "${GREEN}✓ API deployed${NC}"

# Step 8: Deploy Istio configuration
echo -e "\n${YELLOW}Step 8: Deploying Istio configuration...${NC}"
kubectl apply -f k8s/istio/gateway.yaml
kubectl apply -f k8s/istio/virtual-service.yaml
kubectl apply -f k8s/istio/destination-rule.yaml
kubectl apply -f k8s/istio/peer-authentication.yaml
kubectl apply -f k8s/istio/authorization-policy.yaml
echo -e "${GREEN}✓ Istio configuration deployed${NC}"

# Step 9: Deploy autoscaling
echo -e "\n${YELLOW}Step 9: Deploying autoscaling...${NC}"
kubectl apply -f k8s/autoscaling/api-hpa.yaml

if kubectl get crd verticalpodautoscalers.autoscaling.k8s.io &>/dev/null; then
    kubectl apply -f k8s/autoscaling/api-vpa.yaml
    kubectl apply -f k8s/autoscaling/qdrant-vpa.yaml
    kubectl apply -f k8s/autoscaling/neo4j-vpa.yaml
    echo -e "${GREEN}✓ HPA and VPA deployed${NC}"
else
    echo -e "${YELLOW}VPA CRD not found, skipping VPA deployment${NC}"
    echo -e "${GREEN}✓ HPA deployed${NC}"
fi

# Step 10: Deploy monitoring
echo -e "\n${YELLOW}Step 10: Deploying monitoring...${NC}"
if kubectl get crd servicemonitors.monitoring.coreos.com &>/dev/null; then
    kubectl apply -f k8s/monitoring/service-monitor.yaml
    kubectl apply -f k8s/monitoring/prometheus-rules.yaml
    kubectl apply -f k8s/monitoring/grafana-dashboard.yaml
    echo -e "${GREEN}✓ Monitoring deployed${NC}"
else
    echo -e "${YELLOW}Prometheus Operator CRDs not found, skipping monitoring deployment${NC}"
fi

# Summary
echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"

echo -e "\n${YELLOW}Deployment Status:${NC}"
kubectl get pods -n $NAMESPACE

echo -e "\n${YELLOW}Services:${NC}"
kubectl get svc -n $NAMESPACE

echo -e "\n${YELLOW}Ingress:${NC}"
INGRESS_IP=$(kubectl -n istio-system get service istio-ingressgateway -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null)
if [ -n "$INGRESS_IP" ]; then
    echo -e "Istio Ingress Gateway IP: ${GREEN}$INGRESS_IP${NC}"
    echo -e "\nTest API health:"
    echo -e "${YELLOW}curl -H 'Host: context-api.example.com' http://$INGRESS_IP/health${NC}"
else
    echo -e "${YELLOW}Istio Ingress Gateway IP not yet assigned${NC}"
fi

echo -e "\n${YELLOW}Next Steps:${NC}"
echo "1. Update DNS to point to Istio Ingress Gateway IP"
echo "2. Configure TLS certificates"
echo "3. Monitor deployment: kubectl get pods -n $NAMESPACE -w"
echo "4. Check logs: kubectl logs -f deployment/context-api -n $NAMESPACE"
echo "5. Access Grafana dashboard for monitoring"

echo -e "\n${GREEN}For more information, see k8s/README.md${NC}"
