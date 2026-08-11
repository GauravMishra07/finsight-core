# config/logger.py
import logging
import sys

def setup_logger(name: str = "FinSight") -> logging.Logger:
    """
    Sets up a standardized logger instance for FinSight core services.
    """
    logger = logging.getLogger(name)
    
    # Prevent duplicate log output if handlers are already attached
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        
        # Console Handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        
        logger.addHandler(console_handler)
        
    return logger