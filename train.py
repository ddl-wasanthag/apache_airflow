import numpy as np
from sklearn.datasets import load_iris
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import json, os

print("=== Domino ML Training Job ===")

# Load data
data = load_iris()
X, y = data.data, data.target

# Split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# Train
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# Evaluate
preds = model.predict(X_test)
acc = accuracy_score(y_test, preds)
print(f"Accuracy: {acc:.4f}")

# Write results artifact
os.makedirs("/mnt/artifacts", exist_ok=True)
results = {"accuracy": acc, "n_estimators": 100, "dataset": "iris"}
with open("/mnt/artifacts/results.json", "w") as f:
    json.dump(results, f)

print("Results written to /mnt/artifacts/results.json")
print("=== Training complete ===")
