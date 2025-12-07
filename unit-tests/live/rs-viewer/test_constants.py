# License: Apache 2.0. See LICENSE file in root directory.
# Copyright(c) 2023 RealSense, Inc. All Rights Reserved.

"""
Constants and enums used across RealSense viewer tests.
"""

from enum import IntEnum

class HttpStatusCode(IntEnum):
    """HTTP status codes used in agent communication"""
    OK = 200
    ACCEPTED = 202
    BAD_REQUEST = 400
    NOT_FOUND = 404
    INTERNAL_SERVER_ERROR = 500

class TestTiming(IntEnum):
    """Timing constants for test operations (in seconds)"""
    WINDOW_FOCUS_DELAY = 0.5
    WINDOW_MAXIMIZE_DELAY = 0.3
    VIEWER_STARTUP_DELAY = 5
    VIEWER_STARTUP_DELAY_WINDOWS = 8
    VIEWER_ADDITIONAL_WAIT = 3

class WindowSetupMode:
    """Window setup modes for different test scenarios"""
    MINIMAL = "minimal"          # Just focus the window 
    STANDARD = "standard"        # Focus + maximize
    FULLSCREEN = "fullscreen"    # Focus + maximize + fullscreen (for agent tests)

class TestDefaults:
    """Default configuration values for tests"""
    GUI_SERVER_PORT = 5001
    AGENT_SERVER_HOST = '143.185.122.14'  # Remote agent server like stable version
    AGENT_SERVER_PORT = 8099
    DEFAULT_TIMEOUT = 300.0
    POLL_INTERVAL = 2.0
    AGENT_BYPASS_PROXY = True  # Enable proxy bypass by default for agent server
    
    # CI/Jenkins environment configuration
    CI_DISPLAY = ':0'  # X11 display for CI environments
    CI_NO_PROXY_HOST = '143.185.122.14'  # Host to bypass proxy for the agent server
    
    # Test runner configuration
    DEFAULT_TEST_TIMEOUT_SECONDS = 120
    DEFAULT_WINDOW_SETUP = "fullscreen"
    TEST_DISCOVERY_PATTERNS = ["*.json"]
    LOG_LEVEL = "INFO"
    
    # Viewer configuration
    VIEWER_STARTUP_TIMEOUT_SECONDS = 30
    VIEWER_CLEANUP_TIMEOUT_SECONDS = 10

class ValidationPresets:
    """Predefined validation configurations for common test types"""
    
    STEREO_HEALTH = {
        "type": "agent_result",
        "expect_success": True,
        "required_keywords": ["depth", "stereo", "healthy", "stream"]
    }
    
    COLOR_STREAM = {
        "type": "agent_result", 
        "expect_success": True,
        "required_keywords": ["color", "stream", "valid"]
    }
    
    DEVICE_CONNECTION = {
        "type": "agent_result",
        "expect_success": True,
        "required_keywords": ["device", "connected", "detected"]
    }
