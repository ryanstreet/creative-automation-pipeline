#!/usr/bin/env python3
"""
Configuration module for Creative Automation Pipeline

This module centralizes all configuration settings, constants, and environment variables
to improve maintainability and security.
"""

import os
from typing import Optional
from pathlib import Path


class Config:
    """Centralized configuration management."""
    
    # API Endpoints
    ADOBE_AUTH_URL = os.getenv('ADOBE_AUTH_URL', 'https://ims-na1.adobelogin.com/ims/token/v3')
    FIREFLY_BASE_URL = os.getenv('FIREFLY_BASE_URL', 'https://firefly-api.adobe.io/v3')
    PHOTOSHOP_BASE_URL = os.getenv('PHOTOSHOP_BASE_URL', 'https://image.adobe.io/pie/psdService')
    
    # Default Values
    DEFAULT_POLL_INTERVAL = int(os.getenv('DEFAULT_POLL_INTERVAL', '5'))
    DEFAULT_MAX_ATTEMPTS = int(os.getenv('DEFAULT_MAX_ATTEMPTS', '120'))
    DEFAULT_URL_EXPIRATION = int(os.getenv('DEFAULT_URL_EXPIRATION', '3600'))
    DEFAULT_REGION = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
    
    # File Paths
    TMP_DIR = Path('tmp')
    DEFAULT_OUTPUT_FILE = TMP_DIR / 'document_manifest.json'
    
    # Security Settings
    DEBUG_MODE = os.getenv('DEBUG_MODE', 'false').lower() == 'true'
    MAX_FILE_SIZE_MB = int(os.getenv('MAX_FILE_SIZE_MB', '100'))
    
    # API Timeouts
    REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', '30'))
    CONNECT_TIMEOUT = int(os.getenv('CONNECT_TIMEOUT', '10'))
    
    # Rate Limiting Settings
    ENABLE_RATE_LIMITING = os.getenv('ENABLE_RATE_LIMITING', 'true').lower() == 'true'
    RATE_LIMIT_WAIT = os.getenv('RATE_LIMIT_WAIT', 'true').lower() == 'true'
    
    # Adobe API Rate Limits
    ADOBE_AUTH_MAX_REQUESTS = int(os.getenv('ADOBE_AUTH_MAX_REQUESTS', '10'))
    ADOBE_AUTH_TIME_WINDOW = int(os.getenv('ADOBE_AUTH_TIME_WINDOW', '60'))
    ADOBE_FIREFLY_MAX_REQUESTS = int(os.getenv('ADOBE_FIREFLY_MAX_REQUESTS', '20'))
    ADOBE_FIREFLY_TIME_WINDOW = int(os.getenv('ADOBE_FIREFLY_TIME_WINDOW', '60'))
    ADOBE_PHOTOSHOP_MAX_REQUESTS = int(os.getenv('ADOBE_PHOTOSHOP_MAX_REQUESTS', '30'))
    ADOBE_PHOTOSHOP_TIME_WINDOW = int(os.getenv('ADOBE_PHOTOSHOP_TIME_WINDOW', '60'))
    
    # OpenAI API Rate Limits
    OPENAI_MAX_REQUESTS = int(os.getenv('OPENAI_MAX_REQUESTS', '60'))
    OPENAI_TIME_WINDOW = int(os.getenv('OPENAI_TIME_WINDOW', '60'))
    
    # AWS S3 Rate Limits
    S3_MAX_REQUESTS = int(os.getenv('S3_MAX_REQUESTS', '1000'))
    S3_TIME_WINDOW = int(os.getenv('S3_TIME_WINDOW', '60'))
    S3_PRESIGNED_MAX_REQUESTS = int(os.getenv('S3_PRESIGNED_MAX_REQUESTS', '100'))
    S3_PRESIGNED_TIME_WINDOW = int(os.getenv('S3_PRESIGNED_TIME_WINDOW', '60'))
    
    @classmethod
    def ensure_tmp_dir(cls) -> Path:
        """Ensure tmp directory exists."""
        cls.TMP_DIR.mkdir(exist_ok=True)
        return cls.TMP_DIR
    
    @classmethod
    def validate_file_path(cls, file_path: str) -> Path:
        """Validate and sanitize file path to prevent directory traversal."""
        path = Path(file_path)
        
        # Prevent directory traversal
        if '..' in str(path) or path.is_absolute():
            raise ValueError(f"Invalid file path: {file_path}")
        
        # Resolve relative to project root
        resolved_path = Path(__file__).parent / path
        
        # Ensure path is within project directory
        project_root = Path(__file__).parent
        try:
            resolved_path.relative_to(project_root)
        except ValueError:
            raise ValueError(f"File path outside project directory: {file_path}")
        
        return resolved_path


# Constants for better maintainability
class Constants:
    """Application constants."""
    
    # Polling Status
    STATUS_PENDING = 'pending'
    STATUS_RUNNING = 'running'
    STATUS_PROCESSING = 'processing'
    STATUS_SUCCEEDED = 'succeeded'
    STATUS_FAILED = 'failed'
    
    # Content Classes
    CONTENT_PHOTO = 'photo'
    CONTENT_ART = 'art'
    CONTENT_DESIGN = 'design'
    
    # File Types
    MIME_PSD = 'image/vnd.adobe.photoshop'
    MIME_PNG = 'image/png'
    MIME_JPEG = 'image/jpeg'
    
    # S3 Operations
    S3_GET_OBJECT = 'get_object'
    S3_PUT_OBJECT = 'put_object'
    
    # OpenAI Models
    OPENAI_GPT4 = 'gpt-4'
    OPENAI_GPT4_TURBO = 'gpt-4-turbo'
    OPENAI_GPT35_TURBO = 'gpt-3.5-turbo'
