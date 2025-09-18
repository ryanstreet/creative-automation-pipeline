#!/usr/bin/env python3
"""
Adobe Firefly Services Photoshop API Text Layer Editor Script

This script implements the Adobe Firefly Services Photoshop API to edit text layers
in PSD files asynchronously. It takes a layer name and replacement text, then
updates the text content of that layer.

Usage:
    python text_layer_editor.py --input-url INPUT_URL --layer LAYER_NAME --text REPLACEMENT_TEXT --output-url OUTPUT_URL
    python text_layer_editor.py  # Interactive mode

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

from libs.photoshop_api import AdobePhotoshopAPI, validate_url
from libs.utils import InteractiveModeHelper, validate_adobe_credentials


def interactive_mode() -> tuple:
    """Interactive mode to collect required parameters."""
    InteractiveModeHelper.print_header("Adobe Photoshop Text Layer Editor")
    
    # Get input PSD URL
    input_url = InteractiveModeHelper.get_url("Enter URL of the input PSD file")
    
    # Get layer name
    layer_name = InteractiveModeHelper.get_text_input("Enter the name of the text layer to edit")
    
    # Get replacement text
    replacement_text = InteractiveModeHelper.get_text_input("Enter the replacement text")
    
    # Get output URL
    output_url = InteractiveModeHelper.get_url("Enter URL for the output file")
    
    return input_url, layer_name, replacement_text, output_url


def main():
    """Main function to handle command line interface."""
    parser = argparse.ArgumentParser(
        description="Edit text layers in PSD files using Adobe Firefly Services Photoshop API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python text_layer_editor.py --input-url "https://s3.amazonaws.com/bucket/template.psd" --layer "Title" --text "New Title Text" --output-url "https://s3.amazonaws.com/bucket/output.psd"
    python text_layer_editor.py --input-url "https://example.com/document.psd" --layer "Subtitle" --text "Updated Subtitle" --output-url "https://example.com/result.psd" --debug
    python text_layer_editor.py  # Interactive mode

Environment Variables:
    CLIENT_ID: Adobe Developer Console client ID
    CLIENT_SECRET: Adobe Developer Console client secret
        """
    )
    
    parser.add_argument(
        '--input-url',
        help='URL of the input PSD file'
    )
    
    parser.add_argument(
        '--layer',
        help='Name of the text layer to edit'
    )
    
    parser.add_argument(
        '--text',
        help='Replacement text content'
    )
    
    parser.add_argument(
        '--output-url',
        help='URL for the output file'
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
    if not any([args.input_url, args.layer, args.text, args.output_url]):
        print("No arguments provided. Starting interactive mode...")
        input_url, layer_name, replacement_text, output_url = interactive_mode()
    elif not all([args.input_url, args.layer, args.text, args.output_url]):
        print("Not all required arguments provided. Switching to interactive mode...")
        input_url, layer_name, replacement_text, output_url = interactive_mode()
    else:
        input_url = args.input_url
        layer_name = args.layer
        replacement_text = args.text
        output_url = args.output_url
    
    # Validate URLs
    if not validate_url(input_url):
        print("Error: Invalid input URL format", file=sys.stderr)
        sys.exit(1)
    
    if not validate_url(output_url):
        print("Error: Invalid output URL format", file=sys.stderr)
        sys.exit(1)
    
    # Get credentials from environment
    client_id, client_secret = validate_adobe_credentials()
    
    try:
        # Initialize API client
        api = AdobePhotoshopAPI(client_id, client_secret)
        
        # Authenticate
        api.authenticate()
        
        # Initiate text layer editing
        status_url = api.edit_text_layer(
            input_psd_url=input_url,
            layer_name=layer_name,
            replacement_text=replacement_text,
            output_url=output_url
        )
        
        # Poll for completion
        result_data = api.poll_job_status(
            status_url, 
            args.poll_interval, 
            args.max_attempts, 
            args.debug
        )
        
        print("Text layer editing completed successfully!")
        print(f"Output file available at: {output_url}")
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
