from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from datetime import datetime, timedelta
import pandas as pd
import os
from transform_script import transfrom  # Импорт функции

# Параметры DAG
default_args = {
    'owner': 'Kostash Denis',
    'depends_on_past': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}


def extract(**kwargs):
    input_path = '/data/profit_table.csv'
    df = pd.read_csv(input_path)
    kwargs['ti'].xcom_push(key='input_data', value=df)


def transform_task(date, **kwargs):
    # Извлекаем данные из предыдущей задачи
    input_data = kwargs['ti'].xcom_pull(key='input_data', task_ids='extract')
    input_df = pd.DataFrame(input_data)

    # Применяем функцию трансформации
    transformed_data = transfrom(input_df, date)

    # Передаем данные дальше
    kwargs['ti'].xcom_push(key='transformed_data', value=transformed_data)


def load(**kwargs):
    output_path = '/data/flags_activity.csv'
    transformed_data = kwargs['ti'].xcom_pull(key='transformed_data', task_ids='transform')

    # Записываем данные в файл
    if os.path.exists(output_path):
        transformed_data.to_csv(output_path, mode='a', header=False, index=False)
    else:
        transformed_data.to_csv(output_path, index=False)


# Создаем DAG
with DAG(
        'etl_dag_Kostash_Denis',
        default_args=default_args,
        description='ETL DAG for customer activity flags',
        schedule_interval='0 0 5 * *',  # Запуск каждый месяц 5-го числа
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
        op_kwargs={'date': '{{ ds }}'},  # Передача текущей даты как параметра
        provide_context=True,
    )

    load_task = PythonOperator(
        task_id='load',
        python_callable=load,
        provide_context=True,
    )

    # Задаем зависимости
    extract_task >> transform_task_instance >> load_task
