include {
  path = find_in_parent_folders()
}

terraform {  
  source = "${path_relative_from_include()}/module1/wrapper"
}

inputs = {
  repository_name = "example-repository"
  repository_lifecycle_policy = jsonencode({
    rules = [
      {
        rulePriority = 1,
        description  = "Keep last 3 images",
        selection = {
          tagStatus     = "any",
          countType     = "imageCountMoreThan",
          countNumber   = 3
        },
        action = {
          type = "expire"
        }
      }
    ]
  })
}

