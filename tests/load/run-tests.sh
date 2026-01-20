#!/bin/bash
# Run Load Tests Script

set -e

COLOR_GREEN="\033[0;32m"
COLOR_RED="\033[0;31m"
COLOR_YELLOW="\033[0;33m"
COLOR_BLUE="\033[0;34m"
COLOR_RESET="\033[0m"

echo -e "${COLOR_BLUE}===============================================${COLOR_RESET}"
echo -e "${COLOR_BLUE}  MLCF Load Testing Suite${COLOR_RESET}"
echo -e "${COLOR_BLUE}===============================================${COLOR_RESET}"
echo ""

# Configuration
BASE_URL="${BASE_URL:-http://localhost:8000}"
OUTPUT_DIR="results/$(date +%Y%m%d_%H%M%S)"
REPORT_DIR="${OUTPUT_DIR}/reports"

# Create output directories
mkdir -p "${OUTPUT_DIR}"
mkdir -p "${REPORT_DIR}"

echo "Configuration:"
echo "  Base URL: ${BASE_URL}"
echo "  Output Dir: ${OUTPUT_DIR}"
echo ""

# Check if k6 is installed
if ! command -v k6 &> /dev/null; then
    echo -e "${COLOR_RED}Error: k6 is not installed${COLOR_RESET}"
    echo "Install from: https://k6.io/docs/get-started/installation/"
    exit 1
fi

echo -e "${COLOR_GREEN}✓ k6 found${COLOR_RESET}"

# Check if API is running
if ! curl -s "${BASE_URL}/health/simple" > /dev/null; then
    echo -e "${COLOR_RED}Error: API is not responding at ${BASE_URL}${COLOR_RESET}"
    echo "Start the API with: ./scripts/start_api.sh"
    exit 1
fi

echo -e "${COLOR_GREEN}✓ API is running${COLOR_RESET}"
echo ""

# Function to run test
run_test() {
    local test_name=$1
    local test_file=$2
    local output_file="${OUTPUT_DIR}/${test_name}.json"
    local summary_file="${REPORT_DIR}/${test_name}_summary.json"
    
    echo -e "${COLOR_YELLOW}Running ${test_name}...${COLOR_RESET}"
    echo "  Test file: ${test_file}"
    echo "  Output: ${output_file}"
    
    k6 run \
        --out json="${output_file}" \
        --summary-export="${summary_file}" \
        -e BASE_URL="${BASE_URL}" \
        "${test_file}"
    
    local exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        echo -e "${COLOR_GREEN}✓ ${test_name} completed successfully${COLOR_RESET}"
    else
        echo -e "${COLOR_RED}✗ ${test_name} failed (exit code: ${exit_code})${COLOR_RESET}"
    fi
    
    echo ""
    return $exit_code
}

# Test selection
TEST_TYPE="${1:-all}"

case "${TEST_TYPE}" in
    baseline)
        echo -e "${COLOR_BLUE}Running Baseline Test${COLOR_RESET}"
        echo ""
        run_test "baseline" "scenarios/baseline.js"
        ;;
    
    stress)
        echo -e "${COLOR_BLUE}Running Stress Test (10k+ users)${COLOR_RESET}"
        echo ""
        run_test "stress" "scenarios/stress.js"
        ;;
    
    spike)
        echo -e "${COLOR_BLUE}Running Spike Test${COLOR_RESET}"
        echo ""
        run_test "spike" "scenarios/spike.js"
        ;;
    
    soak)
        echo -e "${COLOR_BLUE}Running Soak Test (4 hours)${COLOR_RESET}"
        echo -e "${COLOR_YELLOW}Warning: This test takes 4+ hours${COLOR_RESET}"
        read -p "Continue? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            run_test "soak" "scenarios/soak.js"
        fi
        ;;
    
    journey)
        echo -e "${COLOR_BLUE}Running User Journey Test${COLOR_RESET}"
        echo ""
        run_test "user-journey" "scenarios/user-journey.js"
        ;;
    
    all)
        echo -e "${COLOR_BLUE}Running All Tests (except soak)${COLOR_RESET}"
        echo ""
        
        all_passed=true
        
        run_test "baseline" "scenarios/baseline.js" || all_passed=false
        sleep 30
        
        run_test "spike" "scenarios/spike.js" || all_passed=false
        sleep 30
        
        run_test "user-journey" "scenarios/user-journey.js" || all_passed=false
        sleep 30
        
        run_test "stress" "scenarios/stress.js" || all_passed=false
        
        if [ "$all_passed" = true ]; then
            echo -e "${COLOR_GREEN}All tests passed!${COLOR_RESET}"
        else
            echo -e "${COLOR_RED}Some tests failed${COLOR_RESET}"
        fi
        ;;
    
    *)
        echo -e "${COLOR_RED}Unknown test type: ${TEST_TYPE}${COLOR_RESET}"
        echo ""
        echo "Usage: ./run-tests.sh [test-type]"
        echo ""
        echo "Test types:"
        echo "  baseline  - Basic performance test (100 users)"
        echo "  stress    - Stress test (10k+ users)"
        echo "  spike     - Sudden traffic spike test"
        echo "  soak      - Long-duration test (4 hours)"
        echo "  journey   - Realistic user journey scenarios"
        echo "  all       - Run all tests except soak"
        exit 1
        ;;
esac

# Analyze results if node is available
if command -v node &> /dev/null; then
    echo -e "${COLOR_BLUE}Analyzing results...${COLOR_RESET}"
    echo ""
    
    for summary in "${REPORT_DIR}"/*_summary.json; do
        if [ -f "${summary}" ]; then
            echo -e "${COLOR_YELLOW}Analysis for $(basename ${summary})${COLOR_RESET}"
            node analysis/results-analyzer.js "${summary}" || true
            echo ""
        fi
    done
fi

echo -e "${COLOR_GREEN}Results saved to: ${OUTPUT_DIR}${COLOR_RESET}"
echo -e "${COLOR_GREEN}Summary reports: ${REPORT_DIR}${COLOR_RESET}"
echo ""