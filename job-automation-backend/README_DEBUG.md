# Debug Output Control

This document explains how to control debug output and silence LLM generation in the job automation backend.

## Environment Variables

### DEBUG_LLM
Controls verbose output during LLM (Language Model) generation.

- **Default**: `false` (silent mode)
- **When `true`**: Shows detailed LLM prompts, model loading, and generation output
- **When `false`**: Runs silently with minimal output

```bash
# Enable debug output
export DEBUG_LLM=true  # Linux/Mac
set DEBUG_LLM=true     # Windows CMD
$env:DEBUG_LLM='true'  # PowerShell

# Disable debug output (default)
export DEBUG_LLM=false
unset DEBUG_LLM
```

### DEBUG_SERVER
Controls general server debug output.

- **Default**: `false` (normal logging)
- **When `true`**: Shows detailed server logs
- **When `false`**: Shows only important server messages

```bash
# Enable server debug
export DEBUG_SERVER=true

# Disable server debug (default)
export DEBUG_SERVER=false
```

## What Gets Silenced

When `DEBUG_LLM=false` (default), the following output is suppressed:

1. **LLM Model Loading**: No output during model initialization
2. **LLM Prompts**: The exact prompt sent to the model is hidden
3. **LLM Generation**: Raw output from the model is hidden
4. **Control Token Warnings**: llama-cpp control token warnings are suppressed
5. **JSON Parsing**: Detailed JSON parsing steps are hidden

## What Still Shows

Even in silent mode, you'll still see:

1. **Error Messages**: Important errors are still logged
2. **Server Status**: Basic server startup and status messages
3. **API Responses**: Normal API response messages
4. **Critical Warnings**: Important warnings that need attention

## Example Output

### Silent Mode (DEBUG_LLM=false)
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Debug Mode (DEBUG_LLM=true)
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000

================================================================================
[DEBUG] EXACT PROMPT SENT TO LLM:
================================================================================
Extract from this resume and return as valid JSON with these fields...
================================================================================
[DEBUG] END OF PROMPT
================================================================================
[DEBUG] Attempting to load Mistral-7B v0.3 GGUF model with llama-cpp-python: ./models/mistral-7b-instruct-v0.3.Q4_K_M.gguf
[DEBUG] Mistral-7B v0.3 GGUF model loaded successfully
[DEBUG] About to call llama-cpp-python for generation...

================================================================================
[DEBUG] RAW OUTPUT FROM LLM:
================================================================================
{
  "first_name": "John",
  "last_name": "Doe",
  ...
}
================================================================================
[DEBUG] END OF LLM OUTPUT
================================================================================
[DEBUG] Parsed profile_json: {'first_name': 'John', 'last_name': 'Doe', ...}
```

## Troubleshooting

### If you still see control token warnings:
1. Make sure you're using the latest version of llama-cpp-python
2. Check that the config.py file is being imported correctly
3. Verify that the logging configuration is applied

### If you need to debug LLM issues:
1. Set `DEBUG_LLM=true`
2. Upload a resume and check the console output
3. Look for any error messages or unexpected behavior

### If the server is too verbose:
1. Set `DEBUG_SERVER=false`
2. Set `DEBUG_LLM=false`
3. Restart the server

## Configuration File

The debug settings are centralized in `config.py`. You can modify this file to change default behavior or add new configuration options. 