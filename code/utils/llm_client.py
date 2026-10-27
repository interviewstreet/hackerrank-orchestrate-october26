"""
LLM Client for Experiential Labs Gateway
Handles API calls with retry logic and token tracking
"""
import json
import time
import urllib.request
import urllib.error
from typing import Dict, List, Optional
import config
from config import (
    EXPLABS_API_KEY,
    EXPLABS_BASE_URL,
    MODEL_NAME,
    MAX_RETRIES,
    REQUEST_TIMEOUT
)


class TokenUsageTracker:
    """Tracks token usage and costs across all API calls"""
    
    def __init__(self):
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_calls = 0
        self.total_cost = 0.0
        
    def add_usage(self, prompt_tokens: int, completion_tokens: int, cost: float):
        """Add usage from a single API call"""
        self.total_prompt_tokens += prompt_tokens
        self.total_completion_tokens += completion_tokens
        self.total_calls += 1
        self.total_cost += cost
        
    def get_summary(self) -> Dict:
        """Get usage summary"""
        total_tokens = self.total_prompt_tokens + self.total_completion_tokens
        return {
            "total_calls": self.total_calls,
            "total_prompt_tokens": self.total_prompt_tokens,
            "total_completion_tokens": self.total_completion_tokens,
            "total_tokens": total_tokens,
            "total_cost_usd": self.total_cost,
            "avg_tokens_per_call": total_tokens / self.total_calls if self.total_calls > 0 else 0,
            "avg_cost_per_call": self.total_cost / self.total_calls if self.total_calls > 0 else 0
        }


# Global tracker instance
usage_tracker = TokenUsageTracker()


class LLMClient:
    """Client for making LLM API calls through Experiential Labs gateway"""
    
    def __init__(self):
        self.base_url = EXPLABS_BASE_URL
        self.api_key = EXPLABS_API_KEY
        self.model = MODEL_NAME
        
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict] = None
    ) -> Dict:
        """
        Make a chat completion request
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Optional sampling temperature
            max_tokens: Optional max output tokens
            response_format: Optional JSON schema for structured output
            
        Returns:
            Response dict with 'content', 'usage', and 'cost'
        """
        # Build request body with only model and messages (minimal)
        request_body = {
            "model": self.model,
            "messages": messages
        }
        
        # Add optional parameters only if specified
        if temperature is not None:
            request_body["temperature"] = temperature
        if max_tokens is not None:
            request_body["max_tokens"] = max_tokens
        if response_format is not None:
            request_body["response_format"] = response_format
            
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Retry logic
        for attempt in range(MAX_RETRIES):
            try:
                data = json.dumps(request_body).encode('utf-8')
                req = urllib.request.Request(url, data=data, headers=headers)
                
                with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as response:
                    response_data = json.loads(response.read().decode('utf-8'))
                
                # Extract content and usage
                content = response_data['choices'][0]['message']['content']
                usage = response_data.get('usage', {})
                
                prompt_tokens = usage.get('prompt_tokens', 0)
                completion_tokens = usage.get('completion_tokens', 0)
                cost = usage.get('cost', 0.0)
                
                # Track usage
                usage_tracker.add_usage(prompt_tokens, completion_tokens, cost)
                
                return {
                    "content": content,
                    "usage": usage,
                    "cost": cost,
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens
                }
                
            except urllib.error.HTTPError as e:
                error_body = e.read().decode('utf-8')
                print(f"HTTP Error {e.code} on attempt {attempt + 1}/{MAX_RETRIES}: {error_body}")
                
                if attempt < MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    raise Exception(f"API call failed after {MAX_RETRIES} attempts: {error_body}")
                    
            except Exception as e:
                print(f"Error on attempt {attempt + 1}/{MAX_RETRIES}: {e}")
                
                if attempt < MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)
                else:
                    raise
                    
    def chat_completion_json(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None
    ) -> Dict:
        """
        Make a chat completion request expecting JSON response
        
        Returns:
            Parsed JSON object from the response
        """
        result = self.chat_completion(
            messages=messages,
            temperature=temperature,
            response_format={"type": "json_object"}
        )
        
        try:
            return json.loads(result["content"])
        except json.JSONDecodeError:
            # If JSON parsing fails, try to extract JSON from markdown code blocks
            content = result["content"]
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
                return json.loads(json_str)
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0].strip()
                return json.loads(json_str)
            else:
                raise Exception(f"Failed to parse JSON from response: {content}")
