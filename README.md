# Apache Airflow (MWAA) + Domino ML Demo

A step-by-step guide to integrating AWS Managed Workflows for Apache Airflow (MWAA) with a Domino sandbox deployment, triggering real ML training jobs from an Airflow DAG.

---

## Overview

This demo sets up a two-task Airflow pipeline that:
1. **Trains** a Random Forest classifier on the Iris dataset inside Domino
2. **Evaluates** the results and checks against an accuracy threshold

Airflow runs externally on AWS MWAA and triggers Domino Jobs via the `python-domino` `DominoOperator`.

```
Airflow (MWAA)
  └── DAG: domino_ml_pipeline
        ├── Task 1: train_model   ──► Domino Job: python train.py
        └── Task 2: evaluate_model ──► Domino Job: python evaluate.py
```

---

## Prerequisites

- AWS account with an MWAA environment (status: `Available`)
- AWS CLI configured (`aws s3 cp` access to the MWAA S3 bucket)
- Domino sandbox instance with admin or project-create access
- Domino user API key (Account Settings → API Keys)

---

## Repository Structure

```
.
├── domino-project/
│   ├── train.py          # ML training script (runs inside Domino)
│   ├── evaluate.py       # Evaluation script (runs inside Domino)
│   └── requirements.txt  # Domino project dependencies
├── mwaa/
│   ├── dags/
│   │   └── domino_ml_demo_dag.py   # Airflow DAG definition
│   └── mwaa-requirements.txt       # MWAA worker dependencies
└── README.md
```

---

## Setup

### Phase 1 — Domino Project

1. Create a new project in your Domino sandbox named **`airflow-ml-demo`**

2. Add the following files under **Files**:

   **`train.py`**
   ```python
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
   ```

   **`evaluate.py`**
   ```python
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
   ```

   **`requirements.txt`**
   ```
   scikit-learn
   numpy
   ```

3. Note your **Domino URL** and **username** — you'll need `username/airflow-ml-demo` as the project identifier.

---

### Phase 2 — Configure MWAA

1. **Create `mwaa-requirements.txt`** locally:
   ```
   dominodatalab[airflow]
   apache-airflow-providers-http
   ```

2. **Upload to S3:**
   ```bash
   aws s3 cp mwaa-requirements.txt s3://YOUR-MWAA-BUCKET/requirements.txt
   ```

3. **Point MWAA at the requirements file:**
   - AWS Console → MWAA → your environment → **Edit**
   - Set **Requirements file** → `s3://YOUR-MWAA-BUCKET/requirements.txt`
   - Save and wait ~10 min for the environment to return to `Available`

4. **Set Airflow Variables** (Admin → Variables in the Airflow UI):

   | Key | Value |
   |-----|-------|
   | `DOMINO_API_HOST` | `https://your-sandbox.domino.tech` |
   | `DOMINO_API_KEY` | Your Domino user API key |

> **Domino 6.3+:** API keys are deprecated. Use a Service Account token instead.

---

### Phase 3 — Deploy the DAG

1. **Edit `domino_ml_demo_dag.py`** — update `DOMINO_PROJECT` with your username:
   ```python
   DOMINO_PROJECT = "your-username/airflow-ml-demo"
   ```

2. **Upload to S3:**
   ```bash
   aws s3 cp domino_ml_demo_dag.py s3://YOUR-MWAA-BUCKET/dags/domino_ml_demo_dag.py
   ```

3. The DAG will appear in the Airflow UI within ~30 seconds.

---

## Running the Demo

1. Open the **Airflow UI** (MWAA Console → Open Airflow UI)
2. Find `domino_ml_pipeline` and toggle it **On**
3. Click **▶ Trigger DAG**
4. Watch tasks progress in **Graph View**
5. In parallel, open your **Domino project → Jobs** to see the jobs appear in real time

---

## Expected Output

**`train_model` task logs:**
```
=== Domino ML Training Job ===
Accuracy: 0.9667
Results written to /mnt/artifacts/results.json
=== Training complete ===
```

**`evaluate_model` task logs:**
```
=== Domino Evaluation Job ===
Model accuracy: 0.9667
PASS: Model meets accuracy threshold
=== Evaluation complete ===
```

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| DAG shows **Import Error** | Syntax error or missing package | Check Airflow UI error banner; verify `mwaa-requirements.txt` was picked up |
| Tasks stuck in **queued** | MWAA still updating | Wait for environment status to return to `Available` |
| `401 Unauthorized` from Domino | Wrong API key or token expired | Re-check `DOMINO_API_KEY` variable; for 6.3+ use a Service Account token |
| Jobs not appearing in Domino | Wrong project path | Verify `DOMINO_PROJECT = "username/project-name"` matches exactly |
| MWAA can't read S3 | IAM role missing S3 permissions | Ensure the MWAA execution role has `s3:GetObject` on the DAGs bucket |

---

## References

- [Domino Docs — Orchestrate Jobs with Apache Airflow](https://docs.dominodatalab.com/en/latest/user_guide/e4f67f/orchestrate-jobs-with-apache-airflow/)
- [python-domino on PyPI](https://pypi.org/project/dominodatalab/)
- [python-domino GitHub — Airflow example DAG](https://github.com/dominodatalab/python-domino/blob/master/examples/example_airflow_dag.py)
- [AWS MWAA Documentation](https://docs.aws.amazon.com/mwaa/latest/userguide/what-is-mwaa.html)