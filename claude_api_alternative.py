"""
Alternative solutions to replace playwright-based Claude chat for Streamlit compatibility.

This file provides multiple approaches to interact with Claude without using Playwright,
making it compatible with Streamlit applications.
"""

import requests
import json
import os
from typing import Optional, Generator
import time
from datetime import datetime

class ClaudeAPIClient:
    """
    Direct API client for Claude using Anthropic's official API.
    This is the most reliable alternative to browser automation.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        self.base_url = "https://api.anthropic.com/v1"
        self.headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01"
        }
    
    def ask_claude(self, question: str, model: str = "claude-3-sonnet-20240229") -> Optional[str]:
        """
        Send a question to Claude via official API.
        
        Args:
            question (str): The question to ask
            model (str): Claude model to use
            
        Returns:
            str: Claude's response or None if failed
        """
        if not self.api_key:
            print("Error: ANTHROPIC_API_KEY not found in environment variables")
            return None
            
        try:
            payload = {
                "model": model,
                "max_tokens": 1000,
                "messages": [
                    {
                        "role": "user",
                        "content": question
                    }
                ]
            }
            
            response = requests.post(
                f"{self.base_url}/messages",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                return data['content'][0]['text']
            else:
                print(f"API Error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"Error calling Claude API: {e}")
            return None
    
    def ask_claude_streaming(self, question: str, model: str = "claude-3-sonnet-20240229") -> Generator[str, None, None]:
        """
        Stream Claude's response in real-time.
        
        Args:
            question (str): The question to ask
            model (str): Claude model to use
            
        Yields:
            str: Chunks of Claude's response
        """
        if not self.api_key:
            yield "Error: ANTHROPIC_API_KEY not found in environment variables"
            return
            
        try:
            payload = {
                "model": model,
                "max_tokens": 1000,
                "messages": [
                    {
                        "role": "user",
                        "content": question
                    }
                ],
                "stream": True
            }
            
            response = requests.post(
                f"{self.base_url}/messages",
                headers=self.headers,
                json=payload,
                stream=True,
                timeout=30
            )
            
            if response.status_code == 200:
                for line in response.iter_lines():
                    if line:
                        line = line.decode('utf-8')
                        if line.startswith('data: '):
                            data_str = line[6:]  # Remove 'data: ' prefix
                            if data_str.strip() == '[DONE]':
                                break
                            try:
                                data = json.loads(data_str)
                                if data.get('type') == 'content_block_delta':
                                    text = data.get('delta', {}).get('text', '')
                                    if text:
                                        yield text
                            except json.JSONDecodeError:
                                continue
            else:
                yield f"API Error: {response.status_code} - {response.text}"
                
        except Exception as e:
            yield f"Error calling Claude API: {e}"


class ClaudeWebClient:
    """
    Alternative web-based client using requests instead of Playwright.
    This attempts to interact with Claude.ai web interface directly.
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def ask_claude_web(self, question: str, session_key: Optional[str] = None) -> Optional[str]:
        """
        Attempt to interact with Claude.ai web interface using requests.
        Note: This may require authentication tokens/cookies.
        
        Args:
            question (str): The question to ask
            session_key (str): Optional session authentication
            
        Returns:
            str: Response or None if failed
        """
        # This is a simplified example - actual implementation would need
        # proper authentication and session management
        print("Web client method requires authentication setup")
        print("Consider using the API client instead")
        return None


class ClaudeProxyClient:
    """
    Client that uses a local proxy server to communicate with Claude.
    This can be useful when you need to maintain browser sessions.
    """
    
    def __init__(self, proxy_url: str = "http://localhost:8080"):
        self.proxy_url = proxy_url
    
    def ask_claude_proxy(self, question: str) -> Optional[str]:
        """
        Send question through a local proxy server.
        
        Args:
            question (str): The question to ask
            
        Returns:
            str: Response or None if failed
        """
        try:
            response = requests.post(
                f"{self.proxy_url}/ask",
                json={"question": question},
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json().get('response')
            else:
                print(f"Proxy Error: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"Error calling proxy: {e}")
            return None


# Convenience functions for easy usage
def ask_claude_simple(question: str, method: str = "api") -> Optional[str]:
    """
    Simple function to ask Claude a question using the specified method.
    
    Args:
        question (str): The question to ask
        method (str): Method to use ("api", "web", "proxy")
        
    Returns:
        str: Claude's response or None if failed
    """
    if method == "api":
        client = ClaudeAPIClient()
        return client.ask_claude(question)
    elif method == "web":
        client = ClaudeWebClient()
        return client.ask_claude_web(question)
    elif method == "proxy":
        client = ClaudeProxyClient()
        return client.ask_claude_proxy(question)
    else:
        print(f"Unknown method: {method}")
        return None


def ask_claude_streaming_simple(question: str) -> Generator[str, None, None]:
    """
    Simple streaming function using the API client.
    
    Args:
        question (str): The question to ask
        
    Yields:
        str: Chunks of Claude's response
    """
    client = ClaudeAPIClient()
    yield from client.ask_claude_streaming(question)


# Example usage functions
def demo_api_usage():
    """Demonstrate API usage"""
    print("=== Claude API Demo ===")
    
    # Simple question
    response = ask_claude_simple("How are you?", method="api")
    if response:
        print(f"Response: {response}")
    else:
        print("Failed to get response")
    
    print("\n=== Streaming Demo ===")
    # Streaming response
    for chunk in ask_claude_streaming_simple("Tell me a short joke"):
        print(chunk, end='', flush=True)
    print("\n")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        question = sys.argv[1]
        print(f"Question: {question}")
        
        # Try API method first
        response = ask_claude_simple(question, method="api")
        if response:
            print(f"Response: {response}")
        else:
            print("Failed to get response from API")
    else:
        demo_api_usage()
