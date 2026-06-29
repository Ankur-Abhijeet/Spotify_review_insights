import logging
import sys
import os

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_format = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_format)
        logger.addHandler(console_handler)
        
        # File handler (if desired, could be added here)
        # Ensure log directory exists
        # log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
        # os.makedirs(log_dir, exist_ok=True)
        # file_handler = logging.FileHandler(os.path.join(log_dir, 'app.log'))
        # file_handler.setFormatter(console_format)
        # logger.addHandler(file_handler)

    return logger
