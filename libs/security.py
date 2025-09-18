#!/usr/bin/env python3
"""
Enhanced security utilities for Creative Automation Pipeline

This module provides secure alternatives to common operations.
"""

import re
import secrets
import hashlib
from typing import Optional
from urllib.parse import urlparse
from pathlib import Path


class SecurityUtils:
    """Security utility functions."""
    
    # Allowed URL schemes
    ALLOWED_SCHEMES = {'http', 'https', 's3'}
    
    # Dangerous file extensions
    DANGEROUS_EXTENSIONS = {'.exe', '.bat', '.cmd', '.com', '.pif', '.scr', '.vbs', '.js'}
    
    @staticmethod
    def validate_url_security(url: str) -> bool:
        """
        Enhanced URL validation with security checks.
        
        Args:
            url (str): URL to validate
            
        Returns:
            bool: True if URL is safe, False otherwise
        """
        try:
            parsed = urlparse(url)
            
            # Check scheme
            if parsed.scheme not in SecurityUtils.ALLOWED_SCHEMES:
                return False
            
            # Check for suspicious patterns
            suspicious_patterns = [
                r'javascript:',
                r'data:',
                r'vbscript:',
                r'file:',
                r'ftp:',
                r'<script',
                r'%3Cscript',
                r'%3cscript'
            ]
            
            for pattern in suspicious_patterns:
                if re.search(pattern, url, re.IGNORECASE):
                    return False
            
            # Check for IP addresses (optional - might be legitimate)
            ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
            if re.search(ip_pattern, parsed.netloc):
                # Log warning but don't block
                print(f"Warning: URL contains IP address: {url}")
            
            return True
            
        except Exception:
            return False
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Sanitize filename to prevent path traversal and other attacks.
        
        Args:
            filename (str): Original filename
            
        Returns:
            str: Sanitized filename
        """
        # Remove path separators
        filename = filename.replace('/', '').replace('\\', '')
        
        # Remove dangerous characters
        filename = re.sub(r'[<>:"|?*]', '', filename)
        
        # Limit length
        filename = filename[:255]
        
        # Check for dangerous extensions
        path = Path(filename)
        if path.suffix.lower() in SecurityUtils.DANGEROUS_EXTENSIONS:
            filename = f"{path.stem}.txt"
        
        return filename or "unnamed_file"
    
    @staticmethod
    def generate_secure_token(length: int = 32) -> str:
        """
        Generate a cryptographically secure random token.
        
        Args:
            length (int): Token length
            
        Returns:
            str: Secure random token
        """
        return secrets.token_urlsafe(length)
    
    @staticmethod
    def hash_sensitive_data(data: str) -> str:
        """
        Hash sensitive data for logging purposes.
        
        Args:
            data (str): Sensitive data to hash
            
        Returns:
            str: SHA-256 hash of the data
        """
        return hashlib.sha256(data.encode()).hexdigest()[:8]
    
    @staticmethod
    def sanitize_log_data(data: dict) -> dict:
        """
        Remove sensitive information from data before logging.
        
        Args:
            data (dict): Data to sanitize
            
        Returns:
            dict: Sanitized data
        """
        sensitive_keys = {
            'password', 'secret', 'key', 'token', 'auth', 'credential',
            'client_secret', 'access_token', 'api_key'
        }
        
        sanitized = {}
        for key, value in data.items():
            key_lower = key.lower()
            if any(sensitive in key_lower for sensitive in sensitive_keys):
                if isinstance(value, str) and len(value) > 4:
                    sanitized[key] = f"{value[:2]}...{SecurityUtils.hash_sensitive_data(value)}"
                else:
                    sanitized[key] = "[REDACTED]"
            else:
                sanitized[key] = value
        
        return sanitized


class InputValidator:
    """Input validation utilities."""
    
    @staticmethod
    def validate_file_size(file_path: Path, max_size_mb: int = 100) -> bool:
        """
        Validate file size.
        
        Args:
            file_path (Path): Path to file
            max_size_mb (int): Maximum size in MB
            
        Returns:
            bool: True if file size is acceptable
        """
        if not file_path.exists():
            return False
        
        size_bytes = file_path.stat().st_size
        max_bytes = max_size_mb * 1024 * 1024
        
        return size_bytes <= max_bytes
    
    @staticmethod
    def validate_json_structure(data: dict, required_fields: list) -> bool:
        """
        Validate JSON structure has required fields.
        
        Args:
            data (dict): JSON data
            required_fields (list): List of required field names
            
        Returns:
            bool: True if all required fields present
        """
        return all(field in data for field in required_fields)
    
    @staticmethod
    def validate_layer_name(layer_name: str) -> bool:
        """
        Validate layer name for Photoshop operations.
        
        Args:
            layer_name (str): Layer name
            
        Returns:
            bool: True if layer name is valid
        """
        if not layer_name or len(layer_name.strip()) == 0:
            return False
        
        # Check for dangerous characters
        dangerous_chars = ['<', '>', ':', '"', '|', '?', '*', '\\', '/']
        return not any(char in layer_name for char in dangerous_chars)
