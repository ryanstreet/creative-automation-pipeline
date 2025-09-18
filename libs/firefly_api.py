#!/usr/bin/env python3
"""
Adobe Firefly API Library

This library provides a unified interface for Adobe Firefly API operations including:
- Image generation using text prompts
- Prompt generation using OpenAI API

All operations are asynchronous and use the Adobe Firefly API V3.
"""

import json
import time
import requests
from typing import Dict, Any, Optional, List
from openai import OpenAI

from .base_api import BaseAdobeAPI
from .config import Config, Constants
from .rate_limiter import rate_limiter, rate_limit


class AdobeFireflyAPI(BaseAdobeAPI):
    """Client for Adobe Firefly API V3 Async image generation."""
    
    def __init__(self, client_id: str, client_secret: str):
        """
        Initialize Adobe Firefly API client.
        
        Args:
            client_id (str): Adobe Developer Console client ID
            client_secret (str): Adobe Developer Console client secret
        """
        super().__init__(client_id, client_secret)
        self.base_url = Config.FIREFLY_BASE_URL
    
    def _get_auth_scope(self) -> str:
        """Get authentication scope for Firefly API."""
        return 'openid,AdobeID,read_organizations,firefly'
    
    def _get_rate_limit_name(self) -> str:
        """Get rate limiter name for Firefly API."""
        return 'adobe_firefly'
    
    
    @rate_limit("adobe_firefly", wait=True)
    def generate_images_async(self, prompt: str, num_variations: int = 1, 
                            width: int = 1024, height: int = 1024,
                            prompt_biasing_locale_code: str = "en-US",
                            content_class: str = "photo") -> str:
        """
        Initiate async image generation and return status URL.
        
        Args:
            prompt (str): Text prompt for image generation
            num_variations (int): Number of image variations to generate
            width (int): Image width in pixels
            height (int): Image height in pixels
            prompt_biasing_locale_code (str): Locale code for prompt biasing
            content_class (str): Content class (photo/art/design)
            
        Returns:
            str: Status URL for polling
            
        Raises:
            Exception: If request fails
        """
        print(f"Generating {num_variations} image(s) with prompt: '{prompt}'")
        
        url = f"{self.base_url}/images/generate-async"
        headers = self.get_headers()
        
        data = {
            "prompt": prompt,
            "numVariations": num_variations,
            "size": {
                "width": width,
                "height": height
            },
            "promptBiasingLocaleCode": prompt_biasing_locale_code,
            "contentClass": content_class
        }
        
        try:
            response = self._make_request('POST', url, headers=headers, json=data)
            result = response.json()
            
            # Debug: Print the full response to understand the structure
            if Config.DEBUG_MODE:
                print(f"API Response: {json.dumps(result, indent=2)}")
            
            # Try different possible locations for the status URL
            status_url = None
            
            # Check for direct status URL (Firefly API provides this directly)
            if 'statusUrl' in result:
                status_url = result['statusUrl']
            
            # Check for _links.self.href (common pattern)
            elif '_links' in result and 'self' in result['_links']:
                status_url = result['_links']['self'].get('href')
            
            # Check for direct href
            elif 'href' in result:
                status_url = result['href']
            
            # Check for direct job ID (construct status URL from job ID)
            elif 'jobId' in result:
                status_url = f"{self.base_url}/images/generate-async/{result['jobId']}"
            
            if not status_url:
                raise ValueError(f"No status URL found in API response. Response structure: {json.dumps(result, indent=2)}")
            
            print(f"Image generation job initiated. Status URL: {status_url}")
            return status_url
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to initiate image generation: {e}")
    
    
    def extract_image_urls(self, result_data: Dict[str, Any], debug: bool = False) -> List[str]:
        """
        Extract image URLs from the completed job result.
        
        Args:
            result_data (Dict[str, Any]): Job result data
            debug (bool): Enable debug output
            
        Returns:
            List[str]: List of image URLs
        """
        urls = []
        
        if debug:
            print(f"Extracting URLs from: {json.dumps(result_data, indent=2)}")
        
        # Look for outputs in the result (check both top-level and nested under 'result')
        outputs = result_data.get('outputs', [])
        if not outputs and 'result' in result_data:
            outputs = result_data['result'].get('outputs', [])
        
        if debug:
            print(f"Found {len(outputs)} outputs")
        
        for i, output in enumerate(outputs):
            if debug:
                print(f"Processing output {i}: {json.dumps(output, indent=2)}")
            
            # Check for image data in various possible structures
            if 'image' in output:
                image_data = output['image']
                if isinstance(image_data, dict):
                    if 'url' in image_data:
                        urls.append(image_data['url'])
                    elif 'href' in image_data:
                        urls.append(image_data['href'])
                elif isinstance(image_data, str):
                    urls.append(image_data)
            
            # Check for direct URL in output
            if 'url' in output:
                urls.append(output['url'])
            elif 'href' in output:
                urls.append(output['href'])
        
        # Check for direct image URLs in the result
        if 'images' in result_data:
            images = result_data['images']
            if debug:
                print(f"Found images array: {json.dumps(images, indent=2)}")
            
            for i, image in enumerate(images):
                if isinstance(image, dict):
                    if 'url' in image:
                        urls.append(image['url'])
                    elif 'href' in image:
                        urls.append(image['href'])
                elif isinstance(image, str):
                    urls.append(image)
        
        # Check for direct URLs in the result
        if 'urls' in result_data:
            urls.extend(result_data['urls'])
        
        # Check for result field that might contain URLs
        if 'result' in result_data:
            result_content = result_data['result']
            if isinstance(result_content, list):
                for item in result_content:
                    if isinstance(item, dict) and 'url' in item:
                        urls.append(item['url'])
                    elif isinstance(item, str):
                        urls.append(item)
        
        if debug:
            print(f"Extracted {len(urls)} URLs: {urls}")
        
        return urls


class FireflyPromptGenerator:
    """Generate Adobe Firefly prompts using OpenAI API."""
    
    def __init__(self, openai_api_key: str):
        """
        Initialize Firefly prompt generator.
        
        Args:
            openai_api_key (str): OpenAI API key
        """
        self.client = OpenAI(api_key=openai_api_key)
    
    @rate_limit("openai_chat", wait=True)
    def generate_firefly_prompt(self, demographics: Dict[str, Any], model: str = "gpt-4") -> str:
        """
        Generate Adobe Firefly prompt using OpenAI API.
        
        Args:
            demographics (Dict[str, Any]): Campaign demographics data
            model (str): OpenAI model to use
            
        Returns:
            str: Generated Firefly prompt
            
        Raises:
            Exception: If API call fails
        """
        # Prepare the context for the AI
        context = f"""
Campaign Demographics:
{json.dumps(demographics, indent=2)}
"""
        
        # System instruction
        system_instruction = """You are an AI assistant responsible for generating prompts for Adobe Firefly to create images. Below is the context of a campaign brief. Use this information to compose a robust and accurate prompt to generate images. Generate background images only. Do not reference individual products.  Make your responses concise and to the point."""
        
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": context}
                ],
                max_tokens=500,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
        
        except Exception as e:
            raise Exception(f"Error calling OpenAI API: {e}")
    
    def extract_demographics(self, campaign_brief: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract target_region_market, target_audience, and psychographics from campaign brief.
        
        Args:
            campaign_brief (Dict[str, Any]): Campaign brief data
            
        Returns:
            Dict[str, Any]: Extracted demographics data
        """
        demographics = {}
        
        # Extract target_region_market
        if 'target_region_market' in campaign_brief:
            demographics['target_region_market'] = campaign_brief['target_region_market']
        
        # Extract target_audience
        if 'target_audience' in campaign_brief:
            demographics['target_audience'] = campaign_brief['target_audience']
        
        # Extract psychographics (nested within target_audience)
        if 'target_audience' in campaign_brief and 'psychographics' in campaign_brief['target_audience']:
            demographics['psychographics'] = campaign_brief['target_audience']['psychographics']
        
        return demographics
