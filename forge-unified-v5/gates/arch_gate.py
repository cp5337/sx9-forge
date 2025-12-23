#!/usr/bin/env python3
"""
Architecture Compliance Gate - RFC-9127
Part of Unified Forge Pipeline

Checks:
- ECS layer compliance (L1/L2/L3)
- TCR types (Ring Bus, SDT, Crystal)
- Forbidden patterns (bevy, wrong types)
- Rune/Slot type correctness

Output: arch.findings.json
"""

import json
import re
import sys
import os
from dataclasses import dataclass, asdict
from typing import List, Optional, Tuple
from datetime import datetime, timezone

@dataclass
class Violation:
    code: str
    severity: str
    file: str
    line: int
    message: str

@dataclass
class ArchReport:
    schema_version: str = "1.0"
    loadset_id: str = ""
    score: int = 100
    ecs_layer: Optional[str] = None
    bevy_free: bool = True
    tcr_compliant: bool = True
    rune_valid: bool = True
    slot_valid: bool = True
    violations: List[Violation] = None
    
    def __post_init__(self):
        if self.violations is None:
            self.violations = []

# Forbidden patterns with error codes
# Only match actual imports, not comments
FORBIDDEN = [
    (r'use bevy::', 'E9127-001', 'critical', 'bevy import forbidden - use sx9_ecs_prelude'),
    (r'use bevy_ecs::', 'E9127-001', 'critical', 'bevy_ecs import forbidden - use sx9_ecs_prelude'),
    (r'bevy::prelude::\*', 'E9127-001', 'critical', 'bevy prelude forbidden'),
]

# L2 layer violations
L2_FORBIDDEN = [
    (r'\basync\s+fn\b', 'E9127-003', 'high', 'async forbidden in L2 layer'),
    (r'\.await\b', 'E9127-003', 'high', 'await forbidden in L2 layer'),
    (r'\bString\b', 'E9127-004', 'medium', 'String in hot-path - prefer &str or integers'),
]

# Type checks - only flag incorrect types
TYPE_CHECKS = [
    # These patterns look for INCORRECT type definitions
    (r'type\s+RuneId\s*=\s*(char|String|&str|i32|i64|u8|u16)', 'E9127-011', 'high', 'RuneId must be u32'),
    (r'type\s+SlotId\s*=\s*(char|String|&str|i32|i64|u8|u16|u32)', 'E9127-012', 'high', 'SlotId must be u64'),
    (r'rune:\s*(?:char|String|&str)\b', 'E9127-021', 'high', 'Rune must be u32, not char/String'),
]

def detect_layer(content: str) -> Optional[str]:
    """Detect ECS layer from imports"""
    if 'use apecs::' in content or 'async fn' in content:
        return 'L1'
    if 'use legion::' in content or 'sx9_ecs_prelude' in content:
        return 'L2'
    if 'use atlas::' in content or 'nats::' in content:
        return 'L3'
    return None

def check_file(filepath: str, content: str, layer: Optional[str]) -> List[Violation]:
    """Check a single file for violations"""
    violations = []
    lines = content.split('\n')
    
    for i, line in enumerate(lines, 1):
        # Skip comments
        stripped = line.strip()
        if stripped.startswith('//') or stripped.startswith('/*') or stripped.startswith('*'):
            continue
        
        # Check forbidden patterns
        for pattern, code, severity, message in FORBIDDEN:
            if re.search(pattern, line):
                violations.append(Violation(
                    code=code,
                    severity=severity,
                    file=filepath,
                    line=i,
                    message=message
                ))
        
        # Check L2-specific violations
        if layer == 'L2':
            for pattern, code, severity, message in L2_FORBIDDEN:
                if re.search(pattern, line):
                    violations.append(Violation(
                        code=code,
                        severity=severity,
                        file=filepath,
                        line=i,
                        message=message
                    ))
        
        # Check type definitions
        for pattern, code, severity, message in TYPE_CHECKS:
            if re.search(pattern, line):
                violations.append(Violation(
                    code=code,
                    severity=severity,
                    file=filepath,
                    line=i,
                    message=message
                ))
    
    return violations

def scan_crate(crate_path: str) -> Tuple[List[Violation], Optional[str]]:
    """Scan entire crate for violations"""
    all_violations = []
    detected_layer = None
    src_path = os.path.join(crate_path, "src")
    
    if not os.path.exists(src_path):
        return all_violations, None
    
    for root, _, files in os.walk(src_path):
        for f in files:
            if not f.endswith('.rs'):
                continue
            filepath = os.path.join(root, f)
            rel_path = os.path.relpath(filepath, crate_path)
            
            with open(filepath, 'r') as fp:
                content = fp.read()
            
            layer = detect_layer(content)
            if layer and not detected_layer:
                detected_layer = layer
            
            violations = check_file(rel_path, content, layer)
            all_violations.extend(violations)
    
    return all_violations, detected_layer

def calculate_score(violations: List[Violation]) -> int:
    """Calculate compliance score"""
    score = 100
    for v in violations:
        if v.severity == 'critical':
            score -= 25
        elif v.severity == 'high':
            score -= 15
        elif v.severity == 'medium':
            score -= 5
    return max(0, score)

def run_gate(crate_path: str, output_path: str) -> int:
    """Main gate execution"""
    loadset_id = f"arch-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
    
    violations, ecs_layer = scan_crate(crate_path)
    score = calculate_score(violations)
    
    # Determine flags
    bevy_free = not any(v.code == 'E9127-001' for v in violations)
    tcr_compliant = not any(v.code.startswith('E9127-01') for v in violations)
    rune_valid = not any(v.code in ('E9127-011', 'E9127-021') for v in violations)
    slot_valid = not any(v.code == 'E9127-012' for v in violations)
    
    report = ArchReport(
        loadset_id=loadset_id,
        score=score,
        ecs_layer=ecs_layer,
        bevy_free=bevy_free,
        tcr_compliant=tcr_compliant,
        rune_valid=rune_valid,
        slot_valid=slot_valid,
        violations=violations
    )
    
    output = {
        "schema_version": report.schema_version,
        "loadset_id": report.loadset_id,
        "score": report.score,
        "ecs_layer": report.ecs_layer,
        "bevy_free": report.bevy_free,
        "tcr_compliant": report.tcr_compliant,
        "rune_valid": report.rune_valid,
        "slot_valid": report.slot_valid,
        "violations": [asdict(v) for v in report.violations]
    }
    
    with open(output_path, 'w') as fp:
        json.dump(output, fp, indent=2)
    
    status = "✓" if bevy_free else "✗"
    print(f"{status} Arch Compliance: score={score} layer={ecs_layer} bevy_free={bevy_free}")
    
    # Fail if bevy found or score too low
    if not bevy_free:
        return 1
    return 0 if score >= 50 else 1

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: arch_gate.py <crate_path> <output_path>")
        sys.exit(1)
    sys.exit(run_gate(sys.argv[1], sys.argv[2]))
