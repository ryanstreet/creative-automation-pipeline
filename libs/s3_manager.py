#!/usr/bin/env python3
"""
AWS S3 Library

This library provides a unified interface for Amazon S3 operations including:
- File upload and download
- Presigned URL generation
- Public URL generation
- Adobe-compatible presigned URLs

All operations use boto3 with proper error handling and validation.
"""

import os
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from botocore.config import Config
from pathlib import Path
from typing import Optional

from .config import Config as AppConfig
from .rate_limiter import rate_limiter, rate_limit


class S3Manager:
    """Amazon S3 file manager for upload and download operations."""
    
    def __init__(self, region_name: str = None, debug: bool = False):
        """
        Initialize S3 manager.
        
        Args:
            region_name (str): AWS region name (default: from config)
            debug (bool): Enable debug output (default: False)
        """
        self.region_name = region_name or AppConfig.DEFAULT_REGION
        self.debug = debug
        self.s3_client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize S3 client with proper error handling."""
        try:
            # Initialize S3 client with signature version 4 for proper presigned URLs
            self.s3_client = boto3.client(
                's3', 
                region_name=self.region_name,
                config=Config(signature_version='s3v4')
            )
            # Test credentials by listing buckets
            self.s3_client.list_buckets()
            print("✅ AWS credentials validated successfully!")
        except NoCredentialsError:
            print("❌ Error: AWS credentials not found!")
            print("Please set up your AWS credentials using one of these methods:")
            print("1. AWS CLI: aws configure")
            print("2. Environment variables: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY")
            print("3. IAM roles (if running on EC2)")
            raise
        except ClientError as e:
            print(f"❌ Error initializing S3 client: {e}")
            raise
    
    @rate_limit("s3_operations", wait=True)
    def upload_file(self, local_file_path: str, bucket_name: str, s3_key: str) -> bool:
        """
        Upload a local file to S3.
        
        Args:
            local_file_path (str): Path to the local file
            bucket_name (str): Name of the S3 bucket
            s3_key (str): S3 object key (path in bucket)
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Validate local file exists
            if not os.path.exists(local_file_path):
                print(f"❌ Error: Local file '{local_file_path}' does not exist!")
                return False
            
            # Validate bucket exists
            if not self._bucket_exists(bucket_name):
                print(f"❌ Error: Bucket '{bucket_name}' does not exist or is not accessible!")
                return False
            
            print(f"📤 Uploading '{local_file_path}' to s3://{bucket_name}/{s3_key}")
            
            # Upload file
            self.s3_client.upload_file(local_file_path, bucket_name, s3_key)
            
            print(f"✅ Successfully uploaded '{local_file_path}' to s3://{bucket_name}/{s3_key}")
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchBucket':
                print(f"❌ Error: Bucket '{bucket_name}' does not exist!")
            elif error_code == 'AccessDenied':
                print(f"❌ Error: Access denied to bucket '{bucket_name}'!")
            else:
                print(f"❌ Error uploading file: {e}")
            return False
        except Exception as e:
            print(f"❌ Unexpected error during upload: {e}")
            return False
    
    @rate_limit("s3_operations", wait=True)
    def download_file(self, bucket_name: str, s3_key: str, local_file_path: Optional[str] = None) -> bool:
        """
        Download a file from S3 to local storage.
        
        Args:
            bucket_name (str): Name of the S3 bucket
            s3_key (str): S3 object key (path in bucket)
            local_file_path (str, optional): Local file path. If None, uses tmp/ directory
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Validate bucket exists
            if not self._bucket_exists(bucket_name):
                print(f"❌ Error: Bucket '{bucket_name}' does not exist or is not accessible!")
                return False
            
            # Set default local file path if not provided
            if local_file_path is None:
                # Create tmp directory if it doesn't exist
                tmp_dir = Path("tmp")
                tmp_dir.mkdir(exist_ok=True)
                
                # Extract filename from S3 key
                filename = os.path.basename(s3_key)
                if not filename:
                    filename = "downloaded_file"
                
                local_file_path = tmp_dir / filename
            
            print(f"📥 Downloading s3://{bucket_name}/{s3_key} to '{local_file_path}'")
            
            # Download file
            self.s3_client.download_file(bucket_name, s3_key, str(local_file_path))
            
            print(f"✅ Successfully downloaded s3://{bucket_name}/{s3_key} to '{local_file_path}'")
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchBucket':
                print(f"❌ Error: Bucket '{bucket_name}' does not exist!")
            elif error_code == 'NoSuchKey':
                print(f"❌ Error: Object '{s3_key}' does not exist in bucket '{bucket_name}'!")
            elif error_code == 'AccessDenied':
                print(f"❌ Error: Access denied to bucket '{bucket_name}' or object '{s3_key}'!")
            else:
                print(f"❌ Error downloading file: {e}")
            return False
        except Exception as e:
            print(f"❌ Unexpected error during download: {e}")
            return False
    
    @rate_limit("s3_presigned", wait=True)
    def generate_presigned_upload_url(self, bucket_name: str, s3_key: str, 
                                    expiration: int = 3600, content_type: Optional[str] = None) -> Optional[str]:
        """
        Generate a presigned URL for uploading a file to S3.
        
        Args:
            bucket_name (str): Name of the S3 bucket
            s3_key (str): S3 object key (path in bucket)
            expiration (int): URL expiration time in seconds (default: 3600 = 1 hour)
            content_type (str, optional): MIME type of the file
        
        Returns:
            str: Presigned URL for upload, or None if failed
        """
        try:
            # Validate bucket exists
            if not self._bucket_exists(bucket_name):
                print(f"❌ Error: Bucket '{bucket_name}' does not exist or is not accessible!")
                return None
            
            # Prepare parameters for presigned URL
            params = {
                'Bucket': bucket_name,
                'Key': s3_key
            }
            
            # Add content type if specified
            if content_type:
                params['ContentType'] = content_type
            
            print(f"🔗 Generating presigned upload URL for s3://{bucket_name}/{s3_key}")
            
            # Generate presigned URL for PUT operation
            presigned_url = self.s3_client.generate_presigned_url(
                'put_object',
                Params=params,
                ExpiresIn=expiration
            )
            
            print(f"✅ Presigned upload URL generated successfully!")
            print(f"📋 URL expires in {expiration} seconds ({expiration/3600:.1f} hours)")
            return presigned_url
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchBucket':
                print(f"❌ Error: Bucket '{bucket_name}' does not exist!")
            elif error_code == 'AccessDenied':
                print(f"❌ Error: Access denied to bucket '{bucket_name}'!")
            else:
                print(f"❌ Error generating presigned upload URL: {e}")
            return None
        except Exception as e:
            print(f"❌ Unexpected error generating presigned upload URL: {e}")
            return None
    
    @rate_limit("s3_presigned", wait=True)
    def generate_presigned_download_url(self, bucket_name: str, s3_key: str, expiration: int = 3600) -> Optional[str]:
        """
        Generate a presigned URL for downloading a file from S3.
        
        Args:
            bucket_name (str): Name of the S3 bucket
            s3_key (str): S3 object key (path in bucket)
            expiration (int): URL expiration time in seconds (default: 3600 = 1 hour)
        
        Returns:
            str: Presigned URL for download, or None if failed
        """
        try:
            # Validate bucket exists
            if not self._bucket_exists(bucket_name):
                print(f"❌ Error: Bucket '{bucket_name}' does not exist or is not accessible!")
                return None
            
            # Check if object exists
            try:
                self.s3_client.head_object(Bucket=bucket_name, Key=s3_key)
            except ClientError as e:
                if e.response['Error']['Code'] == 'NoSuchKey':
                    print(f"❌ Error: Object '{s3_key}' does not exist in bucket '{bucket_name}'!")
                    return None
                elif e.response['Error']['Code'] == 'AccessDenied':
                    print(f"❌ Error: Access denied to object '{s3_key}' in bucket '{bucket_name}'!")
                    return None
                else:
                    raise e
            
            print(f"🔗 Generating presigned download URL for s3://{bucket_name}/{s3_key}")
            
            # Generate presigned URL for GET operation
            presigned_url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket_name, 'Key': s3_key},
                ExpiresIn=expiration
            )
            
            print(f"✅ Presigned download URL generated successfully!")
            print(f"📋 URL expires in {expiration} seconds ({expiration/3600:.1f} hours)")
            return presigned_url
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchBucket':
                print(f"❌ Error: Bucket '{bucket_name}' does not exist!")
            elif error_code == 'AccessDenied':
                print(f"❌ Error: Access denied to bucket '{bucket_name}' or object '{s3_key}'!")
            else:
                print(f"❌ Error generating presigned download URL: {e}")
            return None
        except Exception as e:
            print(f"❌ Unexpected error generating presigned download URL: {e}")
            return None
    
    @rate_limit("s3_presigned", wait=True)
    def generate_adobe_compatible_presigned_url(self, bucket_name: str, s3_key: str, 
                                              expiration: int = 3600, operation: str = 'get_object') -> Optional[str]:
        """
        Generate a presigned URL specifically designed for Adobe API compatibility.
        
        Args:
            bucket_name (str): Name of the S3 bucket
            s3_key (str): S3 object key (path in bucket)
            expiration (int): URL expiration time in seconds (default: 3600 = 1 hour)
            operation (str): S3 operation ('get_object' or 'put_object')
        
        Returns:
            str: Adobe-compatible presigned URL, or None if failed
        """
        try:
            # Validate bucket exists
            if not self._bucket_exists(bucket_name):
                print(f"❌ Error: Bucket '{bucket_name}' does not exist or is not accessible!")
                return None
            
            # Prepare parameters for Adobe-compatible presigned URL
            params = {
                'Bucket': bucket_name,
                'Key': s3_key
            }
            
            if self.debug:
                print(f"🔗 Generating Adobe-compatible presigned URL for s3://{bucket_name}/{s3_key}")
            
            # Generate presigned URL with explicit signature version and configuration
            presigned_url = self.s3_client.generate_presigned_url(
                operation,
                Params=params,
                ExpiresIn=expiration,
                HttpMethod='GET' if operation == 'get_object' else 'PUT'
            )
            
            if self.debug:
                print(f"✅ Adobe-compatible presigned URL generated successfully!")
                print(f"📋 URL expires in {expiration} seconds ({expiration/3600:.1f} hours)")
                print(f"🔧 Operation: {operation}")
                print(f"⚠️  Note: Adobe API may require specific bucket policies for server-to-server access")
                
                # Debug: Print URL components to verify signature
                if '?' in presigned_url:
                    base_url, query_params = presigned_url.split('?', 1)
                    print(f"🔍 Debug - Base URL: {base_url}")
                    print(f"🔍 Debug - Query params: {query_params}")
            
            return presigned_url
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchBucket':
                print(f"❌ Error: Bucket '{bucket_name}' does not exist!")
            elif error_code == 'AccessDenied':
                print(f"❌ Error: Access denied to bucket '{bucket_name}'!")
            else:
                print(f"❌ Error generating Adobe-compatible presigned URL: {e}")
            return None
        except Exception as e:
            print(f"❌ Unexpected error generating Adobe-compatible presigned URL: {e}")
            return None
    
    def generate_public_url(self, bucket_name: str, s3_key: str) -> Optional[str]:
        """
        Generate a public S3 URL (requires bucket/object to be public).
        
        Args:
            bucket_name (str): Name of the S3 bucket
            s3_key (str): S3 object key (path in bucket)
        
        Returns:
            str: Public S3 URL
        """
        try:
            # Validate bucket exists
            if not self._bucket_exists(bucket_name):
                print(f"❌ Error: Bucket '{bucket_name}' does not exist or is not accessible!")
                return None
            
            # Generate public URL
            public_url = f"https://{bucket_name}.s3.amazonaws.com/{s3_key}"
            
            print(f"🔗 Generated public URL: {public_url}")
            print(f"⚠️  Note: This URL will only work if the S3 object is public")
            print(f"📝 To make object public: aws s3api put-object-acl --bucket {bucket_name} --key '{s3_key}' --acl public-read")
            
            return public_url
            
        except Exception as e:
            print(f"❌ Error generating public URL: {e}")
            return None
    
    def _bucket_exists(self, bucket_name: str) -> bool:
        """
        Check if a bucket exists and is accessible.
        
        Args:
            bucket_name (str): Name of the S3 bucket
        
        Returns:
            bool: True if bucket exists and is accessible, False otherwise
        """
        try:
            self.s3_client.head_bucket(Bucket=bucket_name)
            return True
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                return False
            elif error_code == '403':
                return False
            else:
                raise e
