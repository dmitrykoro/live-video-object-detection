variable "instance_type" {
  description = "The type of EC2 instance to launch"
  default     = "t2.micro"  # Default to t2.micro (can be overridden)
}

variable "key_name" {
  description = "The key pair name for SSH access"
  type        = string
}

variable "db_allocated_storage" {
  type    = number
  default = 20
}

variable "db_username" {
  type      = string
  sensitive = true
}

variable "db_password" {
  type      = string
  sensitive = true
}

variable "db_name" {
  type = string
  default = "wingsight_db"
}

variable "github_username" {
  type = string
}

variable "github_token" {
  type = string
  sensitive = true
}

variable "aws_region" {
  type    = string
  default = "us-east-1"
  description = "AWS region for resources"
}

variable "img_bucket_name" {
  type = string
}

variable "rabbitmq_user" {
  type = string
  sensitive = true
}

variable "rabbitmq_password" {
  type = string
  sensitive = true
}

variable "github_repository" {
  description = "GitHub repository for the frontend"
  type        = string
  default     = "https://github.com/SWEN-614-Spring-2025/term-project-team2-the-tweet-team.git"
}

variable "repo_branch_name" {
  description = "Branch name for the frontend deployment"
  type        = string
}

variable "amplify_app_name" {
  description = "Name of the Amplify app"
  type        = string
  default     = "WingSight"
}

variable "amplify_domain_name" {
  description = "Custom domain name for the Amplify app (optional)"
  type        = string
  default     = null
}