#!/usr/bin/env python3
"""
Rate Limiting Status Command

This command provides information about the current rate limiting status
for all configured APIs in the Creative Automation Pipeline.
"""

import argparse
import json
import sys
from pathlib import Path

# Add parent directory to path to import libs
sys.path.append(str(Path(__file__).parent.parent))

from libs.rate_limiter import get_rate_limit_status
from libs.config import Config


def main():
    """Main function to display rate limiting status."""
    parser = argparse.ArgumentParser(
        description="Display current rate limiting status for all APIs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python rate_limit_status.py
  python rate_limit_status.py --json
  python rate_limit_status.py --detailed
        """
    )
    
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output status in JSON format'
    )
    
    parser.add_argument(
        '--detailed',
        action='store_true',
        help='Show detailed information about each rate limiter'
    )
    
    args = parser.parse_args()
    
    # Get rate limit status
    status = get_rate_limit_status()
    
    if args.json:
        print(json.dumps(status, indent=2))
        return
    
    # Display formatted status
    print("=" * 80)
    print("RATE LIMITING STATUS")
    print("=" * 80)
    print(f"Rate Limiting Enabled: {'Yes' if Config.ENABLE_RATE_LIMITING else 'No'}")
    print(f"Rate Limit Wait Mode: {'Yes' if Config.RATE_LIMIT_WAIT else 'No'}")
    print()
    
    if not status:
        print("No rate limiters configured.")
        return
    
    for name, info in status.items():
        print(f"📊 {name.upper()}")
        print("-" * 40)
        
        if info['type'] == 'token_bucket':
            print(f"  Type: Token Bucket")
            print(f"  Tokens Available: {info['tokens_available']:.1f}")
            print(f"  Capacity: {info['capacity']}")
            print(f"  Refill Rate: {info['refill_rate']:.2f} tokens/sec")
            
        elif info['type'] == 'sliding_window':
            print(f"  Type: Sliding Window")
            print(f"  Requests in Window: {info['requests_in_window']}")
            print(f"  Max Requests: {info['max_requests']}")
            print(f"  Time Window: {info['time_window']} seconds")
            
        elif info['type'] == 'fixed_window':
            print(f"  Type: Fixed Window")
            print(f"  Request Count: {info['request_count']}")
            print(f"  Max Requests: {info['max_requests']}")
            print(f"  Time Window: {info['time_window']} seconds")
            print(f"  Window Start: {info['window_start']}")
        
        if args.detailed:
            print(f"  Configuration:")
            if name == 'adobe_auth':
                print(f"    Max Requests: {Config.ADOBE_AUTH_MAX_REQUESTS}")
                print(f"    Time Window: {Config.ADOBE_AUTH_TIME_WINDOW}s")
            elif name == 'adobe_firefly':
                print(f"    Max Requests: {Config.ADOBE_FIREFLY_MAX_REQUESTS}")
                print(f"    Time Window: {Config.ADOBE_FIREFLY_TIME_WINDOW}s")
            elif name == 'adobe_photoshop':
                print(f"    Max Requests: {Config.ADOBE_PHOTOSHOP_MAX_REQUESTS}")
                print(f"    Time Window: {Config.ADOBE_PHOTOSHOP_TIME_WINDOW}s")
            elif name == 'openai_chat':
                print(f"    Max Requests: {Config.OPENAI_MAX_REQUESTS}")
                print(f"    Time Window: {Config.OPENAI_TIME_WINDOW}s")
            elif name == 's3_operations':
                print(f"    Max Requests: {Config.S3_MAX_REQUESTS}")
                print(f"    Time Window: {Config.S3_TIME_WINDOW}s")
            elif name == 's3_presigned':
                print(f"    Max Requests: {Config.S3_PRESIGNED_MAX_REQUESTS}")
                print(f"    Time Window: {Config.S3_PRESIGNED_TIME_WINDOW}s")
        
        print()
    
    print("=" * 80)
    print("💡 TIP: Use --detailed flag for configuration details")
    print("💡 TIP: Use --json flag for machine-readable output")


if __name__ == "__main__":
    main()
