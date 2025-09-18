#!/usr/bin/env python3
"""
Adobe Photoshop API Document Manifest Retrieval Script

This script implements the Adobe Photoshop API to retrieve document manifests
asynchronously and save the output to a JSON file in the /tmp/ folder.

Usage:
    python photoshop_manifest.py <input_url> [--output-file OUTPUT_FILE] [--poll-interval SECONDS]

Requirements:
    - Adobe Developer Console credentials (CLIENT_ID and CLIENT_SECRET)
    - Python 3.7+
    - requests library
"""

import argparse
import json
import os
import sys
import time
from typing import Dict, Any, Optional

# Add parent directory to path to import libs
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from libs.photoshop_api import AdobePhotoshopAPI, validate_url, extract_layers_from_manifest
from libs.utils import InteractiveModeHelper, validate_adobe_credentials, save_json_file


def save_manifest_to_file(manifest_data: Dict[str, Any], output_file: str) -> None:
    """Save manifest data to JSON file."""
    try:
        # Ensure /tmp directory exists
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(manifest_data, f, indent=2, ensure_ascii=False)
        
        print(f"Manifest saved to: {output_file}")
        
    except Exception as e:
        raise Exception(f"Failed to save manifest to file: {e}")


def interactive_mode() -> tuple:
    """Interactive mode to collect required parameters."""
    InteractiveModeHelper.print_header("Adobe Photoshop Document Manifest")
    
    # Get input URL
    input_url = InteractiveModeHelper.get_url("Enter URL of the PSD file to process")
    
    # Get output file path
    output_file = InteractiveModeHelper.get_text_input(
        "Enter output JSON file path (default: tmp/document_manifest.json)",
        allow_empty=True
    ) or "tmp/document_manifest.json"
    
    return input_url, output_file


def discover_manifest_files(tmp_dir: str = "tmp") -> list:
    """Discover available manifest JSON files in the tmp directory."""
    manifest_files = []
    
    if not os.path.exists(tmp_dir):
        return manifest_files
    
    try:
        for filename in os.listdir(tmp_dir):
            if filename.endswith('.json') and 'manifest' in filename.lower():
                file_path = os.path.join(tmp_dir, filename)
                if os.path.isfile(file_path):
                    manifest_files.append(file_path)
        
        # Sort files by modification time (newest first)
        manifest_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        
    except Exception as e:
        print(f"Warning: Could not scan tmp directory: {e}")
    
    return manifest_files


def list_available_manifests(tmp_dir: str = "tmp") -> None:
    """List all available manifest files in the tmp directory."""
    manifest_files = discover_manifest_files(tmp_dir)
    
    if not manifest_files:
        print(f"No manifest files found in {tmp_dir}/ directory.")
        print("Available files:")
        try:
            if os.path.exists(tmp_dir):
                files = os.listdir(tmp_dir)
                for file in sorted(files):
                    print(f"  - {file}")
            else:
                print(f"  Directory {tmp_dir}/ does not exist.")
        except Exception as e:
            print(f"  Could not list directory contents: {e}")
        return
    
    print(f"Available manifest files in {tmp_dir}/:")
    print("=" * 50)
    
    for i, manifest_file in enumerate(manifest_files, 1):
        try:
            # Get file modification time
            mtime = os.path.getmtime(manifest_file)
            mtime_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mtime))
            
            # Get file size
            size = os.path.getsize(manifest_file)
            size_str = f"{size:,} bytes"
            
            print(f"{i}. {os.path.basename(manifest_file)}")
            print(f"   Path: {manifest_file}")
            print(f"   Modified: {mtime_str}")
            print(f"   Size: {size_str}")
            print()
            
        except Exception as e:
            print(f"{i}. {os.path.basename(manifest_file)} (error reading file info: {e})")
            print()


def list_layer_names(manifest_file: str) -> None:
    """Extract and list all layer names from a document manifest JSON file."""
    # If it's a relative path and doesn't exist, try in tmp directory
    if not os.path.isabs(manifest_file) and not os.path.exists(manifest_file):
        tmp_path = os.path.join("tmp", manifest_file)
        if os.path.exists(tmp_path):
            manifest_file = tmp_path
        else:
            raise Exception(f"Manifest file not found: {manifest_file}")
    
    # Check if file exists after potential tmp directory resolution
    if not os.path.exists(manifest_file):
        raise Exception(f"Manifest file not found: {manifest_file}")
    
    try:
        with open(manifest_file, 'r', encoding='utf-8') as f:
            manifest_data = json.load(f)
        
        layers = extract_layers_from_manifest(manifest_data)
        
        if not layers:
            print("No layers found in the manifest file.")
            return
        
        # Calculate column widths
        max_id_width = max(len(str(layer['id'])) for layer in layers)
        max_name_width = max(len(layer['name']) for layer in layers)
        max_type_width = max(len(layer['type']) for layer in layers)
        
        # Ensure minimum widths for headers
        id_width = max(max_id_width, 2)  # "ID" header
        name_width = max(max_name_width, 4)  # "Name" header
        type_width = max(max_type_width, 4)  # "Type" header
        
        # Print table header
        print(f"\nFound {len(layers)} layer(s) in the manifest:")
        print(f"File: {manifest_file}")
        print("=" * (id_width + name_width + type_width + 8))  # +8 for separators and padding
        
        # Print column headers
        print(f"{'ID':<{id_width}} | {'Name':<{name_width}} | {'Type':<{type_width}}")
        print("-" * (id_width + name_width + type_width + 8))
        
        # Print layer data
        for layer in layers:
            print(f"{layer['id']:<{id_width}} | {layer['name']:<{name_width}} | {layer['type']:<{type_width}}")
        
        print("=" * (id_width + name_width + type_width + 8))
        
    except FileNotFoundError:
        raise Exception(f"Manifest file not found: {manifest_file}")
    except json.JSONDecodeError as e:
        raise Exception(f"Invalid JSON in manifest file: {e}")
    except Exception as e:
        raise Exception(f"Failed to read manifest file: {e}")


def main():
    """Main function to handle command line interface."""
    parser = argparse.ArgumentParser(
        description="Retrieve Adobe Photoshop document manifest from PSD URLs or list layers from local manifest files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Download manifest from PSD URL
    python photoshop_manifest.py https://example.com/document.psd
    python photoshop_manifest.py https://example.com/document.psd --output-file tmp/my_manifest.json
    python photoshop_manifest.py https://example.com/document.psd --poll-interval 10
    python photoshop_manifest.py https://example.com/document.psd --max-attempts 60
    python photoshop_manifest.py https://example.com/document.psd --debug
    
    # List available manifest files in tmp directory
    python photoshop_manifest.py --list-manifests
    
    # List layers from existing local manifest file
    python photoshop_manifest.py --list-layers tmp/document_manifest.json
    python photoshop_manifest.py --list-layers document_manifest.json  # auto-searches tmp/
    python photoshop_manifest.py --list-layers /full/path/to/manifest.json

Environment Variables:
    CLIENT_ID: Adobe Developer Console client ID
    CLIENT_SECRET: Adobe Developer Console client secret
        """
    )
    
    parser.add_argument(
        'input_url',
        nargs='?',
        help='URL of the PSD file to process (required unless using --list-layers)'
    )
    
    parser.add_argument(
        '--output-file',
        default='tmp/document_manifest.json',
        help='Output JSON file path (default: tmp/document_manifest.json)'
    )
    
    parser.add_argument(
        '--poll-interval',
        type=int,
        default=5,
        help='Polling interval in seconds (default: 5)'
    )
    
    parser.add_argument(
        '--max-attempts',
        type=int,
        default=120,
        help='Maximum polling attempts before timeout (default: 120)'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug output with detailed API responses'
    )
    
    parser.add_argument(
        '--list-layers',
        metavar='MANIFEST_FILE',
        help='List all layer names from an existing manifest JSON file (local file path)'
    )
    
    parser.add_argument(
        '--list-manifests',
        action='store_true',
        help='List all available manifest files in the tmp directory'
    )
    
    args = parser.parse_args()
    
    # Handle list-manifests command
    if args.list_manifests:
        try:
            list_available_manifests()
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        return
    
    # Handle list-layers command
    if args.list_layers:
        try:
            list_layer_names(args.list_layers)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        return
    
    # Check if we should use interactive mode (when no input_url provided and not using --list-layers or --list-manifests)
    if not args.input_url and not args.list_layers and not args.list_manifests:
        print("No input URL provided. Starting interactive mode...")
        input_url, output_file = interactive_mode()
    elif not args.input_url:
        print("Error: input_url is required unless using --list-layers or --list-manifests", file=sys.stderr)
        parser.print_help()
        sys.exit(1)
    else:
        input_url = args.input_url
        output_file = args.output_file
    
    if not validate_url(input_url):
        print("Error: Invalid input URL format", file=sys.stderr)
        sys.exit(1)
    
    # Get credentials from environment
    client_id, client_secret = validate_adobe_credentials()
    
    try:
        # Initialize API client
        api = AdobePhotoshopAPI(client_id, client_secret)
        
        # Authenticate
        api.authenticate()
        
        # Initiate document manifest retrieval
        status_url = api.get_document_manifest(input_url)
        
        # Poll for completion
        manifest_data = api.poll_job_status(status_url, args.poll_interval, args.max_attempts, args.debug)
        
        # Save to file
        save_json_file(manifest_data, output_file, "Manifest")
        
        print("Document manifest retrieval completed successfully!")
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
