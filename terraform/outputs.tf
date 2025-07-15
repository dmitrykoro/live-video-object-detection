output "django_public_dns" {
  value = aws_instance.ec2_webserver.public_dns
}

output "rabbitmq_public_dns" {
  value = aws_instance.ec2_rabbitmq.public_dns
}

data "aws_instances" "asg_instances" {
  filter {
    name   = "tag:Name"
    values = ["stream-parser"]
  }
}

data "aws_instance" "each_instance" {
  for_each    = toset(data.aws_instances.asg_instances.ids)
  instance_id = each.value
}

output "stream_parser_public_dns" {
  value = [for i in data.aws_instance.each_instance : i.public_dns]
}

output "rds_endpoint" {
  value = aws_db_instance.wingsight_db.endpoint
}

output "bird_alerts_topic_arn" {
  value = aws_sns_topic.bird_alerts.arn
}

output "amplify_app_id" {
  value = aws_amplify_app.amplify_app.id
}

output "amplify_app_default_url" {
  value = "https://${var.repo_branch_name}.${aws_amplify_app.amplify_app.id}.amplifyapp.com"
  description = "Default URL of the deployed Amplify app"
}

# Cognito outputs
output "cognito_user_pool_id" {
  value = aws_cognito_user_pool.user_pool.id
  description = "ID of the Cognito User Pool"
}

output "cognito_user_pool_client_id" {
  value = aws_cognito_user_pool_client.user_pool_client.id
  description = "ID of the Cognito User Pool Client"
}

output "cognito_identity_pool_id" {
  value = aws_cognito_identity_pool.identity_pool.id
  description = "ID of the Cognito Identity Pool"
}

# Custom domain output (if provided)
output "amplify_app_custom_url" {
  value = var.amplify_domain_name != null ? "https://${var.amplify_domain_name}" : "No custom domain provided"
  description = "Custom domain URL (if configured)"
}
