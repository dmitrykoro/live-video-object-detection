PROJECT_ROOT_DIR="$(pwd)"

cd "$PROJECT_ROOT_DIR/src/wingsight-stream_processor"

python -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
sudo pip install -U yt-dlp

python src/stream_watcher.py
