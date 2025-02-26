generate "backend" {
  path      = "backend.tf"
  if_exists = "overwrite"
  contents  = <<EOF
terraform {
  backend "local" {
    path = "${path_relative_to_include()}/terraform.tfstate"
  }
}
EOF
}

# Generate providers block for all child terragrunt configurations
generate "providers" {
  path      = "providers.tf"
  if_exists = "overwrite"
  contents  = <<EOF
provider "aws" {
  region = "us-west-2"
}
EOF
}
