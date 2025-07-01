#!/usr/bin/env python3
"""
Configuration file for the job automation backend.
Controls debug output, logging levels, and other settings.
"""

import os
import logging
import warnings

# Debug settings
DEBUG_LLM = os.getenv("DEBUG_LLM", "false").lower() == "true"
DEBUG_SERVER = os.getenv("DEBUG_SERVER", "false").lower() == "true"

# Logging configuration
def configure_logging():
    """Configure logging to suppress unwanted output"""
    
    # Silence llama-cpp related loggers
    logging.getLogger("llama_cpp").setLevel(logging.ERROR)
    logging.getLogger("llama_cpp_python").setLevel(logging.ERROR)
    logging.getLogger("llama_cpp_python.llama").setLevel(logging.ERROR)
    
    # Silence other noisy loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    
    # Configure root logger
    if DEBUG_SERVER:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    
    # Suppress specific warnings
    warnings.filterwarnings("ignore", message=".*control token.*")
    warnings.filterwarnings("ignore", message=".*is not marked as EOG.*")
    warnings.filterwarnings("ignore", message=".*UserWarning.*")

# Model settings
MODEL_PATH = "./models/codellama-7b-instruct.Q4_K_M.gguf"
MODEL_CONTEXT_SIZE = 32768  # Keep 32K to handle longer resumes
MODEL_THREADS = 8  # Reduced for GPU usage
MODEL_GPU_LAYERS = 25  # Optimized for RTX 2080 8GB VRAM

# LLM processing settings
LLM_TIMEOUT_SECONDS = int(os.getenv("LLM_TIMEOUT_SECONDS", "300"))  # 5 minutes default timeout

# Server settings
HOST = "0.0.0.0"
PORT = 8000

# CORS settings
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "chrome-extension://jfcimmieenbgbchfgmogceflafddmkpk"
]

# Initialize logging when module is imported
configure_logging() 