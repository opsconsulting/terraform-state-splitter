#!/usr/bin/env python3
import json
import subprocess
import os
import argparse
import logging
import sys
import glob
import re
from collections import defaultdict

# Add imports for interactive UI
try:
    import inquirer
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import Progress
    from rich.tree import Tree
    from rich import print as rprint
except ImportError:
    print("Interactive mode requires additional packages. Please install them with:")
    print("pip install inquirer rich")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def parse_args():
    parser = argparse.ArgumentParser(description='Split Terraform/Terragrunt state by moving resources between modules')
    parser.add_argument('--source', required=True, help='Source module directory')
    parser.add_argument('--split', action='append', help='Module split mapping in format module=target_dir')
    parser.add_argument('--dry-run', action='store_true', help='Perform a dry run without making changes')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    parser.add_argument('--use-terragrunt', action='store_true', help='Use terragrunt instead of terraform')
    parser.add_argument('--interactive', action='store_true', help='Use interactive mode to select modules and set target prefixes')
    
    args = parser.parse_args()
    
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    return args

def detect_tool(module_dir, force_terragrunt=False):
    """Detect whether to use terraform or terragrunt"""
    if force_terragrunt:
        logger.debug("Forced to use terragrunt")
        return "terragrunt"
    
    # Check if terragrunt.hcl exists in the directory
    if glob.glob(os.path.join(module_dir, "*.hcl")):
        logger.debug(f"Detected terragrunt.hcl in {module_dir}, using terragrunt")
        return "terragrunt"
    
    logger.debug(f"No terragrunt.hcl found in {module_dir}, using terraform")
    return "terraform"

def pull_state(module_dir, use_terragrunt=False):
    """Pull Terraform/Terragrunt state from a module directory"""
    try:
        original_dir = os.getcwd()
        os.chdir(module_dir)
        
        tool = detect_tool(module_dir, force_terragrunt=use_terragrunt)
        
        logger.debug(f"Pulling state from {module_dir} using {tool}")
        result = subprocess.run(
            [tool, 'state', 'pull'], 
            capture_output=True, 
            text=True,
            check=True
        )
        
        state = json.loads(result.stdout)
        logger.debug(f"Successfully pulled state from {module_dir}")
        return state
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to pull state from {module_dir}: {e.stderr}")
        raise
    finally:
        os.chdir(original_dir)

def push_state(module_dir, state, force_serial=None, use_terragrunt=False):
    """Push Terraform/Terragrunt state to a module directory"""
    try:
        original_dir = os.getcwd()
        os.chdir(module_dir)
        
        tool = detect_tool(module_dir, force_terragrunt=use_terragrunt)
        
        # Use specified serial number or increment the existing one
        if force_serial is not None:
            state['serial'] = force_serial
        else:
            state['serial'] = state.get('serial', 0) + 1
            
        logger.debug(f"Pushing state to {module_dir} with serial {state['serial']} using {tool}")
        
        result = subprocess.run(
            [tool, 'state', 'push', '-'],
            input=json.dumps(state),
            capture_output=True,
            text=True,
            check=True
        )
        
        logger.debug(f"Successfully pushed state to {module_dir}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to push state to {module_dir}: {e.stderr}")
        raise
    finally:
        os.chdir(original_dir)

def find_module_resources(state, module_name):
    """Find all resources belonging to a particular module"""
    resources = []
    
    if not state or 'resources' not in state:
        return resources
    
    for resource in state.get('resources', []):
        # Check if the resource belongs to the specified module
        if resource.get('module', '').startswith(f"module.{module_name}"):
            resources.append(resource)
            
    return resources

def get_resource_identifier(resource):
    """Get a unique identifier for a resource"""
    mode = resource.get('mode', '')
    module = resource.get('module', '')
    type = resource.get('type', '')
    name = resource.get('name', '')
    
    return f"{module}.{mode}.{type}.{name}"

def remove_resources_from_state(state, resource_ids):
    """Remove resources from state by their identifiers"""
    if not state or 'resources' not in state:
        return state
    
    remaining_resources = []
    
    for resource in state.get('resources', []):
        resource_id = get_resource_identifier(resource)
        if resource_id not in resource_ids:
            remaining_resources.append(resource)
    
    state['resources'] = remaining_resources
    return state

def add_resources_to_state(state, resources_to_add, source_prefix=None, target_prefix=None):
    """Add resources to state, avoiding duplicates and optionally changing module prefix"""
    if not state:
        state = {"version": 4, "terraform_version": "1.0.0", "serial": 0, "lineage": "", "resources": []}
        
    if 'resources' not in state:
        state['resources'] = []
        
    existing_resources = set()
    
    # Track existing resources to avoid duplicates
    for resource in state['resources']:
        resource_id = get_resource_identifier(resource)
        existing_resources.add(resource_id)
    
    # Add new resources, skipping duplicates
    for resource in resources_to_add:
        # If prefix replacement is requested, update the module path
        if source_prefix and target_prefix and resource.get('module', '').startswith(source_prefix):
            resource['module'] = resource['module'].replace(source_prefix, target_prefix, 1)
            
        resource_id = get_resource_identifier(resource)
        
        if resource_id not in existing_resources:
            state['resources'].append(resource)
            logger.debug(f"Adding resource: {resource_id}")
            existing_resources.add(resource_id)
        else:
            logger.warning(f"Skipping duplicate resource: {resource_id}")
    
    return state

def identify_modules(state):
    """Identify all modules in the state file"""
    modules = set()
    module_resources = defaultdict(list)
    
    if not state or 'resources' not in state:
        return modules, module_resources
    
    # Regular expression to match module patterns
    module_pattern = re.compile(r'^module\.([^\.]+)')
    
    for resource in state.get('resources', []):
        module_path = resource.get('module', '')
        
        if module_path:
            # Find all module references in the path
            match = module_pattern.search(module_path)
            if match:
                module_name = match.group(1)
                modules.add(module_name)
                module_resources[module_name].append(resource)
    
    return modules, module_resources

def interactive_select_modules(source_dir, use_terragrunt=False):
    """Interactive UI for selecting modules and specifying target prefixes and directories"""
    console = Console()
    
    console.print(Panel("[bold cyan]Terraform State Splitter - Interactive Mode[/bold cyan]", 
                       subtitle="Select modules to split and specify target configurations"))
    
    with Progress(transient=True) as progress:
        task = progress.add_task("[green]Pulling state from source module...", total=1)
        source_state = pull_state(source_dir, use_terragrunt)
        progress.update(task, completed=1)
    
    modules, module_resources = identify_modules(source_state)
    
    if not modules:
        console.print("[yellow]No modules found in the source state.[/yellow]")
        return {}
    
    # Create module tree for display
    module_tree = Tree("[bold]Available Modules[/bold]")
    for module in sorted(modules):
        resource_count = len(module_resources[module])
        module_tree.add(f"[green]module.{module}[/green] [dim]({resource_count} resources)[/dim]")
    
    console.print(module_tree)
    console.print()
    
    # Let user select modules to split
    module_selections = []
    continue_selecting = True
    
    while continue_selecting:
        # Select which module to split
        module_choices = [
            inquirer.List('module',
                        message="Select a module to split",
                        choices=sorted(modules),
                        carousel=True)
        ]
        
        module_answers = inquirer.prompt(module_choices)
        if not module_answers:
            break  # User pressed Ctrl+C
            
        selected_module = module_answers['module']
        
        # Ask for target directory
        target_dir_question = [
            inquirer.Text('target_dir',
                        message=f"Enter target directory for module.{selected_module}")
        ]
        
        target_dir_answer = inquirer.prompt(target_dir_question)
        if not target_dir_answer:
            break  # User pressed Ctrl+C
            
        target_dir = target_dir_answer['target_dir']
        
        # Ask for target prefix
        source_prefix = f"module.{selected_module}"
        target_prefix_question = [
            inquirer.Text('target_prefix',
                         message=f"Enter target prefix for {source_prefix} (leave empty to keep as-is)",
                         default=source_prefix)
        ]
        
        target_prefix_answer = inquirer.prompt(target_prefix_question)
        if not target_prefix_answer:
            break  # User pressed Ctrl+C
            
        target_prefix = target_prefix_answer['target_prefix']
        
        # Add selection to our list
        module_selections.append({
            'module': selected_module,
            'source_prefix': source_prefix,
            'target_prefix': target_prefix,
            'target_dir': target_dir
        })
        
        # Remove selected module from available modules
        modules.remove(selected_module)
        
        if not modules:
            console.print("[yellow]All modules have been selected.[/yellow]")
            break
            
        # Ask if user wants to continue selecting modules
        continue_question = [
            inquirer.Confirm('continue',
                           message="Do you want to select another module to split?",
                           default=True)
        ]
        
        continue_answer = inquirer.prompt(continue_question)
        if not continue_answer or not continue_answer['continue']:
            continue_selecting = False
    
    # Print summary of selections
    if module_selections:
        console.print("\n[bold cyan]Module Split Summary:[/bold cyan]")
        for selection in module_selections:
            if selection['source_prefix'] == selection['target_prefix']:
                console.print(f"  • [green]{selection['source_prefix']}[/green] → [blue]{selection['target_dir']}[/blue]")
            else:
                console.print(f"  • [green]{selection['source_prefix']}[/green] → [yellow]{selection['target_prefix']}[/yellow] in [blue]{selection['target_dir']}[/blue]")
    
    return module_selections

def main():
    args = parse_args()
    
    if args.interactive:
        selections = interactive_select_modules(args.source, args.use_terragrunt)
        if not selections:
            logger.error("No modules selected for splitting.")
            sys.exit(1)
            
        # Convert selections to splits format
        splits = {}
        module_prefixes = {}
        for selection in selections:
            module_name = selection['module']
            splits[module_name] = selection['target_dir']
            
            if selection['source_prefix'] != selection['target_prefix']:
                module_prefixes[module_name] = {
                    'source': selection['source_prefix'],
                    'target': selection['target_prefix']
                }
    else:
        if not args.split:
            logger.error("No split mappings provided. Use --split or --interactive")
            sys.exit(1)
        
        # Parse split mappings
        splits = {}
        for split in args.split:
            parts = split.split('=')
            if len(parts) != 2:
                logger.error(f"Invalid split mapping: {split}")
                sys.exit(1)
            
            module_name, target_dir = parts
            splits[module_name] = target_dir
        
        # No prefix changes in non-interactive mode
        module_prefixes = {}
    
    logger.info(f"Source module: {args.source}")
    logger.info(f"Split mappings: {splits}")
    
    # Pull source state
    source_state = pull_state(args.source, args.use_terragrunt)
    original_serial = source_state.get('serial', 0)
    
    # Track resources to remove from source
    all_resources_to_remove = []
    
    # Process each module and target
    for module_name, target_dir in splits.items():
        logger.info(f"Processing module {module_name} -> {target_dir}")
        
        # Find resources for this module
        module_resources = find_module_resources(source_state, module_name)
        logger.info(f"Found {len(module_resources)} resources for module {module_name}")
        
        if not module_resources:
            logger.warning(f"No resources found for module {module_name}")
            continue
        
        # Pull target state
        try:
            target_state = pull_state(target_dir, args.use_terragrunt)
        except Exception as e:
            logger.error(f"Failed to pull state from target {target_dir}, initializing empty state")
            target_state = {
                "version": 4, 
                "terraform_version": source_state.get("terraform_version", "1.0.0"), 
                "serial": 0,
                "lineage": source_state.get("lineage", ""),
                "resources": []
            }
        
        if args.dry_run:
            logger.info(f"DRY RUN: Would move {len(module_resources)} resources from {args.source} to {target_dir}")
            
            # Check if we have a prefix change for this module
            if module_name in module_prefixes:
                source_prefix = module_prefixes[module_name]['source']
                target_prefix = module_prefixes[module_name]['target']
                logger.info(f"  With prefix change: {source_prefix} -> {target_prefix}")
                
            for resource in module_resources:
                resource_id = get_resource_identifier(resource)
                logger.info(f"  - {resource_id}")
        else:
            # Generate list of resource identifiers to remove from source
            resources_to_remove = [
                get_resource_identifier(resource)
                for resource in module_resources
            ]
            
            # Check if we have a prefix change for this module
            source_prefix = None
            target_prefix = None
            if module_name in module_prefixes:
                source_prefix = module_prefixes[module_name]['source']
                target_prefix = module_prefixes[module_name]['target']
            
            # Add resources to target state with possible prefix change
            target_state = add_resources_to_state(
                target_state, 
                module_resources, 
                source_prefix=source_prefix, 
                target_prefix=target_prefix
            )
            
            # Add to our master list of resources to remove
            all_resources_to_remove.extend(resources_to_remove)
            
            # Push the updated target state
            push_state(target_dir, target_state, use_terragrunt=args.use_terragrunt)
    
    # Remove resources from source state and push it
    if not args.dry_run and all_resources_to_remove:
        logger.info(f"Removing {len(all_resources_to_remove)} resources from source state")
        source_state = remove_resources_from_state(source_state, all_resources_to_remove)
        
        # Force serial to be higher than original to avoid conflicts
        push_state(args.source, source_state, force_serial=original_serial+1, use_terragrunt=args.use_terragrunt)
        
        logger.info("State split complete")
    elif args.dry_run:
        logger.info("Dry run complete, no changes made")

if __name__ == "__main__":
    main()