# Apache Airflow (MWAA) + Domino ML Demo

A step-by-step guide to integrating AWS Managed Workflows for Apache Airflow (MWAA) with a Domino deployment, triggering real ML training jobs from an Airflow DAG.

---

## Validated Versions

| Component | Version |
|-----------|---------|
| AWS MWAA Airflow | 3.2.1 |
| python-domino (`dominodatalab`) | latest |
| Python | 3.x |

> **Important:** Airflow 3.x introduced breaking changes to import paths. The DAG in this repo uses `airflow.sdk` imports and is **not** compatible with Airflow 2.x without modification. See the [Airflow 3.x notes](#airflow-3x-compatibility) section below.

---

## Overview

This demo sets up a two-task Airflow pipeline that:
1. **Trains** a Random Forest classifier on the Iris dataset inside Domino
2. **Evaluates** the results and checks against an accuracy threshold

Airflow runs externally on AWS MWAA and triggers Domino Jobs via the `python-domino` SDK using a `PythonOperator`.

```
Airflow (MWAA)
  └── DAG: domino_ml_pipeline
        ├── Task 1: train_model    ──► Domino Job: python /mnt/code/train.py
        └── Task 2: evaluate_model ──► Domino Job: python /mnt/code/evaluate.py
```

---

## Prerequisites

- AWS account with an MWAA environment (status: `Available`)
- AWS CLI configured with permissions to read/write the MWAA S3 bucket
- Domino deployment with project-create access
- Domino user API key (Account Settings → API Keys)

> **Domino 6.3+:** API keys are deprecated. Use a Service Account token instead — see [Manage Domino Service Accounts](https://docs.dominodatalab.com/en/cloud/admin_guide/6921e5/manage-domino-service-accounts/).

---

## Repository Structure

```
.
├── domino-project/
│   ├── train.py          # ML training script — upload to Domino project Files
│   ├── evaluate.py       # Evaluation script — upload to Domino project Files
│   └── requirements.txt  # Domino project dependencies
├── mwaa/
│   ├── dags/
│   │   └── domino_ml_demo_dag.py   # Airflow DAG — upload to S3 dags/ folder
│   └── requirements.txt            # MWAA worker dependencies — upload to S3 root
└── README.md
```

---

## Setup

### Phase 1 — Domino Project

1. Create a new project in Domino named **`airflow-ml-demo`**

2. Upload the three files from `domino-project/` to the project via **Files**:
   - `train.py` — trains a Random Forest model and writes results to `/mnt/artifacts/results.json`
   - `evaluate.py` — reads the results artifact and validates against a 90% accuracy threshold
   - `requirements.txt` — installs `scikit-learn` and `numpy` into the Domino environment

3. Note your **Domino username** — you'll need `username/airflow-ml-demo` as the project identifier in the next phase.

---

### Phase 2 — Configure MWAA

#### 2.1 Create the MWAA environment

In the AWS Console go to **Amazon MWAA → Environments → Create environment**:

- **Airflow version:** `3.2.1` (or latest available)
- **Web server access:** `Public network` (fine for dev/sandbox)
- **S3 bucket:** create or select a bucket for DAGs and requirements
- **DAGs folder:** `s3://YOUR-BUCKET/dags/`
- **Execution role:** let MWAA create one, then add S3 permissions (see below)

#### 2.2 Fix S3 permissions on the execution role

MWAA's auto-created role doesn't include your bucket by default. In **IAM → Roles**, find the MWAA execution role and attach this inline policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject*",
        "s3:GetBucket*",
        "s3:List*",
        "s3:PutObject*",
        "s3:DeleteObject*"
      ],
      "Resource": [
        "arn:aws:s3:::YOUR-BUCKET",
        "arn:aws:s3:::YOUR-BUCKET/*"
      ]
    }
  ]
}
```

#### 2.3 Upload MWAA requirements and DAG

```bash
# Install dominodatalab on MWAA workers
aws s3 cp mwaa/requirements.txt s3://YOUR-BUCKET/requirements.txt

# Upload the DAG
aws s3 cp mwaa/dags/domino_ml_demo_dag.py s3://YOUR-BUCKET/dags/domino_ml_demo_dag.py
```

Then point MWAA at the requirements file:

```bash
aws mwaa update-environment \
  --name YOUR-ENVIRONMENT-NAME \
  --requirements-s3-path requirements.txt
```

Wait ~10 minutes for the environment to return to `Available`.

#### 2.4 Set Airflow Variables

Open the Airflow UI (MWAA Console → **Open Airflow UI**) and go to **Admin → Variables**. Create these three variables:

| Key | Value |
|-----|-------|
| `DOMINO_API_HOST` | Your Domino deployment URL |
| `DOMINO_API_KEY` | Your Domino user API key (or Service Account token) |
| `DOMINO_PROJECT` | `your-username/airflow-ml-demo` |

---

### Phase 3 — Run the Demo

1. In the Airflow UI find `domino_ml_pipeline` and toggle it **On**
2. Click **▶ Trigger DAG** → **Trigger**
3. Click into the DAG → **Graph** tab to watch tasks progress
4. In parallel open your **Domino project → Jobs** — you'll see the jobs appear in real time as Airflow triggers them

---

## Expected Output

**`train_model` task logs (via Airflow):**
```
=== Domino ML Training Job ===
Accuracy: 0.9667
Results written to /mnt/artifacts/results.json
=== Training complete ===
```

**`evaluate_model` task logs (via Airflow):**
```
=== Domino Evaluation Job ===
Model accuracy: 0.9667
PASS: Model meets accuracy threshold
=== Evaluation complete ===
```

---

## Airflow 3.x Compatibility

Airflow 3.x restructured its SDK with breaking import path changes. This DAG uses the updated paths — **do not use the older Airflow 2.x patterns**:

| Airflow 2.x (broken on 3.x) | Airflow 3.x (correct) |
|-----------------------------|----------------------|
| `from airflow import DAG` | `from airflow.sdk import DAG` |
| `from airflow.models import Variable` | `from airflow.sdk import Variable` |
| `schedule_interval=None` | `schedule=None` |
| `DominoOperator` from `domino.airflow` | `PythonOperator` calling `runs_start_blocking` |

The `DominoOperator` (from `dominodatalab[airflow]`) does **not** work on Airflow 3.x. Use the `PythonOperator` + `runs_start_blocking` pattern in this repo instead.

Also note that `runs_start_blocking` expects `command` as a **list of strings**, not a single string:

```python
# Correct
command=["python", "/mnt/code/train.py"]

# Wrong — causes "can't open file" error in Domino
command=["python /mnt/code/train.py"]
```

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| DAG not appearing in UI, no import error shown | Airflow 2.x import paths used in DAG | Update imports to use `airflow.sdk` — see [Airflow 3.x Compatibility](#airflow-3x-compatibility) |
| DAG shows `# DAGs: 0, # Errors: 1` in processing logs | DAG parse failure | Enable DAGProcessing logs in CloudWatch at `DEBUG` level to see traceback |
| `Provided role does not have sufficient permissions for s3 location` | MWAA IAM role missing S3 policy | Attach inline S3 policy to the MWAA execution role — see Phase 2.2 |
| `ModuleNotFoundError: No module named 'domino'` | `requirements.txt` not linked or install failed | Run `update-environment --requirements-s3-path` and wait for `Available` |
| `python: can't open file '/mnt/code/python /mnt/code/train.py'` | Command passed as single string instead of list | Use `["python", "/mnt/code/train.py"]` not `["python /mnt/code/train.py"]` |
| `401 Unauthorized` from Domino | Wrong API key or expired token | Re-check `DOMINO_API_KEY` variable; for Domino 6.3+ use a Service Account token |
| Jobs not appearing in Domino | Wrong project path in `DOMINO_PROJECT` | Value must be exactly `username/project-name` matching your Domino project URL |
| MWAA environment stuck in `Updating` | Normal — dependency install takes time | Wait ~10 min; check CloudWatch Scheduler logs if it stays updating longer |

---

## Enabling CloudWatch Logs

If you need to debug DAG parsing or scheduler issues, enable full logging:

```bash
aws mwaa update-environment \
  --name YOUR-ENVIRONMENT-NAME \
  --logging-configuration '{
    "SchedulerLogs": {"Enabled": true, "LogLevel": "INFO"},
    "WebserverLogs": {"Enabled": true, "LogLevel": "INFO"},
    "WorkerLogs":    {"Enabled": true, "LogLevel": "INFO"},
    "DagProcessingLogs": {"Enabled": true, "LogLevel": "DEBUG"}
  }'
```

Then look for these log groups in CloudWatch:
- `airflow-YOUR-ENV-DAGProcessing` — DAG parse errors
- `airflow-YOUR-ENV-Scheduler` — scheduler startup and job dispatch
- `airflow-YOUR-ENV-Worker` — task execution logs

---

## References

- [Domino Docs — Orchestrate Jobs with Apache Airflow](https://docs.dominodatalab.com/en/latest/user_guide/e4f67f/orchestrate-jobs-with-apache-airflow/)
- [python-domino on PyPI](https://pypi.org/project/dominodatalab/)
- [python-domino GitHub — Airflow example DAG](https://github.com/dominodatalab/python-domino/blob/master/examples/example_airflow_dag.py)
- [AWS MWAA Documentation](https://docs.aws.amazon.com/mwaa/latest/userguide/what-is-mwaa.html)
- [Apache Airflow 3.x Migration Guide](https://airflow.apache.org/docs/apache-airflow/stable/migration-guide.html)
