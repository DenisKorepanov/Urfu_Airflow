from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from datetime import datetime, timedelta
import pandas as pd
import os
from transform_script import transfrom  

# Описываем Параметры DAG
default_args = {
    'owner': 'Korepanov Denis',
    'depends_on_past': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}


def extract(**kwargs):
    input_path = '/data/profit_table.csv'
    df = pd.read_csv(input_path)
    kwargs['ti'].xcom_push(key='input_data', value=df)


def transform_task(date, **kwargs):
    # Здесь извлекаем данные из предыдущей задачи
    input_data = kwargs['ti'].xcom_pull(key='input_data', task_ids='extract')
    input_df = pd.DataFrame(input_data)

    # Трансформация
    transformed_data = transfrom(input_df, date)

    kwargs['ti'].xcom_push(key='transformed_data', value=transformed_data)


def load(**kwargs):
    output_path = '/data/flags_activity.csv'
    transformed_data = kwargs['ti'].xcom_pull(key='transformed_data', task_ids='transform')

    # Запись данных
    if os.path.exists(output_path):
        transformed_data.to_csv(output_path, mode='a', header=False, index=False)
    else:
        transformed_data.to_csv(output_path, index=False)


# Создание DAG
with DAG(
        'etl_dag_Korepanov_Denis',
        default_args=default_args,
        description='ETL DAG for customer activity flags',
        schedule_interval='0 0 6 * *',  # Запуск осуществляется каждый месяц 6-го числа
        start_date=datetime(2023, 10, 1),
        catchup=False,
        tags=['ETL', 'Activity Flags'],
) as dag:
    extract_task = PythonOperator(
        task_id='extract',
        python_callable=extract,
        provide_context=True,
    )

    transform_task_instance = PythonOperator(
        task_id='transform',
        python_callable=transform_task,
        op_kwargs={'date': '{{ ds }}'},  # Передаем дату как параметр
        provide_context=True,
    )

    load_task = PythonOperator(
        task_id='load',
        python_callable=load,
        provide_context=True,
    )

    # Зависимости
    extract_task >> transform_task_instance >> load_task
