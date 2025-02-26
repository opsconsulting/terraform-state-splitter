include {
  path = find_in_parent_folders()
}

terraform {
  source = "${path_relative_from_include()}/module3/split-2"
}

inputs = {
  vpc_name = "custom-vpc-name"
  vpc_cidr = "10.0.0.0/16"
  environment = "production"
  
  s3_bucket_name = "custom-s3-bucket-name"
  s3_versioning_enabled = true
  
  tags = {
    Environment = "production"
    Project     = "example-project"
    Owner       = "terraform-team"
  }
}
