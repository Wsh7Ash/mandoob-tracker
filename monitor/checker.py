"""
Service health checker for government platforms.

This module handles the actual health checking of government services
including HTTP requests, SSL validation, and content verification.
"""

import asyncio
import aiohttp
import ssl
import time
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass
import re
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    service_id: str
    endpoint: str
    status: str  # 'operational', 'degraded', 'down'
    response_time: float
    status_code: Optional[int]
    error_message: Optional[str]
    timestamp: datetime
    ssl_valid: bool = True
    ssl_expiry_days: Optional[int] = None
    content_match: bool = True
    metadata: Dict = None


class ServiceHealthChecker:
    """
    Health checker for government services.
    
    This class performs comprehensive health checks including
    HTTP status, response time, SSL validation, and content verification.
    """
    
    def __init__(self, timeout: int = 30, retry_count: int = 3):
        """
        Initialize the health checker.
        
        Args:
            timeout: Request timeout in seconds
            retry_count: Number of retries for failed requests
        """
        self.timeout = timeout
        self.retry_count = retry_count
        self.session = None
        
        # SSL context for certificate validation
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = True
        self.ssl_context.verify_mode = ssl.CERT_REQUIRED
    
    async def __aenter__(self):
        """Async context manager entry."""
        connector = aiohttp.TCPConnector(
            ssl=self.ssl_context,
            limit=100,
            limit_per_host=10,
            ttl_dns_cache=300,
            use_dns_cache=True,
        )
        
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={
                'User-Agent': 'Mandoob-Tracker/1.0 (Health Check Monitor)',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
        )
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def check_service(self, service_config: Dict) -> HealthCheckResult:
        """
        Perform comprehensive health check on a service.
        
        Args:
            service_config: Service configuration dictionary
        
        Returns:
            HealthCheckResult with detailed status
        """
        service_id = service_config['id']
        base_url = service_config['url']
        endpoints = service_config.get('endpoints', [{'path': '/', 'method': 'GET'}])
        
        logger.info(f"Checking service: {service_id}")
        
        # Check main endpoint first
        main_result = await self._check_endpoint(service_id, base_url, endpoints[0])
        
        if main_result.status == 'down':
            # If main endpoint is down, service is down
            return main_result
        
        # Check additional endpoints
        additional_results = []
        for endpoint in endpoints[1:]:
            result = await self._check_endpoint(service_id, base_url, endpoint)
            additional_results.append(result)
        
        # Aggregate results
        return self._aggregate_results(main_result, additional_results)
    
    async def _check_endpoint(self, service_id: str, base_url: str, endpoint: Dict) -> HealthCheckResult:
        """
        Check a specific endpoint.
        
        Args:
            service_id: Service identifier
            base_url: Base URL of the service
            endpoint: Endpoint configuration
        
        Returns:
            HealthCheckResult for the endpoint
        """
        url = base_url + endpoint['path']
        method = endpoint.get('method', 'GET')
        expected_status = endpoint.get('expected_status', 200)
        content_keywords = endpoint.get('content_keywords', [])
        
        start_time = time.time()
        timestamp = datetime.utcnow()
        
        for attempt in range(self.retry_count):
            try:
                async with self.session.request(method, url) as response:
                    response_time = time.time() - start_time
                    
                    # Check SSL certificate
                    ssl_valid, ssl_expiry_days = await self._check_ssl_certificate(url)
                    
                    # Check content if keywords are specified
                    content_match = True
                    if content_keywords:
                        content = await response.text()
                        content_match = await self._check_content_keywords(content, content_keywords)
                    
                    # Determine status
                    status = self._determine_status(
                        response.status, expected_status, response_time, content_match
                    )
                    
                    return HealthCheckResult(
                        service_id=service_id,
                        endpoint=url,
                        status=status,
                        response_time=response_time,
                        status_code=response.status,
                        error_message=None,
                        timestamp=timestamp,
                        ssl_valid=ssl_valid,
                        ssl_expiry_days=ssl_expiry_days,
                        content_match=content_match,
                        metadata={
                            'attempt': attempt + 1,
                            'content_length': response.headers.get('content-length'),
                            'server': response.headers.get('server'),
                            'response_headers': dict(response.headers)
                        }
                    )
            
            except asyncio.TimeoutError:
                error_msg = f"Timeout after {self.timeout}s"
                logger.warning(f"Attempt {attempt + 1} failed for {url}: {error_msg}")
                if attempt == self.retry_count - 1:
                    return HealthCheckResult(
                        service_id=service_id,
                        endpoint=url,
                        status='down',
                        response_time=self.timeout,
                        status_code=None,
                        error_message=error_msg,
                        timestamp=timestamp,
                        ssl_valid=False
                    )
                    await asyncio.sleep(1)  # Wait before retry
            
            except aiohttp.ClientError as e:
                error_msg = str(e)
                logger.warning(f"Attempt {attempt + 1} failed for {url}: {error_msg}")
                if attempt == self.retry_count - 1:
                    return HealthCheckResult(
                        service_id=service_id,
                        endpoint=url,
                        status='down',
                        response_time=time.time() - start_time,
                        status_code=None,
                        error_message=error_msg,
                        timestamp=timestamp,
                        ssl_valid=False
                    )
                    await asyncio.sleep(1)  # Wait before retry
            
            except Exception as e:
                error_msg = f"Unexpected error: {str(e)}"
                logger.error(f"Unexpected error checking {url}: {error_msg}")
                return HealthCheckResult(
                    service_id=service_id,
                    endpoint=url,
                    status='down',
                    response_time=time.time() - start_time,
                    status_code=None,
                    error_message=error_msg,
                    timestamp=timestamp,
                    ssl_valid=False
                )
        
        # This should not be reached
        return HealthCheckResult(
            service_id=service_id,
            endpoint=url,
            status='down',
            response_time=time.time() - start_time,
            status_code=None,
            error_message="All retries failed",
            timestamp=timestamp,
            ssl_valid=False
        )
    
    async def _check_ssl_certificate(self, url: str) -> Tuple[bool, Optional[int]]:
        """
        Check SSL certificate validity and expiry.
        
        Args:
            url: URL to check
        
        Returns:
            Tuple of (is_valid, days_until_expiry)
        """
        try:
            parsed_url = urlparse(url)
            if parsed_url.scheme != 'https':
                return True, None
            
            hostname = parsed_url.hostname
            if not hostname:
                return False, None
            
            # Get SSL certificate
            context = ssl.create_default_context()
            with socket.create_connection((hostname, 443), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert = ssock.getpeercert()
                    
                    # Check if certificate is valid
                    if not cert:
                        return False, None
                    
                    # Check expiry date
                    expiry_date = datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z')
                    days_until_expiry = (expiry_date - datetime.utcnow()).days
                    
                    # Consider certificate valid if more than 7 days until expiry
                    is_valid = days_until_expiry > 7
                    
                    return is_valid, days_until_expiry
        
        except Exception as e:
            logger.warning(f"SSL check failed for {url}: {e}")
            return False, None
    
    async def _check_content_keywords(self, content: str, keywords: List[str]) -> bool:
        """
        Check if content contains expected keywords.
        
        Args:
            content: Response content
            keywords: List of keywords to check for
        
        Returns:
            True if all keywords are found, False otherwise
        """
        content_lower = content.lower()
        
        for keyword in keywords:
            if keyword.lower() not in content_lower:
                logger.warning(f"Keyword '{keyword}' not found in content")
                return False
        
        return True
    
    def _determine_status(self, status_code: int, expected_status: int, 
                         response_time: float, content_match: bool) -> str:
        """
        Determine service status based on check results.
        
        Args:
            status_code: HTTP status code
            expected_status: Expected status code
            response_time: Response time in seconds
            content_match: Whether content matches expectations
        
        Returns:
            Status string: 'operational', 'degraded', or 'down'
        """
        # Check if status code matches expected
        if status_code != expected_status:
            return 'down'
        
        # Check response time
        if response_time > 10:  # 10 seconds threshold
            return 'degraded'
        
        # Check content match
        if not content_match:
            return 'degraded'
        
        # Check for slow response (5-10 seconds)
        if response_time > 5:
            return 'degraded'
        
        return 'operational'
    
    def _aggregate_results(self, main_result: HealthCheckResult, 
                          additional_results: List[HealthCheckResult]) -> HealthCheckResult:
        """
        Aggregate results from multiple endpoints.
        
        Args:
            main_result: Result from main endpoint
            additional_results: Results from additional endpoints
        
        Returns:
            Aggregated HealthCheckResult
        """
        if not additional_results:
            return main_result
        
        # Count endpoint statuses
        total_endpoints = len(additional_results) + 1
        operational_count = sum(1 for r in additional_results if r.status == 'operational')
        degraded_count = sum(1 for r in additional_results if r.status == 'degraded')
        down_count = sum(1 for r in additional_results if r.status == 'down')
        
        # Add main endpoint to counts
        if main_result.status == 'operational':
            operational_count += 1
        elif main_result.status == 'degraded':
            degraded_count += 1
        else:
            down_count += 1
        
        # Determine overall status
        if down_count > 0:
            overall_status = 'down'
        elif degraded_count > 0:
            overall_status = 'degraded'
        else:
            overall_status = 'operational'
        
        # Calculate average response time
        response_times = [r.response_time for r in additional_results + [main_result]]
        avg_response_time = sum(response_times) / len(response_times)
        
        # Create aggregated result
        aggregated = HealthCheckResult(
            service_id=main_result.service_id,
            endpoint=main_result.endpoint,
            status=overall_status,
            response_time=avg_response_time,
            status_code=main_result.status_code,
            error_message=main_result.error_message,
            timestamp=main_result.timestamp,
            ssl_valid=main_result.ssl_valid,
            ssl_expiry_days=main_result.ssl_expiry_days,
            content_match=main_result.content_match,
            metadata={
                'total_endpoints': total_endpoints,
                'operational_endpoints': operational_count,
                'degraded_endpoints': degraded_count,
                'down_endpoints': down_count,
                'individual_results': [
                    {
                        'endpoint': r.endpoint,
                        'status': r.status,
                        'response_time': r.response_time,
                        'status_code': r.status_code
                    }
                    for r in additional_results + [main_result]
                ]
            }
        )
        
        return aggregated
    
    async def check_multiple_services(self, service_configs: List[Dict]) -> List[HealthCheckResult]:
        """
        Check multiple services concurrently.
        
        Args:
            service_configs: List of service configurations
        
        Returns:
            List of HealthCheckResult objects
        """
        tasks = [self.check_service(config) for config in service_configs]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results and handle exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error checking service {service_configs[i]['id']}: {result}")
                processed_results.append(HealthCheckResult(
                    service_id=service_configs[i]['id'],
                    endpoint=service_configs[i]['url'],
                    status='down',
                    response_time=0,
                    status_code=None,
                    error_message=str(result),
                    timestamp=datetime.utcnow(),
                    ssl_valid=False
                ))
            else:
                processed_results.append(result)
        
        return processed_results
    
    def get_service_summary(self, results: List[HealthCheckResult]) -> Dict:
        """
        Get summary of service check results.
        
        Args:
            results: List of HealthCheckResult objects
        
        Returns:
            Summary dictionary
        """
        total_services = len(results)
        operational = sum(1 for r in results if r.status == 'operational')
        degraded = sum(1 for r in results if r.status == 'degraded')
        down = sum(1 for r in results if r.status == 'down')
        
        avg_response_time = sum(r.response_time for r in results) / total_services if total_services > 0 else 0
        
        return {
            'total_services': total_services,
            'operational': operational,
            'degraded': degraded,
            'down': down,
            'operational_percentage': (operational / total_services * 100) if total_services > 0 else 0,
            'average_response_time': avg_response_time,
            'last_check': datetime.utcnow().isoformat(),
            'services': [
                {
                    'id': r.service_id,
                    'status': r.status,
                    'response_time': r.response_time,
                    'endpoint': r.endpoint
                }
                for r in results
            ]
        }
