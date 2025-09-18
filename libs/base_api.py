#!/usr/bin/env python3
"""
Base API client for Adobe services

This module provides a common base class for Adobe API operations to reduce code duplication.
"""

import json
import time
import requests
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod

from .config import Config, Constants
from .rate_limiter import rate_limiter, RateLimitConfig, RateLimitAlgorithm


class BaseAdobeAPI(ABC):
    """Base class for Adobe API clients."""
    
    def __init__(self, client_id: str, client_secret: str):
        """
        Initialize Adobe API client.
        
        Args:
            client_id (str): Adobe Developer Console client ID
            client_secret (str): Adobe Developer Console client secret
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token: Optional[str] = None
        self.auth_url = Config.ADOBE_AUTH_URL
    
    def authenticate(self) -> str:
        """
        Authenticate with Adobe and get access token.
        
        Returns:
            str: Access token
            
        Raises:
            Exception: If authentication fails
        """
        # Apply rate limiting for authentication
        if Config.ENABLE_RATE_LIMITING:
            rate_limiter.wait_if_needed("adobe_auth")
        
        print("Authenticating with Adobe...")
        
        auth_data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'client_credentials',
            'scope': self._get_auth_scope()
        }
        
        try:
            response = requests.post(
                self.auth_url, 
                data=auth_data,
                timeout=Config.REQUEST_TIMEOUT
            )
            response.raise_for_status()
            auth_result = response.json()
            self.access_token = auth_result.get('access_token')
            
            if not self.access_token:
                raise ValueError("No access token received from Adobe")
            
            print("Authentication successful!")
            return self.access_token
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Authentication failed: {e}")
    
    def get_headers(self) -> Dict[str, str]:
        """
        Get headers for API requests.
        
        Returns:
            Dict[str, str]: Headers with authorization and API key
            
        Raises:
            ValueError: If not authenticated
        """
        if not self.access_token:
            raise ValueError("Not authenticated. Call authenticate() first.")
        
        return {
            'Authorization': f'Bearer {self.access_token}',
            'x-api-key': self.client_id,
            'Content-Type': 'application/json'
        }
    
    def poll_job_status(self, status_url: str, poll_interval: int = None, 
                       max_attempts: int = None, debug: bool = False) -> Dict[str, Any]:
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
        poll_interval = poll_interval or Config.DEFAULT_POLL_INTERVAL
        max_attempts = max_attempts or Config.DEFAULT_MAX_ATTEMPTS
        
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
                # Apply rate limiting for polling requests
                if Config.ENABLE_RATE_LIMITING:
                    rate_limiter.wait_if_needed(self._get_rate_limit_name())
                
                response = requests.get(
                    status_url, 
                    headers=headers,
                    timeout=Config.REQUEST_TIMEOUT
                )
                if debug:
                    print(f"Response status code: {response.status_code}")
                response.raise_for_status()
                status_data = response.json()
                
                if debug:
                    print(f"Full response: {json.dumps(status_data, indent=2)}")
                
                # Check for job status using common patterns
                status = self._extract_status(status_data)
                print(f"Job status: {status}")
                
                if status == Constants.STATUS_SUCCEEDED:
                    print("Job completed successfully!")
                    return status_data
                elif status == Constants.STATUS_FAILED:
                    error_msg = status_data.get('error', status_data.get('message', 'Unknown error'))
                    raise Exception(f"Job failed: {error_msg}")
                elif status in [Constants.STATUS_PENDING, Constants.STATUS_RUNNING, Constants.STATUS_PROCESSING]:
                    print(f"Job still {status}, waiting {poll_interval} seconds...")
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
    
    def _extract_status(self, status_data: Dict[str, Any]) -> Optional[str]:
        """
        Extract status from API response data.
        
        Args:
            status_data (Dict[str, Any]): API response data
            
        Returns:
            Optional[str]: Status string or None if not found
        """
        # Try different possible locations for the status field
        if 'status' in status_data:
            return status_data.get('status')
        elif 'outputs' in status_data and len(status_data.get('outputs', [])) > 0:
            # Check if status is in the outputs array
            output = status_data['outputs'][0]
            return output.get('status')
        elif 'job' in status_data:
            # Check if status is nested under job
            return status_data['job'].get('status')
        
        return None
    
    @abstractmethod
    def _get_auth_scope(self) -> str:
        """
        Get the authentication scope for the specific API.
        
        Returns:
            str: Authentication scope string
        """
        pass
    
    @abstractmethod
    def _get_rate_limit_name(self) -> str:
        """
        Get the rate limiter name for this API.
        
        Returns:
            str: Rate limiter name
        """
        pass
    
    def _make_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """
        Make an HTTP request with common error handling.
        
        Args:
            method (str): HTTP method
            url (str): Request URL
            **kwargs: Additional request parameters
            
        Returns:
            requests.Response: Response object
            
        Raises:
            Exception: If request fails
        """
        try:
            response = requests.request(
                method, 
                url, 
                timeout=Config.REQUEST_TIMEOUT,
                **kwargs
            )
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            raise Exception(f"Request failed: {e}")
