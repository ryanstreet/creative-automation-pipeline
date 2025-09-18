#!/usr/bin/env python3
"""
Creative Automation Pipeline (CAP) - Unified Command Entrypoint

This is the main entrypoint for the Creative Automation Pipeline. It provides
a unified interface to all available commands through a single command-line tool.

Usage:
    python cap.py <command> [command-options]
    
Available Commands:
    campaign-prompt     Generate Adobe Firefly prompts from campaign briefs
    firefly-image       Generate images using Adobe Firefly API
    photoshop-manifest  Retrieve Photoshop document manifests
    smart-object        Replace smart objects in PSD files
    text-layer          Edit text layers in PSD files
    rendition           Create PNG renditions from PSD files
    s3                  Manage S3 file operations
    rate-limit          Display rate limiting status for all APIs

Examples:
    python cap.py campaign-prompt tmp/campaign_brief.json
    python cap.py firefly-image "a beautiful sunset"
    python cap.py photoshop-manifest https://example.com/file.psd
    python cap.py smart-object --manifest manifest.json --layer "Logo"
    python cap.py text-layer --input-url url --layer "Title" --text "New Text"
    python cap.py rendition --input-url url --output-url url
    python cap.py s3 upload file.txt bucket key
    python cap.py rate-limit --detailed
"""

import sys
import os
import argparse
from pathlib import Path

# Add commands directory to path
commands_dir = Path(__file__).parent / "commands"
sys.path.insert(0, str(commands_dir))

# Import all command modules
try:
    import campaign_prompt_generator
    import firefly_image_generator
    import photoshop_manifest
    import smart_object_replacer
    import text_layer_editor
    import psd_rendition_creator
    import s3_manager
    import rate_limit_status
    import campaign_pipeline
except ImportError as e:
    print(f"Error importing command modules: {e}")
    sys.exit(1)


def create_command_parser():
    """Create the main argument parser with subcommands."""
    parser = argparse.ArgumentParser(
        prog='cap.py',
        description='Creative Automation Pipeline - Unified Command Interface',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Available Commands:
  campaign-prompt     Generate Adobe Firefly prompts from campaign briefs
  firefly-image       Generate images using Adobe Firefly API  
  photoshop-manifest  Retrieve Photoshop document manifests or list layers from local manifests
  smart-object        Replace smart objects in PSD files
  text-layer          Edit text layers in PSD files
  rendition           Create PNG renditions from PSD files
  s3                  Manage S3 file operations
  rate-limit          Display rate limiting status for all APIs
  campaign-pipeline   Execute complete campaign automation pipeline

For detailed help on any command, use:
  python cap.py <command> --help
        """
    )
    
    subparsers = parser.add_subparsers(
        dest='command',
        help='Available commands',
        metavar='<command>'
    )
    
    # Campaign Prompt Generator
    campaign_parser = subparsers.add_parser(
        'campaign-prompt',
        help='Generate Adobe Firefly prompts from campaign briefs',
        description='Parse campaign brief JSON files and generate Adobe Firefly prompts using OpenAI API'
    )
    campaign_parser.add_argument(
        'json_file',
        nargs='?',
        help='Path to the campaign brief JSON file (e.g., tmp/campaign_brief.json)'
    )
    campaign_parser.add_argument(
        '--model',
        help='OpenAI model to use (default: gpt-4)',
        default='gpt-4',
        choices=['gpt-4', 'gpt-4-turbo', 'gpt-3.5-turbo']
    )
    
    # Firefly Image Generator
    firefly_parser = subparsers.add_parser(
        'firefly-image',
        help='Generate images using Adobe Firefly API',
        description='Generate images based on text prompts using Adobe Firefly API V3'
    )
    firefly_parser.add_argument(
        'prompt',
        nargs='?',
        help='Text prompt for image generation'
    )
    firefly_parser.add_argument(
        '--num-variations',
        type=int,
        default=1,
        help='Number of image variations to generate (default: 1)'
    )
    firefly_parser.add_argument(
        '--width',
        type=int,
        default=1024,
        help='Image width in pixels (default: 1024)'
    )
    firefly_parser.add_argument(
        '--height',
        type=int,
        default=1024,
        help='Image height in pixels (default: 1024)'
    )
    firefly_parser.add_argument(
        '--locale',
        dest='prompt_biasing_locale_code',
        default='en-US',
        help='Prompt biasing locale code (default: en-US)'
    )
    firefly_parser.add_argument(
        '--content-class',
        default='photo',
        choices=['photo', 'art', 'design'],
        help='Content class for the generated images (default: photo)'
    )
    firefly_parser.add_argument(
        '--poll-interval',
        type=int,
        default=5,
        help='Polling interval in seconds (default: 5)'
    )
    firefly_parser.add_argument(
        '--max-attempts',
        type=int,
        default=120,
        help='Maximum polling attempts before timeout (default: 120)'
    )
    firefly_parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug output with detailed API responses'
    )
    
    # Photoshop Manifest
    manifest_parser = subparsers.add_parser(
        'photoshop-manifest',
        help='Retrieve Photoshop document manifests or list layers from local manifests',
        description='Retrieve document manifests from PSD files using Adobe Photoshop API or list layers from local manifest files'
    )
    manifest_parser.add_argument(
        'input_url',
        nargs='?',
        help='URL of the PSD file to process'
    )
    manifest_parser.add_argument(
        '--output-file',
        default='tmp/document_manifest.json',
        help='Output JSON file path (default: tmp/document_manifest.json)'
    )
    manifest_parser.add_argument(
        '--poll-interval',
        type=int,
        default=5,
        help='Polling interval in seconds (default: 5)'
    )
    manifest_parser.add_argument(
        '--max-attempts',
        type=int,
        default=120,
        help='Maximum polling attempts before timeout (default: 120)'
    )
    manifest_parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug output with detailed API responses'
    )
    manifest_parser.add_argument(
        '--list-layers',
        metavar='MANIFEST_FILE',
        help='List all layer names from an existing manifest JSON file (local file path)'
    )
    manifest_parser.add_argument(
        '--list-manifests',
        action='store_true',
        help='List all available manifest files in the tmp directory'
    )
    
    # Smart Object Replacer
    smart_object_parser = subparsers.add_parser(
        'smart-object',
        help='Replace smart objects in PSD files',
        description='Replace smart objects in PSD files using Adobe Firefly Services Photoshop API'
    )
    smart_object_parser.add_argument(
        '--manifest',
        help='Path to the document manifest JSON file'
    )
    smart_object_parser.add_argument(
        '--layer',
        help='Name of the layer to replace'
    )
    smart_object_parser.add_argument(
        '--smart-object-url',
        help='S3 URL of the new smart object'
    )
    smart_object_parser.add_argument(
        '--output-url',
        help='S3 URL for the output file'
    )
    smart_object_parser.add_argument(
        '--poll-interval',
        type=int,
        default=5,
        help='Polling interval in seconds (default: 5)'
    )
    smart_object_parser.add_argument(
        '--max-attempts',
        type=int,
        default=120,
        help='Maximum polling attempts before timeout (default: 120)'
    )
    smart_object_parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug output with detailed API responses'
    )
    
    # Text Layer Editor
    text_parser = subparsers.add_parser(
        'text-layer',
        help='Edit text layers in PSD files',
        description='Edit text layers in PSD files using Adobe Firefly Services Photoshop API'
    )
    text_parser.add_argument(
        '--input-url',
        help='URL of the input PSD file'
    )
    text_parser.add_argument(
        '--layer',
        help='Name of the text layer to edit'
    )
    text_parser.add_argument(
        '--text',
        help='Replacement text content'
    )
    text_parser.add_argument(
        '--output-url',
        help='URL for the output file'
    )
    text_parser.add_argument(
        '--poll-interval',
        type=int,
        default=5,
        help='Polling interval in seconds (default: 5)'
    )
    text_parser.add_argument(
        '--max-attempts',
        type=int,
        default=120,
        help='Maximum polling attempts before timeout (default: 120)'
    )
    text_parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug output with detailed API responses'
    )
    
    # Rendition Creator
    rendition_parser = subparsers.add_parser(
        'rendition',
        help='Create PNG renditions from PSD files',
        description='Create PNG renditions of PSD files using Adobe Photoshop API'
    )
    rendition_parser.add_argument(
        '--input-url',
        help='AWS presigned download URL for the PSD file'
    )
    rendition_parser.add_argument(
        '--output-url',
        help='AWS presigned upload URL for the PNG output'
    )
    rendition_parser.add_argument(
        '--poll-interval',
        type=int,
        default=5,
        help='Polling interval in seconds (default: 5)'
    )
    rendition_parser.add_argument(
        '--max-attempts',
        type=int,
        default=120,
        help='Maximum polling attempts before timeout (default: 120)'
    )
    rendition_parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug output with detailed API responses'
    )
    
    # S3 Manager
    s3_parser = subparsers.add_parser(
        's3',
        help='Manage S3 file operations',
        description='Upload, download, and generate presigned URLs for S3 operations'
    )
    s3_subparsers = s3_parser.add_subparsers(
        dest='s3_command',
        help='S3 operations',
        metavar='<s3-command>'
    )
    
    # S3 Upload
    upload_parser = s3_subparsers.add_parser('upload', help='Upload a local file to S3')
    upload_parser.add_argument('local_file', help='Path to the local file to upload')
    upload_parser.add_argument('bucket', help='S3 bucket name')
    upload_parser.add_argument('s3_key', help='S3 object key (path in bucket)')
    upload_parser.add_argument('--region', default='us-east-1', help='AWS region (default: us-east-1)')
    
    # S3 Download
    download_parser = s3_subparsers.add_parser('download', help='Download a file from S3')
    download_parser.add_argument('bucket', help='S3 bucket name')
    download_parser.add_argument('s3_key', help='S3 object key (path in bucket)')
    download_parser.add_argument('--output', help='Local file path (default: tmp/<filename>)')
    download_parser.add_argument('--region', default='us-east-1', help='AWS region (default: us-east-1)')
    
    # S3 Presigned Upload
    presigned_upload_parser = s3_subparsers.add_parser('presigned-upload', help='Generate presigned URL for uploading')
    presigned_upload_parser.add_argument('bucket', help='S3 bucket name')
    presigned_upload_parser.add_argument('s3_key', help='S3 object key (path in bucket)')
    presigned_upload_parser.add_argument('--expiration', type=int, default=3600, help='URL expiration time in seconds (default: 3600)')
    presigned_upload_parser.add_argument('--content-type', help='MIME type of the file')
    presigned_upload_parser.add_argument('--region', default='us-east-1', help='AWS region (default: us-east-1)')
    
    # S3 Presigned Download
    presigned_download_parser = s3_subparsers.add_parser('presigned-download', help='Generate presigned URL for downloading')
    presigned_download_parser.add_argument('bucket', help='S3 bucket name')
    presigned_download_parser.add_argument('s3_key', help='S3 object key (path in bucket)')
    presigned_download_parser.add_argument('--expiration', type=int, default=3600, help='URL expiration time in seconds (default: 3600)')
    presigned_download_parser.add_argument('--region', default='us-east-1', help='AWS region (default: us-east-1)')
    
    # S3 Public URL
    public_url_parser = s3_subparsers.add_parser('public-url', help='Generate public S3 URL')
    public_url_parser.add_argument('bucket', help='S3 bucket name')
    public_url_parser.add_argument('s3_key', help='S3 object key (path in bucket)')
    public_url_parser.add_argument('--region', default='us-east-1', help='AWS region (default: us-east-1)')
    
    # S3 Adobe Presigned
    adobe_presigned_parser = s3_subparsers.add_parser('adobe-presigned', help='Generate Adobe-compatible presigned URL')
    adobe_presigned_parser.add_argument('bucket', help='S3 bucket name')
    adobe_presigned_parser.add_argument('s3_key', help='S3 object key (path in bucket)')
    adobe_presigned_parser.add_argument('--operation', choices=['get_object', 'put_object'], default='get_object', help='S3 operation (default: get_object)')
    adobe_presigned_parser.add_argument('--expiration', type=int, default=7200, help='URL expiration time in seconds (default: 7200)')
    adobe_presigned_parser.add_argument('--region', default='us-east-1', help='AWS region (default: us-east-1)')
    
    # Rate Limit Status
    rate_limit_parser = subparsers.add_parser(
        'rate-limit',
        help='Display rate limiting status for all APIs',
        description='Display current rate limiting status and configuration for all APIs'
    )
    rate_limit_parser.add_argument(
        '--json',
        action='store_true',
        help='Output status in JSON format'
    )
    rate_limit_parser.add_argument(
        '--detailed',
        action='store_true',
        help='Show detailed information about each rate limiter'
    )
    
    # Full Campaign Pipeline
    pipeline_parser = subparsers.add_parser(
        'campaign-pipeline',
        help='Execute complete campaign automation pipeline',
        description='Execute the complete campaign automation pipeline: parse briefs, upload templates, create manifests, apply edits, generate images, and create renditions'
    )
    pipeline_parser.add_argument(
        'brief_files',
        nargs='*',
        help='Path(s) to campaign brief JSON file(s) (default: all files in tmp/briefs/)'
    )
    pipeline_parser.add_argument(
        '--bucket',
        help='S3 bucket name for file operations (required)'
    )
    pipeline_parser.add_argument(
        '--region',
        default='us-east-1',
        help='AWS region (default: us-east-1)'
    )
    pipeline_parser.add_argument(
        '--poll-interval',
        type=int,
        default=5,
        help='Polling interval in seconds (default: 5)'
    )
    pipeline_parser.add_argument(
        '--max-attempts',
        type=int,
        default=120,
        help='Maximum polling attempts before timeout (default: 120)'
    )
    pipeline_parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug output with detailed API responses'
    )
    pipeline_parser.add_argument(
        '--skip-firefly',
        action='store_true',
        help='Skip Firefly image generation step'
    )
    
    return parser


def build_campaign_prompt_args(args):
    """Build arguments for campaign prompt generator."""
    sys.argv = ['campaign_prompt_generator.py']
    if args.json_file:
        sys.argv.append(args.json_file)
    if args.model != 'gpt-4':
        sys.argv.extend(['--model', args.model])


def build_firefly_image_args(args):
    """Build arguments for firefly image generator."""
    sys.argv = ['firefly_image_generator.py']
    if args.prompt:
        sys.argv.append(args.prompt)
    if args.num_variations != 1:
        sys.argv.extend(['--num-variations', str(args.num_variations)])
    if args.width != 1024:
        sys.argv.extend(['--width', str(args.width)])
    if args.height != 1024:
        sys.argv.extend(['--height', str(args.height)])
    if args.prompt_biasing_locale_code != 'en-US':
        sys.argv.extend(['--locale', args.prompt_biasing_locale_code])
    if args.content_class != 'photo':
        sys.argv.extend(['--content-class', args.content_class])
    if args.poll_interval != 5:
        sys.argv.extend(['--poll-interval', str(args.poll_interval)])
    if args.max_attempts != 120:
        sys.argv.extend(['--max-attempts', str(args.max_attempts)])
    if args.debug:
        sys.argv.append('--debug')


def build_photoshop_manifest_args(args):
    """Build arguments for photoshop manifest."""
    sys.argv = ['photoshop_manifest.py']
    if args.input_url:
        sys.argv.append(args.input_url)
    if args.output_file != 'tmp/document_manifest.json':
        sys.argv.extend(['--output-file', args.output_file])
    if args.poll_interval != 5:
        sys.argv.extend(['--poll-interval', str(args.poll_interval)])
    if args.max_attempts != 120:
        sys.argv.extend(['--max-attempts', str(args.max_attempts)])
    if args.debug:
        sys.argv.append('--debug')
    if args.list_layers:
        sys.argv.extend(['--list-layers', args.list_layers])
    if args.list_manifests:
        sys.argv.append('--list-manifests')


def build_smart_object_args(args):
    """Build arguments for smart object replacer."""
    sys.argv = ['smart_object_replacer.py']
    if args.manifest:
        sys.argv.extend(['--manifest', args.manifest])
    if args.layer:
        sys.argv.extend(['--layer', args.layer])
    if args.smart_object_url:
        sys.argv.extend(['--smart-object-url', args.smart_object_url])
    if args.output_url:
        sys.argv.extend(['--output-url', args.output_url])
    if args.poll_interval != 5:
        sys.argv.extend(['--poll-interval', str(args.poll_interval)])
    if args.max_attempts != 120:
        sys.argv.extend(['--max-attempts', str(args.max_attempts)])
    if args.debug:
        sys.argv.append('--debug')


def build_text_layer_args(args):
    """Build arguments for text layer editor."""
    sys.argv = ['text_layer_editor.py']
    if args.input_url:
        sys.argv.extend(['--input-url', args.input_url])
    if args.layer:
        sys.argv.extend(['--layer', args.layer])
    if args.text:
        sys.argv.extend(['--text', args.text])
    if args.output_url:
        sys.argv.extend(['--output-url', args.output_url])
    if args.poll_interval != 5:
        sys.argv.extend(['--poll-interval', str(args.poll_interval)])
    if args.max_attempts != 120:
        sys.argv.extend(['--max-attempts', str(args.max_attempts)])
    if args.debug:
        sys.argv.append('--debug')


def build_rendition_args(args):
    """Build arguments for rendition creator."""
    sys.argv = ['psd_rendition_creator.py']
    if args.input_url:
        sys.argv.extend(['--input-url', args.input_url])
    if args.output_url:
        sys.argv.extend(['--output-url', args.output_url])
    if args.poll_interval != 5:
        sys.argv.extend(['--poll-interval', str(args.poll_interval)])
    if args.max_attempts != 120:
        sys.argv.extend(['--max-attempts', str(args.max_attempts)])
    if args.debug:
        sys.argv.append('--debug')


def build_s3_args(args):
    """Build arguments for S3 manager."""
    sys.argv = ['s3_manager.py', args.s3_command]
    
    if args.s3_command == 'upload':
        sys.argv.extend([args.local_file, args.bucket, args.s3_key])
        if args.region != 'us-east-1':
            sys.argv.extend(['--region', args.region])
    elif args.s3_command == 'download':
        sys.argv.extend([args.bucket, args.s3_key])
        if args.output:
            sys.argv.extend(['--output', args.output])
        if args.region != 'us-east-1':
            sys.argv.extend(['--region', args.region])
    elif args.s3_command == 'presigned-upload':
        sys.argv.extend([args.bucket, args.s3_key])
        if args.expiration != 3600:
            sys.argv.extend(['--expiration', str(args.expiration)])
        if args.content_type:
            sys.argv.extend(['--content-type', args.content_type])
        if args.region != 'us-east-1':
            sys.argv.extend(['--region', args.region])
    elif args.s3_command == 'presigned-download':
        sys.argv.extend([args.bucket, args.s3_key])
        if args.expiration != 3600:
            sys.argv.extend(['--expiration', str(args.expiration)])
        if args.region != 'us-east-1':
            sys.argv.extend(['--region', args.region])
    elif args.s3_command == 'public-url':
        sys.argv.extend([args.bucket, args.s3_key])
        if args.region != 'us-east-1':
            sys.argv.extend(['--region', args.region])
    elif args.s3_command == 'adobe-presigned':
        sys.argv.extend([args.bucket, args.s3_key])
        if args.operation != 'get_object':
            sys.argv.extend(['--operation', args.operation])
        if args.expiration != 7200:
            sys.argv.extend(['--expiration', str(args.expiration)])
        if args.region != 'us-east-1':
            sys.argv.extend(['--region', args.region])


def build_rate_limit_args(args):
    """Build arguments for rate limit status."""
    sys.argv = ['rate_limit_status.py']
    if args.json:
        sys.argv.append('--json')
    if args.detailed:
        sys.argv.append('--detailed')


def build_campaign_pipeline_args(args):
    """Build arguments for campaign pipeline."""
    sys.argv = ['campaign_pipeline.py']
    if args.brief_files:
        sys.argv.extend(args.brief_files)
    if args.bucket:
        sys.argv.extend(['--bucket', args.bucket])
    if args.region != 'us-east-1':
        sys.argv.extend(['--region', args.region])
    if args.poll_interval != 5:
        sys.argv.extend(['--poll-interval', str(args.poll_interval)])
    if args.max_attempts != 120:
        sys.argv.extend(['--max-attempts', str(args.max_attempts)])
    if args.debug:
        sys.argv.append('--debug')
    if args.skip_firefly:
        sys.argv.append('--skip-firefly')


def execute_command(command, args):
    """Execute the specified command with the given arguments using dispatch pattern."""
    # Command dispatch table
    command_handlers = {
        'campaign-prompt': {
            'build_args': build_campaign_prompt_args,
            'execute': campaign_prompt_generator.main
        },
        'firefly-image': {
            'build_args': build_firefly_image_args,
            'execute': firefly_image_generator.main
        },
        'photoshop-manifest': {
            'build_args': build_photoshop_manifest_args,
            'execute': photoshop_manifest.main
        },
        'smart-object': {
            'build_args': build_smart_object_args,
            'execute': smart_object_replacer.main
        },
        'text-layer': {
            'build_args': build_text_layer_args,
            'execute': text_layer_editor.main
        },
        'rendition': {
            'build_args': build_rendition_args,
            'execute': psd_rendition_creator.main
        },
        's3': {
            'build_args': build_s3_args,
            'execute': s3_manager.main
        },
        'rate-limit': {
            'build_args': build_rate_limit_args,
            'execute': rate_limit_status.main
        },
        'campaign-pipeline': {
            'build_args': build_campaign_pipeline_args,
            'execute': campaign_pipeline.main
        }
    }
    
    # Get command handler
    handler = command_handlers.get(command)
    if not handler:
        print(f"Unknown command: {command}")
        return 1
    
    try:
        # Build arguments and execute command
        handler['build_args'](args)
        handler['execute']()
        return 0
    except Exception as e:
        print(f"Error executing command '{command}': {e}")
        return 1


def main():
    """Main entrypoint for the Creative Automation Pipeline."""
    parser = create_command_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    return execute_command(args.command, args)


if __name__ == "__main__":
    sys.exit(main())
