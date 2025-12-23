#!/usr/bin/env python3
"""
Pattern Matching Gate - Canonical Block Discovery
Part of Unified Forge Pipeline

Matches code against canonical N-V-N-N blocks:
- Structural similarity (AST shape)
- Semantic similarity (intent)
- Constraint validation

Output: pattern.matches.json
"""

import json
import re
import sys
import os
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Optional
from datetime import datetime, timezone

@dataclass
class Candidate:
    pattern_id: str
    confidence: float
    structural_score: float
    semantic_score: float
    violations: List[str] = field(default_factory=list)

@dataclass
class Match:
    file: str
    symbol: str
    classification: str  # NO_MATCH, PARTIAL_MATCH, STRONG_MATCH, AMBIGUOUS
    candidates: List[Candidate] = field(default_factory=list)

@dataclass
class PatternReport:
    schema_version: str = "1.0"
    loadset_id: str = ""
    score: int = 0
    matches: List[Match] = field(default_factory=list)

# Canonical block signatures for matching
CANONICAL_SIGNATURES = {
    "USER_VALIDATE_INPUT_SECURITY": {
        "category": "validation",
        "patterns": [
            r'fn\s+validate',
            r'Result<.*,\s*\w*Error>',
            r'if\s+\w+\.is_empty\(\)',
        ],
        "constraints": ["deterministic", "no_io", "single_responsibility"],
        "anti_patterns": [r'println!', r'eprintln!', r'std::io', r'tokio::fs'],
    },
    "SYSTEM_WRITE_IDEMPOTENT_RECORD": {
        "category": "persistence",
        "patterns": [
            r'fn\s+write|fn\s+save|fn\s+persist',
            r'idempotent|upsert|insert_or_update',
        ],
        "constraints": ["deterministic", "no_logging"],
        "anti_patterns": [r'println!', r'log::'],
    },
    "WORKER_PROCESS_TASK_BOUNDED": {
        "category": "concurrency",
        "patterns": [
            r'fn\s+process|fn\s+handle|fn\s+execute',
            r'bounded|limit|max_',
        ],
        "constraints": ["deterministic", "bounded"],
        "anti_patterns": [r'loop\s*\{[^}]*\}(?![^}]*break)'],  # Unbounded loops
    },
    "SERVICE_ROTATE_TOKEN_SECURE": {
        "category": "security",
        "patterns": [
            r'fn\s+rotate|fn\s+refresh|fn\s+renew',
            r'token|secret|credential',
        ],
        "constraints": ["deterministic", "no_logging"],
        "anti_patterns": [r'println!.*token', r'dbg!.*secret'],
    },
    "RESOURCE_CLOSE_GRACEFUL": {
        "category": "lifecycle",
        "patterns": [
            r'fn\s+close|fn\s+shutdown|fn\s+cleanup',
            r'Drop|drop|dispose',
        ],
        "constraints": ["graceful"],
        "anti_patterns": [r'panic!', r'unwrap\(\)(?!\s*//\s*safe)'],
    },
    "SERVICE_ADAPTER_IO_WRAPPER": {
        "category": "design",
        "patterns": [
            r'trait\s+\w+Adapter|impl\s+\w+Adapter',
            r'wrap|delegate|proxy',
        ],
        "constraints": ["declares_side_effects"],
        "anti_patterns": [],
    },
}

def extract_functions(content: str) -> List[tuple]:
    """Extract function names and their bodies"""
    pattern = r'(pub\s+)?fn\s+(\w+)[^{]*\{([^}]*(?:\{[^}]*\}[^}]*)*)\}'
    matches = re.findall(pattern, content, re.DOTALL)
    return [(m[1], m[2]) for m in matches]

def match_pattern(func_name: str, func_body: str, pattern_id: str, sig: dict) -> Optional[Candidate]:
    """Check if function matches a canonical pattern"""
    full_text = f"fn {func_name} {func_body}"
    
    # Check positive patterns
    pattern_matches = sum(1 for p in sig["patterns"] if re.search(p, full_text, re.IGNORECASE))
    if pattern_matches == 0:
        return None
    
    structural_score = min(1.0, pattern_matches / len(sig["patterns"]))
    
    # Check anti-patterns (violations)
    violations = []
    for ap in sig["anti_patterns"]:
        if re.search(ap, full_text):
            violations.append(f"violates: {ap[:30]}")
    
    # Penalize for violations
    violation_penalty = len(violations) * 0.2
    semantic_score = max(0, 1.0 - violation_penalty)
    
    confidence = (structural_score * 0.6 + semantic_score * 0.4)
    
    if confidence < 0.3:
        return None
    
    return Candidate(
        pattern_id=pattern_id,
        confidence=round(confidence, 2),
        structural_score=round(structural_score, 2),
        semantic_score=round(semantic_score, 2),
        violations=violations
    )

def classify(candidates: List[Candidate]) -> str:
    """Classify match based on candidates"""
    if not candidates:
        return "NO_MATCH"
    
    best = max(candidates, key=lambda c: c.confidence)
    if best.confidence >= 0.7:
        if len(candidates) > 1 and candidates[1].confidence > 0.5:
            return "AMBIGUOUS"
        return "STRONG_MATCH"
    elif best.confidence >= 0.4:
        return "PARTIAL_MATCH"
    return "NO_MATCH"

def scan_crate(crate_path: str, registry_path: str) -> List[Match]:
    """Scan crate and match against canonical patterns"""
    matches = []
    src_path = os.path.join(crate_path, "src")
    
    if not os.path.exists(src_path):
        return matches
    
    for root, _, files in os.walk(src_path):
        for f in files:
            if not f.endswith('.rs'):
                continue
            filepath = os.path.join(root, f)
            rel_path = os.path.relpath(filepath, crate_path)
            
            with open(filepath, 'r') as fp:
                content = fp.read()
            
            functions = extract_functions(content)
            for func_name, func_body in functions:
                candidates = []
                for pattern_id, sig in CANONICAL_SIGNATURES.items():
                    candidate = match_pattern(func_name, func_body, pattern_id, sig)
                    if candidate:
                        candidates.append(candidate)
                
                # Sort by confidence
                candidates.sort(key=lambda c: c.confidence, reverse=True)
                
                matches.append(Match(
                    file=rel_path,
                    symbol=func_name,
                    classification=classify(candidates),
                    candidates=candidates[:3]  # Top 3
                ))
    
    return matches

def calculate_score(matches: List[Match]) -> int:
    """Calculate pattern score"""
    if not matches:
        return 70  # Baseline for crates with no functions (type definitions)
    
    # Filter to only functions that could match patterns
    relevant = [m for m in matches if m.candidates]
    if not relevant:
        return 70  # No matchable functions = baseline score
    
    strong = sum(1 for m in matches if m.classification == "STRONG_MATCH")
    partial = sum(1 for m in matches if m.classification == "PARTIAL_MATCH")
    total = len(relevant)
    
    if total == 0:
        return 70
    
    return min(100, int((strong * 100 + partial * 50) / total))

def run_gate(crate_path: str, registry_path: str, output_path: str) -> int:
    """Main gate execution"""
    loadset_id = f"pattern-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
    
    matches = scan_crate(crate_path, registry_path)
    score = calculate_score(matches)
    
    report = PatternReport(
        loadset_id=loadset_id,
        score=score,
        matches=matches
    )
    
    output = {
        "schema_version": report.schema_version,
        "loadset_id": report.loadset_id,
        "score": report.score,
        "matches": [
            {
                "file": m.file,
                "symbol": m.symbol,
                "classification": m.classification,
                "candidates": [asdict(c) for c in m.candidates]
            }
            for m in report.matches
        ]
    }
    
    with open(output_path, 'w') as fp:
        json.dump(output, fp, indent=2)
    
    strong_count = sum(1 for m in matches if m.classification == "STRONG_MATCH")
    print(f"✓ Pattern Match: score={score} strong={strong_count}/{len(matches)}")
    return 0

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: pattern_gate.py <crate_path> <registry_path> <output_path>")
        sys.exit(1)
    sys.exit(run_gate(sys.argv[1], sys.argv[2], sys.argv[3]))
