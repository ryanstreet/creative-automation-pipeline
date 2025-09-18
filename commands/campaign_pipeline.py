#!/usr/bin/env python3
"""
Campaign Pipeline - Complete Automation Pipeline

This script executes the complete campaign automation pipeline:
1. Parse and load campaign brief JSON files
2. Upload templates to S3 and create presigned URLs
3. Create document manifests from templates
4. Apply text edits to templates
5. Apply smart object replacements for product images
6. Generate Firefly images using campaign prompts
7. Replace background images with generated images
8. Create renditions and download to output folders

Usage:
    python campaign_pipeline.py [brief_files...] --bucket BUCKET_NAME [options]
    python campaign_pipeline.py  # Interactive mode
"""

import argparse
import json
import os
import sys
import time
import glob
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add parent directory to path to import libs
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from libs.firefly_api import AdobeFireflyAPI, FireflyPromptGenerator
from libs.photoshop_api import AdobePhotoshopAPI
from libs.s3_manager import S3Manager
from libs.utils import InteractiveModeHelper, validate_adobe_credentials, validate_openai_credentials, load_json_file


class CampaignPipeline:
    """Complete campaign automation pipeline."""
    
    def __init__(self, bucket: str, region: str = 'us-east-1', poll_interval: int = 5, max_attempts: int = 120, debug: bool = False):
        self.bucket = bucket
        self.region = region
        self.poll_interval = poll_interval
        self.max_attempts = max_attempts
        self.debug = debug
        
        # Initialize API clients
        self.s3_manager = S3Manager(region_name=region, debug=debug)
        
        # Get credentials
        self.adobe_client_id, self.adobe_client_secret = validate_adobe_credentials()
        self.openai_api_key = validate_openai_credentials()
        
        # Initialize Adobe APIs
        self.firefly_api = AdobeFireflyAPI(self.adobe_client_id, self.adobe_client_secret)
        self.photoshop_api = AdobePhotoshopAPI(self.adobe_client_id, self.adobe_client_secret)
        self.prompt_generator = FireflyPromptGenerator(self.openai_api_key)
        
        # Authenticate
        self.firefly_api.authenticate()
        self.photoshop_api.authenticate()
        
        # Create output directories
        self.output_dir = Path("tmp/output")
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def log(self, message: str, level: str = "INFO"):
        """Log a message with timestamp."""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
    
    def debug_log(self, message: str):
        """Log debug message if debug mode is enabled."""
        if self.debug:
            self.log(message, "DEBUG")
    
    def load_campaign_briefs(self, brief_files: List[str]) -> List[Dict[str, Any]]:
        """Load and parse campaign brief JSON files."""
        self.log("Loading campaign brief files...")
        
        if not brief_files:
            # Default to all JSON files in tmp/briefs/
            briefs_dir = Path("tmp/briefs")
            if briefs_dir.exists():
                brief_files = list(briefs_dir.glob("*.json"))
            else:
                raise Exception("No brief files specified and tmp/briefs/ directory not found")
        
        briefs = []
        for brief_file in brief_files:
            # Handle both Path objects and strings
            if isinstance(brief_file, Path):
                brief_path = brief_file
            else:
                brief_path = Path(brief_file)
                if not brief_path.is_absolute():
                    brief_path = Path("tmp/briefs") / brief_file
            
            if not brief_path.exists():
                self.log(f"Warning: Brief file not found: {brief_path}", "WARNING")
                continue
            
            try:
                brief_data = load_json_file(brief_path, "campaign brief")
                briefs.append(brief_data)
                self.log(f"Loaded brief: {brief_path}")
            except Exception as e:
                self.log(f"Error loading brief {brief_path}: {e}", "ERROR")
                continue
        
        if not briefs:
            raise Exception("No valid campaign briefs loaded")
        
        self.log(f"Successfully loaded {len(briefs)} campaign brief(s)")
        return briefs
    
    def upload_template_to_s3(self, template_path: Path) -> str:
        """Upload template to S3 and return presigned download URL."""
        self.log(f"Uploading template: {template_path}")
        
        if not template_path.exists():
            raise Exception(f"Template file not found: {template_path}")
        
        # Generate S3 key
        s3_key = f"templates/{template_path.name}"
        
        # Upload file
        success = self.s3_manager.upload_file(str(template_path), self.bucket, s3_key)
        if not success:
            raise Exception(f"Failed to upload template to S3: {template_path}")
        
        # Generate Adobe-compatible presigned download URL
        download_url = self.s3_manager.generate_adobe_compatible_presigned_url(
            self.bucket, s3_key, expiration=7200, operation="get_object"
        )
        
        if not download_url:
            raise Exception("Failed to generate Adobe-compatible presigned download URL")
        
        self.log(f"Template uploaded and presigned URL generated")
        return download_url
    
    def create_document_manifest(self, template_url: str, output_file: str) -> Dict[str, Any]:
        """Create document manifest from template URL."""
        self.log("Creating document manifest...")
        
        # Initiate document manifest retrieval
        status_url = self.photoshop_api.get_document_manifest(template_url)
        
        # Poll for completion
        manifest_data = self.photoshop_api.poll_job_status(
            status_url, self.poll_interval, self.max_attempts, self.debug
        )
        
        # Save manifest to file
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(manifest_data, f, indent=2, ensure_ascii=False)
        
        self.log(f"Document manifest created: {output_file}")
        return manifest_data
    
    def apply_text_edit(self, template_url: str, layer_name: str, text: str, output_filename: str) -> str:
        """Apply text edit to template and return output URL."""
        self.log(f"Applying text edit to layer '{layer_name}'")
        
        # Generate S3 key for output
        s3_key = f"processed/{output_filename}"
        
        # Generate Adobe-compatible presigned upload URL
        output_url = self.s3_manager.generate_adobe_compatible_presigned_url(
            self.bucket, s3_key, expiration=7200, operation="put_object"
        )
        
        if not output_url:
            raise Exception("Failed to generate Adobe-compatible presigned upload URL")
        
        # Initiate text layer editing
        status_url = self.photoshop_api.edit_text_layer(
            input_psd_url=template_url,
            layer_name=layer_name,
            replacement_text=text,
            output_url=output_url
        )
        
        # Poll for completion
        self.photoshop_api.poll_job_status(
            status_url, self.poll_interval, self.max_attempts, self.debug
        )
        
        # Generate Adobe-compatible download URL for the output file
        # This is needed because Adobe will use this URL as input for the next step
        download_url = self.s3_manager.generate_adobe_compatible_presigned_url(
            self.bucket, s3_key, expiration=7200, operation="get_object"
        )
        
        if not download_url:
            raise Exception("Failed to generate Adobe-compatible download URL for text edit output")
        
        self.log(f"Text edit completed: {output_filename}")
        return download_url
    
    def upload_product_image(self, product_path: Path) -> str:
        """Upload product image to S3 and return presigned download URL."""
        self.log(f"Uploading product image: {product_path}")
        
        if not product_path.exists():
            raise Exception(f"Product image not found: {product_path}")
        
        # Generate S3 key
        s3_key = f"products/{product_path.name}"
        
        # Upload file
        success = self.s3_manager.upload_file(str(product_path), self.bucket, s3_key)
        if not success:
            raise Exception(f"Failed to upload product image to S3: {product_path}")
        
        # Generate Adobe-compatible presigned download URL
        download_url = self.s3_manager.generate_adobe_compatible_presigned_url(
            self.bucket, s3_key, expiration=7200, operation="get_object"
        )
        
        if not download_url:
            raise Exception("Failed to generate Adobe-compatible presigned download URL for product image")
        
        self.log(f"Product image uploaded and presigned URL generated")
        return download_url
    
    def apply_smart_object_replace(self, input_url: str, layer_name: str, smart_object_url: str, output_filename: str) -> str:
        """Apply smart object replacement and return output URL."""
        self.log(f"Applying smart object replacement to layer '{layer_name}'")
        
        # Generate S3 key for output
        s3_key = f"processed/{output_filename}"
        
        # Generate Adobe-compatible presigned upload URL
        output_url = self.s3_manager.generate_adobe_compatible_presigned_url(
            self.bucket, s3_key, expiration=7200, operation="put_object"
        )
        
        if not output_url:
            raise Exception("Failed to generate Adobe-compatible presigned upload URL")
        
        # Initiate smart object replacement
        status_url = self.photoshop_api.replace_smart_object(
            input_psd_url=input_url,
            layer_name=layer_name,
            smart_object_url=smart_object_url,
            output_url=output_url
        )
        
        # Poll for completion
        self.photoshop_api.poll_job_status(
            status_url, self.poll_interval, self.max_attempts, self.debug
        )
        
        # Generate Adobe-compatible download URL for the output file
        # This is needed because Adobe will use this URL as input for the next step
        download_url = self.s3_manager.generate_adobe_compatible_presigned_url(
            self.bucket, s3_key, expiration=7200, operation="get_object"
        )
        
        if not download_url:
            raise Exception("Failed to generate Adobe-compatible download URL for output")
        
        self.log(f"Smart object replacement completed: {output_filename}")
        return download_url
    
    def generate_firefly_images(self, campaign_brief: Dict[str, Any]) -> List[str]:
        """Generate Firefly images using campaign prompt."""
        self.log("Generating Firefly images...")
        
        # Extract demographics and generate prompt
        demographics = self.prompt_generator.extract_demographics(campaign_brief)
        if not demographics:
            raise Exception("No demographics data found in campaign brief")
        
        firefly_prompt = self.prompt_generator.generate_firefly_prompt(demographics, "gpt-4")
        self.log(f"Generated prompt: {firefly_prompt}")
        
        # Get technical specs
        tech_specs = campaign_brief.get("technical_specs", {})
        variations = tech_specs.get("variations", 1)
        width = tech_specs.get("asset_width", 1024)
        height = tech_specs.get("asset_height", 1024)
        
        # Generate images
        status_url = self.firefly_api.generate_images_async(
            prompt=firefly_prompt,
            num_variations=variations,
            width=width,
            height=height,
            prompt_biasing_locale_code="en-US",
            content_class="photo"
        )
        
        # Poll for completion
        result_data = self.firefly_api.poll_job_status(
            status_url, self.poll_interval, self.max_attempts, self.debug
        )
        
        # Extract image URLs
        image_urls = self.firefly_api.extract_image_urls(result_data, self.debug)
        
        if not image_urls:
            raise Exception("No image URLs found in Firefly response")
        
        self.log(f"Generated {len(image_urls)} Firefly image(s)")
        return image_urls
    
    def upload_firefly_image(self, image_url: str, filename: str) -> str:
        """Download Firefly image and upload to S3, return presigned download URL."""
        self.log(f"Processing Firefly image: {filename}")
        
        # Download image from Firefly URL
        import requests
        response = requests.get(image_url)
        response.raise_for_status()
        
        # Save temporarily
        temp_path = Path("tmp") / filename
        temp_path.parent.mkdir(parents=True, exist_ok=True)
        with open(temp_path, 'wb') as f:
            f.write(response.content)
        
        # Upload to S3
        s3_key = f"firefly-images/{filename}"
        success = self.s3_manager.upload_file(str(temp_path), self.bucket, s3_key)
        if not success:
            raise Exception(f"Failed to upload Firefly image to S3: {filename}")
        
        # Generate Adobe-compatible presigned download URL
        download_url = self.s3_manager.generate_adobe_compatible_presigned_url(
            self.bucket, s3_key, expiration=7200, operation="get_object"
        )
        
        if not download_url:
            raise Exception("Failed to generate Adobe-compatible presigned download URL for Firefly image")
        
        # Clean up temp file
        temp_path.unlink()
        
        self.log(f"Firefly image processed and uploaded: {filename}")
        return download_url
    
    def create_rendition(self, input_url: str, output_filename: str) -> str:
        """Create PNG rendition and return output URL."""
        self.log(f"Creating rendition: {output_filename}")
        
        # Generate S3 key for output
        s3_key = f"renditions/{output_filename}"
        
        # Generate Adobe-compatible presigned upload URL
        output_url = self.s3_manager.generate_adobe_compatible_presigned_url(
            self.bucket, s3_key, expiration=7200, operation="put_object"
        )
        
        if not output_url:
            raise Exception("Failed to generate Adobe-compatible presigned upload URL for rendition")
        
        # Initiate rendition creation
        status_url = self.photoshop_api.create_rendition(input_url, output_url)
        
        # Poll for completion
        self.photoshop_api.poll_job_status(
            status_url, self.poll_interval, self.max_attempts, self.debug
        )
        
        # Generate Adobe-compatible download URL for the rendition
        # This is needed because we need to download the file locally
        download_url = self.s3_manager.generate_adobe_compatible_presigned_url(
            self.bucket, s3_key, expiration=7200, operation="get_object"
        )
        
        if not download_url:
            raise Exception("Failed to generate Adobe-compatible download URL for rendition")
        
        self.log(f"Rendition created: {output_filename}")
        return download_url
    
    def download_rendition(self, rendition_url: str, local_path: Path):
        """Download rendition from S3 to local path."""
        self.log(f"Downloading rendition to: {local_path}")
        
        # Download from S3
        import requests
        response = requests.get(rendition_url)
        response.raise_for_status()
        
        # Save to local path
        local_path.parent.mkdir(parents=True, exist_ok=True)
        with open(local_path, 'wb') as f:
            f.write(response.content)
        
        self.log(f"Rendition downloaded: {local_path}")
    
    def process_campaign_brief(self, campaign_brief: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single campaign brief through the complete pipeline."""
        self.log("="*80)
        self.log("Processing Campaign Brief")
        self.log("="*80)
        
        # Extract technical specs
        tech_specs = campaign_brief.get("technical_specs", {})
        template_name = tech_specs.get("template", "")
        aspect_ratio = tech_specs.get("aspect_ratio", "1x1")
        product_photo = tech_specs.get("product_photo", "")
        campaign_message = campaign_brief.get("campaign_message", "")
        
        if not template_name:
            raise Exception("Template name not found in technical_specs")
        
        results = {
            "campaign_brief": campaign_brief,
            "template_name": template_name,
            "aspect_ratio": aspect_ratio,
            "files_created": []
        }
        
        # Step 1: Upload template and create manifest
        template_path = Path("tmp/templates") / template_name
        if not template_path.exists():
            # Try in tmp/ directory
            template_path = Path("tmp") / template_name
        
        if not template_path.exists():
            raise Exception(f"Template file not found: {template_name}")
        
        template_url = self.upload_template_to_s3(template_path)
        manifest_file = f"tmp/manifests/{template_name.replace('.psd', '')}-manifest.json"
        manifest_data = self.create_document_manifest(template_url, manifest_file)
        
        # Step 2: Apply text edit
        text_output_filename = f"{template_name.replace('.psd', '')}-text.psd"
        text_output_url = self.apply_text_edit(template_url, "Campaign Message", campaign_message, text_output_filename)
        results["files_created"].append(text_output_filename)
        
        # Step 3: Apply product smart object replacement
        if product_photo:
            product_path = Path("tmp/images") / product_photo
            if not product_path.exists():
                # Try in tmp/ directory
                product_path = Path("tmp") / product_photo
            
            if product_path.exists():
                product_url = self.upload_product_image(product_path)
                product_output_filename = f"{template_name.replace('.psd', '')}-product.psd"
                product_output_url = self.apply_smart_object_replace(text_output_url, "Product", product_url, product_output_filename)
                results["files_created"].append(product_output_filename)
            else:
                self.log(f"Warning: Product image not found: {product_photo}", "WARNING")
                product_output_url = text_output_url  # Use text-edited template
        else:
            self.log("Warning: No product photo specified", "WARNING")
            product_output_url = text_output_url  # Use text-edited template
        
        # Step 4: Generate Firefly images (if not skipped)
        firefly_image_urls = []
        if not getattr(self, 'skip_firefly', False):
            try:
                firefly_image_urls = self.generate_firefly_images(campaign_brief)
            except Exception as e:
                self.log(f"Warning: Firefly image generation failed: {e}", "WARNING")
                firefly_image_urls = []
        
        # Step 5: Replace background images with Firefly images
        final_files = []
        if firefly_image_urls:
            for i, firefly_url in enumerate(firefly_image_urls):
                # Upload Firefly image to S3
                firefly_filename = f"firefly-bg-{i+1}.png"
                firefly_s3_url = self.upload_firefly_image(firefly_url, firefly_filename)
                
                # Replace background image
                final_filename = f"{template_name.replace('.psd', '')}-final-{i+1}.psd"
                final_url = self.apply_smart_object_replace(product_output_url, "Background Image", firefly_s3_url, final_filename)
                final_files.append((final_filename, final_url))
                results["files_created"].append(final_filename)
        else:
            # No Firefly images, use product file as final
            final_files.append((product_output_filename, product_output_url))
        
        # Step 6: Create renditions
        aspect_ratio_dir = self.output_dir / aspect_ratio
        aspect_ratio_dir.mkdir(parents=True, exist_ok=True)
        
        # Get SKU from campaign brief
        sku = "UNKNOWN"
        if "products" in campaign_brief and len(campaign_brief["products"]) > 0:
            sku = campaign_brief["products"][0].get("sku", "UNKNOWN")
        
        for i, (final_filename, final_url) in enumerate(final_files, 1):
            # New naming convention: {sku}-{aspect_ratio}-final-{number}.png
            rendition_filename = f"{sku}-{aspect_ratio}-final-{i}.png"
            rendition_url = self.create_rendition(final_url, rendition_filename)
            
            # Download rendition to output directory
            local_rendition_path = aspect_ratio_dir / rendition_filename
            self.download_rendition(rendition_url, local_rendition_path)
            results["files_created"].append(f"rendition: {rendition_filename}")
        
        self.log("Campaign brief processing completed successfully!")
        return results
    
    def run_pipeline(self, brief_files: List[str], skip_firefly: bool = False):
        """Run the complete campaign pipeline."""
        self.skip_firefly = skip_firefly
        
        self.log("Starting Campaign Automation Pipeline")
        self.log("="*80)
        
        # Load campaign briefs
        campaign_briefs = self.load_campaign_briefs(brief_files)
        
        # Process each brief
        all_results = []
        for i, brief in enumerate(campaign_briefs):
            try:
                result = self.process_campaign_brief(brief)
                all_results.append(result)
            except Exception as e:
                self.log(f"Error processing campaign brief {i+1}: {e}", "ERROR")
                continue
        
        # Summary
        self.log("="*80)
        self.log("Pipeline Summary")
        self.log("="*80)
        self.log(f"Processed {len(all_results)} campaign brief(s)")
        
        for i, result in enumerate(all_results):
            self.log(f"Brief {i+1}: {result['template_name']}")
            self.log(f"  Aspect Ratio: {result['aspect_ratio']}")
            self.log(f"  Files Created: {len(result['files_created'])}")
            for file in result['files_created']:
                self.log(f"    - {file}")
        
        self.log("Campaign automation pipeline completed!")


def interactive_mode() -> tuple:
    """Interactive mode to collect required parameters."""
    InteractiveModeHelper.print_header("Campaign Automation Pipeline")
    
    # Get brief files
    brief_files = []
    briefs_dir = Path("tmp/briefs")
    if briefs_dir.exists():
        available_briefs = list(briefs_dir.glob("*.json"))
        if available_briefs:
            print("Available campaign brief files:")
            for i, brief in enumerate(available_briefs, 1):
                print(f"  {i}. {brief.name}")
            
            use_all = InteractiveModeHelper.get_boolean("Use all available brief files?", default=True)
            if not use_all:
                choice = InteractiveModeHelper.get_integer(
                    "Select brief file number",
                    min_value=1,
                    max_value=len(available_briefs)
                )
                brief_files = [available_briefs[choice-1]]
            else:
                brief_files = available_briefs
        else:
            brief_file = InteractiveModeHelper.get_file_path("Enter path to campaign brief JSON file")
            brief_files = [brief_file]
    else:
        brief_file = InteractiveModeHelper.get_file_path("Enter path to campaign brief JSON file")
        brief_files = [brief_file]
    
    # Get S3 bucket
    bucket = InteractiveModeHelper.get_text_input("Enter S3 bucket name")
    
    # Get region
    region = InteractiveModeHelper.get_text_input(
        "Enter AWS region (default: us-east-1)",
        allow_empty=True
    ) or "us-east-1"
    
    # Get polling settings
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
    
    # Get debug mode
    debug = InteractiveModeHelper.get_boolean("Enable debug mode?", default=False)
    
    # Get skip Firefly option
    skip_firefly = InteractiveModeHelper.get_boolean("Skip Firefly image generation?", default=False)
    
    return brief_files, bucket, region, poll_interval, max_attempts, debug, skip_firefly


def main():
    """Main function to handle command line interface."""
    parser = argparse.ArgumentParser(
        description="Execute complete campaign automation pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python campaign_pipeline.py --bucket my-bucket
    python campaign_pipeline.py tmp/briefs/campaign_brief.json --bucket my-bucket
    python campaign_pipeline.py brief1.json brief2.json --bucket my-bucket --region us-west-2
    python campaign_pipeline.py --bucket my-bucket --skip-firefly
    python campaign_pipeline.py  # Interactive mode

Environment Variables:
    CLIENT_ID: Adobe Developer Console client ID
    CLIENT_SECRET: Adobe Developer Console client secret
    OPENAI_API_KEY: OpenAI API key for prompt generation
    AWS_ACCESS_KEY_ID: AWS access key ID
    AWS_SECRET_ACCESS_KEY: AWS secret access key
        """
    )
    
    parser.add_argument(
        'brief_files',
        nargs='*',
        help='Path(s) to campaign brief JSON file(s) (default: all files in tmp/briefs/)'
    )
    
    parser.add_argument(
        '--bucket',
        help='S3 bucket name for file operations (required)'
    )
    
    parser.add_argument(
        '--region',
        default='us-east-1',
        help='AWS region (default: us-east-1)'
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
        '--skip-firefly',
        action='store_true',
        help='Skip Firefly image generation step'
    )
    
    args = parser.parse_args()
    
    # Check if we should use interactive mode
    if not args.bucket:
        print("S3 bucket not specified. Starting interactive mode...")
        brief_files, bucket, region, poll_interval, max_attempts, debug, skip_firefly = interactive_mode()
    else:
        brief_files = args.brief_files
        bucket = args.bucket
        region = args.region
        poll_interval = args.poll_interval
        max_attempts = args.max_attempts
        debug = args.debug
        skip_firefly = args.skip_firefly
    
    try:
        # Initialize and run pipeline
        pipeline = CampaignPipeline(
            bucket=bucket,
            region=region,
            poll_interval=poll_interval,
            max_attempts=max_attempts,
            debug=debug
        )
        
        pipeline.run_pipeline(brief_files, skip_firefly)
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
