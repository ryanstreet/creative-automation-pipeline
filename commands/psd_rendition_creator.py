#!/usr/bin/env python3
"""
Adobe Photoshop Rendition Creator

This script implements the Adobe Photoshop API createRenditionAsync endpoint
to create PNG renditions of PSD files using AWS presigned URLs.

Usage:
    python psd_rendition_creator.py --input-url <presigned_download_url> --output-url <presigned_upload_url>
    
    Or run without arguments for interactive mode:
    python psd_rendition_creator.py
"""

import os
import sys
import json
import time
import argparse

# Add parent directory to path to import libs
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from libs.photoshop_api import AdobePhotoshopAPI
from libs.utils import InteractiveModeHelper, validate_adobe_credentials


def interactive_mode():
    """Interactive mode for user input"""
    InteractiveModeHelper.print_header("Adobe Photoshop Rendition Creator")
    
    # Get input URL
    input_url = InteractiveModeHelper.get_url("Enter AWS presigned download URL for the PSD file")
    
    # Get output URL
    output_url = InteractiveModeHelper.get_url("Enter AWS presigned upload URL for the PNG output")
    
    # Optional settings
    poll_interval = InteractiveModeHelper.get_integer(
        "Enter polling interval in seconds (default: 5)",
        min_value=1,
        default=5
    )
    
    max_attempts = InteractiveModeHelper.get_integer(
        "Enter maximum polling attempts (default: 120)",
        min_value=1,
        default=120
    )
    
    debug = InteractiveModeHelper.get_boolean("Enable debug mode?", default=False)
    
    print(f"\n📋 Configuration:")
    print(f"   Input URL: {input_url}")
    print(f"   Output URL: {output_url}")
    print(f"   Poll interval: {poll_interval} seconds")
    print(f"   Max attempts: {max_attempts}")
    print(f"   Debug mode: {'Yes' if debug else 'No'}")
    print()
    
    # Create rendition
    client_id, client_secret = validate_adobe_credentials()
    
    api = AdobePhotoshopAPI(client_id, client_secret)
    api.authenticate()
    
    status_url = api.create_rendition(input_url, output_url)
    success = api.poll_job_status(status_url, poll_interval, max_attempts, debug)
    
    if success:
        print("🎉 Rendition creation completed successfully!")
        print(f"📁 PNG file should be available at: {output_url}")
    else:
        print("❌ Rendition creation failed!")
        sys.exit(1)


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Create PNG renditions of PSD files using Adobe Photoshop API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python psd_rendition_creator.py --input-url "https://s3.amazonaws.com/bucket/file.psd?..." --output-url "https://s3.amazonaws.com/bucket/output.png?..."
  python psd_rendition_creator.py --input-url "https://..." --output-url "https://..." --debug
  python psd_rendition_creator.py  # Interactive mode
        """
    )
    
    parser.add_argument('--input-url', 
                       help='AWS presigned download URL for the PSD file')
    parser.add_argument('--output-url', 
                       help='AWS presigned upload URL for the PNG output')
    parser.add_argument('--poll-interval', type=int, default=5,
                       help='Polling interval in seconds (default: 5)')
    parser.add_argument('--max-attempts', type=int, default=120,
                       help='Maximum polling attempts before timeout (default: 120)')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug output with detailed API responses')
    
    args = parser.parse_args()
    
    # Check if we have required arguments
    if not args.input_url or not args.output_url:
        print("Not all required arguments provided. Switching to interactive mode...\n")
        interactive_mode()
        return
    
    # Validate URLs
    if not args.input_url.startswith('http'):
        print("❌ Input URL must be a valid HTTP/HTTPS URL")
        sys.exit(1)
        
    if not args.output_url.startswith('http'):
        print("❌ Output URL must be a valid HTTP/HTTPS URL")
        sys.exit(1)
    
    # Create rendition
    client_id, client_secret = validate_adobe_credentials()
    
    api = AdobePhotoshopAPI(client_id, client_secret)
    api.authenticate()
    
    status_url = api.create_rendition(args.input_url, args.output_url)
    success = api.poll_job_status(status_url, args.poll_interval, args.max_attempts, args.debug)
    
    if success:
        print("🎉 Rendition creation completed successfully!")
        print(f"📁 PNG file should be available at: {args.output_url}")
    else:
        print("❌ Rendition creation failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
