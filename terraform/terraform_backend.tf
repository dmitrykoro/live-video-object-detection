terraform {
  backend "s3" {
    bucket = "bucket_name_here"
    key = "terraform.tfstate"
    region = "us-east-1"
  }
}

# confirming existence of img_bucket
data "aws_s3_bucket" "img_bucket" {
  bucket = var.img_bucket_name
}
