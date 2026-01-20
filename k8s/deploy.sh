#!/bin/bash
# MLCF Kubernetes Deployment Script

set -e

NAMESPACE="mlcf"
COLOR_GREEN="\033[0;32m"
COLOR_RED="\033[0;31m"
COLOR_YELLOW="\033[0;33m"
COLOR_RESET="\033[0m"

echo -e "${COLOR_GREEN}===============================================${COLOR_RESET}"
echo -e "${COLOR_GREEN}  MLCF Kubernetes Deployment${COLOR_RESET}"
echo -e "${COLOR_GREEN}===============================================${COLOR_RESET}"
echo ""

# Check prerequisites
echo "Checking prerequisites..."

if ! command -v kubectl &> /dev/null; then
    echo -e "${COLOR_RED}kubectl not found. Please install kubectl.${COLOR_RESET}"
    exit 1
fi

echo -e "${COLOR_GREEN}✓ kubectl found${COLOR_RESET}"

# Check cluster connectivity
if ! kubectl cluster-info &> /dev/null; then
    echo -e "${COLOR_RED}Cannot connect to Kubernetes cluster${COLOR_RESET}"
    exit 1
fi

echo -e "${COLOR_GREEN}✓ Connected to cluster${COLOR_RESET}"
echo ""

# Create namespace
echo "Step 1: Creating namespace..."
kubectl apply -f base/namespace.yaml
echo -e "${COLOR_GREEN}✓ Namespace created${COLOR_RESET}"
echo ""

# Check secrets
echo "Step 2: Checking secrets..."
if kubectl get secret mlcf-api-secrets -n $NAMESPACE &> /dev/null; then
    echo -e "${COLOR_YELLOW}  Secrets already exist. Skipping...${COLOR_RESET}"
else
    echo -e "${COLOR_YELLOW}  Creating default secrets (CHANGE IN PRODUCTION!)${COLOR_RESET}"
    kubectl apply -f base/secrets.yaml
fi
echo ""

# Apply ConfigMaps
echo "Step 3: Applying ConfigMaps..."
kubectl apply -f base/configmap.yaml
echo -e "${COLOR_GREEN}✓ ConfigMaps applied${COLOR_RESET}"
echo ""

# Apply Storage Classes
echo "Step 4: Applying Storage Classes..."
kubectl apply -f storage/storageclass.yaml
echo -e "${COLOR_GREEN}✓ Storage Classes applied${COLOR_RESET}"
echo ""

# Deploy Databases
echo "Step 5: Deploying databases..."
echo "  Deploying Qdrant..."
kubectl apply -f deployments/qdrant-statefulset.yaml
kubectl apply -f services/services.yaml

echo "  Deploying Neo4j..."
kubectl apply -f deployments/neo4j-statefulset.yaml

echo "  Waiting for databases to be ready..."
kubectl wait --for=condition=ready pod -l app=qdrant -n $NAMESPACE --timeout=300s || true
kubectl wait --for=condition=ready pod -l app=neo4j -n $NAMESPACE --timeout=300s || true
echo -e "${COLOR_GREEN}✓ Databases deployed${COLOR_RESET}"
echo ""

# Deploy RBAC
echo "Step 6: Applying RBAC..."
kubectl apply -f security/rbac.yaml
echo -e "${COLOR_GREEN}✓ RBAC configured${COLOR_RESET}"
echo ""

# Deploy API
echo "Step 7: Deploying API..."
kubectl apply -f deployments/api-deployment.yaml

echo "  Waiting for API to be ready..."
kubectl wait --for=condition=ready pod -l app=mlcf-api -n $NAMESPACE --timeout=180s || true
echo -e "${COLOR_GREEN}✓ API deployed${COLOR_RESET}"
echo ""

# Configure Autoscaling
echo "Step 8: Configuring autoscaling..."
kubectl apply -f autoscaling/hpa.yaml
kubectl apply -f autoscaling/pdb.yaml
echo -e "${COLOR_GREEN}✓ Autoscaling configured${COLOR_RESET}"
echo ""

# Apply Network Policies
echo "Step 9: Applying network policies..."
kubectl apply -f security/network-policies.yaml
echo -e "${COLOR_GREEN}✓ Network policies applied${COLOR_RESET}"
echo ""

# Configure Monitoring
echo "Step 10: Configuring monitoring..."
if kubectl get namespace monitoring &> /dev/null; then
    kubectl apply -f monitoring/servicemonitor.yaml
    kubectl apply -f monitoring/prometheus-rules.yaml
    echo -e "${COLOR_GREEN}✓ Monitoring configured${COLOR_RESET}"
else
    echo -e "${COLOR_YELLOW}  Monitoring namespace not found. Skipping...${COLOR_RESET}"
fi
echo ""

# Deployment Summary
echo -e "${COLOR_GREEN}===============================================${COLOR_RESET}"
echo -e "${COLOR_GREEN}  Deployment Complete!${COLOR_RESET}"
echo -e "${COLOR_GREEN}===============================================${COLOR_RESET}"
echo ""
echo "Pod Status:"
kubectl get pods -n $NAMESPACE
echo ""
echo "Service Status:"
kubectl get svc -n $NAMESPACE
echo ""
echo "HPA Status:"
kubectl get hpa -n $NAMESPACE
echo ""
echo -e "${COLOR_YELLOW}Next Steps:${COLOR_RESET}"
echo "1. Configure ingress: kubectl apply -f ingress/ingress.yaml"
echo "2. Test API: kubectl port-forward svc/mlcf-api 8000:80 -n $NAMESPACE"
echo "3. Check logs: kubectl logs -f deployment/mlcf-api -n $NAMESPACE"
echo "4. Access health: curl http://localhost:8000/health"
echo ""