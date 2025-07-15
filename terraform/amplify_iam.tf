# IAM Role for Amplify to deploy the backend
resource "aws_iam_role" "amplify_backend_role" {
  name = "${var.amplify_app_name}-amplify-backend-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Principal = {
          Service = "amplify.amazonaws.com"
        },
        Action = "sts:AssumeRole"
      }
    ]
  })
}

# Policy to allow Amplify to create and manage Cognito and SSM resources
resource "aws_iam_role_policy" "amplify_backend_policy" {
  name = "amplify-backend-policy"
  role = aws_iam_role.amplify_backend_role.id
  
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "cognito-idp:*",
          "cognito-identity:*",
          "iam:PassRole",
          "iam:GetRole",
          "iam:CreateServiceLinkedRole",
          "iam:ListRoles",
          "iam:UpdateAssumeRolePolicy",
          # Add SSM permissions needed for CDK
          "ssm:GetParameter",
          "ssm:GetParameters",
          "ssm:PutParameter",
          "ssm:DeleteParameter",
          "ssm:ListParameters",
          # CloudFormation permissions for CDK
          "cloudformation:*",
          # S3 permissions 
          "s3:*",
          # ECR permissions
          "ecr:*",
          # Lambda permissions
          "lambda:*"
        ],
        Resource = "*"
      }
    ]
  })
}

# Create a new policy for CDK Bootstrap permissions
resource "aws_iam_role_policy" "amplify_cdk_bootstrap_policy" {
  name = "amplify-cdk-bootstrap-policy"
  role = aws_iam_role.amplify_backend_role.id
  
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          # Specific SSM parameter access for CDK bootstrap
          "ssm:GetParameter",
          "ssm:GetParameters",
          "ssm:PutParameter"
        ],
        Resource = "arn:aws:ssm:${var.aws_region}:*:parameter/cdk-bootstrap/*"
      },
      {
        Effect = "Allow",
        Action = "sts:AssumeRole",
        Resource = "arn:aws:iam::*:role/cdk-*"
      }
    ]
  })
}