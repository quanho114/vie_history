"""Calculate Cohen's Kappa Agreement for HistoriEval-VN."""

import json
import os
import numpy as np

def cohens_kappa(y1, y2):
    categories = list(set(y1).union(set(y2)))
    cat_map = {cat: idx for idx, cat in enumerate(categories)}
    n_classes = len(categories)
    
    cm = np.zeros((n_classes, n_classes))
    for val1, val2 in zip(y1, y2):
        cm[cat_map[val1]][cat_map[val2]] += 1
        
    n = np.sum(cm)
    po = np.trace(cm) / n
    
    pe = 0
    row_sums = np.sum(cm, axis=1)
    col_sums = np.sum(cm, axis=0)
    for i in range(n_classes):
        pe += (row_sums[i] * col_sums[i]) / (n * n)
        
    if pe == 1.0:
        return 1.0
    return (po - pe) / (1 - pe)

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    labels_path = os.path.join(current_dir, "annotator_labels.json")
    
    with open(labels_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    y1 = [item["annotator_1"] for item in data]
    y2 = [item["annotator_2"] for item in data]
    
    kappa = cohens_kappa(y1, y2)
    print(f"Cohen's Kappa Agreement: {kappa:.3f}")
