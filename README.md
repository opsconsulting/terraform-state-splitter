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
- Interactive UI mode for selecting modules and configuring target prefixes
- Ability to rename module prefixes during the migration (e.g., from `module.vpc.module.vpc` to just `module.vpc`)
- Dry-run mode to preview changes without applying them
- Preserves state lineage and version information
- Handles duplicate resources gracefully
- Verbose logging for detailed operation information

## Installation

No installation is required. Simply clone this repository and run the Python script.

```bash
git clone https://github.com/opsconsulting/terraform-state-splitter.git
cd terraform-state-splitter
```

### Requirements

- Python 3.6+
- Terraform or Terragrunt installed and in your PATH
- For interactive mode: `inquirer` and `rich` Python packages
  ```bash
  pip install inquirer rich
  ```

## Usage

### Standard Mode

```bash
python state_splitter.py --source <source_module_directory> --split <module_name>=<target_directory> [--split <module_name>=<target_directory> ...] [options]
```

### Interactive Mode

```bash
python state_splitter.py --source <source_module_directory> --interactive [options]
```

### Arguments

- `--source`: Directory containing the Terraform or Terragrunt module with the source state
- `--split`: Module mapping in format `module=target_dir` (can be specified multiple times)
- `--interactive`: Use interactive UI mode to select modules and configure target prefixes
- `--dry-run`: Perform a dry run without making changes
- `--verbose`: Enable verbose logging
- `--use-terragrunt`: Force using Terragrunt instead of auto-detection

### Example

```bash
# Standard mode: Move resources from the "networking" module in source to the target directory
python state_splitter.py --source ./main-infrastructure --split networking=./networking-module

# Move multiple modules at once
python state_splitter.py --source ./monolith --split networking=./networking --split database=./database --split compute=./compute

# Perform a dry run to preview changes
python state_splitter.py --source ./monolith --split database=./database --dry-run

# Use interactive mode to select modules and configure target prefixes
python state_splitter.py --source ./monolith --interactive
```

## Interactive Mode

The interactive mode provides a user-friendly interface for:

1. Viewing all available modules in the source state
2. Selecting which modules to split
3. Specifying target directories for each module
4. Customizing module prefixes in the target state (e.g., simplifying nested module paths)
5. Summarizing planned changes before execution

Interactive mode requires additional Python packages:
```bash
pip install inquirer rich
```

## How It Works

1. Pulls the state from the source module
2. Identifies resources belonging to the specified module(s)
3. Pulls the state from the target module(s)
4. Optionally renames module prefixes according to your configuration
5. Adds the identified resources to the target state(s)
6. Removes the resources from the source state
7. Pushes the updated states back to their respective modules

## Handling Module Prefixes

When splitting states, you can change how modules are referenced in the target state:

- In interactive mode, you'll be prompted to specify the target prefix for each module
- This allows you to simplify nested module structures (e.g., from `module.networking.module.vpc` to just `module.vpc`)
- The original resources are preserved in the source state until successfully moved

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


