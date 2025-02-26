#!/usr/bin/env python3
import json
import subprocess
import os
import argparse
import logging
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def parse_args():
    parser = argparse.ArgumentParser(description='Split Terraform state by moving resources between modules')
    parser.add_argument('--source', required=True, help='Source module directory')
    parser.add_argument('--split', action='append', help='Module split mapping in format module=target_dir')
    parser.add_argument('--dry-run', action='store_true', help='Perform a dry run without making changes')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    return args

def pull_state(module_dir):
    """Pull Terraform state from a module directory"""
    try:
        original_dir = os.getcwd()
        os.chdir(module_dir)
        
        logger.debug(f"Pulling state from {module_dir}")
        result = subprocess.run(
            ['terraform', 'state', 'pull'], 
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

def push_state(module_dir, state, force_serial=None):
    """Push Terraform state to a module directory"""
    try:
        original_dir = os.getcwd()
        os.chdir(module_dir)
        
        # Use specified serial number or increment the existing one
        if force_serial is not None:
            state['serial'] = force_serial
        else:
            state['serial'] = state.get('serial', 0) + 1
            
        logger.debug(f"Pushing state to {module_dir} with serial {state['serial']}")
        
        result = subprocess.run(
            ['terraform', 'state', 'push', '-'],
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

def find_module_resources(state, module_prefix):
    """Find all resources in state that belong to a specific module"""
    resources = []
    
    for resource in state.get('resources', []):
        if resource.get('module', '').startswith(module_prefix):
            resources.append(resource)
    
    return resources

def get_resource_identifier(resource):
    """Generate a unique identifier for a resource"""
    return f"{resource.get('module', '')}.{resource.get('type')}.{resource.get('name')}"

def remove_resources_from_state(state, resources_to_remove):
    """Remove specified resources from state"""
    new_resources = []
    
    for resource in state.get('resources', []):
        # Generate a unique identifier for this resource
        resource_id = get_resource_identifier(resource)
        
        if resource_id not in resources_to_remove:
            new_resources.append(resource)
        else:
            logger.debug(f"Removing resource {resource_id} from state")
    
    state['resources'] = new_resources
    return state

def add_resources_to_state(state, resources_to_add):
    """Add specified resources to state, avoiding duplicates"""
    # Create a set of existing resource identifiers
    existing_resources = {
        get_resource_identifier(resource)
        for resource in state.get('resources', [])
    }
    
    # Add only non-duplicate resources
    for resource in resources_to_add:
        resource_id = get_resource_identifier(resource)
        if resource_id not in existing_resources:
            logger.debug(f"Adding resource {resource_id} to state")
            state['resources'].append(resource)
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
    source_state = pull_state(args.source)
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
            target_state = pull_state(target_dir)
        except:
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
            
            # Push updated target state
            logger.info(f"Pushing updated state to {target_dir}")
            push_state(target_dir, target_state)
    
    if not args.dry_run and all_resources_to_remove:
        # Pull source state again to ensure we have the latest version
        source_state = pull_state(args.source)
        
        # Remove all resources from source state
        source_state = remove_resources_from_state(source_state, all_resources_to_remove)
        
        # Force serial to be greater than original
        new_serial = max(original_serial + 1, source_state.get('serial', 0) + 1)
        
        # Push updated source state
        logger.info(f"Pushing updated state to {args.source} with serial {new_serial}")
        push_state(args.source, source_state, force_serial=new_serial)
    
    logger.info("Terraform state splitting completed")

if __name__ == "__main__":
    main()