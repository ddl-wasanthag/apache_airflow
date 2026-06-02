from datetime import datetime, timedelta
from airflow.sdk import DAG
from airflow.operators.python import PythonOperator


def run_domino_job(command: list):
    """Trigger a blocking Domino job run via the python-domino SDK."""
    import domino as dm
    from airflow.sdk import Variable

    api_key = Variable.get("DOMINO_API_KEY")
    host    = Variable.get("DOMINO_API_HOST")
    project = Variable.get("DOMINO_PROJECT")

    print(f"Connecting to Domino at {host}")
    print(f"Project: {project}")
    print(f"Running command: {command}")

    d = dm.Domino(project, api_key=api_key, host=host)
    run = d.runs_start_blocking(command=command)
    print(f"Job completed: {run}")


with DAG(
    dag_id="domino_ml_pipeline",
    description="Train and evaluate an ML model via Domino",
    default_args={
        "owner": "domino-demo",
        "depends_on_past": False,
        "retries": 1,
        "retry_delay": timedelta(minutes=2),
    },
    start_date=datetime(2024, 1, 1),
    schedule=None,        # manual trigger
    catchup=False,
    tags=["domino", "ml", "demo"],
) as dag:

    train = PythonOperator(
        task_id="train_model",
        python_callable=run_domino_job,
        op_kwargs={"command": ["python", "/mnt/code/train.py"]},
    )

    evaluate = PythonOperator(
        task_id="evaluate_model",
        python_callable=run_domino_job,
        op_kwargs={"command": ["python", "/mnt/code/evaluate.py"]},
    )

    train >> evaluate
