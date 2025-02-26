# Terraform State Splitter Examples

This directory contains example configurations to demonstrate how to use the Terraform State Splitter. 
These examples will help you understand the workflow for splitting Terraform or Terragrunt states.

## Directory Structure

```
examples/
├── terraform/     # Examples for Terraform
│   └── basic/     # Basic Terraform example with multiple modules
│       ├── module1/
│       ├── module2/
│       └── module3/
└── terragrunt/    # Examples for Terragrunt
    └── basic/     # Basic Terragrunt example with multiple modules
        ├── module1/
        ├── module2/
        ├── module3/
        └── terragrunt.hcl
```

> **Note:** Although the directory structure uses names like module1, module2, and module3, the actual module names in the state file are "vpc", "s3_bucket", and "ecr" as they use AWS community modules.

## Terraform Example

The Terraform example demonstrates how to split a state file across multiple modules.

### Setup

1. Initialize and apply the source module:

```bash
cd examples/terraform/basic/module1
terraform init
terraform apply
```

2. This will create a state with resources that we want to split into separate modules.

### Splitting the State

Use the Terraform State Splitter to move resources from module1 to module2 and module3:

```bash
# From the repository root
python state_splitter.py --source examples/terraform/basic/module1 --split vpc=examples/terraform/basic/module2 --split s3_bucket=examples/terraform/basic/module3
```

To run a dry run first:

```bash
python state_splitter.py --source examples/terraform/basic/module1 --split vpc=examples/terraform/basic/module2 --split s3_bucket=examples/terraform/basic/module3 --dry-run
```

### Verification

After running the state splitter, verify that the resources have been moved correctly:

```bash
# Check module2 state (contains vpc resources)
cd examples/terraform/basic/module2
terraform state list

# Check module3 state (contains s3_bucket resources)
cd examples/terraform/basic/module3
terraform state list

# Check remaining resources in module1 (should still have ecr resources)
cd examples/terraform/basic/module1
terraform state list
```

## Terragrunt Example

The Terragrunt example demonstrates the same state splitting process but within a Terragrunt configuration.

### Setup

1. Initialize and apply the source module:

```bash
cd examples/terragrunt/basic/module1
terragrunt init
terragrunt apply
```

2. This will create a state with resources that we want to split into separate modules.

### Splitting the State

Use the Terraform State Splitter with the `--use-terragrunt` flag:

```bash
# From the repository root
python state_splitter.py --source examples/terragrunt/basic/module1 --split vpc=examples/terragrunt/basic/module2 --split s3_bucket=examples/terragrunt/basic/module3 --use-terragrunt
```

To run a dry run first:

```bash
python state_splitter.py --source examples/terragrunt/basic/module1 --split vpc=examples/terragrunt/basic/module2 --split s3_bucket=examples/terragrunt/basic/module3 --use-terragrunt --dry-run
```

### Verification

After running the state splitter, verify that the resources have been moved correctly:

```bash
# Check module2 state (contains vpc resources)
cd examples/terragrunt/basic/module2
terragrunt state list

# Check module3 state (contains s3_bucket resources)
cd examples/terragrunt/basic/module3
terragrunt state list

# Check remaining resources in module1 (should still have ecr resources)
cd examples/terragrunt/basic/module1
terragrunt state list
```

## Tips for Using the Examples

1. These examples are simplified to demonstrate the core functionality
2. In a real-world scenario, your module structure would be more complex
3. Always run with `--dry-run` first to validate the expected changes
4. The example modules have minimal resource definitions for demonstration purposes
5. You may need to modify the examples to match your specific infrastructure setup
6. Remember to use `python state_splitter.py` rather than just `./state_splitter.py` when running the script

## Next Steps

After understanding how to use the examples, you can apply the same techniques to your own Terraform or Terragrunt configurations. Start with small, controlled moves and gradually refactor your infrastructure as needed. 