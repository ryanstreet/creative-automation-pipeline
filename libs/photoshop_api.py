#!/usr/bin/env python3
"""
Adobe Photoshop API Library

This library provides a unified interface for Adobe Photoshop API operations including:
- Document manifest retrieval
- Smart object replacement
- Text layer editing
- Rendition creation

All operations are asynchronous and use the Adobe Firefly Services Photoshop API.
"""

import json
import time
import requests
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse

from .base_api import BaseAdobeAPI
from .config import Config, Constants
from .rate_limiter import rate_limiter, rate_limit


class AdobePhotoshopAPI(BaseAdobeAPI):
    """Unified client for Adobe Photoshop API operations."""
    
    def __init__(self, client_id: str, client_secret: str):
        """
        Initialize Adobe Photoshop API client.
        
        Args:
            client_id (str): Adobe Developer Console client ID
            client_secret (str): Adobe Developer Console client secret
        """
        super().__init__(client_id, client_secret)
        self.base_url = Config.PHOTOSHOP_BASE_URL
    
    def _get_auth_scope(self) -> str:
        """Get authentication scope for Photoshop API."""
        return 'openid,AdobeID,read_organizations'
    
    def _get_rate_limit_name(self) -> str:
        """Get rate limiter name for Photoshop API."""
        return 'adobe_photoshop'
    
    
    def poll_job_status(self, status_url: str, poll_interval: int = 5, 
                       max_attempts: int = 120, debug: bool = False) -> Dict[str, Any]:
        """
        Poll job status until completion.
        
        Args:
            status_url (str): URL to poll for job status
            poll_interval (int): Seconds between polling attempts
            max_attempts (int): Maximum number of polling attempts
            debug (bool): Enable debug output
            
        Returns:
            Dict[str, Any]: Final job result data
            
        Raises:
            Exception: If job fails or times out
        """
        print("Polling job status...")
        
        headers = self.get_headers()
        # Remove Content-Type header for GET requests
        headers.pop('Content-Type', None)
        
        if debug:
            print(f"Polling URL: {status_url}")
            print(f"Headers: {headers}")
        
        attempt = 0
        while attempt < max_attempts:
            try:
                response = requests.get(status_url, headers=headers)
                if debug:
                    print(f"Response status code: {response.status_code}")
                response.raise_for_status()
                status_data = response.json()
                
                if debug:
                    print(f"Full response: {json.dumps(status_data, indent=2)}")
                
                # Try different possible locations for the status field
                status = None
                if 'status' in status_data:
                    status = status_data.get('status')
                elif 'outputs' in status_data and len(status_data.get('outputs', [])) > 0:
                    # Check if status is in the outputs array
                    output = status_data['outputs'][0]
                    status = output.get('status')
                elif 'job' in status_data:
                    # Check if status is nested under job
                    status = status_data['job'].get('status')
                
                print(f"Job status: {status}")
                
                if status == 'succeeded':
                    print("Job completed successfully!")
                    return status_data
                elif status == 'failed':
                    error_msg = status_data.get('error', status_data.get('message', 'Unknown error'))
                    raise Exception(f"Job failed: {error_msg}")
                elif status in ['pending', 'running', 'processing']:
                    print(f"Job still {status}, waiting {poll_interval} seconds...")
                    time.sleep(poll_interval)
                elif status is None:
                    # If no status found, check if we have outputs (might be completed)
                    if 'outputs' in status_data and len(status_data.get('outputs', [])) > 0:
                        print("No status field found, but outputs present - assuming success")
                        return status_data
                    else:
                        print("No status field found and no outputs - continuing to poll...")
                        time.sleep(poll_interval)
                else:
                    print(f"Unknown status: {status}, continuing to poll...")
                    time.sleep(poll_interval)
                
                attempt += 1
                    
            except requests.exceptions.RequestException as e:
                if debug:
                    print(f"Request error: {e}")
                    print(f"Response content: {response.text if 'response' in locals() else 'No response'}")
                raise Exception(f"Error polling job status: {e}")
        
        # If we've exhausted all attempts
        raise Exception(f"Job did not complete within {max_attempts * poll_interval} seconds")
    
    @rate_limit("adobe_photoshop", wait=True)
    def get_document_manifest(self, input_url: str) -> str:
        """
        Initiate document manifest retrieval and return status URL.
        
        Args:
            input_url (str): URL of the PSD file to process
            
        Returns:
            str: Status URL for polling
            
        Raises:
            Exception: If request fails
        """
        print(f"Initiating document manifest retrieval for: {input_url}")
        
        url = f"{self.base_url}/documentManifest"
        headers = self.get_headers()
        
        data = {
            'inputs': [
                {
                    'href': input_url,
                    'storage': 'external'
                }
            ]
        }
        
        try:
            response = self._make_request('POST', url, headers=headers, json=data)
            result = response.json()
            
            # Extract the status URL from the response
            status_url = result.get('_links', {}).get('self', {}).get('href')
            if not status_url:
                raise ValueError("No status URL received from API")
            
            print(f"Job initiated. Status URL: {status_url}")
            return status_url
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to initiate document manifest: {e}")
    
    @rate_limit("adobe_photoshop", wait=True)
    def replace_smart_object(self, input_psd_url: str, layer_name: str, 
                           smart_object_url: str, output_url: str) -> str:
        """
        Initiate smart object replacement and return status URL.
        
        Args:
            input_psd_url (str): URL of the input PSD file
            layer_name (str): Name of the layer to replace
            smart_object_url (str): URL of the new smart object
            output_url (str): URL for the output file
            
        Returns:
            str: Status URL for polling
            
        Raises:
            Exception: If request fails
        """
        print(f"Replacing smart object in layer '{layer_name}'...")
        
        url = f"{self.base_url}/smartObject"
        headers = self.get_headers()
        
        data = {
            "inputs": [
                {
                    "href": input_psd_url,
                    "storage": "external"
                }
            ],
            "outputs": [
                {
                    "href": output_url,
                    "storage": "external",
                    "type": "image/vnd.adobe.photoshop",
                    "overwrite": True,
                    "width": 0,
                    "quality": 7,
                    "compression": "small"
                }
            ],
            "options": {
                "layers": [
                    {
                        "name": layer_name,
                        "input": {
                            "href": smart_object_url,
                            "storage": "external"
                        }
                    }
                ]
            }
        }
        
        try:
            response = self._make_request('POST', url, headers=headers, json=data)
            result = response.json()
            
            # Extract the status URL from the response
            status_url = result.get('_links', {}).get('self', {}).get('href')
            if not status_url:
                raise ValueError("No status URL received from API")
            
            print(f"Smart object replacement job initiated. Status URL: {status_url}")
            return status_url
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to initiate smart object replacement: {e}")
    
    @rate_limit("adobe_photoshop", wait=True)
    def edit_text_layer(self, input_psd_url: str, layer_name: str, 
                       replacement_text: str, output_url: str) -> str:
        """
        Initiate text layer editing and return status URL.
        
        Args:
            input_psd_url (str): URL of the input PSD file
            layer_name (str): Name of the text layer to edit
            replacement_text (str): New text content
            output_url (str): URL for the output file
            
        Returns:
            str: Status URL for polling
            
        Raises:
            Exception: If request fails
        """
        print(f"Editing text in layer '{layer_name}' to: '{replacement_text}'")
        
        url = f"{self.base_url}/text"
        headers = self.get_headers()
        
        data = {
            "inputs": [
                {
                    "href": input_psd_url,
                    "storage": "external"
                }
            ],
            "outputs": [
                {
                    "href": output_url,
                    "storage": "external",
                    "type": "image/vnd.adobe.photoshop",
                    "overwrite": True,
                    "quality": 7,
                    "compression": "small"
                }
            ],
            "options": {
                "manageMissingFonts": "useDefault",
                "layers": [
                    {
                        "name": layer_name,
                        "text": {
                            "content": replacement_text,
                            "orientation": "horizontal",
                            "textType": "point"
                        }
                    }
                ]
            }
        }
        
        try:
            response = self._make_request('POST', url, headers=headers, json=data)
            result = response.json()
            
            # Extract the status URL from the response
            status_url = result.get('_links', {}).get('self', {}).get('href')
            if not status_url:
                raise ValueError("No status URL received from API")
            
            print(f"Text layer editing job initiated. Status URL: {status_url}")
            return status_url
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to initiate text layer editing: {e}")
    
    @rate_limit("adobe_photoshop", wait=True)
    def create_rendition(self, input_url: str, output_url: str) -> str:
        """
        Create PNG rendition of PSD file and return status URL.
        
        Args:
            input_url (str): URL of the input PSD file
            output_url (str): URL for the output PNG file
            
        Returns:
            str: Status URL for polling
            
        Raises:
            Exception: If request fails
        """
        print("Creating PNG rendition...")
        
        url = f"{self.base_url}/renditionCreate"
        headers = self.get_headers()
        
        data = {
            "inputs": [
                {
                    "href": input_url,
                    "storage": "external"
                }
            ],
            "outputs": [
                {
                    "href": output_url,
                    "storage": "external",
                    "type": "image/png",
                    "overwrite": True,
                    "compression": "small",
                    "trimToCanvas": True
                }
            ]
        }
        
        try:
            response = self._make_request('POST', url, headers=headers, json=data)
            result = response.json()
            
            # Extract the status URL from the response
            status_url = result.get('_links', {}).get('status', {}).get('href')
            if not status_url:
                status_url = result.get('_links', {}).get('self', {}).get('href')
            
            if not status_url:
                raise ValueError("No status URL received from API")
            
            print(f"Rendition creation job initiated. Status URL: {status_url}")
            return status_url
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to initiate rendition creation: {e}")


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


def extract_layers_from_manifest(manifest_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract all layer names from a document manifest JSON data.
    
    Args:
        manifest_data (Dict[str, Any]): Manifest data dictionary
        
    Returns:
        List[Dict[str, Any]]: List of layer information dictionaries
    """
    layers = []
    
    def extract_layers(data, path=""):
        if isinstance(data, dict):
            if 'name' in data and 'id' in data:
                # This looks like a layer
                layer_name = data.get('name', 'Unnamed')
                layer_id = data.get('id', 'Unknown')
                
                # Determine layer type
                layer_type = "Layer"  # Default
                if 'text' in data:
                    layer_type = "Text Layer"
                elif 'smartObject' in data:
                    layer_type = "Smart Object Layer"
                
                layers.append({
                    'name': layer_name,
                    'id': layer_id,
                    'type': layer_type
                })
            
            # Recursively search through nested structures
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    new_path = f"{path}.{key}" if path else key
                    extract_layers(value, new_path)
                    
        elif isinstance(data, list):
            for i, item in enumerate(data):
                if isinstance(item, (dict, list)):
                    new_path = f"{path}[{i}]" if path else f"[{i}]"
                    extract_layers(item, new_path)
    
    extract_layers(manifest_data)
    return layers


def find_layer_in_manifest(manifest: Dict[str, Any], layer_name: str) -> Optional[Dict[str, Any]]:
    """
    Find a layer by name in the manifest.
    
    Args:
        manifest (Dict[str, Any]): Manifest data dictionary
        layer_name (str): Name of the layer to find
        
    Returns:
        Optional[Dict[str, Any]]: Layer data if found, None otherwise
    """
    try:
        outputs = manifest.get('outputs', [])
        if not outputs:
            return None
        
        # Get layers from the first output
        layers = outputs[0].get('layers', [])
        
        # Search for the layer by name
        for layer in layers:
            if layer.get('name') == layer_name:
                return layer
        
        return None
        
    except Exception as e:
        raise Exception(f"Error searching for layer in manifest: {e}")


def get_input_psd_url(manifest: Dict[str, Any]) -> str:
    """
    Extract the input PSD URL from the manifest.
    
    Args:
        manifest (Dict[str, Any]): Manifest data dictionary
        
    Returns:
        str: Input PSD URL
        
    Raises:
        ValueError: If no input URL found
    """
    try:
        outputs = manifest.get('outputs', [])
        if not outputs:
            raise ValueError("No outputs found in manifest")
        
        input_url = outputs[0].get('input')
        if not input_url:
            raise ValueError("No input URL found in manifest")
        
        return input_url
        
    except Exception as e:
        raise Exception(f"Error extracting input PSD URL: {e}")
