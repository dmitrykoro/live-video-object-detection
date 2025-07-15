# IAM Role for EC2 with combined permissions (Rekognition and SNS)
resource "aws_iam_role" "ec2_combined_role" {
  name = "ec2-combined-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = "sts:AssumeRole",
        Effect = "Allow",
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "WingSight EC2 Combined Role"
  }
}

# IAM Policy for Rekognition access
resource "aws_iam_policy" "rekognition_access" {
  name        = "rekognition-access-policy"
  description = "Policy for accessing AWS Rekognition services"
  
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = [
          "rekognition:DetectLabels",
          "rekognition:DetectText"
        ],
        Effect = "Allow",
        Resource = "*"
      }
    ]
  })
}

# IAM Policy attachment with permissions to put and get from S3
resource "aws_iam_role_policy" "thumbnails_s3_access" {
  name = "thumbnails-s3-access"
  role = aws_iam_role.ec2_combined_role.name

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "s3:PutObject",
          "s3:GetObject"
        ],
        Resource = "arn:aws:s3:::${var.img_bucket_name}/thumbnails/*"
      }
    ]
  })
}

# IAM Policy for SNS permissions
resource "aws_iam_policy" "sns_policy" {
  name        = "sns-publish-subscribe-policy"
  description = "Policy allowing publish and subscribe to SNS topics"
  
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = [
           "sns:Publish",
          "sns:Subscribe",
          "sns:CreateTopic",
          "sns:DeleteTopic",
          "sns:ListTopics",
          "sns:ListSubscriptionsByTopic",
          "sns:GetTopicAttributes",
          "sns:SetTopicAttributes"
        ],
        Effect   = "Allow",
        Resource = [aws_sns_topic.bird_alerts.arn,  
                   "arn:aws:sns:${var.aws_region}:*:wingsight-user-*"]
      }
    ]
  })
}

# Attach Rekognition policy to the combined role
resource "aws_iam_role_policy_attachment" "rekognition_attach" {
  role       = aws_iam_role.ec2_combined_role.name
  policy_arn = aws_iam_policy.rekognition_access.arn
}

# Attach SNS policy to the combined role
resource "aws_iam_role_policy_attachment" "sns_policy_attachment" {
  role       = aws_iam_role.ec2_combined_role.name
  policy_arn = aws_iam_policy.sns_policy.arn
}

# Create a combined instance profile for the EC2 instance
resource "aws_iam_instance_profile" "ec2_combined_profile" {
  name = "ec2-combined-profile"
  role = aws_iam_role.ec2_combined_role.name
}
