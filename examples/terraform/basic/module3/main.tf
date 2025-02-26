provider "aws" {
  region = "us-west-2"
  # This is for testing only
  skip_credentials_validation = true
  skip_requesting_account_id = true
  skip_metadata_api_check = true
}

module "s3_bucket" {
  source  = "terraform-aws-modules/s3-bucket/aws"
  version = "3.15.1"

  bucket = "example-s3-bucket-terraform-test"
  

  versioning = {
    enabled = true
  }

  tags = {
    Environment = "test"
    Module      = "s3_bucket"
  }
} 