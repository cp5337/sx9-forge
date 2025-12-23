#!/bin/bash
# forge-pipeline.sh - Unified Forge Pipeline Runner
# Synthesizes: RFC-9120, RFC-9121, RFC-9127, QA Bundle
#
# Usage: ./forge-pipeline.sh <crate_path>

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FORGE_DIR="$SCRIPT_DIR"
GATES_DIR="$FORGE_DIR/gates"
CANONICAL_DIR="$FORGE_DIR/canonical"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${BLUE}[FORGE]${NC} $1"; }
ok() { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
fail() { echo -e "${RED}[✗]${NC} $1"; }

usage() {
    echo "Usage: $0 <crate_path> [--output <dir>]"
    echo ""
    echo "Runs unified Forge QA pipeline:"
    echo "  1. Static QA (structure, complexity)"
    echo "  2. Architecture Compliance (ECS, TCR, bevy check)"
    echo "  3. Pattern Matching (canonical N-V-N-N blocks)"
    echo "  4. Aggregation (final grade)"
    exit 1
}

# Parse args
CRATE_PATH=""
OUTPUT_DIR=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --output)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        -h|--help)
            usage
            ;;
        *)
            CRATE_PATH="$1"
            shift
            ;;
    esac
done

if [[ -z "$CRATE_PATH" ]]; then
    usage
fi

if [[ ! -d "$CRATE_PATH" ]]; then
    fail "Crate path not found: $CRATE_PATH"
    exit 1
fi

# Resolve paths
CRATE_PATH="$(cd "$CRATE_PATH" && pwd)"
CRATE_NAME="$(basename "$CRATE_PATH")"

if [[ -z "$OUTPUT_DIR" ]]; then
    OUTPUT_DIR="$CRATE_PATH/.forge"
fi
mkdir -p "$OUTPUT_DIR"

log "════════════════════════════════════════════════════"
log "        UNIFIED FORGE PIPELINE v4.0"
log "════════════════════════════════════════════════════"
log "Crate:  $CRATE_NAME"
log "Path:   $CRATE_PATH"
log "Output: $OUTPUT_DIR"
log "════════════════════════════════════════════════════"
echo ""

# Stage 1: Static QA
log "Stage 1: Static QA Gate..."
python3 "$GATES_DIR/static_gate.py" "$CRATE_PATH" "$OUTPUT_DIR/static.json"
STATIC_EXIT=$?

# Stage 2: Architecture Compliance
log "Stage 2: Architecture Compliance Gate..."
python3 "$GATES_DIR/arch_gate.py" "$CRATE_PATH" "$OUTPUT_DIR/arch.json"
ARCH_EXIT=$?

# Stage 3: Pattern Matching
log "Stage 3: Pattern Matching Gate..."
python3 "$GATES_DIR/pattern_gate.py" "$CRATE_PATH" "$CANONICAL_DIR" "$OUTPUT_DIR/pattern.json"
PATTERN_EXIT=$?

# Stage 4: Aggregation
log "Stage 4: Aggregating results..."
python3 "$GATES_DIR/aggregator.py" \
    "$OUTPUT_DIR/static.json" \
    "$OUTPUT_DIR/arch.json" \
    "$OUTPUT_DIR/pattern.json" \
    "$OUTPUT_DIR/qa.report.json" \
    "$CRATE_NAME"
AGG_EXIT=$?

# Read final grade
if [[ -f "$OUTPUT_DIR/qa.report.json" ]]; then
    GRADE=$(python3 -c "import json; print(json.load(open('$OUTPUT_DIR/qa.report.json'))['grade'])")
    SCORE=$(python3 -c "import json; print(json.load(open('$OUTPUT_DIR/qa.report.json'))['score'])")
    PASS=$(python3 -c "import json; print(json.load(open('$OUTPUT_DIR/qa.report.json'))['pass'])")
    
    echo ""
    log "════════════════════════════════════════════════════"
    if [[ "$PASS" == "True" ]]; then
        ok "PIPELINE COMPLETE: Grade $GRADE ($SCORE/100) - PASS"
        log "Ready for: git branch factory/SX9-$CRATE_NAME"
    else
        fail "PIPELINE COMPLETE: Grade $GRADE ($SCORE/100) - FAIL"
        warn "Review directives in $OUTPUT_DIR/qa.report.json"
    fi
    log "════════════════════════════════════════════════════"
    
    # Show directives if failed
    if [[ "$PASS" != "True" ]]; then
        echo ""
        warn "Refactor directives:"
        python3 -c "
import json
report = json.load(open('$OUTPUT_DIR/qa.report.json'))
for d in report.get('refactor_directives', []):
    print(f'  • {d}')
"
    fi
else
    fail "Failed to generate QA report"
    exit 1
fi

# Exit with aggregate result
exit $AGG_EXIT
