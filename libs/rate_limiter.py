#!/usr/bin/env python3
"""
Rate Limiting Utilities for Creative Automation Pipeline

This module provides comprehensive rate limiting capabilities using multiple algorithms
to ensure API calls stay within service limits and prevent abuse.
"""

import time
import threading
from typing import Dict, Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum
from collections import defaultdict, deque
import functools

from .config import Config


class RateLimitAlgorithm(Enum):
    """Rate limiting algorithms."""
    TOKEN_BUCKET = "token_bucket"
    SLIDING_WINDOW = "sliding_window"
    FIXED_WINDOW = "fixed_window"


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    max_requests: int
    time_window: int  # in seconds
    algorithm: RateLimitAlgorithm = RateLimitAlgorithm.TOKEN_BUCKET
    burst_capacity: Optional[int] = None  # for token bucket
    refill_rate: Optional[float] = None  # requests per second for token bucket


class TokenBucket:
    """Token bucket rate limiter implementation."""
    
    def __init__(self, capacity: int, refill_rate: float):
        """
        Initialize token bucket.
        
        Args:
            capacity (int): Maximum number of tokens
            refill_rate (float): Tokens added per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.time()
        self._lock = threading.Lock()
    
    def acquire(self, tokens: int = 1) -> bool:
        """
        Try to acquire tokens from the bucket.
        
        Args:
            tokens (int): Number of tokens to acquire
            
        Returns:
            bool: True if tokens were acquired, False otherwise
        """
        with self._lock:
            self._refill()
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
    
    def _refill(self):
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill
        tokens_to_add = elapsed * self.refill_rate
        
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now
    
    def get_wait_time(self, tokens: int = 1) -> float:
        """
        Get time to wait before tokens will be available.
        
        Args:
            tokens (int): Number of tokens needed
            
        Returns:
            float: Seconds to wait
        """
        with self._lock:
            self._refill()
            
            if self.tokens >= tokens:
                return 0.0
            
            tokens_needed = tokens - self.tokens
            return tokens_needed / self.refill_rate


class SlidingWindow:
    """Sliding window rate limiter implementation."""
    
    def __init__(self, max_requests: int, time_window: int):
        """
        Initialize sliding window.
        
        Args:
            max_requests (int): Maximum requests allowed
            time_window (int): Time window in seconds
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = deque()
        self._lock = threading.Lock()
    
    def acquire(self) -> bool:
        """
        Try to acquire permission for a request.
        
        Returns:
            bool: True if request is allowed, False otherwise
        """
        with self._lock:
            now = time.time()
            
            # Remove old requests outside the window
            while self.requests and self.requests[0] <= now - self.time_window:
                self.requests.popleft()
            
            if len(self.requests) < self.max_requests:
                self.requests.append(now)
                return True
            return False
    
    def get_wait_time(self) -> float:
        """
        Get time to wait before next request will be allowed.
        
        Returns:
            float: Seconds to wait
        """
        with self._lock:
            if len(self.requests) < self.max_requests:
                return 0.0
            
            oldest_request = self.requests[0]
            return oldest_request + self.time_window - time.time()


class FixedWindow:
    """Fixed window rate limiter implementation."""
    
    def __init__(self, max_requests: int, time_window: int):
        """
        Initialize fixed window.
        
        Args:
            max_requests (int): Maximum requests allowed
            time_window (int): Time window in seconds
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.window_start = time.time()
        self.request_count = 0
        self._lock = threading.Lock()
    
    def acquire(self) -> bool:
        """
        Try to acquire permission for a request.
        
        Returns:
            bool: True if request is allowed, False otherwise
        """
        with self._lock:
            now = time.time()
            
            # Reset window if needed
            if now - self.window_start >= self.time_window:
                self.window_start = now
                self.request_count = 0
            
            if self.request_count < self.max_requests:
                self.request_count += 1
                return True
            return False
    
    def get_wait_time(self) -> float:
        """
        Get time to wait before next window starts.
        
        Returns:
            float: Seconds to wait
        """
        with self._lock:
            now = time.time()
            window_end = self.window_start + self.time_window
            
            if now >= window_end:
                return 0.0
            
            return window_end - now


class RateLimiter:
    """Main rate limiter class that manages multiple limiters."""
    
    def __init__(self):
        """Initialize rate limiter."""
        self.limiters: Dict[str, Any] = {}
        self._lock = threading.Lock()
    
    def add_limiter(self, name: str, config: RateLimitConfig):
        """
        Add a rate limiter.
        
        Args:
            name (str): Name of the limiter
            config (RateLimitConfig): Rate limit configuration
        """
        with self._lock:
            if config.algorithm == RateLimitAlgorithm.TOKEN_BUCKET:
                capacity = config.burst_capacity or config.max_requests
                refill_rate = config.refill_rate or (config.max_requests / config.time_window)
                self.limiters[name] = TokenBucket(capacity, refill_rate)
            elif config.algorithm == RateLimitAlgorithm.SLIDING_WINDOW:
                self.limiters[name] = SlidingWindow(config.max_requests, config.time_window)
            elif config.algorithm == RateLimitAlgorithm.FIXED_WINDOW:
                self.limiters[name] = FixedWindow(config.max_requests, config.time_window)
    
    def acquire(self, name: str, tokens: int = 1) -> bool:
        """
        Try to acquire permission from a limiter.
        
        Args:
            name (str): Name of the limiter
            tokens (int): Number of tokens to acquire (for token bucket)
            
        Returns:
            bool: True if permission granted, False otherwise
        """
        if name not in self.limiters:
            return True  # No limiter configured
        
        limiter = self.limiters[name]
        # Only TokenBucket supports tokens parameter
        if isinstance(limiter, TokenBucket):
            return limiter.acquire(tokens)
        else:
            # SlidingWindow and FixedWindow don't support tokens
            return limiter.acquire()
    
    def get_wait_time(self, name: str, tokens: int = 1) -> float:
        """
        Get wait time for a limiter.
        
        Args:
            name (str): Name of the limiter
            tokens (int): Number of tokens needed
            
        Returns:
            float: Seconds to wait
        """
        if name not in self.limiters:
            return 0.0
        
        limiter = self.limiters[name]
        # Only TokenBucket supports tokens parameter
        if isinstance(limiter, TokenBucket):
            return limiter.get_wait_time(tokens)
        else:
            # SlidingWindow and FixedWindow don't support tokens
            return limiter.get_wait_time()
    
    def wait_if_needed(self, name: str, tokens: int = 1) -> None:
        """
        Wait if rate limit would be exceeded.
        
        Args:
            name (str): Name of the limiter
            tokens (int): Number of tokens needed
        """
        wait_time = self.get_wait_time(name, tokens)
        if wait_time > 0:
            print(f"Rate limit reached for '{name}'. Waiting {wait_time:.2f} seconds...")
            time.sleep(wait_time)


# Global rate limiter instance
rate_limiter = RateLimiter()


def rate_limit(name: str, tokens: int = 1, wait: bool = True):
    """
    Decorator for rate limiting function calls.
    
    Args:
        name (str): Name of the rate limiter
        tokens (int): Number of tokens to consume
        wait (bool): Whether to wait if rate limited
        
    Returns:
        Callable: Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if wait:
                rate_limiter.wait_if_needed(name, tokens)
            elif not rate_limiter.acquire(name, tokens):
                raise RateLimitExceeded(f"Rate limit exceeded for '{name}'")
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


class RateLimitExceeded(Exception):
    """Exception raised when rate limit is exceeded."""
    pass


def setup_default_rate_limits():
    """Setup default rate limits for common APIs."""
    
    # Adobe APIs (conservative limits)
    rate_limiter.add_limiter("adobe_auth", RateLimitConfig(
        max_requests=10,
        time_window=60,
        algorithm=RateLimitAlgorithm.TOKEN_BUCKET,
        burst_capacity=5,
        refill_rate=0.1  # 1 request per 10 seconds
    ))
    
    rate_limiter.add_limiter("adobe_firefly", RateLimitConfig(
        max_requests=20,
        time_window=60,
        algorithm=RateLimitAlgorithm.SLIDING_WINDOW
    ))
    
    rate_limiter.add_limiter("adobe_photoshop", RateLimitConfig(
        max_requests=30,
        time_window=60,
        algorithm=RateLimitAlgorithm.SLIDING_WINDOW
    ))
    
    # OpenAI API (based on typical limits)
    rate_limiter.add_limiter("openai_chat", RateLimitConfig(
        max_requests=60,
        time_window=60,
        algorithm=RateLimitAlgorithm.TOKEN_BUCKET,
        burst_capacity=20,
        refill_rate=1.0  # 1 request per second
    ))
    
    # AWS S3 (very generous limits)
    rate_limiter.add_limiter("s3_operations", RateLimitConfig(
        max_requests=1000,
        time_window=60,
        algorithm=RateLimitAlgorithm.SLIDING_WINDOW
    ))
    
    # Presigned URL generation (moderate limits)
    rate_limiter.add_limiter("s3_presigned", RateLimitConfig(
        max_requests=100,
        time_window=60,
        algorithm=RateLimitAlgorithm.SLIDING_WINDOW
    ))


def get_rate_limit_status() -> Dict[str, Dict[str, Any]]:
    """
    Get current status of all rate limiters.
    
    Returns:
        Dict[str, Dict[str, Any]]: Status information for each limiter
    """
    status = {}
    
    for name, limiter in rate_limiter.limiters.items():
        if isinstance(limiter, TokenBucket):
            status[name] = {
                "type": "token_bucket",
                "tokens_available": limiter.tokens,
                "capacity": limiter.capacity,
                "refill_rate": limiter.refill_rate
            }
        elif isinstance(limiter, SlidingWindow):
            status[name] = {
                "type": "sliding_window",
                "requests_in_window": len(limiter.requests),
                "max_requests": limiter.max_requests,
                "time_window": limiter.time_window
            }
        elif isinstance(limiter, FixedWindow):
            status[name] = {
                "type": "fixed_window",
                "request_count": limiter.request_count,
                "max_requests": limiter.max_requests,
                "window_start": limiter.window_start,
                "time_window": limiter.time_window
            }
    
    return status


# Initialize default rate limits
setup_default_rate_limits()
