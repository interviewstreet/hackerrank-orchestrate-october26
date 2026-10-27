#!/usr/bin/env python3
"""
Experiential Labs API Smoke Test
Tests connection to the gateway with qwen3.8-flash model
"""
import os
import sys
import json
import urllib.request
import urllib.error

# Read API key from environment
API_KEY = os.environ.get('EXPLABS_API_KEY')
if not API_KEY:
    print("ERROR: EXPLABS_API_KEY environment variable not set")
    sys.exit(1)

# Gateway configuration
BASE_URL = "https://api.experientiallabs.ai/v1"
MODEL = "claude-haiku-5.5"

print("="*80)
print("Experiential Labs API Smoke Test")
print("="*80)
print(f"Base URL: {BASE_URL}")
print(f"Model: {MODEL}")
print(f"API Key: {'*' * 20}{API_KEY[-8:]}")  # Show only last 8 chars
print("="*80)
print()

# Prepare minimal request body (model + messages ONLY, no sampling params)
request_body = {
    "model": MODEL,
    "messages": [
        {
            "role": "user",
            "content": "Respond with exactly: 'Gateway connection successful!'"
        }
    ]
}

# Prepare request
url = f"{BASE_URL}/chat/completions"
headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}
data = json.dumps(request_body).encode('utf-8')

print("Making test call...")
print(f"Endpoint: {url}")
print(f"Request body: {json.dumps(request_body, indent=2)}")
print()

try:
    # Make the request
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req) as response:
        response_data = json.loads(response.read().decode('utf-8'))
    
    print("✅ SUCCESS!")
    print("="*80)
    print("Response:")
    print(json.dumps(response_data, indent=2))
    print("="*80)
    
    # Extract key information
    if 'choices' in response_data and len(response_data['choices']) > 0:
        message = response_data['choices'][0].get('message', {})
        content = message.get('content', '')
        print(f"\nModel Response: {content}")
    
    if 'usage' in response_data:
        usage = response_data['usage']
        prompt_tokens = usage.get('prompt_tokens', 0)
        completion_tokens = usage.get('completion_tokens', 0)
        total_tokens = usage.get('total_tokens', 0)
        
        print(f"\nToken Usage:")
        print(f"  Prompt: {prompt_tokens}")
        print(f"  Completion: {completion_tokens}")
        print(f"  Total: {total_tokens}")
        
        # Calculate cost for claude-haiku-5.5: $0.10 in / $0.50 out per 1M tokens
        input_cost = (prompt_tokens / 1_000_000) * 0.10
        output_cost = (completion_tokens / 1_000_000) * 0.50
        total_cost = input_cost + output_cost
        
        print(f"\nEstimated Cost:")
        print(f"  Input: ${input_cost:.6f}")
        print(f"  Output: ${output_cost:.6f}")
        print(f"  Total: ${total_cost:.6f}")
    
    print("\n✅ Gateway connection test PASSED!")
    
except urllib.error.HTTPError as e:
    print(f"❌ FAILED: HTTP {e.code}")
    print(f"Response: {e.read().decode('utf-8')}")
    sys.exit(1)
except Exception as e:
    print(f"❌ FAILED: {e}")
    sys.exit(1)
