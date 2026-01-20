#!/bin/bash

# Multi-Layer Context Foundation - Teardown Script
# This script removes all deployed resources

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

NAMESPACE="context-foundation"

echo -e "${RED}WARNING: This will delete all resources in namespace $NAMESPACE${NC}"
read -p "Are you sure? (yes/no): " -r
if [[ ! $REPLY =~ ^yes$ ]]; then
    echo "Teardown cancelled"
    exit 0
fi

echo -e "\n${YELLOW}Starting teardown...${NC}"

# Delete monitoring
echo -e "\n${YELLOW}Removing monitoring...${NC}"
kubectl delete -f k8s/monitoring/ --ignore-not-found=true

# Delete autoscaling
echo -e "\n${YELLOW}Removing autoscaling...${NC}"
kubectl delete -f k8s/autoscaling/ --ignore-not-found=true

# Delete Istio configuration
echo -e "\n${YELLOW}Removing Istio configuration...${NC}"
kubectl delete -f k8s/istio/ --ignore-not-found=true

# Delete API
echo -e "\n${YELLOW}Removing API...${NC}"
kubectl delete -f k8s/deployments/api-deployment.yaml --ignore-not-found=true
kubectl delete -f k8s/services/api-service.yaml --ignore-not-found=true

# Delete databases
echo -e "\n${YELLOW}Removing databases...${NC}"
kubectl delete -f k8s/statefulsets/neo4j-statefulset.yaml --ignore-not-found=true
kubectl delete -f k8s/services/neo4j-service.yaml --ignore-not-found=true

kubectl delete -f k8s/statefulsets/qdrant-statefulset.yaml --ignore-not-found=true
kubectl delete -f k8s/services/qdrant-service.yaml --ignore-not-found=true

# Wait for StatefulSets to be deleted
echo "Waiting for StatefulSets to be deleted..."
kubectl wait --for=delete statefulset/qdrant -n $NAMESPACE --timeout=300s 2>/dev/null || true
kubectl wait --for=delete statefulset/neo4j -n $NAMESPACE --timeout=300s 2>/dev/null || true

# Delete security policies
echo -e "\n${YELLOW}Removing security policies...${NC}"
kubectl delete -f k8s/security/ --ignore-not-found=true

# Delete storage (WARNING: This deletes data!)
echo -e "\n${RED}WARNING: The following will delete all persistent data${NC}"
read -p "Delete PVCs and data? (yes/no): " -r
if [[ $REPLY =~ ^yes$ ]]; then
    kubectl delete -f k8s/storage/ --ignore-not-found=true
    kubectl delete pvc --all -n $NAMESPACE
    echo -e "${GREEN}✓ Storage deleted${NC}"
else
    echo -e "${YELLOW}Skipping storage deletion${NC}"
fi

# Delete base configuration
echo -e "\n${YELLOW}Removing base configuration...${NC}"
kubectl delete -f k8s/base/configmaps.yaml --ignore-not-found=true

read -p "Delete secrets? (yes/no): " -r
if [[ $REPLY =~ ^yes$ ]]; then
    kubectl delete -f k8s/base/secrets.yaml --ignore-not-found=true
    echo -e "${GREEN}✓ Secrets deleted${NC}"
else
    echo -e "${YELLOW}Skipping secrets deletion${NC}"
fi

# Delete namespace
echo -e "\n${YELLOW}Removing namespace...${NC}"
read -p "Delete namespace $NAMESPACE? (yes/no): " -r
if [[ $REPLY =~ ^yes$ ]]; then
    kubectl delete -f k8s/base/namespace.yaml --ignore-not-found=true
    echo "Waiting for namespace to be deleted..."
    kubectl wait --for=delete namespace/$NAMESPACE --timeout=300s 2>/dev/null || true
    echo -e "${GREEN}✓ Namespace deleted${NC}"
else
    echo -e "${YELLOW}Skipping namespace deletion${NC}"
fi

echo -e "\n${GREEN}Teardown complete!${NC}"
