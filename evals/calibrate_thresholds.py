"""Calibration script to optimize CitationVerifier thresholds using F1 score maximization."""

import os
import sys
import json
import asyncio
from typing import List, Dict, Any

# Adjust python path to find app package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../apps/api")))

from app.services.citation.verifier import CitationVerifier

def calculate_f1(true_statuses: List[str], pred_statuses: List[str]) -> float:
    """Calculate macro F1 score for supported, partially_supported, unsupported."""
    classes = ["supported", "partially_supported", "unsupported"]
    f1_scores = []
    
    for cls in classes:
        tp = sum(1 for t, p in zip(true_statuses, pred_statuses) if t == cls and p == cls)
        fp = sum(1 for t, p in zip(true_statuses, pred_statuses) if t != cls and p == cls)
        fn = sum(1 for t, p in zip(true_statuses, pred_statuses) if t == cls and p != cls)
        
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        f1_scores.append(f1)
        
    return sum(f1_scores) / len(f1_scores)

async def calibrate() -> None:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    dataset_path = os.path.join(current_dir, "verification_calibration_dataset.json")
    
    if not os.path.exists(dataset_path):
        print(f"Error: Calibration dataset not found at {dataset_path}")
        return

    with open(dataset_path, "r", encoding="utf-8") as f:
        samples = json.load(f)

    # Search space for thresholds
    thresholds = [x / 100.0 for x in range(50, 95, 5)]
    partial_thresholds = [x / 100.0 for x in range(40, 90, 5)]

    best_f1 = -1.0
    best_t = 0.75
    best_pt = 0.60
    all_runs = []

    print(f"Starting threshold grid search calibration on {len(samples)} samples...")

    for t in thresholds:
        for pt in partial_thresholds:
            if pt >= t:
                continue

            verifier = CitationVerifier(threshold=t, partial_threshold=pt)
            pred_statuses = []
            true_statuses = []

            for sample in samples:
                claim = sample["claim"] + " [S1]"
                source = sample["source"]
                expected = sample["expected_status"]
                
                # Verify using dummy chunks list
                res = await verifier.verify(claim, [{"content": source}])
                pred = res["claims"][0]["status"]
                
                pred_statuses.append(pred)
                true_statuses.append(expected)

            f1 = calculate_f1(true_statuses, pred_statuses)
            all_runs.append({
                "threshold": t,
                "partial_threshold": pt,
                "macro_f1": f1
            })

            if f1 > best_f1:
                best_f1 = f1
                best_t = t
                best_pt = pt

    print("\n=== Calibration Complete ===")
    print(f"Optimal Threshold (supported): {best_t:.2f}")
    print(f"Optimal Partial Threshold: {best_pt:.2f}")
    print(f"Max Macro F1 Score: {best_f1:.4f}")

    # Save calibration run report
    report_path = os.path.join(current_dir, "calibration_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump({
            "optimal_threshold": best_t,
            "optimal_partial_threshold": best_pt,
            "max_macro_f1": best_f1,
            "all_runs": all_runs
        }, f, indent=2, ensure_ascii=False)
    print(f"Saved calibration report to {report_path}")

if __name__ == "__main__":
    asyncio.run(calibrate())
