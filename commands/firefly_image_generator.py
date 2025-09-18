#!/usr/bin/env python3
"""
Adobe Firefly API V3 Async Image Generation Script

This script implements the Adobe Firefly API V3 Async for image generation.
It generates images based on text prompts and outputs the generated image URLs to the console.

Usage:
    python firefly_image_generator.py "your prompt here" [options]

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

from libs.firefly_api import AdobeFireflyAPI
from libs.utils import InteractiveModeHelper, validate_adobe_credentials


def interactive_mode() -> tuple:
    """Interactive mode to collect required parameters."""
    InteractiveModeHelper.print_header("Adobe Firefly Image Generator")
    
    # Get prompt
    prompt = InteractiveModeHelper.get_text_input("Enter text prompt for image generation")
    
    # Get number of variations
    num_variations = InteractiveModeHelper.get_integer(
        "Enter number of image variations (default: 1)",
        min_value=1,
        default=1
    )
    
    # Get width
    width = InteractiveModeHelper.get_integer(
        "Enter image width in pixels (default: 1024)",
        min_value=1,
        default=1024
    )
    
    # Get height
    height = InteractiveModeHelper.get_integer(
        "Enter image height in pixels (default: 1024)",
        min_value=1,
        default=1024
    )
    
    # Get content class
    content_class = InteractiveModeHelper.get_choice(
        "Enter content class (photo/art/design, default: photo)",
        ["photo", "art", "design"],
        "photo"
    )
    
    # Get locale
    locale = InteractiveModeHelper.get_text_input(
        "Enter prompt biasing locale code (default: en-US)",
        allow_empty=True
    ) or "en-US"
    
    return prompt, num_variations, width, height, content_class, locale


def main():
    """Main function to handle command line interface."""
    parser = argparse.ArgumentParser(
        description="Generate images using Adobe Firefly API V3 Async",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python firefly_image_generator.py "a beautiful sunset over mountains"
    python firefly_image_generator.py "a cat wearing a hat" --num-variations 3
    python firefly_image_generator.py "abstract art" --width 512 --height 512
    python firefly_image_generator.py "portrait" --content-class "photo" --locale "en-US"
    python firefly_image_generator.py "landscape" --poll-interval 10 --debug
    python firefly_image_generator.py  # Interactive mode

Environment Variables:
    CLIENT_ID: Adobe Developer Console client ID
    CLIENT_SECRET: Adobe Developer Console client secret
        """
    )
    
    parser.add_argument(
        'prompt',
        nargs='?',
        help='Text prompt for image generation (required unless using interactive mode)'
    )
    
    parser.add_argument(
        '--num-variations',
        type=int,
        default=1,
        help='Number of image variations to generate (default: 1)'
    )
    
    parser.add_argument(
        '--width',
        type=int,
        default=1024,
        help='Image width in pixels (default: 1024)'
    )
    
    parser.add_argument(
        '--height',
        type=int,
        default=1024,
        help='Image height in pixels (default: 1024)'
    )
    
    parser.add_argument(
        '--locale',
        dest='prompt_biasing_locale_code',
        default='en-US',
        help='Prompt biasing locale code (default: en-US)'
    )
    
    parser.add_argument(
        '--content-class',
        default='photo',
        choices=['photo', 'art', 'design'],
        help='Content class for the generated images (default: photo)'
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
    
    # Check if we should use interactive mode (when no prompt provided)
    if not args.prompt:
        print("No prompt provided. Starting interactive mode...")
        prompt, num_variations, width, height, content_class, locale = interactive_mode()
    else:
        prompt = args.prompt
        num_variations = args.num_variations
        width = args.width
        height = args.height
        content_class = args.content_class
        locale = args.prompt_biasing_locale_code
    
    # Get credentials from environment
    client_id, client_secret = validate_adobe_credentials()
    
    try:
        # Initialize API client
        api = AdobeFireflyAPI(client_id, client_secret)
        
        # Authenticate
        api.authenticate()
        
        # Initiate image generation
        status_url = api.generate_images_async(
            prompt=prompt,
            num_variations=num_variations,
            width=width,
            height=height,
            prompt_biasing_locale_code=locale,
            content_class=content_class
        )
        
        # Poll for completion
        result_data = api.poll_job_status(
            status_url, 
            args.poll_interval, 
            args.max_attempts, 
            args.debug
        )
        
        # Extract and display image URLs
        image_urls = api.extract_image_urls(result_data, args.debug)
        
        if image_urls:
            print("\n" + "="*60)
            print("GENERATED IMAGE URLS:")
            print("="*60)
            for i, url in enumerate(image_urls, 1):
                print(f"{i}. {url}")
            print("="*60)
        else:
            print("Warning: No image URLs found in the response")
            if args.debug:
                print("Full response data:")
                print(json.dumps(result_data, indent=2))
        
        print(f"\nImage generation completed successfully! Generated {len(image_urls)} image(s).")
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
