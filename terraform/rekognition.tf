# AWS Rekognition resources for bird detection
# Replacing previous SageMaker resources with Rekognition

# Output information about the Rekognition service
output "rekognition_info" {
  value = "AWS Rekognition will be used for bird detection and classification"
  description = "Information about AWS Rekognition usage"
}

# Add a local-exec provisioner to the EC2 instance to output the service info
resource "null_resource" "rekognition_info" {
  depends_on = [aws_instance.ec2_webserver]

  provisioner "local-exec" {
    command = "echo 'Bird detection will be available at: http://${aws_instance.ec2_webserver.public_dns}/api/bird-recognition after deployment'"
  }
}

# Note: Unlike SageMaker, Rekognition doesn't require endpoint deployment.
# It's a fully managed service that's ready to use with proper IAM permissions.
