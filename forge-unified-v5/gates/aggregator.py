#!/usr/bin/env python3
"""
QA Aggregator - Unified Grade Calculation
Part of Unified Forge Pipeline

Combines:
- Static QA (structure + complexity)
- Architecture Compliance
- Pattern Matching

Output: qa.report.json with final grade
"""

import json
import sys
import os
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Optional
from datetime import datetime, timezone

@dataclass
class Dimension:
    name: str
    score: int
    weight: float
    findings_count: int = 0

@dataclass
class QaReport:
    schema_version: str = "1.0"
    loadset_id: str = ""
    crate_name: str = ""
    grade: str = "F"
    score: int = 0
    pass_: bool = False
    dimensions: Dict[str, Dimension] = field(default_factory=dict)
    arch_summary: Dict = field(default_factory=dict)
    pattern_summary: Dict = field(default_factory=dict)
    refactor_directives: List[str] = field(default_factory=list)

WEIGHTS = {
    "structure": 0.25,
    "complexity": 0.25,
    "pattern": 0.25,
    "arch": 0.25,
}

THRESHOLDS = {
    "A": 85,
    "B": 70,
    "C": 55,
    "D": 40,
}

def grade_from_score(score: int) -> str:
    if score >= THRESHOLDS["A"]:
        return "A"
    if score >= THRESHOLDS["B"]:
        return "B"
    if score >= THRESHOLDS["C"]:
        return "C"
    if score >= THRESHOLDS["D"]:
        return "D"
    return "F"

def load_json(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    with open(path, 'r') as f:
        return json.load(f)

def aggregate(static_path: str, arch_path: str, pattern_path: str, crate_name: str) -> QaReport:
    """Aggregate all gate outputs into final report"""
    
    static = load_json(static_path)
    arch = load_json(arch_path)
    pattern = load_json(pattern_path)
    
    # Build dimensions
    dimensions = {}
    
    dimensions["structure"] = Dimension(
        name="structure",
        score=static.get("structure_score", 50),
        weight=WEIGHTS["structure"],
        findings_count=len(static.get("findings", []))
    )
    
    dimensions["complexity"] = Dimension(
        name="complexity",
        score=static.get("complexity_score", 50),
        weight=WEIGHTS["complexity"],
    )
    
    dimensions["arch"] = Dimension(
        name="arch",
        score=arch.get("score", 50),
        weight=WEIGHTS["arch"],
        findings_count=len(arch.get("violations", []))
    )
    
    dimensions["pattern"] = Dimension(
        name="pattern",
        score=pattern.get("score", 50),
        weight=WEIGHTS["pattern"],
        findings_count=len([m for m in pattern.get("matches", []) if m.get("classification") != "STRONG_MATCH"])
    )
    
    # Calculate weighted score
    total_score = sum(
        dim.score * dim.weight 
        for dim in dimensions.values()
    )
    score = int(round(total_score))
    grade = grade_from_score(score)
    
    # Check for auto-fail conditions
    bevy_free = arch.get("bevy_free", True)
    if not bevy_free:
        grade = "F"
        score = min(score, 39)
    
    # Generate refactor directives
    directives = []
    if not bevy_free:
        directives.append("CRITICAL: Replace all bevy imports with sx9_ecs_prelude")
    if dimensions["complexity"].score < 60:
        directives.append("Reduce function complexity - split large functions")
    if dimensions["pattern"].score < 60:
        directives.append("Align functions with canonical N-V-N-N patterns")
    
    for v in arch.get("violations", []):
        if v.get("severity") in ("critical", "high"):
            directives.append(f"FIX: {v.get('message', 'Unknown violation')}")
    
    loadset_id = f"qa-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
    
    return QaReport(
        loadset_id=loadset_id,
        crate_name=crate_name,
        grade=grade,
        score=score,
        pass_=grade in ("A", "B"),
        dimensions={k: asdict(v) for k, v in dimensions.items()},
        arch_summary={
            "ecs_layer": arch.get("ecs_layer"),
            "bevy_free": arch.get("bevy_free", True),
            "tcr_compliant": arch.get("tcr_compliant", True),
        },
        pattern_summary={
            "strong_matches": len([m for m in pattern.get("matches", []) if m.get("classification") == "STRONG_MATCH"]),
            "total_functions": len(pattern.get("matches", [])),
        },
        refactor_directives=directives[:5],  # Top 5
    )

def run_aggregator(static_path: str, arch_path: str, pattern_path: str, output_path: str, crate_name: str) -> int:
    """Main aggregator execution"""
    
    report = aggregate(static_path, arch_path, pattern_path, crate_name)
    
    output = {
        "schema_version": report.schema_version,
        "loadset_id": report.loadset_id,
        "crate_name": report.crate_name,
        "grade": report.grade,
        "score": report.score,
        "pass": report.pass_,
        "dimensions": report.dimensions,
        "arch_summary": report.arch_summary,
        "pattern_summary": report.pattern_summary,
        "refactor_directives": report.refactor_directives,
    }
    
    with open(output_path, 'w') as fp:
        json.dump(output, fp, indent=2)
    
    status = "✅ PASS" if report.pass_ else "❌ FAIL"
    print(f"\n{'='*50}")
    print(f"  FORGE QA RESULT: Grade {report.grade} ({report.score}/100)")
    print(f"  {status}")
    print(f"{'='*50}")
    print(f"  Structure:   {report.dimensions['structure']['score']}/100")
    print(f"  Complexity:  {report.dimensions['complexity']['score']}/100")
    print(f"  Pattern:     {report.dimensions['pattern']['score']}/100")
    print(f"  Arch:        {report.dimensions['arch']['score']}/100")
    print(f"{'='*50}")
    
    if report.refactor_directives:
        print("\n  Directives:")
        for d in report.refactor_directives:
            print(f"    • {d}")
    
    return 0 if report.pass_ else 1

if __name__ == "__main__":
    if len(sys.argv) != 6:
        print("Usage: aggregator.py <static.json> <arch.json> <pattern.json> <output.json> <crate_name>")
        sys.exit(1)
    sys.exit(run_aggregator(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]))
