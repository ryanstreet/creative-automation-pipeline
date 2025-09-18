#!/usr/bin/env python3
"""
Adobe Firefly Services Photoshop API Smart Object Replacement Script

This script implements the Adobe Firefly Services Photoshop API to replace smart objects
in PSD files asynchronously. It takes a document manifest JSON file, locates a specified
layer, and replaces it with a new smart object from an S3 URL.

Usage:
    python smart_object_replacer.py --manifest MANIFEST_FILE --layer LAYER_NAME --smart-object-url SMART_OBJECT_URL --output-url OUTPUT_URL
    python smart_object_replacer.py  # Interactive mode

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
from typing import Dict, Any, Optional, List

# Add parent directory to path to import libs
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from libs.photoshop_api import AdobePhotoshopAPI, validate_url, find_layer_in_manifest, get_input_psd_url
from libs.utils import InteractiveModeHelper, validate_adobe_credentials, load_json_file


def load_manifest(manifest_file: str) -> Dict[str, Any]:
    """Load and validate the document manifest JSON file."""
    manifest = load_json_file(manifest_file, "manifest")
    
    # Validate manifest structure
    if 'outputs' not in manifest:
        raise ValueError("Manifest must contain 'outputs' field")
    
    outputs = manifest['outputs']
    if not isinstance(outputs, list) or len(outputs) == 0:
        raise ValueError("Manifest 'outputs' must be a non-empty array")
    
    # Get the first output (assuming single document processing)
    output = outputs[0]
    if 'input' not in output:
        raise ValueError("Output must contain 'input' field with PSD URL")
    
    return manifest


def interactive_mode() -> tuple:
    """Interactive mode to collect required parameters."""
    InteractiveModeHelper.print_header("Adobe Photoshop Smart Object Replacement")
    
    # Get manifest file path
    manifest_file = InteractiveModeHelper.get_file_path("Enter path to document manifest JSON file")
    
    # Get layer name
    layer_name = InteractiveModeHelper.get_text_input("Enter the name of the layer to replace")
    
    # Get smart object URL
    smart_object_url = InteractiveModeHelper.get_url("Enter S3 URL of the new smart object")
    
    # Get output URL
    output_url = InteractiveModeHelper.get_url("Enter S3 URL for the output file")
    
    return manifest_file, layer_name, smart_object_url, output_url


def main():
    """Main function to handle command line interface."""
    parser = argparse.ArgumentParser(
        description="Replace smart objects in PSD files using Adobe Firefly Services Photoshop API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python smart_object_replacer.py --manifest tmp/document_manifest.json --layer "Logo" --smart-object-url "https://s3.amazonaws.com/bucket/new-logo.png" --output-url "https://s3.amazonaws.com/bucket/output.psd"
    python smart_object_replacer.py --manifest manifest.json --layer "Background" --smart-object-url "https://example.com/image.jpg" --output-url "https://example.com/result.psd" --debug
    python smart_object_replacer.py  # Interactive mode

Environment Variables:
    CLIENT_ID: Adobe Developer Console client ID
    CLIENT_SECRET: Adobe Developer Console client secret
        """
    )
    
    parser.add_argument(
        '--manifest',
        help='Path to the document manifest JSON file'
    )
    
    parser.add_argument(
        '--layer',
        help='Name of the layer to replace'
    )
    
    parser.add_argument(
        '--smart-object-url',
        help='S3 URL of the new smart object'
    )
    
    parser.add_argument(
        '--output-url',
        help='S3 URL for the output file'
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
    
    args = parser.parse_args()
    
    # Check if we should use interactive mode (when no arguments provided at all)
    if not any([args.manifest, args.layer, args.smart_object_url, args.output_url]):
        print("No arguments provided. Starting interactive mode...")
        manifest_file, layer_name, smart_object_url, output_url = interactive_mode()
    elif not all([args.manifest, args.layer, args.smart_object_url, args.output_url]):
        print("Not all required arguments provided. Switching to interactive mode...")
        manifest_file, layer_name, smart_object_url, output_url = interactive_mode()
    else:
        manifest_file = args.manifest
        layer_name = args.layer
        smart_object_url = args.smart_object_url
        output_url = args.output_url
    
    # Validate URLs
    if not validate_url(smart_object_url):
        print("Error: Invalid smart object URL format", file=sys.stderr)
        sys.exit(1)
    
    if not validate_url(output_url):
        print("Error: Invalid output URL format", file=sys.stderr)
        sys.exit(1)
    
    # Get credentials from environment
    client_id, client_secret = validate_adobe_credentials()
    
    try:
        # Load and validate manifest
        print(f"Loading manifest from: {manifest_file}")
        manifest = load_manifest(manifest_file)
        
        # Find the specified layer
        print(f"Searching for layer: {layer_name}")
        layer = find_layer_in_manifest(manifest, layer_name)
        if not layer:
            print(f"Error: Layer '{layer_name}' not found in manifest", file=sys.stderr)
            print("Available layers:", file=sys.stderr)
            try:
                outputs = manifest.get('outputs', [])
                if outputs and 'layers' in outputs[0]:
                    for layer_info in outputs[0]['layers']:
                        print(f"  - {layer_info.get('name', 'Unnamed')}", file=sys.stderr)
            except Exception:
                pass
            sys.exit(1)
        
        print(f"Found layer: {layer_name} (ID: {layer.get('id', 'Unknown')})")
        
        # Get input PSD URL
        input_psd_url = get_input_psd_url(manifest)
        print(f"Using input PSD URL: {input_psd_url}")
        
        # Initialize API client
        api = AdobePhotoshopAPI(client_id, client_secret)
        
        # Authenticate
        api.authenticate()
        
        # Initiate smart object replacement
        status_url = api.replace_smart_object(
            input_psd_url=input_psd_url,
            layer_name=layer_name,
            smart_object_url=smart_object_url,
            output_url=output_url
        )
        
        # Poll for completion
        result_data = api.poll_job_status(
            status_url, 
            args.poll_interval, 
            args.max_attempts, 
            args.debug
        )
        
        print("Smart object replacement completed successfully!")
        print(f"Output file available at: {output_url}")
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
