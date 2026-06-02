import numpy as np
   from sklearn.datasets import load_iris
   from sklearn.ensemble import RandomForestClassifier
   from sklearn.model_selection import train_test_split
   from sklearn.metrics import accuracy_score
   import json, os

   data = load_iris()
   X_train, X_test, y_train, y_test = train_test_split(
       data.data, data.target, test_size=0.2, random_state=42
   )
   model = RandomForestClassifier(n_estimators=100, random_state=42)
   model.fit(X_train, y_train)
   acc = accuracy_score(y_test, model.predict(X_test))
   print(f"Accuracy: {acc:.4f}")

   os.makedirs("/mnt/artifacts", exist_ok=True)
   with open("/mnt/artifacts/results.json", "w") as f:
       json.dump({"accuracy": acc, "n_estimators": 100, "dataset": "iris"}, f)
   print("Training complete.")