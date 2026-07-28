"""Health, readiness, liveness, and Prometheus metrics."""
import time

from fastapi import APIRouter, HTTPException

from api import dependencies as deps

router = APIRouter(tags=["health"])


@router.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Word Filter API - Optimized", "total_words": len(deps.words_list)}


@router.get("/health")
async def health_check():
    """Health check endpoint for Kubernetes/Railway."""
    try:
        word_count = await deps.word_manager.get_word_count()
        storage_info = await deps.word_manager.get_storage_info()
        return {
            "status": "healthy",
            "word_count": word_count,
            "storage_connected": storage_info.get("connected", False),
            "storage_provider": storage_info.get("provider", "unknown"),
            "storage_type": storage_info.get("type", "unknown"),
            "timestamp": time.time(),
        }
    except Exception as e:
        deps.logger.error("Health check failed: %s", e)
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}") from e


@router.get("/health/ready")
async def readiness_check():
    """Readiness probe for deployment orchestrators."""
    try:
        if not deps.words_list:
            await deps.load_words_concurrent()

        if not deps.words_list:
            raise RuntimeError("Word database not loaded")

        return {
            "ready": True,
            "words_loaded": len(deps.words_list),
            "timestamp": time.time(),
        }
    except Exception as e:
        deps.logger.error("Readiness check failed: %s", e)
        raise HTTPException(status_code=503, detail="Not ready") from e


@router.get("/health/live")
async def liveness_check():
    """Liveness probe for deployment orchestrators."""
    try:
        return {
            "alive": True,
            "uptime": time.time(),
            "version": "2.2.0",
        }
    except Exception as e:
        deps.logger.error("Liveness check failed: %s", e)
        raise HTTPException(status_code=503, detail="Service dead") from e


@router.get("/metrics")
async def prometheus_metrics():
    """Prometheus metrics endpoint for monitoring."""
    try:
        metrics = [
            "# HELP word_filter_total_words Total number of words in database",
            "# TYPE word_filter_total_words gauge",
            f"word_filter_total_words {len(deps.words_list)}",
            "# HELP word_filter_api_requests_total Total API requests",
            "# TYPE word_filter_api_requests_total counter",
            f"word_filter_api_requests_total {deps.total_api_requests}",
        ]
        return "\n".join(metrics) + "\n"
    except Exception as e:
        deps.logger.error("Metrics endpoint failed: %s", e)
        raise HTTPException(status_code=500, detail="Metrics unavailable") from e
