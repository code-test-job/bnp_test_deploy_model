import os
from airflow import DAG
from airflow.providers.google.cloud.operators.vertex_ai.model_service import UploadModelOperator
from airflow.providers.google.cloud.operators.vertex_ai.endpoint_service import CreateEndpointOperator, DeployModelOperator
from airflow.operators.dummy import DummyOperator
from airflow.utils.dates import timedelta, datetime

#######################################################################
# Start Parameters Global
#######################################################################

# Default env_var Reserved Variables
GCS_BUCKET = os.environ.get('GCS_BUCKET')  # DO NOT CHANGE
GCP_PROJECT = os.environ.get('GCP_PROJECT')  # DO NOT CHANGE
DAGS_FOLDER = os.environ.get('DAGS_FOLDER')  # DO NOT CHANGE
COMPOSER_LOCATION = os.environ.get('COMPOSER_LOCATION')  # DO NOT CHANGE

# Editable general variables (Be always careful and follow the rules on ReadMe and Confluence)
dag_name = 'bnp_test_deploy_model'
description = "Model Deployment"                                       
tags_dag = ['vertex_ai', 'model', 'deploy']                          
schedule_interval = "@once"    
model_name = 'long_calculation'                                        
start_date = datetime(2023, 5, 13)                            

# Editable model variables (Be always careful and follow the rules on ReadMe and Confluence)
display_name_model = model_name                                                             
description_model = 'description model'                                                     
version_description_model = 'description model version'                                     
image_uri = f'us-east1-docker.pkg.dev/{GCP_PROJECT}/mlops-custom-container/github_code-test-job_bnp_test_custom_container@sha256' \
            f':46e571edbde3ea72938662d7ae1183c710e608b6e184928e15548f23416b6f30'            
predict_route = '/predict'                                                                  
health_route = '/healthcheck'                                                               

# Editable endpoint variables (Be always careful and follow the rules on ReadMe and Confluence)
display_name_endpoint = f'{model_name}_endpoint'                                            
description_endpoint = 'endpoint'                                               

# Editable deploy variables (Be always careful and follow the rules on ReadMe and Confluence)
display_name_deploy = f'deployed_{model_name}'                                             
machine_type = 'n1-standard-2'                                                              
min_replica_count = 1                                                                       
max_replica_count = 1                                                                       

#######################################################################
# Finish Parameters Global
#######################################################################


default_args = {
    'owner': 'bnp_paribas',
    'start_date': start_date,
    'retries': 1,
    'retry_delay': timedelta(minutes=1),
}

with DAG(dag_name,
         default_args=default_args,
         description=description,
         schedule_interval=schedule_interval,
         tags=tags_dag,
         catchup=False,
         ) as dag:
    start_dag = DummyOperator(task_id='start_dag')

    upload_model = UploadModelOperator(
        task_id=f'upload_model-{model_name}',
        project_id=GCP_PROJECT,
        region=COMPOSER_LOCATION,
        model={
            'name': display_name_model,
            'display_name': display_name_model,
            'description': description_model,
            'version_description': version_description_model,
            'container_spec': {
                'image_uri': image_uri,
                'predict_route': predict_route,
                'health_route': health_route
            },
        } 
    )

    create_endpoint = CreateEndpointOperator(
            task_id=f'create_endpoint-{model_name}',
            project_id=GCP_PROJECT,
            region=COMPOSER_LOCATION,
            endpoint={
                'display_name': display_name_endpoint,
                'description': description_endpoint
            }  
        )

    deploy_model = DeployModelOperator(
            task_id=f'deploy_model-{model_name}',
            project_id=GCP_PROJECT,
            region=COMPOSER_LOCATION,
            endpoint_id=create_endpoint.output["endpoint_id"],
            deployed_model={
                'model': "{{{{ task_instance.xcom_pull(task_ids='{task_id}')['model'] }}}}".format(task_id=f'upload_model-{model_name}'),
                'display_name': display_name_deploy,
                'dedicated_resources': {
                    'machine_spec': {
                        'machine_type': machine_type,
                    },
                    'min_replica_count': min_replica_count,
                    'max_replica_count': max_replica_count,
                }
            }  
        )

    end_dag = DummyOperator(task_id='end_dag')

    start_dag >> upload_model >> create_endpoint >> deploy_model >> end_dag
