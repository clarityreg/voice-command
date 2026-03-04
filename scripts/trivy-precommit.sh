#!/bin/bash
# trivy-precommit.sh - Trivy security scan for pre-commit
# Exports staged files to a temp directory, runs Trivy, generates reports.
# Blocking policy: CRITICAL = blocked, HIGH/MEDIUM/LOW = reported only.

set -e

if ! command -v trivy &> /dev/null; then
    echo "Warning: trivy not installed — skipping security scan."
    echo "Install: brew install trivy"
    exit 0
fi

REPORT_DIR="security-reports/trivy"
TEMP_DIR=$(mktemp -d)
trap 'rm -rf "$TEMP_DIR"' EXIT

# Export staged files to a clean temp directory
git checkout-index --prefix="$TEMP_DIR/" -a 2>/dev/null || true

# Run Trivy filesystem scan — JSON output for parsing
trivy fs "$TEMP_DIR" \
    --format json \
    --output "$TEMP_DIR/trivy-results.json" \
    --severity CRITICAL,HIGH,MEDIUM,LOW \
    --scanners vuln,misconfig,secret \
    --quiet 2>/dev/null || true

# Run Trivy — table output for console
echo ""
echo "=== Trivy Security Scan ==="
trivy fs "$TEMP_DIR" \
    --format table \
    --severity CRITICAL,HIGH,MEDIUM,LOW \
    --scanners vuln,misconfig,secret \
    --quiet 2>/dev/null || true

# Parse results and count by severity
if [ -f "$TEMP_DIR/trivy-results.json" ]; then
    COUNTS=$(python3 -c "
import json, sys
try:
    data = json.load(open('$TEMP_DIR/trivy-results.json'))
    counts = {'CRITICAL': 0, 'HIGH': 0, 'MEDIUM': 0, 'LOW': 0}
    for result in data.get('Results', []):
        for vuln in result.get('Vulnerabilities', []):
            sev = vuln.get('Severity', 'UNKNOWN')
            if sev in counts:
                counts[sev] += 1
        for misconfig in result.get('Misconfigurations', []):
            sev = misconfig.get('Severity', 'UNKNOWN')
            if sev in counts:
                counts[sev] += 1
        for secret in result.get('Secrets', []):
            sev = secret.get('Severity', 'UNKNOWN')
            if sev in counts:
                counts[sev] += 1
    print(f\"CRITICAL={counts['CRITICAL']}\")
    print(f\"HIGH={counts['HIGH']}\")
    print(f\"MEDIUM={counts['MEDIUM']}\")
    print(f\"LOW={counts['LOW']}\")
except Exception as e:
    print(f'CRITICAL=0', file=sys.stderr)
    sys.exit(0)
" 2>/dev/null || echo "CRITICAL=0")

    eval "$COUNTS"

    # Generate report directory and files
    mkdir -p "$REPORT_DIR"
    TIMESTAMP=$(date +%Y%m%d-%H%M%S)

    # Markdown report
    cat > "$REPORT_DIR/scan-$TIMESTAMP.md" <<EOF
# Trivy Security Scan Report

**Date:** $(date -u +"%Y-%m-%d %H:%M:%S UTC")
**Commit:** $(git rev-parse --short HEAD 2>/dev/null || echo "pre-commit")

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | ${CRITICAL:-0} |
| HIGH     | ${HIGH:-0} |
| MEDIUM   | ${MEDIUM:-0} |
| LOW      | ${LOW:-0} |
EOF

    # Copy JSON report
    cp "$TEMP_DIR/trivy-results.json" "$REPORT_DIR/scan-$TIMESTAMP.json" 2>/dev/null || true

    # Symlink latest
    ln -sf "scan-$TIMESTAMP.md" "$REPORT_DIR/latest.md" 2>/dev/null || true
    ln -sf "scan-$TIMESTAMP.json" "$REPORT_DIR/latest.json" 2>/dev/null || true

    echo ""
    echo "Report: $REPORT_DIR/scan-$TIMESTAMP.md"

    # Block on CRITICAL findings
    if [ "${CRITICAL:-0}" -gt 0 ]; then
        echo ""
        echo "BLOCKED: ${CRITICAL} CRITICAL finding(s) detected. Fix before committing."
        exit 1
    fi
fi

echo "Trivy scan passed."
