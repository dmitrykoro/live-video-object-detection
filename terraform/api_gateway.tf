resource "aws_apigatewayv2_api" "django_api" {
  name          = "django-http-api"
  protocol_type = "HTTP"

  cors_configuration {
    allow_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    allow_origins = ["*"]
    allow_headers = ["*"]
  }
}

resource "aws_apigatewayv2_integration" "django_integration" {
  api_id                 = aws_apigatewayv2_api.django_api.id
  integration_type       = "HTTP_PROXY"
  integration_uri        = "http://${aws_instance.ec2_webserver.public_dns}/{proxy}"
  integration_method     = "ANY"
  payload_format_version = "1.0"
}

resource "aws_apigatewayv2_route" "django_route" {
  api_id    = aws_apigatewayv2_api.django_api.id
  route_key = "ANY /{proxy+}"
  target    = "integrations/${aws_apigatewayv2_integration.django_integration.id}"
}

# No integration for OPTIONS method - CORS will be automatically handled by API Gateway
resource "aws_apigatewayv2_route" "django_options_route" {
  api_id    = aws_apigatewayv2_api.django_api.id
  route_key = "OPTIONS /{proxy+}"
}

resource "aws_apigatewayv2_stage" "django_stage" {
  api_id      = aws_apigatewayv2_api.django_api.id
  name        = "$default"
  auto_deploy = true
}

output "django_api_gateway_url" {
  value       = aws_apigatewayv2_api.django_api.api_endpoint
  description = "Use this URL in your Amplify frontend to securely access Django backend"
}
