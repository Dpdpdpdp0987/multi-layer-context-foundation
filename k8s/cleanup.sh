#!/bin/bash
# MLCF Kubernetes Cleanup Script

set -e

NAMESPACE="mlcf"
COLOR_RED="\033[0;31m"
COLOR_YELLOW="\033[0;33m"
COLOR_RESET="\033[0m"

echo -e "${COLOR_RED}===============================================${COLOR_RESET}"
echo -e "${COLOR_RED}  MLCF Kubernetes Cleanup${COLOR_RESET}"
echo -e "${COLOR_RED}===============================================${COLOR_RESET}"
echo ""
echo -e "${COLOR_YELLOW}WARNING: This will delete all MLCF resources!${COLOR_RESET}"
echo -e "${COLOR_YELLOW}Press Ctrl+C to cancel or Enter to continue...${COLOR_RESET}"
read

echo "Deleting ingress..."
kubectl delete -f ingress/ --ignore-not-found=true

echo "Deleting monitoring..."
kubectl delete -f monitoring/ --ignore-not-found=true

echo "Deleting autoscaling..."
kubectl delete -f autoscaling/ --ignore-not-found=true

echo "Deleting network policies..."
kubectl delete -f security/network-policies.yaml --ignore-not-found=true

echo "Deleting API deployment..."
kubectl delete -f deployments/api-deployment.yaml --ignore-not-found=true

echo "Deleting databases..."
kubectl delete -f deployments/qdrant-statefulset.yaml --ignore-not-found=true
kubectl delete -f deployments/neo4j-statefulset.yaml --ignore-not-found=true

echo "Deleting services..."
kubectl delete -f services/ --ignore-not-found=true

echo "Deleting RBAC..."
kubectl delete -f security/rbac.yaml --ignore-not-found=true

echo "Deleting ConfigMaps and Secrets..."
kubectl delete -f base/configmap.yaml --ignore-not-found=true
kubectl delete -f base/secrets.yaml --ignore-not-found=true

echo "Deleting PVCs..."
kubectl delete pvc --all -n $NAMESPACE

echo "Deleting namespace..."
kubectl delete namespace $NAMESPACE --ignore-not-found=true

echo ""
echo -e "${COLOR_RED}Cleanup complete!${COLOR_RESET}"
echo ""