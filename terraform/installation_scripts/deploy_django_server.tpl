PROJECT_ROOT_DIR="$(pwd)"

cd "$PROJECT_ROOT_DIR/src/wingsight-server/"

# Add Amplify details to environment for CORS settings
echo "export AMPLIFY_APP_ID=${amplify_app_id}" >> ~/.bashrc
echo "export AMPLIFY_BRANCH=${repo_branch_name}" >> ~/.bashrc
source ~/.bashrc

python -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install mysqlclient

python manage.py migrate
sudo venv/bin/python manage.py runserver 0.0.0.0:80

echo "Django web server deployed successfully!"