import asyncio
import httpx
from typing import Dict, Any, Optional
from urllib.parse import urlparse
from tenacity import retry, stop_after_attempt, wait_exponential_jitter
import logging

from core.config import REQUEST_TIMEOUT, CONCURRENCY_PER_HOST, USER_AGENT

logger = logging.getLogger(__name__)


class RateLimitedClient:
    def __init__(self):
        self.semaphores: Dict[str, asyncio.Semaphore] = {}
        
        # Create client with SSL verification handling
        import ssl
        import os
        
        # Check if we should disable SSL verification (for development/corporate networks)
        verify_ssl = os.getenv("VERIFY_SSL", "true").lower() != "false"
        
        if verify_ssl:
            # Normal SSL verification
            self.client = httpx.AsyncClient(
                timeout=REQUEST_TIMEOUT,
                headers={"User-Agent": USER_AGENT},
                follow_redirects=True
            )
        else:
            # Disable SSL verification for development/corporate networks
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            self.client = httpx.AsyncClient(
                timeout=REQUEST_TIMEOUT,
                headers={"User-Agent": USER_AGENT},
                follow_redirects=True,
                verify=False
            )
            # Only warn once about SSL verification 
            if not hasattr(get_client, '_ssl_warned'):
                logger.warning("SSL verification disabled - use only in development/trusted networks")
                get_client._ssl_warned = True
    
    def get_semaphore(self, host: str) -> asyncio.Semaphore:
        if host not in self.semaphores:
            self.semaphores[host] = asyncio.Semaphore(CONCURRENCY_PER_HOST)
        return self.semaphores[host]
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential_jitter(initial=1, max=30, jitter=5)
    )
    async def get_json(self, url: str, params: Optional[Dict[str, Any]] = None, 
                      headers: Optional[Dict[str, str]] = None) -> Optional[Dict[str, Any]]:
        """Get JSON response with rate limiting and retries."""
        parsed = urlparse(url)
        host = parsed.netloc
        
        semaphore = self.get_semaphore(host)
        
        async with semaphore:
            try:
                response = await self.client.get(url, params=params, headers=headers or {})
                
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", "60"))
                    logger.warning(f"Rate limited by {host}, waiting {retry_after}s")
                    await asyncio.sleep(retry_after)
                    raise httpx.HTTPStatusError("Rate limited", request=response.request, response=response)
                
                response.raise_for_status()
                return response.json()
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code >= 500:
                    logger.warning(f"Server error {e.response.status_code} from {host}, will retry")
                    raise
                elif e.response.status_code == 404:
                    logger.debug(f"Not found: {url}")
                    return None
                else:
                    logger.error(f"HTTP error {e.response.status_code} from {url}")
                    return None
            except Exception as e:
                logger.error(f"Request failed for {url}: {e}")
                raise
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential_jitter(initial=1, max=30, jitter=5)
    )
    async def get_text(self, url: str, headers: Optional[Dict[str, str]] = None) -> Optional[str]:
        """Get text response with rate limiting and retries."""
        parsed = urlparse(url)
        host = parsed.netloc
        
        semaphore = self.get_semaphore(host)
        
        async with semaphore:
            try:
                response = await self.client.get(url, headers=headers or {})
                
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", "60"))
                    logger.warning(f"Rate limited by {host}, waiting {retry_after}s")
                    await asyncio.sleep(retry_after)
                    raise httpx.HTTPStatusError("Rate limited", request=response.request, response=response)
                
                response.raise_for_status()
                return response.text
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code >= 500:
                    logger.warning(f"Server error {e.response.status_code} from {host}, will retry")
                    raise
                elif e.response.status_code == 404:
                    logger.debug(f"Not found: {url}")
                    return None
                else:
                    logger.error(f"HTTP error {e.response.status_code} from {url}")
                    return None
            except Exception as e:
                logger.error(f"Request failed for {url}: {e}")
                return None
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential_jitter(initial=1, max=30, jitter=5)
    )
    async def post_json(self, url: str, data: Dict[str, Any], 
                       headers: Optional[Dict[str, str]] = None) -> Optional[Dict[str, Any]]:
        """POST JSON data and get JSON response with rate limiting and retries."""
        parsed = urlparse(url)
        host = parsed.netloc
        
        semaphore = self.get_semaphore(host)
        
        default_headers = {"Content-Type": "application/json"}
        if headers:
            default_headers.update(headers)
        
        async with semaphore:
            try:
                response = await self.client.post(url, json=data, headers=default_headers)
                
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", "60"))
                    logger.warning(f"Rate limited by {host}, waiting {retry_after}s")
                    await asyncio.sleep(retry_after)
                    raise httpx.HTTPStatusError("Rate limited", request=response.request, response=response)
                
                response.raise_for_status()
                return response.json()
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code >= 500:
                    logger.warning(f"Server error {e.response.status_code} from {host}, will retry")
                    raise
                elif e.response.status_code == 404:
                    logger.debug(f"Not found: {url}")
                    return None
                else:
                    logger.error(f"HTTP error {e.response.status_code} from {url}")
                    return None
            except Exception as e:
                logger.error(f"Request failed for {url}: {e}")
                return None
    
    async def close(self):
        await self.client.aclose()


_client_instance: Optional[RateLimitedClient] = None

def get_client() -> RateLimitedClient:
    global _client_instance
    if _client_instance is None:
        _client_instance = RateLimitedClient()
    return _client_instance

async def close_client():
    global _client_instance
    if _client_instance:
        await _client_instance.close()
        _client_instance = None