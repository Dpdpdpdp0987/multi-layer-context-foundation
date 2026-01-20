#!/bin/bash

# Multi-Layer Context Foundation - Validation Script
# This script validates the deployment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

NAMESPACE="context-foundation"

echo -e "${GREEN}Validating Multi-Layer Context Foundation Deployment${NC}"

# Check namespace
echo -e "\n${YELLOW}Checking namespace...${NC}"
if kubectl get namespace $NAMESPACE &>/dev/null; then
    echo -e "${GREEN}✓ Namespace exists${NC}"
else
    echo -e "${RED}✗ Namespace not found${NC}"
    exit 1
fi

# Check Istio injection
if kubectl get namespace $NAMESPACE -o jsonpath='{.metadata.labels.istio-injection}' | grep -q "enabled"; then
    echo -e "${GREEN}✓ Istio injection enabled${NC}"
else
    echo -e "${YELLOW}⚠ Istio injection not enabled${NC}"
fi

# Check pods
echo -e "\n${YELLOW}Checking pods...${NC}"
NOT_READY=$(kubectl get pods -n $NAMESPACE --field-selector=status.phase!=Running --no-headers 2>/dev/null | wc -l)
if [ "$NOT_READY" -eq 0 ]; then
    echo -e "${GREEN}✓ All pods are running${NC}"
    kubectl get pods -n $NAMESPACE
else
    echo -e "${RED}✗ Some pods are not running${NC}"
    kubectl get pods -n $NAMESPACE
    exit 1
fi

# Check services
echo -e "\n${YELLOW}Checking services...${NC}"
if kubectl get svc context-api -n $NAMESPACE &>/dev/null && \
   kubectl get svc qdrant -n $NAMESPACE &>/dev/null && \
   kubectl get svc neo4j -n $NAMESPACE &>/dev/null; then
    echo -e "${GREEN}✓ All services exist${NC}"
else
    echo -e "${RED}✗ Some services are missing${NC}"
    exit 1
fi

# Check StatefulSets
echo -e "\n${YELLOW}Checking StatefulSets...${NC}"
QDRANT_READY=$(kubectl get statefulset qdrant -n $NAMESPACE -o jsonpath='{.status.readyReplicas}' 2>/dev/null || echo 0)
NEO4J_READY=$(kubectl get statefulset neo4j -n $NAMESPACE -o jsonpath='{.status.readyReplicas}' 2>/dev/null || echo 0)

if [ "$QDRANT_READY" -ge 2 ]; then
    echo -e "${GREEN}✓ Qdrant StatefulSet healthy ($QDRANT_READY replicas ready)${NC}"
else
    echo -e "${RED}✗ Qdrant StatefulSet unhealthy (only $QDRANT_READY replicas ready)${NC}"
fi

if [ "$NEO4J_READY" -ge 2 ]; then
    echo -e "${GREEN}✓ Neo4j StatefulSet healthy ($NEO4J_READY replicas ready)${NC}"
else
    echo -e "${RED}✗ Neo4j StatefulSet unhealthy (only $NEO4J_READY replicas ready)${NC}"
fi

# Check deployments
echo -e "\n${YELLOW}Checking deployments...${NC}"
API_READY=$(kubectl get deployment context-api -n $NAMESPACE -o jsonpath='{.status.readyReplicas}' 2>/dev/null || echo 0)
if [ "$API_READY" -ge 2 ]; then
    echo -e "${GREEN}✓ API Deployment healthy ($API_READY replicas ready)${NC}"
else
    echo -e "${RED}✗ API Deployment unhealthy (only $API_READY replicas ready)${NC}"
fi

# Check PVCs
echo -e "\n${YELLOW}Checking PVCs...${NC}"
UNBOUND=$(kubectl get pvc -n $NAMESPACE --field-selector=status.phase!=Bound --no-headers 2>/dev/null | wc -l)
if [ "$UNBOUND" -eq 0 ]; then
    echo -e "${GREEN}✓ All PVCs are bound${NC}"
else
    echo -e "${RED}✗ Some PVCs are not bound${NC}"
    kubectl get pvc -n $NAMESPACE
fi

# Check HPA
echo -e "\n${YELLOW}Checking HPA...${NC}"
if kubectl get hpa context-api -n $NAMESPACE &>/dev/null; then
    echo -e "${GREEN}✓ HPA configured${NC}"
    kubectl get hpa context-api -n $NAMESPACE
else
    echo -e "${YELLOW}⚠ HPA not found${NC}"
fi

# Check Istio configuration
echo -e "\n${YELLOW}Checking Istio configuration...${NC}"
if kubectl get gateway context-gateway -n $NAMESPACE &>/dev/null && \
   kubectl get virtualservice context-api -n $NAMESPACE &>/dev/null; then
    echo -e "${GREEN}✓ Istio Gateway and VirtualService configured${NC}"
else
    echo -e "${YELLOW}⚠ Some Istio resources are missing${NC}"
fi

# Check monitoring
echo -e "\n${YELLOW}Checking monitoring...${NC}"
if kubectl get crd servicemonitors.monitoring.coreos.com &>/dev/null; then
    if kubectl get servicemonitor -n $NAMESPACE &>/dev/null; then
        echo -e "${GREEN}✓ ServiceMonitors configured${NC}"
    else
        echo -e "${YELLOW}⚠ ServiceMonitors not found${NC}"
    fi
else
    echo -e "${YELLOW}⚠ Prometheus Operator not installed${NC}"
fi

# Test API health
echo -e "\n${YELLOW}Testing API health endpoint...${NC}"
API_POD=$(kubectl get pod -n $NAMESPACE -l app=context-api -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
if [ -n "$API_POD" ]; then
    if kubectl exec -n $NAMESPACE "$API_POD" -- curl -s http://localhost:8000/health >/dev/null 2>&1; then
        echo -e "${GREEN}✓ API health endpoint responding${NC}"
    else
        echo -e "${RED}✗ API health endpoint not responding${NC}"
    fi
fi

# Test Qdrant health
echo -e "\n${YELLOW}Testing Qdrant health endpoint...${NC}"
QDRANT_POD=$(kubectl get pod -n $NAMESPACE -l app=qdrant -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
if [ -n "$QDRANT_POD" ]; then
    if kubectl exec -n $NAMESPACE "$QDRANT_POD" -- curl -s http://localhost:6333/healthz >/dev/null 2>&1; then
        echo -e "${GREEN}✓ Qdrant health endpoint responding${NC}"
    else
        echo -e "${RED}✗ Qdrant health endpoint not responding${NC}"
    fi
fi

# Summary
echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}Validation Complete${NC}"
echo -e "${GREEN}========================================${NC}"

echo -e "\n${YELLOW}Resource Summary:${NC}"
echo "Pods: $(kubectl get pods -n $NAMESPACE --no-headers 2>/dev/null | wc -l)"
echo "Services: $(kubectl get svc -n $NAMESPACE --no-headers 2>/dev/null | wc -l)"
echo "PVCs: $(kubectl get pvc -n $NAMESPACE --no-headers 2>/dev/null | wc -l)"

echo -e "\n${YELLOW}For detailed status, run:${NC}"
echo "kubectl get all -n $NAMESPACE"
