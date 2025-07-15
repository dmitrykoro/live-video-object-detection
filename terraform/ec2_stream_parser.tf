resource "aws_security_group" "ec2_stream_parser_sg" {
  name        = "ec2_stream_parser_sg"
  description = "Allow stream parser traffic"
  vpc_id      = aws_vpc.wingsight_vpc.id

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"] # Allow SSH from anywhere (modify for security)
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_launch_template" "ec2_stream_parser" {
  depends_on = [aws_db_instance.wingsight_db, aws_instance.ec2_rabbitmq]
  image_id      = data.aws_ami.amazon_linux_2023.id
  instance_type = var.instance_type
  vpc_security_group_ids = [aws_security_group.ec2_stream_parser_sg.id]
  key_name      = var.key_name
  iam_instance_profile {
    name = aws_iam_instance_profile.ec2_combined_profile.name
  }
  # for SNS, Rekognition and S3 thumbnails

  user_data = base64encode(join("\n", [
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
    templatefile("installation_scripts/deploy_stream_watcher.tpl", {})
  ]
  ))

  tags = {
    Name = "stream-parser"
  }
}

resource "aws_autoscaling_group" "stream_parser_asg" {
  desired_capacity = 1
  max_size         = 3
  min_size         = 1
  vpc_zone_identifier = [aws_subnet.public_subnet.id]

  launch_template {
    id      = aws_launch_template.ec2_stream_parser.id
    version = "$Latest"
  }

  tag {
    key                 = "Name"
    value               = "stream-parser"
    propagate_at_launch = true
  }

  health_check_type         = "EC2"
  health_check_grace_period = 300
}

resource "aws_autoscaling_policy" "scale_out" {
  name                   = "scale-out-stream-parser"
  scaling_adjustment     = 1
  adjustment_type        = "ChangeInCapacity"
  cooldown               = 300
  autoscaling_group_name = aws_autoscaling_group.stream_parser_asg.name
}


resource "aws_cloudwatch_metric_alarm" "high_cpu_alarm" {
  alarm_name          = "HighCPUStreamParser"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = 60
  statistic           = "Average"
  threshold           = 70
  alarm_description   = "This metric monitors high CPU usage"
  dimensions = {
    AutoScalingGroupName = aws_autoscaling_group.stream_parser_asg.name
  }

  alarm_actions = [aws_autoscaling_policy.scale_out.arn]
}
