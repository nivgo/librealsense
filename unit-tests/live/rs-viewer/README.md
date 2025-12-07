# RealSense Viewer Test Runner

This directory contains a general test runner system for RealSense Viewer tests that can be defined in JSON format.

## Files Structure

```
rs-viewer/
├── general_viewer_test_runner.py    # Main test runner script
├── test-stereo-depth-health-agent.py # Original specific test (kept for reference)
├── agent_server_client.py           # Agent communication utilities
├── viewer_process_manager.py        # Viewer process management
├── gui_server_manager.py           # GUI control server
├── test_constants.py               # Test constants, configurations, and validation presets
└── tests/                          # JSON test definitions directory
    ├── stereo_depth_health.json    # Stereo depth health test
    ├── resolution_test_sequence.json # Resolution testing sequence
    ├── color_stream_basic.json     # Color stream basic test
    └── device_connection.json      # Device connection test
```

## Usage

### Run All Tests
```bash
python general_viewer_test_runner.py
```

### Run Specific Test
```bash
python general_viewer_test_runner.py stereo_depth_health
python general_viewer_test_runner.py resolution_test_sequence
```

### List Available Tests
```bash
python general_viewer_test_runner.py --list
```

### Use Custom Tests Directory
```bash
python general_viewer_test_runner.py --tests-dir /path/to/custom/tests
```

## Enabling/Disabling Tests

Tests can be enabled or disabled by setting the `enabled` field in the JSON:

```json
{
  "name": "My Test",
  "enabled": false,
  "description": "This test is disabled and won't run"
}
```

- `enabled: true` (default): Test will run when discovered
- `enabled: false`: Test will be skipped during discovery
- If the field is missing, it defaults to `true`

## JSON Test Format

### Basic Test Structure

```json
{
  "name": "Test Name",
  "description": "Detailed description of what this test does",
  "enabled": true,
  "device_requirements": ["D455", "D435i"],
  "task_description": "What the agent should do",
  "window_setup": "fullscreen|normal|maximized",
  "timeout_seconds": 120,
  "validation": {
    "type": "agent_result",
    "expect_success": true,
    "required_keywords": ["keyword1", "keyword2"]
  }
}
```

### Sequence Test Structure

For multi-step tests, add a `sequence` array:

```json
{
  "name": "Multi-Step Test",
  "description": "Test with multiple steps",
  "sequence": [
    {
      "type": "task",
      "prompt": "Description of action to perform",
      "name": "Human-readable step name"
    },
    {
      "type": "validate",
      "expectation": "What should be validated",
      "mode": "validation_mode",
      "name": "Validation step name"
    }
  ]
}
```

## Test Types

### Single Task Tests
- Simple tests with one agent task
- Good for basic functionality verification
- Example: `stereo_depth_health.json`, `color_stream_basic.json`

### Sequence Tests  
- Multi-step tests with tasks and validations
- Good for complex workflows
- Example: `resolution_test_sequence.json`

## Field Descriptions

### Required Fields
- `name`: Test name (string)
- `task_description`: What the agent should do (for single task tests)
- `sequence`: Array of steps (for sequence tests)

### Optional Fields
- `description`: Detailed test description
- `enabled`: Whether the test is enabled (default: true)
- `device_requirements`: Array of device types that support this test
- `window_setup`: Window mode ("fullscreen", "normal", "maximized")
- `timeout_seconds`: Maximum test execution time
- `validation`: Test result validation configuration

### Validation Configuration
- `type`: "agent_result" (standard) or "custom" 
- `expect_success`: Whether test should pass (true) or fail (false)
- `required_keywords`: Keywords that must appear in results

### Sequence Step Types
- `task`: Perform an action via agent
  - `prompt`: Description of action
  - `name`: Human-readable step name
- `validate`: Validate a condition
  - `expectation`: What should be validated
  - `mode`: Validation mode/context
  - `name`: Human-readable validation name

## Examples

### Basic Stereo Depth Test
```json
{
  "name": "Stereo Depth Health Test",
  "description": "Test the health of stereo depth module",
  "enabled": true,
  "device_requirements": ["D455"],
  "task_description": "Start stereo module and verify depth stream health",
  "validation": {
    "type": "agent_result", 
    "expect_success": true,
    "required_keywords": ["depth", "healthy"]
  }
}
```

### Resolution Testing Sequence  
```json
{
  "name": "Resolution Testing",
  "description": "Test multiple resolutions",
  "enabled": true,
  "sequence": [
    {
      "type": "task",
      "prompt": "Set resolution to 480x270",
      "name": "Set Resolution"
    },
    {
      "type": "task", 
      "prompt": "Start stereo module",
      "name": "Enable Stream"
    },
    {
      "type": "validate",
      "expectation": "Depth stream is healthy at 480x270",
      "mode": "stereo_health",
      "name": "Verify Health"
    }
  ]
}
```

## Environment Variables

The test runner respects the same environment variables as the original agent tests:

- `AGENT_SERVER_HOST`: Agent server hostname
- `AGENT_SERVER_PORT`: Agent server port  
- `AGENT_SERVER_TIMEOUT_SEC`: Test timeout
- `AGENT_SERVER_POLL_INTERVAL_SEC`: Polling interval
- `AGENT_SERVER_FORCE`: Force mode
- `AGENT_SERVER_BYPASS_PROXY`: Bypass proxy settings

## Adding New Tests

1. Create a new JSON file in the `tests/` directory
2. Follow the JSON schema documented above
3. Test locally with the runner
4. The test will be automatically discovered and can be run

## Migration from Specific Tests

The original `test-stereo-depth-health-agent.py` has been kept for reference, but the functionality has been converted to `tests/stereo_depth_health.json`. This demonstrates how specific Python tests can be converted to the general JSON format.

The general test runner provides:
- Easier test creation (JSON vs Python code)
- Consistent test structure
- Better test discovery and filtering
- Sequence test support
- Flexible validation options
