# Retrace Interpreter

A Python interpreter with provenance tracking capabilities, exposing debugging functionality via an MCP (Model Context Protocol) server for LLM integration.

## Components

### Core Interpreter
- `retraceinterpreter.py` - Main interpreter with instruction-level execution tracking
- `retrace_provenance.py` - Provenance tracking engine that records where values come from

### C++ Extensions
- `_retraceinterpreter.cpp` - Python C extension for high-performance tracing
- `frame.cpp/h` - Frame state management
- `interpreter.cpp/h` - Core interpreter logic
- `opcodes.cpp` - Python opcode handling
- `threadstate.cpp/h` - Thread state management
- `setup.py` - Build configuration for the C extension

### MCP Server
- `mcp_server.py` - Model Context Protocol server exposing interpreter API to LLMs

#### MCP Tools Available
| Tool | Description |
|------|-------------|
| `open_trace` | Open a recorded execution for analysis |
| `close_trace` | Close a debugging session |
| `run_to_instruction` | Execute to a specific instruction |
| `list_frames_at_step` | Get call stack at a point in execution |
| `get_provenance` | Get provenance info for a variable |
| `trace_provenance` | Trace backwards to find value origins |
| `get_source` | Get source code context |
| `search_variables` | Search for variables by pattern |
| `get_execution_summary` | Get overview of recorded execution |
| `list_sessions` | List all open debugging sessions |

## Building the C Extension

```bash
python setup.py build_ext --inplace
```

## Running the MCP Server

```bash
python mcp_server.py
```

The server uses JSON-RPC 2.0 over stdin/stdout for communication with LLM clients.

## Tests

```bash
python -m pytest test_interpreter.py
python -m pytest test_provenance.py
python -m pytest test_instruction_counting.py
```

## Usage with Claude

Configure the MCP server in your Claude client settings to enable automated debugging capabilities. Claude can then:

1. Open recorded executions
2. Search for suspicious values
3. Trace provenance backwards to find root causes
4. Provide detailed analysis and recommendations
