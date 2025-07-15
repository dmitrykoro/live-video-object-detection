resource "aws_security_group" "ec2_rabbitmq_sg" {
  name        = "ec2_rabbitmq_sg"
  description = "Allow RabbitMQ traffic"
  vpc_id      = aws_vpc.wingsight_vpc.id

  ingress {
    from_port       = 5672
    to_port         = 5672
    protocol        = "tcp"
    security_groups = [aws_security_group.ec2_django_sg.id, aws_security_group.ec2_stream_parser_sg.id]
  }

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

resource "aws_instance" "ec2_rabbitmq" {
  ami                         = data.aws_ami.ubuntu_22_04.id
  instance_type               = var.instance_type
  subnet_id                   = aws_subnet.public_subnet.id
  vpc_security_group_ids      = [aws_security_group.ec2_rabbitmq_sg.id]
  associate_public_ip_address = true
  key_name                    = var.key_name

  user_data = templatefile("installation_scripts/deploy_rabbitmq.tpl", {
    rabbitmq_user = var.rabbitmq_user
    rabbitmq_password = var.rabbitmq_password
  })

  tags = {
    Name = "rabbitmq-server"
  }
}