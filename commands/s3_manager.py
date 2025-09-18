#!/usr/bin/env python3
"""
Amazon S3 File Manager

A command-line tool for uploading and downloading files to/from Amazon S3, 
including presigned URL generation.

Features:
- Upload local files to S3
- Download S3 files to local tmp/ directory
- Generate presigned URLs for upload operations
- Generate presigned URLs for download operations
- Command-line interface with proper argument parsing
- Comprehensive error handling
- Environment variable support for AWS credentials

Usage:
    python s3_manager.py upload <local_file> <s3_bucket> <s3_key>
    python s3_manager.py download <s3_bucket> <s3_key>
    python s3_manager.py download <s3_bucket> <s3_key> --output <local_file>
    python s3_manager.py presigned-upload <s3_bucket> <s3_key>
    python s3_manager.py presigned-download <s3_bucket> <s3_key>
"""

import argparse
import os
import sys

# Add parent directory to path to import libs
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from libs.s3_manager import S3Manager
from libs.utils import InteractiveModeHelper


def interactive_mode():
    """Interactive mode to collect required parameters."""
    InteractiveModeHelper.print_header("Amazon S3 File Manager")
    
    # Get command
    print("Available commands:")
    print("1. upload - Upload a local file to S3")
    print("2. download - Download a file from S3")
    print("3. presigned-upload - Generate presigned URL for uploading")
    print("4. presigned-download - Generate presigned URL for downloading")
    print("5. public-url - Generate public S3 URL")
    print("6. adobe-presigned - Generate Adobe-compatible presigned URL")
    
    command_choice = InteractiveModeHelper.get_integer(
        "Enter command number (1-6)",
        min_value=1,
        max_value=6
    )
    
    command_map = {
        1: "upload",
        2: "download", 
        3: "presigned-upload",
        4: "presigned-download",
        5: "public-url",
        6: "adobe-presigned"
    }
    
    command = command_map[command_choice]
    
    # Get region
    region = InteractiveModeHelper.get_text_input(
        "Enter AWS region (default: us-east-1)",
        allow_empty=True
    ) or "us-east-1"
    
    # Get bucket
    bucket = InteractiveModeHelper.get_text_input("Enter S3 bucket name")
    
    # Get S3 key
    s3_key = InteractiveModeHelper.get_text_input("Enter S3 object key (path in bucket)")
    
    # Command-specific parameters
    if command == "upload":
        local_file = InteractiveModeHelper.get_file_path("Enter path to local file to upload")
        return command, local_file, bucket, s3_key, region, None, None, None
    
    elif command == "download":
        output = InteractiveModeHelper.get_text_input(
            "Enter local output path (default: tmp/<filename>)",
            allow_empty=True
        )
        return command, None, bucket, s3_key, region, output, None, None
    
    elif command == "presigned-upload":
        expiration = InteractiveModeHelper.get_integer(
            "Enter expiration time in seconds (default: 3600)",
            min_value=1,
            default=3600
        )
        
        content_type = InteractiveModeHelper.get_text_input(
            "Enter content type (optional, e.g., image/jpeg)",
            allow_empty=True
        )
        
        return command, None, bucket, s3_key, region, None, expiration, content_type
    
    elif command == "presigned-download":
        expiration = InteractiveModeHelper.get_integer(
            "Enter expiration time in seconds (default: 3600)",
            min_value=1,
            default=3600
        )
        
        return command, None, bucket, s3_key, region, None, expiration, None
    
    elif command == "public-url":
        return command, None, bucket, s3_key, region, None, None, None
    
    elif command == "adobe-presigned":
        operation = InteractiveModeHelper.get_choice(
            "Enter operation (get_object/put_object, default: get_object)",
            ["get_object", "put_object"],
            "get_object"
        )
        
        expiration = InteractiveModeHelper.get_integer(
            "Enter expiration time in seconds (default: 7200)",
            min_value=1,
            default=7200
        )
        
        return command, None, bucket, s3_key, region, None, expiration, operation


def main():
    """Main function to handle command-line arguments and execute operations."""
    parser = argparse.ArgumentParser(
        description="Amazon S3 File Manager - Upload and download files to/from S3",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Upload a local file to S3
  python s3_manager.py upload ./myfile.txt my-bucket path/to/myfile.txt
  
  # Download a file from S3 to tmp/ directory
  python s3_manager.py download my-bucket path/to/myfile.txt
  
  # Download a file from S3 to specific local path
  python s3_manager.py download my-bucket path/to/myfile.txt --output ./downloaded_file.txt
  
  # Generate presigned URL for uploading
  python s3_manager.py presigned-upload my-bucket path/to/myfile.txt
  
  # Generate presigned URL for downloading
  python s3_manager.py presigned-download my-bucket path/to/myfile.txt
  
  # Generate presigned upload URL with custom expiration and content type
  python s3_manager.py presigned-upload my-bucket path/to/image.jpg --expiration 7200 --content-type image/jpeg
  
  # Generate public URL for Adobe API compatibility
  python s3_manager.py public-url my-bucket path/to/file.txt
  
  # Generate Adobe-compatible presigned URL for smart object replacement
  python s3_manager.py adobe-presigned my-bucket path/to/smart-object.png --operation get_object --expiration 7200
  
  # Upload with custom region
  python s3_manager.py upload ./myfile.txt my-bucket path/to/myfile.txt --region us-west-2
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Upload command
    upload_parser = subparsers.add_parser('upload', help='Upload a local file to S3')
    upload_parser.add_argument('local_file', help='Path to the local file to upload')
    upload_parser.add_argument('bucket', help='S3 bucket name')
    upload_parser.add_argument('s3_key', help='S3 object key (path in bucket)')
    upload_parser.add_argument('--region', default='us-east-1', help='AWS region (default: us-east-1)')
    
    # Download command
    download_parser = subparsers.add_parser('download', help='Download a file from S3')
    download_parser.add_argument('bucket', help='S3 bucket name')
    download_parser.add_argument('s3_key', help='S3 object key (path in bucket)')
    download_parser.add_argument('--output', help='Local file path (default: tmp/<filename>)')
    download_parser.add_argument('--region', default='us-east-1', help='AWS region (default: us-east-1)')
    
    # Presigned upload URL command
    presigned_upload_parser = subparsers.add_parser('presigned-upload', help='Generate a presigned URL for uploading to S3')
    presigned_upload_parser.add_argument('bucket', help='S3 bucket name')
    presigned_upload_parser.add_argument('s3_key', help='S3 object key (path in bucket)')
    presigned_upload_parser.add_argument('--expiration', type=int, default=3600, help='URL expiration time in seconds (default: 3600)')
    presigned_upload_parser.add_argument('--content-type', help='MIME type of the file (e.g., image/jpeg, application/pdf)')
    presigned_upload_parser.add_argument('--region', default='us-east-1', help='AWS region (default: us-east-1)')
    
    # Presigned download URL command
    presigned_download_parser = subparsers.add_parser('presigned-download', help='Generate a presigned URL for downloading from S3')
    presigned_download_parser.add_argument('bucket', help='S3 bucket name')
    presigned_download_parser.add_argument('s3_key', help='S3 object key (path in bucket)')
    presigned_download_parser.add_argument('--expiration', type=int, default=3600, help='URL expiration time in seconds (default: 3600)')
    presigned_download_parser.add_argument('--region', default='us-east-1', help='AWS region (default: us-east-1)')
    
    # Public URL command (for Adobe API compatibility)
    public_url_parser = subparsers.add_parser('public-url', help='Generate a public S3 URL (requires object to be public)')
    public_url_parser.add_argument('bucket', help='S3 bucket name')
    public_url_parser.add_argument('s3_key', help='S3 object key (path in bucket)')
    public_url_parser.add_argument('--region', default='us-east-1', help='AWS region (default: us-east-1)')
    
    # Adobe-compatible presigned URL command
    adobe_presigned_parser = subparsers.add_parser('adobe-presigned', help='Generate Adobe-compatible presigned URL')
    adobe_presigned_parser.add_argument('bucket', help='S3 bucket name')
    adobe_presigned_parser.add_argument('s3_key', help='S3 object key (path in bucket)')
    adobe_presigned_parser.add_argument('--operation', choices=['get_object', 'put_object'], default='get_object', help='S3 operation (default: get_object)')
    adobe_presigned_parser.add_argument('--expiration', type=int, default=7200, help='URL expiration time in seconds (default: 7200 = 2 hours)')
    adobe_presigned_parser.add_argument('--region', default='us-east-1', help='AWS region (default: us-east-1)')
    
    args = parser.parse_args()
    
    # Check if we should use interactive mode (when no command provided)
    if not args.command:
        print("No command provided. Starting interactive mode...")
        command, local_file, bucket, s3_key, region, output, expiration, extra_param = interactive_mode()
        
        # Initialize S3 manager
        s3_manager = S3Manager(region_name=region)
        
        # Execute command based on interactive input
        if command == 'upload':
            success = s3_manager.upload_file(local_file, bucket, s3_key)
        elif command == 'download':
            success = s3_manager.download_file(bucket, s3_key, output)
        elif command == 'presigned-upload':
            presigned_url = s3_manager.generate_presigned_upload_url(
                bucket, s3_key, expiration, extra_param
            )
            if presigned_url:
                print(f"\n🔗 Presigned Upload URL:")
                print(f"{presigned_url}")
                print(f"\n📝 Usage: Use this URL with PUT request to upload your file")
                print(f"⏰ URL expires in {expiration} seconds ({expiration/3600:.1f} hours)")
                success = True
            else:
                success = False
        elif command == 'presigned-download':
            presigned_url = s3_manager.generate_presigned_download_url(
                bucket, s3_key, expiration
            )
            if presigned_url:
                print(f"\n🔗 Presigned Download URL:")
                print(f"{presigned_url}")
                print(f"\n📝 Usage: Use this URL with GET request to download the file")
                print(f"⏰ URL expires in {expiration} seconds ({expiration/3600:.1f} hours)")
                success = True
            else:
                success = False
        elif command == 'public-url':
            public_url = s3_manager.generate_public_url(bucket, s3_key)
            if public_url:
                print(f"\n🔗 Public S3 URL:")
                print(f"{public_url}")
                print(f"\n📝 Usage: Use this URL with Adobe APIs (requires object to be public)")
                print(f"⚠️  Make sure the object is public before using with Adobe APIs")
                success = True
            else:
                success = False
        elif command == 'adobe-presigned':
            adobe_url = s3_manager.generate_adobe_compatible_presigned_url(
                bucket, s3_key, expiration, extra_param
            )
            if adobe_url:
                print(f"\n🔗 Adobe-Compatible Presigned URL:")
                print(f"{adobe_url}")
                print(f"\n📝 Usage: Use this URL with Adobe APIs")
                print(f"⏰ URL expires in {expiration} seconds ({expiration/3600:.1f} hours)")
                print(f"🔧 Operation: {extra_param}")
                print(f"⚠️  Ensure your bucket policy allows Adobe API access")
                success = True
            else:
                success = False
        
        # Exit with appropriate code
        sys.exit(0 if success else 1)
    
    # Initialize S3 manager
    s3_manager = S3Manager(region_name=args.region)
    
    # Execute command
    if args.command == 'upload':
        success = s3_manager.upload_file(args.local_file, args.bucket, args.s3_key)
    elif args.command == 'download':
        success = s3_manager.download_file(args.bucket, args.s3_key, args.output)
    elif args.command == 'presigned-upload':
        presigned_url = s3_manager.generate_presigned_upload_url(
            args.bucket, 
            args.s3_key, 
            args.expiration, 
            args.content_type
        )
        if presigned_url:
            print(f"\n🔗 Presigned Upload URL:")
            print(f"{presigned_url}")
            print(f"\n📝 Usage: Use this URL with PUT request to upload your file")
            print(f"⏰ URL expires in {args.expiration} seconds ({args.expiration/3600:.1f} hours)")
            success = True
        else:
            success = False
    elif args.command == 'presigned-download':
        presigned_url = s3_manager.generate_presigned_download_url(
            args.bucket, 
            args.s3_key, 
            args.expiration
        )
        if presigned_url:
            print(f"\n🔗 Presigned Download URL:")
            print(f"{presigned_url}")
            print(f"\n📝 Usage: Use this URL with GET request to download the file")
            print(f"⏰ URL expires in {args.expiration} seconds ({args.expiration/3600:.1f} hours)")
            success = True
        else:
            success = False
    elif args.command == 'public-url':
        public_url = s3_manager.generate_public_url(args.bucket, args.s3_key)
        if public_url:
            print(f"\n🔗 Public S3 URL:")
            print(f"{public_url}")
            print(f"\n📝 Usage: Use this URL with Adobe APIs (requires object to be public)")
            print(f"⚠️  Make sure the object is public before using with Adobe APIs")
            success = True
        else:
            success = False
    elif args.command == 'adobe-presigned':
        adobe_url = s3_manager.generate_adobe_compatible_presigned_url(
            args.bucket, 
            args.s3_key, 
            args.expiration, 
            args.operation
        )
        if adobe_url:
            print(f"\n🔗 Adobe-Compatible Presigned URL:")
            print(f"{adobe_url}")
            print(f"\n📝 Usage: Use this URL with Adobe APIs")
            print(f"⏰ URL expires in {args.expiration} seconds ({args.expiration/3600:.1f} hours)")
            print(f"🔧 Operation: {args.operation}")
            print(f"⚠️  Ensure your bucket policy allows Adobe API access")
            success = True
        else:
            success = False
    else:
        print(f"❌ Unknown command: {args.command}")
        sys.exit(1)
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
