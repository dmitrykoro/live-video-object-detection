resource "aws_amplify_app" "amplify_app" {
  name        = var.amplify_app_name
  repository  = var.github_repository
  oauth_token = var.github_token
  platform    = "WEB"
  
  # Add IAM service role for backend deployment permissions
  iam_service_role_arn = aws_iam_role.amplify_backend_role.arn

  # Stage 1: Create the app without dependencies on Cognito resources
  build_spec = <<-EOT
    version: 1
    frontend:
      phases:
        preBuild:
          commands:
            - cd src/wingsight-frontend/wingsight
            - npm ci
            - echo "Initial build with placeholder config"
        build:
          commands:
            - npm run build
      artifacts:
        baseDirectory: src/wingsight-frontend/wingsight/dist
        files:
          - '**/*'
      cache:
        paths:
          - node_modules/**/*
  EOT

  # Use API Gateway for secure backend access instead of direct HTTP connection
  custom_rule {
    source = "/v1/<*>"
    status = "200"
    target = "${aws_apigatewayv2_api.django_api.api_endpoint}/<*>"
  }

  environment_variables = {
    VITE_WINGSIGHT_API_URL = "/v1/"  # Use relative URL instead of full domain
    # Use the API Gateway v2 endpoint
    VITE_API_GATEWAY_URL = aws_apigatewayv2_api.django_api.api_endpoint
    VITE_API_POLLY = "https://${aws_api_gateway_rest_api.my_api.id}.execute-api.${var.aws_region}.amazonaws.com/dev/${aws_api_gateway_resource.playaudio.path_part}"
  }

  enable_auto_branch_creation = true

  auto_branch_creation_config {
    enable_auto_build = true
    enable_pull_request_preview = true
  }
}

# Create a new Cognito User Pool instead of trying to reference one that doesn't exist
resource "aws_cognito_user_pool" "user_pool" {
  name = "${var.amplify_app_name}-user-pool"
  
  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]
  
  password_policy {
    minimum_length    = 8
    require_lowercase = true
    require_numbers   = true
    require_symbols   = false
    require_uppercase = true
  }
  
  schema {
    attribute_data_type = "String"
    name                = "email"
    required            = true
    mutable             = true
  }

  # Remove preferred_username since it was causing issues in the frontend
  # If needed later, it can be added back
}

/*
data "aws_cognito_user_pool" "existing_user_pool" {
  user_pool_id = "us-east-1_BGcxu3UE5"  # Changed from 'id' to 'user_pool_id'
}
*/

# Create User Pool Client with generic callback URLs
resource "aws_cognito_user_pool_client" "user_pool_client" {
  name                = "${var.amplify_app_name}-client"
  user_pool_id        = aws_cognito_user_pool.user_pool.id
  
  generate_secret     = false
  refresh_token_validity = 30
  prevent_user_existence_errors = "ENABLED"
  explicit_auth_flows = [
    "ALLOW_USER_SRP_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH",
    "ALLOW_USER_PASSWORD_AUTH"
  ]
  
  # Use generic callback URLs to break the cycle
  # We'll update these in a separate resource after everything is created
  callback_urls       = ["https://example.com", "http://localhost:5173"]
  logout_urls         = ["https://example.com", "http://localhost:5173"]
  
  supported_identity_providers = ["COGNITO"]
}

# Create Identity Pool - KEEP ONLY THIS ONE DEFINITION
resource "aws_cognito_identity_pool" "identity_pool" {
  identity_pool_name               = "${var.amplify_app_name}_identity_pool"
  allow_unauthenticated_identities = true
  
  cognito_identity_providers {
    client_id               = aws_cognito_user_pool_client.user_pool_client.id
    provider_name           = "cognito-idp.${var.aws_region}.amazonaws.com/${aws_cognito_user_pool.user_pool.id}"
    server_side_token_check = false
  }
}

# Create IAM roles for authenticated and unauthenticated users
resource "aws_iam_role" "authenticated" {
  name = "${var.amplify_app_name}-authenticated-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Principal = {
          Federated = "cognito-identity.amazonaws.com"
        },
        Action = "sts:AssumeRoleWithWebIdentity",
        Condition = {
          StringEquals = {
            "cognito-identity.amazonaws.com:aud" = aws_cognito_identity_pool.identity_pool.id
          },
          "ForAnyValue:StringLike" = {
            "cognito-identity.amazonaws.com:amr" = "authenticated"
          }
        }
      }
    ]
  })
}

resource "aws_iam_role" "unauthenticated" {
  name = "${var.amplify_app_name}-unauthenticated-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Principal = {
          Federated = "cognito-identity.amazonaws.com"
        },
        Action = "sts:AssumeRoleWithWebIdentity",
        Condition = {
          StringEquals = {
            "cognito-identity.amazonaws.com:aud" = aws_cognito_identity_pool.identity_pool.id
          },
          "ForAnyValue:StringLike" = {
            "cognito-identity.amazonaws.com:amr" = "unauthenticated"
          }
        }
      }
    ]
  })
}

# Attach basic policies to the roles
resource "aws_iam_role_policy" "authenticated_policy" {
  name = "authenticated_policy"
  role = aws_iam_role.authenticated.id
  
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "cognito-identity:GetCredentialsForIdentity",
          "cognito-sync:*"
        ],
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role_policy" "unauthenticated_policy" {
  name = "unauthenticated_policy"
  role = aws_iam_role.unauthenticated.id
  
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "cognito-identity:GetCredentialsForIdentity"
        ],
        Resource = "*"
      }
    ]
  })
}

# Attach roles to Identity Pool
resource "aws_cognito_identity_pool_roles_attachment" "identity_pool_roles" {
  identity_pool_id = aws_cognito_identity_pool.identity_pool.id
  
  roles = {
    "authenticated"   = aws_iam_role.authenticated.arn
    "unauthenticated" = aws_iam_role.unauthenticated.arn
  }
}

# Stage 2: Create branch with proper environment variables
resource "aws_amplify_branch" "amplify_branch" {
  app_id      = aws_amplify_app.amplify_app.id
  branch_name = var.repo_branch_name
  
  enable_auto_build = true
  
  framework = "React"
  stage     = "PRODUCTION"
  
  # Add ALL environment variables needed for both frontend and backend auth
  # These must match exactly what amplify/auth/resource.ts expects
  environment_variables = {
    # Frontend environment variables with VITE_ prefix
    VITE_USER_POOL_ID = aws_cognito_user_pool.user_pool.id
    VITE_USER_POOL_CLIENT_ID = aws_cognito_user_pool_client.user_pool_client.id
    VITE_IDENTITY_POOL_ID = aws_cognito_identity_pool.identity_pool.id
    VITE_AWS_REGION = var.aws_region
    VITE_WINGSIGHT_API_URL = "/v1/"  # Use relative URL to work with the proxy
    # Use API Gateway URL for secure HTTPS API access
    VITE_API_GATEWAY_URL = aws_apigatewayv2_api.django_api.api_endpoint
    # No longer need these flags with API Gateway in place
    # VITE_ALLOW_MIXED_CONTENT = "true"
    # VITE_FORCE_HTTP_API = "true"
    VITE_USE_API_PROXY = "false"  # Using API Gateway instead of Amplify's built-in proxy
    
    # Backend environment variables without prefix (for Amplify Gen 2)
    USER_POOL_ID = aws_cognito_user_pool.user_pool.id
    USER_POOL_CLIENT_ID = aws_cognito_user_pool_client.user_pool_client.id
    IDENTITY_POOL_ID = aws_cognito_identity_pool.identity_pool.id
    AUTH_ROLE_ARN = aws_iam_role.authenticated.arn
    UNAUTH_ROLE_ARN = aws_iam_role.unauthenticated.arn
    REGION = var.aws_region  # Changed from AWS_REGION to REGION
  }
  
  depends_on = [
    aws_amplify_app.amplify_app,
    aws_cognito_user_pool.user_pool,
    aws_cognito_user_pool_client.user_pool_client,
    aws_cognito_identity_pool.identity_pool,
    aws_iam_role.authenticated,
    aws_iam_role.unauthenticated
  ]
}

# Replace problematic null_resource with webhook-based approach
# Do not use local-exec with aws CLI commands anymore
resource "aws_amplify_webhook" "auto_build" {
  app_id      = aws_amplify_app.amplify_app.id
  branch_name = aws_amplify_branch.amplify_branch.branch_name
  description = "Auto deployment webhook for ${var.repo_branch_name} branch"

  depends_on = [
    aws_amplify_branch.amplify_branch
  ]
}

# Output the webhook URL to use for triggering builds
output "amplify_webhook_url" {
  value       = aws_amplify_webhook.auto_build.url
  description = "Webhook URL to trigger Amplify builds (run this in browser to start a build)"
  sensitive   = false
}

# Optional: Set up custom domain if specified
resource "aws_amplify_domain_association" "domain_association" {
  count       = var.amplify_domain_name != null ? 1 : 0
  app_id      = aws_amplify_app.amplify_app.id
  domain_name = var.amplify_domain_name

  sub_domain {
    branch_name = aws_amplify_branch.amplify_branch.branch_name
    prefix      = ""
  }
}

# The webhook for auto deployment is already defined above
# Removing this duplicate resource
/*
# Set up webhook for auto deployment
resource "aws_amplify_webhook" "example" {
  app_id      = aws_amplify_app.amplify_app.id
  branch_name = aws_amplify_branch.amplify_branch.branch_name
  description = "Auto deployment webhook"
}
*/