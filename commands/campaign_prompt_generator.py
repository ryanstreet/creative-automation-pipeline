#!/usr/bin/env python3
"""
Campaign Prompt Generator

A command-line tool that parses campaign brief JSON files and generates
Adobe Firefly prompts using OpenAI's API based on target demographics.
"""

import argparse
import sys
import os
from pathlib import Path

# Add parent directory to path to import libs
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from libs.firefly_api import FireflyPromptGenerator
from libs.utils import InteractiveModeHelper, validate_openai_credentials, load_json_file


def interactive_mode() -> tuple:
    """Interactive mode to collect required parameters."""
    InteractiveModeHelper.print_header("Campaign Prompt Generator")
    
    # Get JSON file path
    json_file_path = InteractiveModeHelper.get_file_path("Enter path to campaign brief JSON file")
    
    # Get model
    model = InteractiveModeHelper.get_choice(
        "Enter OpenAI model (gpt-4/gpt-4-turbo/gpt-3.5-turbo, default: gpt-4)",
        ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"],
        "gpt-4"
    )
    
    return json_file_path, model


def main():
    """Main function to handle command line arguments and execute the script."""
    parser = argparse.ArgumentParser(
        description="Generate Adobe Firefly prompts from campaign brief JSON files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python campaign_prompt_generator.py tmp/campaign_brief.json
  python campaign_prompt_generator.py tmp/campaign_brief.json --model gpt-4-turbo
  python campaign_prompt_generator.py  # Interactive mode
        """
    )
    
    parser.add_argument(
        'json_file',
        nargs='?',
        help='Path to the campaign brief JSON file (e.g., tmp/campaign_brief.json)'
    )
    
    parser.add_argument(
        '--model',
        help='OpenAI model to use (default: gpt-4)',
        default='gpt-4',
        choices=['gpt-4', 'gpt-4-turbo', 'gpt-3.5-turbo']
    )
    
    args = parser.parse_args()
    
    # Check if we should use interactive mode (when no json_file provided)
    if not args.json_file:
        print("No JSON file provided. Starting interactive mode...")
        json_file_path, model = interactive_mode()
    else:
        # Resolve file path
        json_file_path = Path(args.json_file)
        if not json_file_path.is_absolute():
            # Use relative path as-is from project root
            json_file_path = Path(__file__).parent / args.json_file
        
        model = args.model
    
    # Get API key from environment variable
    api_key = validate_openai_credentials()
    
    # Load and parse campaign brief
    print(f"Loading campaign brief from: {json_file_path}")
    campaign_brief = load_json_file(json_file_path, "campaign brief")
    
    # Extract demographics
    print("Extracting demographics...")
    prompt_generator = FireflyPromptGenerator(api_key)
    demographics = prompt_generator.extract_demographics(campaign_brief)
    
    if not demographics:
        print("Warning: No demographics data found in the campaign brief.")
        sys.exit(1)
    
    # Generate Firefly prompt
    print(f"Generating Firefly prompt using OpenAI API ({model})...")
    firefly_prompt = prompt_generator.generate_firefly_prompt(demographics, model)
    
    # Output the result
    print("\n" + "="*80)
    print("GENERATED ADOBE FIREFLY PROMPT:")
    print("="*80)
    print(firefly_prompt)
    print("="*80)


if __name__ == "__main__":
    main()
