"""
Health Monitoring - Comprehensive health checks.
"""

from typing import Dict, Any, List
from datetime import datetime
import asyncio
from enum import Enum
from loguru import logger


class HealthStatus(str, Enum):
    """Health status enumeration."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class HealthCheck:
    """
    Individual health check.
    """
    
    def __init__(self, name: str, check_func, timeout: float = 5.0):
        """
        Initialize health check.
        
        Args:
            name: Check name
            check_func: Async function that performs the check
            timeout: Check timeout in seconds
        """
        self.name = name
        self.check_func = check_func
        self.timeout = timeout
    
    async def execute(self) -> Dict[str, Any]:
        """
        Execute health check.
        
        Returns:
            Health check result
        """
        start_time = datetime.utcnow()
        
        try:
            # Run check with timeout
            result = await asyncio.wait_for(
                self.check_func(),
                timeout=self.timeout
            )
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            return {
                "name": self.name,
                "status": HealthStatus.HEALTHY,
                "message": result.get("message", "OK"),
                "details": result.get("details", {}),
                "duration_seconds": duration,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        except asyncio.TimeoutError:
            duration = (datetime.utcnow() - start_time).total_seconds()
            logger.warning(f"Health check '{self.name}' timed out")
            
            return {
                "name": self.name,
                "status": HealthStatus.UNHEALTHY,
                "message": f"Timeout after {self.timeout}s",
                "duration_seconds": duration,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            logger.error(f"Health check '{self.name}' failed: {e}")
            
            return {
                "name": self.name,
                "status": HealthStatus.UNHEALTHY,
                "message": str(e),
                "error_type": type(e).__name__,
                "duration_seconds": duration,
                "timestamp": datetime.utcnow().isoformat()
            }


class HealthMonitor:
    """
    Manages health checks and monitoring.
    """
    
    def __init__(self):
        """Initialize health monitor."""
        self.checks: List[HealthCheck] = []
        self.start_time = datetime.utcnow()
    
    def register_check(self, name: str, check_func, timeout: float = 5.0):
        """
        Register a health check.
        
        Args:
            name: Check name
            check_func: Async check function
            timeout: Check timeout
        """
        check = HealthCheck(name, check_func, timeout)
        self.checks.append(check)
        logger.info(f"Registered health check: {name}")
    
    async def run_checks(self) -> Dict[str, Any]:
        """
        Run all health checks.
        
        Returns:
            Health check results
        """
        # Run all checks concurrently
        results = await asyncio.gather(
            *[check.execute() for check in self.checks],
            return_exceptions=True
        )
        
        # Process results
        check_results = []
        for result in results:
            if isinstance(result, Exception):
                check_results.append({
                    "status": HealthStatus.UNHEALTHY,
                    "message": str(result),
                    "error_type": type(result).__name__
                })
            else:
                check_results.append(result)
        
        # Determine overall status
        statuses = [r.get("status", HealthStatus.UNKNOWN) for r in check_results]
        
        if all(s == HealthStatus.HEALTHY for s in statuses):
            overall_status = HealthStatus.HEALTHY
        elif any(s == HealthStatus.UNHEALTHY for s in statuses):
            overall_status = HealthStatus.UNHEALTHY
        else:
            overall_status = HealthStatus.DEGRADED
        
        # Calculate uptime
        uptime = (datetime.utcnow() - self.start_time).total_seconds()
        
        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": uptime,
            "checks": check_results,
            "summary": {
                "total": len(check_results),
                "healthy": sum(1 for r in check_results if r.get("status") == HealthStatus.HEALTHY),
                "degraded": sum(1 for r in check_results if r.get("status") == HealthStatus.DEGRADED),
                "unhealthy": sum(1 for r in check_results if r.get("status") == HealthStatus.UNHEALTHY)
            }
        }
    
    async def get_simple_status(self) -> Dict[str, Any]:
        """
        Get simple health status (faster, for readiness/liveness probes).
        
        Returns:
            Simple health status
        """
        uptime = (datetime.utcnow() - self.start_time).total_seconds()
        
        return {
            "status": HealthStatus.HEALTHY,
            "uptime_seconds": uptime,
            "timestamp": datetime.utcnow().isoformat()
        }


# Global health monitor
health_monitor = HealthMonitor()


# Define default health checks

async def check_orchestrator() -> Dict[str, Any]:
    """Check context orchestrator health."""
    from mlcf.api.main import app_state
    
    if app_state.orchestrator:
        stats = app_state.orchestrator.get_statistics()
        return {
            "message": "Orchestrator operational",
            "details": {
                "total_items": stats.get("total_items", 0)
            }
        }
    else:
        raise Exception("Orchestrator not initialized")


async def check_vector_store() -> Dict[str, Any]:
    """Check vector store health."""
    from mlcf.api.main import app_state
    
    if app_state.vector_store:
        try:
            info = app_state.vector_store.get_collection_info()
            return {
                "message": "Vector store operational",
                "details": {
                    "vectors_count": info.get("vectors_count", 0)
                }
            }
        except Exception as e:
            raise Exception(f"Vector store error: {e}")
    else:
        return {"message": "Vector store disabled"}


async def check_graph_store() -> Dict[str, Any]:
    """Check graph store health."""
    from mlcf.api.main import app_state
    
    if app_state.graph_store:
        try:
            stats = app_state.graph_store.get_statistics()
            total_nodes = sum(stats.get("nodes_by_type", {}).values())
            return {
                "message": "Graph store operational",
                "details": {
                    "total_nodes": total_nodes
                }
            }
        except Exception as e:
            raise Exception(f"Graph store error: {e}")
    else:
        return {"message": "Graph store disabled"}


async def check_memory() -> Dict[str, Any]:
    """Check memory usage."""
    try:
        import psutil
        process = psutil.Process()
        mem_info = process.memory_info()
        mem_percent = process.memory_percent()
        
        if mem_percent > 90:
            raise Exception(f"High memory usage: {mem_percent:.1f}%")
        
        return {
            "message": f"Memory usage: {mem_percent:.1f}%",
            "details": {
                "rss_mb": mem_info.rss / 1024 / 1024,
                "percent": mem_percent
            }
        }
    except ImportError:
        return {"message": "Memory monitoring not available"}


# Register default health checks
health_monitor.register_check("orchestrator", check_orchestrator, timeout=2.0)
health_monitor.register_check("vector_store", check_vector_store, timeout=3.0)
health_monitor.register_check("graph_store", check_graph_store, timeout=3.0)
health_monitor.register_check("memory", check_memory, timeout=1.0)