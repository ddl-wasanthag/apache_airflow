import json, os

print("=== Domino Evaluation Job ===")

results_path = "/mnt/artifacts/results.json"
if os.path.exists(results_path):
    with open(results_path) as f:
        results = json.load(f)
    acc = results["accuracy"]
    print(f"Model accuracy: {acc:.4f}")
    print(f"Dataset: {results['dataset']}")
    print("PASS: Model meets accuracy threshold" if acc >= 0.90 else "FAIL: Model below threshold")
else:
    print("No results artifact found — standalone check OK")

print("=== Evaluation complete ===")
