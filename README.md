# Terraform State Splitter

A tool for splitting large Terraform states into smaller, more manageable states by moving resources between modules.

## Overview

Terraform State Splitter helps you refactor your Terraform or Terragrunt configuration by moving resources from one state file to another. This is particularly useful when:

- Breaking down a monolithic Terraform configuration into smaller modules
- Rearchitecting your infrastructure code
- Migrating resources between states
- Implementing infrastructure as code best practices

## Features

- Supports both Terraform and Terragrunt
- Automatically detects whether to use Terraform or Terragrunt based on configuration files
- Dry-run mode to preview changes without applying them
- Preserves state lineage and version information
- Handles duplicate resources gracefully
- Verbose logging for detailed operation information

## Installation

No installation is required. Simply clone this repository and run the Python script.

```bash
git clone https://github.com/yourusername/TerraformSplitter.git
cd TerraformSplitter
```

### Requirements

- Python 3.6+
- Terraform or Terragrunt installed and in your PATH

## Usage

```bash
./state_splitter.py --source <source_module_directory> --split <module_name>=<target_directory> [--split <module_name>=<target_directory> ...] [options]
```

### Arguments

- `--source`: Directory containing the Terraform or Terragrunt module with the source state
- `--split`: Module mapping in format `module=target_dir` (can be specified multiple times)
- `--dry-run`: Perform a dry run without making changes
- `--verbose`: Enable verbose logging
- `--use-terragrunt`: Force using Terragrunt instead of auto-detection

### Example

```bash
# Move resources from the "networking" module in source to the target directory
./state_splitter.py --source ./main-infrastructure --split networking=./networking-module

# Move multiple modules at once
./state_splitter.py --source ./monolith --split networking=./networking --split database=./database --split compute=./compute

# Perform a dry run to preview changes
./state_splitter.py --source ./monolith --split database=./database --dry-run
```

## How It Works

1. Pulls the state from the source module
2. Identifies resources belonging to the specified module(s)
3. Pulls the state from the target module(s)
4. Adds the identified resources to the target state(s)
5. Removes the resources from the source state
6. Pushes the updated states back to their respective modules

## Examples

The `examples` directory contains sample configurations for both Terraform and Terragrunt. Check out the [examples README](examples/README.md) for detailed instructions on how to use these examples to learn about state splitting.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Disclaimer

Always backup your state files before using this tool. While care has been taken to ensure safe operation, manipulating Terraform state can be risky.


