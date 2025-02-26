provider "aws" {
  region = "us-west-2"
  # This is for testing only
  skip_credentials_validation = true
  skip_requesting_account_id = true
  skip_metadata_api_check = true
}

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "5.19.0"

  name = "example-vpc"
  cidr = "10.0.0.0/16"

  azs             = ["us-west-2a", "us-west-2b", "us-west-2c"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]

  enable_nat_gateway = true
  single_nat_gateway = true

  tags = {
    Environment = "test"
    Module      = "vpc"
  }
}

module "rds_aurora" {
  source  = "terraform-aws-modules/rds-aurora/aws"
  version = "9.12.0"

  name            = "example-aurora-db"
  engine          = "aurora-postgresql"
  engine_version  = "15.4"
  instance_class = "db.t4g.medium"
  instances       = { 1 = {} }

  vpc_id          = module.vpc.vpc_id
  
  # Fix for missing subnet group
  db_subnet_group_name = "db-subnet-group-${module.vpc.vpc_id}"
  create_db_subnet_group = true
  subnets         = module.vpc.private_subnets

  master_username = "postgres"
  master_password = "password"
  
  # Security group configuration
  create_security_group = true

  # For test purposes only
  skip_final_snapshot  = true
  storage_encrypted    = true

  tags = {
    Environment = "test",
    Module      = "rds_aurora"
  }
} 