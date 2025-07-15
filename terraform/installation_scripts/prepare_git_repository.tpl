#!/bin/bash

sudo yum update -y
sudo yum install -y mysql-devel
sudo yum install -y git
sudo yum install -y pip
sudo yum install -y python3.12
sudo yum install -y mariadb105
sudo yum install -y mesa-libGL
sudo alternatives --install /usr/bin/python python /usr/bin/python3.12 1

GITHUB_USERNAME="${github_username}"
GITHUB_TOKEN="${github_token}"
REPO_URL="https://$GITHUB_USERNAME:$GITHUB_TOKEN@github.com/dmitrykoro/live-video-object-detection.git"

cd /home/ec2-user

git clone "$REPO_URL"
cd live-video-object-detection/
