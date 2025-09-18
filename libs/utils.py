#!/usr/bin/env python3
"""
Creative Automation Pipeline Utilities

This module provides common utility functions used across all command scripts including:
- Interactive mode helpers
- File operations
- Environment variable validation
- Input validation
- Error handling patterns
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import urlparse


class InteractiveModeHelper:
    """Helper class for creating interactive command-line interfaces."""
    
    @staticmethod
    def print_header(title: str) -> None:
        """Print a formatted header for interactive mode."""
        print(f"=== {title} - Interactive Mode ===")
        print()
    
    @staticmethod
    def get_file_path(prompt: str, must_exist: bool = True, default_path: Optional[str] = None) -> Path:
        """
        Get a file path from user input with validation.
        
        Args:
            prompt (str): Prompt message for user
            must_exist (bool): Whether the file must exist
            default_path (str, optional): Default path to suggest
            
        Returns:
            Path: Validated file path
        """
        while True:
            file_input = input(f"{prompt}: ").strip()
            if not file_input and default_path:
                file_input = default_path
            
            if file_input:
                file_path = Path(file_input)
                if not file_path.is_absolute():
                    file_path = Path(__file__).parent.parent / file_input
                
                if not must_exist or file_path.exists():
                    return file_path
                print("Error: File not found. Please enter a valid file path.")
            else:
                print("Error: File path cannot be empty.")
    
    @staticmethod
    def get_url(prompt: str) -> str:
        """
        Get a valid URL from user input.
        
        Args:
            prompt (str): Prompt message for user
            
        Returns:
            str: Validated URL
        """
        while True:
            url = input(f"{prompt}: ").strip()
            if url and validate_url(url):
                return url
            print("Error: Please enter a valid URL.")
    
    @staticmethod
    def get_text_input(prompt: str, allow_empty: bool = False) -> str:
        """
        Get text input from user.
        
        Args:
            prompt (str): Prompt message for user
            allow_empty (bool): Whether empty input is allowed
            
        Returns:
            str: User input text
        """
        while True:
            text = input(f"{prompt}: ").strip()
            if text or allow_empty:
                return text
            print("Error: Input cannot be empty.")
    
    @staticmethod
    def get_choice(prompt: str, choices: List[str], default: Optional[str] = None) -> str:
        """
        Get a choice from a list of valid options.
        
        Args:
            prompt (str): Prompt message for user
            choices (List[str]): List of valid choices
            default (str, optional): Default choice
            
        Returns:
            str: Selected choice
        """
        while True:
            choice = input(f"{prompt}: ").strip().lower()
            if not choice and default:
                return default
            if choice in [c.lower() for c in choices]:
                return choice
            print(f"Error: Choice must be one of: {', '.join(choices)}")
    
    @staticmethod
    def get_integer(prompt: str, min_value: Optional[int] = None, max_value: Optional[int] = None, 
                   default: Optional[int] = None) -> int:
        """
        Get an integer from user input with validation.
        
        Args:
            prompt (str): Prompt message for user
            min_value (int, optional): Minimum allowed value
            max_value (int, optional): Maximum allowed value
            default (int, optional): Default value
            
        Returns:
            int: Validated integer
        """
        while True:
            try:
                value_input = input(f"{prompt}: ").strip()
                if not value_input and default is not None:
                    return default
                
                value = int(value_input)
                
                if min_value is not None and value < min_value:
                    print(f"Error: Value must be at least {min_value}.")
                    continue
                
                if max_value is not None and value > max_value:
                    print(f"Error: Value must be at most {max_value}.")
                    continue
                
                return value
                
            except ValueError:
                print("Error: Please enter a valid number.")
    
    @staticmethod
    def get_boolean(prompt: str, default: bool = False) -> bool:
        """
        Get a boolean value from user input.
        
        Args:
            prompt (str): Prompt message for user
            default (bool): Default value
            
        Returns:
            bool: Boolean value
        """
        while True:
            response = input(f"{prompt} (y/N): ").strip().lower()
            if not response:
                return default
            if response in ['y', 'yes']:
                return True
            elif response in ['n', 'no']:
                return False
            print("Error: Please enter 'y' for yes or 'n' for no.")


def validate_url(url: str) -> bool:
    """
    Validate that the input URL is properly formatted.
    
    Args:
        url (str): URL to validate
        
    Returns:
        bool: True if URL is valid, False otherwise
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def validate_adobe_credentials() -> Tuple[str, str]:
    """
    Validate Adobe API credentials from environment variables.
    
    Returns:
        Tuple[str, str]: (client_id, client_secret)
        
    Raises:
        SystemExit: If credentials are not found
    """
    client_id = os.getenv('CLIENT_ID')
    client_secret = os.getenv('CLIENT_SECRET')
    
    if not client_id or not client_secret:
        print("Error: CLIENT_ID and CLIENT_SECRET environment variables must be set", file=sys.stderr)
        print("Please set your Adobe Developer Console credentials:", file=sys.stderr)
        print("export CLIENT_ID='your_client_id'", file=sys.stderr)
        print("export CLIENT_SECRET='your_client_secret'", file=sys.stderr)
        sys.exit(1)
    
    return client_id, client_secret


def validate_openai_credentials() -> str:
    """
    Validate OpenAI API key from environment variables.
    
    Returns:
        str: OpenAI API key
        
    Raises:
        SystemExit: If API key is not found
    """
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("Error: OpenAI API key is required. Set OPENAI_API_KEY environment variable.")
        sys.exit(1)
    return api_key


def load_json_file(file_path: Union[str, Path], description: str = "JSON file") -> Dict[str, Any]:
    """
    Load and parse a JSON file with comprehensive error handling.
    
    Args:
        file_path (Union[str, Path]): Path to the JSON file
        description (str): Description of the file for error messages
        
    Returns:
        Dict[str, Any]: Parsed JSON data
        
    Raises:
        SystemExit: If file cannot be loaded or parsed
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except FileNotFoundError:
        print(f"Error: {description} '{file_path}' not found.")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in '{file_path}': {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading {description} '{file_path}': {e}")
        sys.exit(1)


def save_json_file(data: Dict[str, Any], file_path: Union[str, Path], description: str = "JSON file") -> None:
    """
    Save data to a JSON file with comprehensive error handling.
    
    Args:
        data (Dict[str, Any]): Data to save
        file_path (Union[str, Path]): Path to save the file
        description (str): Description of the file for error messages
        
    Raises:
        Exception: If file cannot be saved
    """
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"{description} saved to: {file_path}")
        
    except Exception as e:
        raise Exception(f"Failed to save {description} to file: {e}")


def print_success(message: str) -> None:
    """Print a success message with formatting."""
    print(f"✅ {message}")


def print_error(message: str) -> None:
    """Print an error message with formatting."""
    print(f"❌ {message}")


def print_info(message: str) -> None:
    """Print an info message with formatting."""
    print(f"ℹ️  {message}")


def print_warning(message: str) -> None:
    """Print a warning message with formatting."""
    print(f"⚠️  {message}")


def print_debug(message: str, debug: bool = False) -> None:
    """Print a debug message with formatting if debug is enabled."""
    if debug:
        print(f"🔍 DEBUG: {message}")


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in bytes to human readable format.
    
    Args:
        size_bytes (int): Size in bytes
        
    Returns:
        str: Formatted size string
    """
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"


def ensure_tmp_directory() -> Path:
    """
    Ensure the tmp directory exists and return its path.
    
    Returns:
        Path: Path to the tmp directory
    """
    tmp_dir = Path("tmp")
    tmp_dir.mkdir(exist_ok=True)
    return tmp_dir


def get_filename_from_path(file_path: Union[str, Path]) -> str:
    """
    Extract filename from a file path.
    
    Args:
        file_path (Union[str, Path]): File path
        
    Returns:
        str: Filename
    """
    return os.path.basename(file_path)


def create_output_filename(input_path: Union[str, Path], suffix: str = "", extension: str = "") -> str:
    """
    Create an output filename based on input path with optional suffix and extension.
    
    Args:
        input_path (Union[str, Path]): Input file path
        suffix (str): Suffix to add before extension
        extension (str): New extension (without dot)
        
    Returns:
        str: Generated output filename
    """
    input_path = Path(input_path)
    stem = input_path.stem
    ext = f".{extension}" if extension else input_path.suffix
    
    if suffix:
        return f"{stem}-{suffix}{ext}"
    else:
        return f"{stem}{ext}"
