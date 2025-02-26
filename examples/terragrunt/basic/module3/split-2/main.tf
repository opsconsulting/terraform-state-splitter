# Split 2

variable "vpc_name" {
  description = "Name of the VPC"
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "s3_bucket_name" {
  description = "Name of the S3 bucket"
  type        = string
}

variable "s3_versioning_enabled" {
  description = "Enable versioning for S3 bucket"
  type        = bool
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
}

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "5.19.0"

  name = var.vpc_name
  cidr = var.vpc_cidr

  azs             = ["us-west-2a", "us-west-2b", "us-west-2c"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]

  enable_nat_gateway = true
  single_nat_gateway = true

  tags = var.tags
}

module "s3_bucket" {
  source  = "terraform-aws-modules/s3-bucket/aws"
  version = "3.15.1"

  bucket = var.s3_bucket_name

  versioning = {
    enabled = var.s3_versioning_enabled
  }

  tags = var.tags
} 