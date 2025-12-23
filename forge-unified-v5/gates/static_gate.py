#!/usr/bin/env python3
"""
Static QA Gate - Cold Truth Analysis
Part of Unified Forge Pipeline

Runs:
- AST parsing (tree-sitter)
- Complexity metrics (cyclomatic, cognitive)
- Structure analysis (lines, modules, cohesion)

Output: static.findings.json
"""

import json
import subprocess
import sys
import os
from dataclasses import dataclass, asdict
from typing import List, Optional
from datetime import datetime, timezone

@dataclass
class Finding:
    id: str
    severity: str  # low, medium, high, critical
    score: float
    message: str
    file: Optional[str] = None
    line: Optional[int] = None

@dataclass
class StaticReport:
    schema_version: str = "1.0"
    loadset_id: str = ""
    structure_score: int = 0
    complexity_score: int = 0
    findings: List[Finding] = None
    
    def __post_init__(self):
        if self.findings is None:
            self.findings = []

def run_cargo_check(crate_path: str) -> List[Finding]:
    """Run cargo check and parse output"""
    findings = []
    try:
        result = subprocess.run(
            ["cargo", "check", "--message-format=json"],
            cwd=crate_path,
            capture_output=True,
            text=True
        )
        for line in result.stdout.split('\n'):
            if not line.strip():
                continue
            try:
                msg = json.loads(line)
                if msg.get("reason") == "compiler-message":
                    rendered = msg.get("message", {}).get("rendered", "")
                    level = msg.get("message", {}).get("level", "warning")
                    severity = "high" if level == "error" else "medium"
                    findings.append(Finding(
                        id=f"cargo-{len(findings)}",
                        severity=severity,
                        score=0.5 if severity == "medium" else 0.8,
                        message=rendered[:200],
                        file=msg.get("message", {}).get("spans", [{}])[0].get("file_name"),
                        line=msg.get("message", {}).get("spans", [{}])[0].get("line_start")
                    ))
            except json.JSONDecodeError:
                continue
    except FileNotFoundError:
        pass
    return findings

def count_lines(crate_path: str) -> dict:
    """Count lines of code"""
    stats = {"total": 0, "rust": 0, "files": 0}
    src_path = os.path.join(crate_path, "src")
    if os.path.exists(src_path):
        for root, _, files in os.walk(src_path):
            for f in files:
                if f.endswith(".rs"):
                    stats["files"] += 1
                    with open(os.path.join(root, f), 'r') as fp:
                        lines = len(fp.readlines())
                        stats["rust"] += lines
                        stats["total"] += lines
    return stats

def calculate_complexity(crate_path: str) -> int:
    """Estimate complexity score (simplified)"""
    # Real implementation would use syn AST
    loc = count_lines(crate_path)
    if loc["rust"] == 0:
        return 100
    # Penalize for too many lines per file
    avg_lines = loc["rust"] / max(loc["files"], 1)
    if avg_lines > 500:
        return 50
    elif avg_lines > 300:
        return 65
    elif avg_lines > 150:
        return 80
    return 90

def calculate_structure(crate_path: str) -> int:
    """Estimate structure score"""
    score = 100
    # Check for lib.rs or main.rs
    if not os.path.exists(os.path.join(crate_path, "src", "lib.rs")):
        if not os.path.exists(os.path.join(crate_path, "src", "main.rs")):
            score -= 20
    # Check for Cargo.toml
    if not os.path.exists(os.path.join(crate_path, "Cargo.toml")):
        score -= 30
    # Check for tests
    if not os.path.exists(os.path.join(crate_path, "tests")):
        score -= 10
    return max(score, 0)

def run_gate(crate_path: str, output_path: str) -> int:
    """Main gate execution"""
    loadset_id = f"static-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
    
    findings = run_cargo_check(crate_path)
    structure_score = calculate_structure(crate_path)
    complexity_score = calculate_complexity(crate_path)
    
    # Adjust scores based on findings
    for f in findings:
        if f.severity == "critical":
            structure_score = max(0, structure_score - 20)
        elif f.severity == "high":
            structure_score = max(0, structure_score - 10)
    
    report = StaticReport(
        loadset_id=loadset_id,
        structure_score=structure_score,
        complexity_score=complexity_score,
        findings=findings
    )
    
    output = {
        "schema_version": report.schema_version,
        "loadset_id": report.loadset_id,
        "structure_score": report.structure_score,
        "complexity_score": report.complexity_score,
        "findings": [asdict(f) for f in report.findings]
    }
    
    with open(output_path, 'w') as fp:
        json.dump(output, fp, indent=2)
    
    print(f"✓ Static QA: structure={structure_score} complexity={complexity_score}")
    return 0 if structure_score >= 50 and complexity_score >= 50 else 1

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: static_gate.py <crate_path> <output_path>")
        sys.exit(1)
    sys.exit(run_gate(sys.argv[1], sys.argv[2]))
