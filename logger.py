import json
import logging
import sys
from datetime import datetime
from typing import Any, Dict, Optional
import os

class StructuredLogger:
    def __init__(self, name: str, log_file: str = "scraper_logs.jsonl", level: int = logging.INFO):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        self.logger.handlers = []  # Clear existing handlers
        
        # Console Handler (Human Readable)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(console_handler)
        
        # File Handler (JSON Lines)
        self.log_file = log_file
        # Ensure log file exists or can be created
        try:
            with open(self.log_file, 'a') as f:
                pass
        except Exception:
            pass

    def _log(self, level: str, message: str, context: Optional[Dict[str, Any]] = None):
        """Log a message with context variables."""
        timestamp = datetime.utcnow().isoformat()
        
        log_entry = {
            "timestamp": timestamp,
            "level": level,
            "message": message,
            "context": context or {}
        }
        
        # Write to JSONL file
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            print(f"FAILED TO WRITE LOG: {e}")
            
        # Log to console using standard logging
        if level == "INFO":
            self.logger.info(f"{message} | {context if context else ''}")
        elif level == "WARNING":
            self.logger.warning(f"{message} | {context if context else ''}")
        elif level == "ERROR":
            self.logger.error(f"{message} | {context if context else ''}")
        elif level == "DEBUG":
            self.logger.debug(f"{message} | {context if context else ''}")

    def info(self, message: str, **kwargs):
        self._log("INFO", message, kwargs)

    def warning(self, message: str, **kwargs):
        self._log("WARNING", message, kwargs)
        
    def error(self, message: str, **kwargs):
        self._log("ERROR", message, kwargs)
        
    def debug(self, message: str, **kwargs):
        self._log("DEBUG", message, kwargs)

# Global instance for easy import
logger = StructuredLogger("GlobalScraperLogger")
