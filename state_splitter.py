#!/usr/bin/env python3
import json
import subprocess
import os
import argparse
import logging
import sys
import glob

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

def add_resources_to_state(state, resources_to_add):
    """Add resources to state, avoiding duplicates"""
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
        resource_id = get_resource_identifier(resource)
        
        if resource_id not in existing_resources:
            state['resources'].append(resource)
            logger.debug(f"Adding resource: {resource_id}")
            existing_resources.add(resource_id)
        else:
            logger.warning(f"Skipping duplicate resource: {resource_id}")
    
    return state

def main():
    args = parse_args()
    
    if not args.split:
        logger.error("No split mappings provided")
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
            for resource in module_resources:
                resource_id = get_resource_identifier(resource)
                logger.info(f"  - {resource_id}")
        else:
            # Generate list of resource identifiers to remove from source
            resources_to_remove = [
                get_resource_identifier(resource)
                for resource in module_resources
            ]
            
            # Add resources to target state
            target_state = add_resources_to_state(target_state, module_resources)
            
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
    else:
        logger.info("No resources to move")

if __name__ == "__main__":
    main()