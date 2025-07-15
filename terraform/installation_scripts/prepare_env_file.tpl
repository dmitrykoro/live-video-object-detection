PROJECT_ROOT_DIR="$(pwd)"

cd "$PROJECT_ROOT_DIR/src"

sudo sed -i 's/DEPLOYMENT_ENV=local/DEPLOYMENT_ENV=aws/g' .env
sudo sed -i 's/DATABASE_NAME=db_name_here/DATABASE_NAME=${db_name}/g' .env
sudo sed -i 's/DATABASE_USER=db_username_here/DATABASE_USER=${db_username}/g' .env
sudo sed -i 's/DATABASE_PASSWORD=db_password_here/DATABASE_PASSWORD=${db_password}/g' .env
sudo sed -i 's/DATABASE_HOST=db_host_here/DATABASE_HOST=${db_host}/g' .env
sudo sed -i 's/S3_BUCKET_NAME=bucket_name_here/S3_BUCKET_NAME=${img_bucket_name}/g' .env
sudo sed -i 's/SNS_TOPIC_ARN=sns_topic_arn_here/SNS_TOPIC_ARN=${sns_topic_arn}/g' .env
sudo sed -i 's/AWS_REGION=aws_region_here/AWS_REGION=${aws_region}/g' .env
sudo sed -i 's/MQ_HOST=localhost/MQ_HOST=${rabbitmq_host}/g' .env
sudo sed -i 's/MQ_USER=mq_user_here/MQ_USER=${rabbitmq_user}/g' .env
sudo sed -i 's/MQ_PASSWORD=mq_password_here/MQ_PASSWORD=${rabbitmq_password}/g' .env

sudo sed -i 's/USER_POOL_ID=user_pool_id_here/USER_POOL_ID=${user_pool_id}/g' .env
sudo sed -i 's/APP_CLIENT_ID=app_client_id_here/APP_CLIENT_ID=${app_client_id}/g' .env

cd "$PROJECT_ROOT_DIR"
