"""
Logging configuration for the Word Filter API
"""
import logging
import logging.config
import sys
from datetime import datetime
import json
from typing import Dict, Any
import os


class JSONFormatter(logging.Formatter):
    """
    Custom JSON formatter for structured logging
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields if present
        if hasattr(record, 'extra_fields'):
            log_entry.update(record.extra_fields)
        
        # Add request context if available
        if hasattr(record, 'request_id'):
            log_entry["request_id"] = record.request_id
        
        return json.dumps(log_entry, ensure_ascii=False)


class RequestContextFilter(logging.Filter):
    """
    Filter to add request context to log records
    """
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Add request context to log record"""
        # This would be populated by middleware in a real app
        if not hasattr(record, 'request_id'):
            record.request_id = getattr(record, 'request_id', 'no-request')
        
        return True


# Logging configuration
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "detailed": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(funcName)s:%(lineno)d - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S"
        },
        "simple": {
            "format": "%(levelname)s - %(message)s"
        },
        "json": {
            "()": JSONFormatter,
        }
    },
    "filters": {
        "request_context": {
            "()": RequestContextFilter,
        }
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "detailed",
            "stream": "ext://sys.stdout",
            "filters": ["request_context"]
        },
        "file": {
            "level": "DEBUG",
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "json",
            "filename": "logs/app.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "filters": ["request_context"]
        },
        "error_file": {
            "level": "ERROR", 
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "json",
            "filename": "logs/error.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "filters": ["request_context"]
        },
        "performance_file": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler", 
            "formatter": "json",
            "filename": "logs/performance.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 3,
            "filters": ["request_context"]
        }
    },
    "loggers": {
        "word_filter": {
            "level": "DEBUG",
            "handlers": ["console", "file"],
            "propagate": False
        },
        "word_filter.performance": {
            "level": "INFO",
            "handlers": ["performance_file"],
            "propagate": False
        },
        "word_filter.api": {
            "level": "INFO", 
            "handlers": ["console", "file"],
            "propagate": False
        },
        "uvicorn": {
            "level": "INFO",
            "handlers": ["console"],
            "propagate": False
        },
        "uvicorn.access": {
            "level": "INFO",
            "handlers": ["file"],
            "propagate": False
        }
    },
    "root": {
        "level": "INFO",
        "handlers": ["console", "error_file"]
    }
}


def setup_logging(config: Dict[str, Any] = None) -> None:
    """
    Set up logging configuration
    
    Args:
        config: Optional custom logging configuration
    """
    if config is None:
        config = LOGGING_CONFIG
    
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    # Apply logging configuration
    logging.config.dictConfig(config)
    
    # Get logger and log startup
    logger = logging.getLogger("word_filter")
    logger.info("Logging system initialized")


def get_logger(name: str = None) -> logging.Logger:
    """
    Get a logger instance
    
    Args:
        name: Logger name (defaults to word_filter)
        
    Returns:
        Configured logger instance
    """
    if name is None:
        name = "word_filter"
    
    return logging.getLogger(name)


def log_performance(operation: str, duration: float, **kwargs) -> None:
    """
    Log performance metrics
    
    Args:
        operation: Name of the operation
        duration: Duration in seconds
        **kwargs: Additional context
    """
    perf_logger = logging.getLogger("word_filter.performance")
    
    extra_fields = {
        "operation": operation,
        "duration_seconds": duration,
        "performance_metric": True,
        **kwargs
    }
    
    perf_logger.info(
        f"Performance: {operation} completed in {duration:.4f}s",
        extra={"extra_fields": extra_fields}
    )


def log_api_call(method: str, endpoint: str, status_code: int, 
                duration: float, **kwargs) -> None:
    """
    Log API call details
    
    Args:
        method: HTTP method
        endpoint: API endpoint
        status_code: Response status code
        duration: Request duration in seconds
        **kwargs: Additional context
    """
    api_logger = logging.getLogger("word_filter.api")
    
    extra_fields = {
        "http_method": method,
        "endpoint": endpoint,
        "status_code": status_code,
        "duration_seconds": duration,
        "api_call": True,
        **kwargs
    }
    
    level = logging.ERROR if status_code >= 400 else logging.INFO
    
    api_logger.log(
        level,
        f"{method} {endpoint} - {status_code} - {duration:.4f}s",
        extra={"extra_fields": extra_fields}
    )


class LoggerMixin:
    """
    Mixin class to add logging capabilities to other classes
    """
    
    @property
    def logger(self) -> logging.Logger:
        """Get logger for this class"""
        return get_logger(f"word_filter.{self.__class__.__name__.lower()}")
    
    def log_debug(self, message: str, **kwargs) -> None:
        """Log debug message"""
        self.logger.debug(message, extra={"extra_fields": kwargs} if kwargs else None)
    
    def log_info(self, message: str, **kwargs) -> None:
        """Log info message"""
        self.logger.info(message, extra={"extra_fields": kwargs} if kwargs else None)
    
    def log_warning(self, message: str, **kwargs) -> None:
        """Log warning message"""
        self.logger.warning(message, extra={"extra_fields": kwargs} if kwargs else None)
    
    def log_error(self, message: str, exc_info: bool = False, **kwargs) -> None:
        """Log error message"""
        self.logger.error(
            message, 
            exc_info=exc_info,
            extra={"extra_fields": kwargs} if kwargs else None
        )
    
    def log_performance(self, operation: str, duration: float, **kwargs) -> None:
        """Log performance metric"""
        log_performance(operation, duration, 
                       class_name=self.__class__.__name__, **kwargs)


# Performance monitoring decorator
def monitor_performance(operation_name: str = None):
    """
    Decorator to monitor function performance
    
    Args:
        operation_name: Optional custom operation name
    """
    import functools
    import time
    
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                op_name = operation_name or f"{func.__module__}.{func.__name__}"
                log_performance(op_name, duration, 
                              success=True, args_count=len(args))
                
                return result
            except Exception as e:
                duration = time.time() - start_time
                
                op_name = operation_name or f"{func.__module__}.{func.__name__}"
                log_performance(op_name, duration, 
                              success=False, error=str(e), args_count=len(args))
                
                logger = get_logger()
                logger.error(f"Error in {op_name}: {e}", exc_info=True)
                raise
        
        return wrapper
    return decorator


def monitor_async_performance(operation_name: str = None):
    """
    Decorator to monitor async function performance
    
    Args:
        operation_name: Optional custom operation name
    """
    import functools
    import time
    
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                
                op_name = operation_name or f"{func.__module__}.{func.__name__}"
                log_performance(op_name, duration, 
                              success=True, args_count=len(args))
                
                return result
            except Exception as e:
                duration = time.time() - start_time
                
                op_name = operation_name or f"{func.__module__}.{func.__name__}"
                log_performance(op_name, duration, 
                              success=False, error=str(e), args_count=len(args))
                
                logger = get_logger()
                logger.error(f"Error in {op_name}: {e}", exc_info=True)
                raise
        
        return wrapper
    return decorator
