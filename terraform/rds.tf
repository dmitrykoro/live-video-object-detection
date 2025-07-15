# RDS Database
# Set up a MySQL RDS instance for WingSight.

# RDS Instance
resource "aws_db_instance" "wingsight_db" {
  identifier             = "wingsight-db"                                     # Unique identifier for the RDS instance
  allocated_storage      = var.db_allocated_storage
  storage_type           = "gp2"                                              # General Purpose SSD
  engine                 = "mysql"                                            # MySQL database engine
  engine_version         = "8.0"                                              # MySQL version 8.0
  instance_class         = "db.t3.micro"                                      # Free tier eligible instance type
  db_name                = var.db_name                                        # Name of the database
  username               = var.db_username                                    # Database admin username
  password               = var.db_password                                    # Replace with a secure password
  parameter_group_name   = "default.mysql8.0"                                 # Default parameter group for MySQL 8.0
  skip_final_snapshot    = true                                               # Skip final snapshot when destroying the database
  vpc_security_group_ids = [aws_security_group.rds_sg.id]                     # Attach the RDS security group
  db_subnet_group_name   = aws_db_subnet_group.wingsight_db_subnet_group.name # Use the created subnet group
}


# RDS Security Group
resource "aws_security_group" "rds_sg" {
  name        = "wingsight_rds_sg"
  description = "Security group for WingSight RDS instance"
  vpc_id      = aws_vpc.wingsight_vpc.id

  ingress {
    from_port       = 3306
    to_port         = 3306
    protocol        = "tcp"
    security_groups = [
      aws_security_group.ec2_django_sg.id,
      aws_security_group.ec2_stream_parser_sg.id
    ] # allow from django and stream parser
  }
}
