# AWS Provider Configuration
provider "aws" {
  region = "us-east-1"  # Set your AWS region
}

# Security Group
resource "aws_security_group" "ec2_django_sg" {
  name        = "Allow Django HTTP and SSH"
  description = "Security group for Web Server EC2 instance"
  vpc_id      = aws_vpc.wingsight_vpc.id

  # Inbound rules (allow SSH and HTTP)
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"] # Allow SSH from anywhere (modify for security)
  }

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"] # Allow HTTP from anywhere
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"] # Allow HTTPS
  }

  ingress {
    from_port   = 5000
    to_port     = 5000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"] # Allow API access from anywhere
  }

  # Outbound rules (allow all outbound traffic)
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "EC2-Django-SecurityGroup"
  }
}

# EC2 Django web server
resource "aws_instance" "ec2_webserver" {
  depends_on = [aws_db_instance.wingsight_db, aws_instance.ec2_rabbitmq]
  ami           = data.aws_ami.amazon_linux_2023.id
  instance_type = var.instance_type
  subnet_id     = aws_subnet.public_subnet.id
  key_name      = var.key_name
  vpc_security_group_ids = [aws_security_group.ec2_django_sg.id]
  iam_instance_profile = aws_iam_instance_profile.ec2_combined_profile.name

  user_data = join("\n", [
    templatefile("installation_scripts/prepare_git_repository.tpl", {
      github_username = var.github_username
      github_token    = var.github_token
    }),
    templatefile("installation_scripts/prepare_env_file.tpl", {
      db_name           = var.db_name
      db_username       = var.db_username
      db_password       = var.db_password
      db_host           = aws_db_instance.wingsight_db.address
      sns_topic_arn     = aws_sns_topic.bird_alerts.arn
      aws_region        = var.aws_region
      rabbitmq_host     = aws_instance.ec2_rabbitmq.public_dns
      rabbitmq_user     = var.rabbitmq_user
      rabbitmq_password = var.rabbitmq_password
      img_bucket_name   = var.img_bucket_name

      user_pool_id      = aws_cognito_user_pool.user_pool.id
      app_client_id     = aws_cognito_user_pool_client.user_pool_client.id

    }),
    templatefile("installation_scripts/deploy_django_server.tpl", {
      amplify_app_id = var.amplify_app_name
      repo_branch_name = var.repo_branch_name
    })
  ]
  )

  tags = {
    Name = "django-server"
  }
}
