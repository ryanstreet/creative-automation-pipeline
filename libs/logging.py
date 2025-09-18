#!/usr/bin/env python3
"""
Enhanced logging utilities for Creative Automation Pipeline

This module provides secure, structured logging capabilities.
"""

import sys
import json
from typing import Any, Dict, Optional
from pathlib import Path
from loguru import logger

from .config import Config
from .security import SecurityUtils


class SecureLogger:
    """Secure logging utility that filters sensitive information."""
    
    def __init__(self, log_file: Optional[Path] = None):
        """
        Initialize secure logger.
        
        Args:
            log_file (Optional[Path]): Optional log file path
        """
        # Remove default handler
        logger.remove()
        
        # Add console handler
        logger.add(
            sys.stdout,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            level="INFO"
        )
        
        # Add file handler if specified
        if log_file:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            logger.add(
                log_file,
                format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
                level="DEBUG",
                rotation="10 MB",
                retention="30 days"
            )
    
    @staticmethod
    def log_api_request(method: str, url: str, headers: Dict[str, str] = None, 
                       data: Dict[str, Any] = None, debug: bool = False):
        """
        Log API request with sensitive data filtering.
        
        Args:
            method (str): HTTP method
            url (str): Request URL
            headers (Dict[str, str]): Request headers
            data (Dict[str, Any]): Request data
            debug (bool): Enable debug logging
        """
        if not debug and not Config.DEBUG_MODE:
            return
        
        log_data = {
            'method': method,
            'url': url,
            'headers': SecurityUtils.sanitize_log_data(headers or {}),
            'data': SecurityUtils.sanitize_log_data(data or {})
        }
        
        logger.debug(f"API Request: {json.dumps(log_data, indent=2)}")
    
    @staticmethod
    def log_api_response(response_data: Dict[str, Any], debug: bool = False):
        """
        Log API response with sensitive data filtering.
        
        Args:
            response_data (Dict[str, Any]): Response data
            debug (bool): Enable debug logging
        """
        if not debug and not Config.DEBUG_MODE:
            return
        
        sanitized_data = SecurityUtils.sanitize_log_data(response_data)
        logger.debug(f"API Response: {json.dumps(sanitized_data, indent=2)}")
    
    @staticmethod
    def log_error(error: Exception, context: str = ""):
        """
        Log error with context.
        
        Args:
            error (Exception): Error to log
            context (str): Additional context
        """
        message = f"Error: {str(error)}"
        if context:
            message = f"{context} - {message}"
        logger.error(message)
    
    @staticmethod
    def log_success(message: str):
        """
        Log success message.
        
        Args:
            message (str): Success message
        """
        logger.success(message)
    
    @staticmethod
    def log_info(message: str):
        """
        Log info message.
        
        Args:
            message (str): Info message
        """
        logger.info(message)
    
    @staticmethod
    def log_warning(message: str):
        """
        Log warning message.
        
        Args:
            message (str): Warning message
        """
        logger.warning(message)


# Global logger instance
secure_logger = SecureLogger()


def setup_logging(log_file: Optional[Path] = None) -> SecureLogger:
    """
    Setup logging for the application.
    
    Args:
        log_file (Optional[Path]): Optional log file path
        
    Returns:
        SecureLogger: Configured logger instance
    """
    return SecureLogger(log_file)
