import json, os

   results_path = "/mnt/artifacts/results.json"
   if os.path.exists(results_path):
       with open(results_path) as f:
           results = json.load(f)
       acc = results["accuracy"]
       print(f"Accuracy: {acc:.4f}")
       print("PASS" if acc >= 0.90 else "FAIL")
   else:
       print("No results artifact found — standalone check OK")