from notion_agent import Notionagent
from fastapi import FastAPI, HTTPException, Form
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Dict, Optional, List, Union
from dotenv import load_dotenv
import os
import hashlib
import uvicorn
import time

import logfire

# Load environment variables
load_dotenv()

# Configure logfire if token is available
logfire_token = os.getenv('logfire_token')
if logfire_token:
    logfire.configure(token=logfire_token)
    logfire.instrument_pydantic_ai()

startup_time = time.time()


# Initialize FastAPI app
app = FastAPI(
    title="Notion Agent API", 
    description="""
    ## Notion AI Agent API
    
    A comprehensive API for interacting with Notion AI Agent with Notion workspace integration.
    
    ### Available Endpoints:
    
    **GET Requests:**
    - `/health` - Check API health status and uptime
    - `/api-docs` - Get comprehensive API documentation
    
    **POST Requests:**
    - `/chat` - Main chat endpoint for text-based interactions with Notion
    - `/reset` - Reset Notion Agent's memory and conversation history
    
    ### Features:
    - Text-based chat interactions
    - Notion workspace integration
    - OpenAI GPT integration
    - Composio tools integration
    - Memory management and conversation reset
    - Health monitoring and uptime tracking
    """,
    version="0.1.0",
    docs_url=None,  # Disable built-in docs
    redoc_url=None  # Disable redoc as well
)

# KeyCache will handle agent initialization

class EndpointInfo(BaseModel):
    path: str
    method: str
    description: str
    parameters: List[Dict[str, str]]
    example_request: Dict[str, str]
    example_response: Dict[str, str]

class APIDocumentation(BaseModel):
    name: str
    version: str
    description: str
    endpoints: List[EndpointInfo]

class KeyCache:
    def __init__(self):
        self._last_keys_hash = None
        self._notion_agent = None
    
    def _compute_keys_hash(self, api_keys: Dict[str, str]) -> str:
        # Sort keys to ensure consistent hashing regardless of order
        sorted_keys = dict(sorted(api_keys.items()))
        # Create a string representation of the keys
        keys_str = "|".join(f"{k}:{v}" for k, v in sorted_keys.items() if v is not None)
        # Compute hash
        return hashlib.sha256(keys_str.encode()).hexdigest()
    
    def get_notion_agent(self, api_keys: Dict[str, str]) -> Notionagent:
        current_hash = self._compute_keys_hash(api_keys)
        
        # Initialize or reinitialize if keys have changed
        if self._last_keys_hash != current_hash:
            # Filter out None values for initialization
            init_keys = {k: v for k, v in api_keys.items() if v is not None}
            # Initialize with MCP server URL and API keys
            self._notion_agent = Notionagent(
                mcp_server_url=os.getenv('mcp_server_url'),
                api_keys=init_keys
            )
            self._last_keys_hash = current_hash
        
        return self._notion_agent
    
    def reset(self):
        if self._notion_agent:
            self._notion_agent.reset()
        self._last_keys_hash = None

# Initialize key cache
key_cache = KeyCache()

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "uptime": time.time() - startup_time,
        "version": "0.1.0",
        "service": "Notion Agent API"
    }

@app.post("/chat")
async def chat(
    query: str = Form(...),
    openai_api_key: str = Form(...),
    composio_key: str = Form(...),
):
    try:
        api_keys = {
            "openai_api_key": openai_api_key,
            "composio_key": composio_key
        }
        
        # Get or initialize Notion Agent instance based on keys
        try:
            notion_agent = key_cache.get_notion_agent(api_keys)
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error getting Notion Agent instance: {str(e)}")
        
        # Use the chat method from Notionagent
        response = await notion_agent.chat(query)
        
        return {
            "response": response
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in chat: {str(e)}")

@app.post("/reset")
async def reset_notion_agent():
    try:
        key_cache.reset()
        return {"status": "success", "message": "Notion Agent memory reset successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tool-schemas")
async def get_tool_schemas(
    openai_api_key: str = Form(...),
    composio_key: str = Form(...),
):
    try:
        api_keys = {
            "openai_api_key": openai_api_key,
            "composio_key": composio_key
        }
        
        notion_agent = key_cache.get_notion_agent(api_keys)
        return {"tool_schemas": notion_agent.tool_shemas}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving tool schemas: {str(e)}")

@app.get("/api-docs")
async def get_markdown_documentation():
    """
    Returns comprehensive documentation for all API endpoints in markdown format
    """
  
    return """# Notion Agent API Documentation

**Version:** 0.1.0

## Description
API for interacting with Notion AI Agent, including Notion workspace integration, chat, and content management capabilities.

---

## Endpoints

### POST `/chat`
**Description:** Main chat endpoint that processes text queries and integrates with Notion workspace.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| query | string | Yes | The text query to process |
| openai_api_key | string | Yes | OpenAI API key for language model |
| composio_key | string | Yes | Composio API key for Notion workspace integration |

**Example Request:**
```json
{
    "query": "Create a new page in my Notion workspace",
    "openai_api_key": "your_openai_api_key",
    "composio_key": "your_composio_key"
}
```

**Example Response:**
```json
{
    "response": "I've created a new page in your Notion workspace..."
}
```

---

### POST `/reset`
**Description:** Reset Notion Agent's memory and conversation history

**Parameters:** None

**Example Request:**
```json

```

**Example Response:**
```json
{
    "status": "success",
    "message": "Notion Agent memory reset successfully"
}
```

---

### GET `/health`
**Description:** Check API health status and uptime

**Parameters:** None

**Example Request:** No body required

**Example Response:**
```json
{
    "status": "healthy",
    "uptime": 3600.5,
    "version": "0.1.0",
    "service": "Notion Agent API"
}
```

---

### GET `/tool-schemas`
**Description:** Get available tool schemas for the Notion agent

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| openai_api_key | string | Yes | OpenAI API key for language model |
| composio_key | string | Yes | Composio API key for Notion workspace integration |

**Example Response:**
```json
{
    "tool_schemas": {
        "notion_tools": ["create_page", "update_page", "search_pages", "..."]
    }
}
```

---

### GET `/docs`
**Description:** Get comprehensive API documentation in JSON format

**Parameters:** None

**Example Request:** No body required

**Example Response:** Returns structured JSON documentation

---

### GET `/api-docs`
**Description:** Get comprehensive API documentation in markdown format

**Parameters:** None

**Example Request:** No body required

**Example Response:** Returns this markdown documentation

---

## Notion Integration Features
- **Page Management:** Create, update, delete, and search Notion pages
- **Database Operations:** Query and manipulate Notion databases
- **Content Management:** Add text, images, and other content blocks
- **Workspace Navigation:** Browse and organize Notion workspace

## Additional Features
- Text-based chat interactions
- Notion workspace full integration
- OpenAI GPT integration
- Composio tools integration
- Memory management and conversation reset
- Health monitoring and uptime tracking

## Usage Notes
- All requests should use multipart/form-data encoding
- OpenAI API key and Composio key are required for full functionality
- The chat endpoint processes text queries and executes Notion operations
- Tool schemas provide information about available Notion operations
"""

@app.get("/docs")
async def get_docs():
    """
    Returns comprehensive documentation for all API endpoints in JSON format
    """
    return {
        "name": "Notion Agent API",
        "version": "0.1.0", 
        "description": "API for interacting with Notion AI Agent with Notion workspace integration",
        "endpoints": [
            {
                "path": "/chat",
                "method": "POST",
                "description": "Main chat endpoint with Notion workspace integration",
                "content_type": "multipart/form-data",
                "parameters": [
                    {
                        "name": "query",
                        "type": "string",
                        "required": True,
                        "description": "The text query to process"
                    },
                    {
                        "name": "openai_api_key",
                        "type": "string", 
                        "required": True,
                        "description": "OpenAI API key for language model"
                    },
                    {
                        "name": "composio_key",
                        "type": "string",
                        "required": True,
                        "description": "Composio API key for Notion workspace integration"
                    }
                ],
                "response": {
                    "response": "string - The AI assistant's response"
                }
            },
            {
                "path": "/reset",
                "method": "POST", 
                "description": "Reset Notion Agent's memory and conversation history",
                "parameters": [],
                "response": {
                    "status": "string - success/error status",
                    "message": "string - confirmation message"
                }
            },
            {
                "path": "/tool-schemas",
                "method": "GET",
                "description": "Get available tool schemas for the Notion agent",
                "content_type": "multipart/form-data",
                "parameters": [
                    {
                        "name": "openai_api_key",
                        "type": "string", 
                        "required": True,
                        "description": "OpenAI API key for language model"
                    },
                    {
                        "name": "composio_key",
                        "type": "string",
                        "required": True,
                        "description": "Composio API key for Notion workspace integration"
                    }
                ],
                "response": {
                    "tool_schemas": "object - Available Notion tool schemas"
                }
            },
            {
                "path": "/health",
                "method": "GET",
                "description": "Check API health status and uptime", 
                "parameters": [],
                "response": {
                    "status": "string - health status",
                    "uptime": "number - seconds since startup",
                    "version": "string - API version",
                    "service": "string - service name"
                }
            },
            {
                "path": "/docs",
                "method": "GET",
                "description": "Get comprehensive API documentation in JSON format",
                "parameters": [],
                "response": "object - This documentation structure"
            },
            {
                "path": "/api-docs", 
                "method": "GET",
                "description": "Get comprehensive API documentation in markdown format",
                "parameters": [],
                "response": {
                    "markdown": "string - Full API documentation in markdown format"
                }
            }
        ],
        "notion_integration_features": [
            "Page Management - Create, update, delete, and search Notion pages",
            "Database Operations - Query and manipulate Notion databases",
            "Content Management - Add text, images, and other content blocks",
            "Workspace Navigation - Browse and organize Notion workspace"
        ],
        "usage_notes": [
            "All requests must use multipart/form-data encoding",
            "OpenAI API key and Composio key are required for full functionality", 
            "The chat endpoint processes text queries and executes Notion operations",
            "Tool schemas provide information about available Notion operations"
        ]
    }

@app.get("/", response_class=HTMLResponse)
async def root():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Notion AI Agent API</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
            h2 { color: #2c3e50; }
            h3 { color: #34495e; }
            code { background-color: #f4f4f4; padding: 2px 4px; border-radius: 3px; }
            ul { line-height: 1.6; }
            .feature-list { background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 10px 0; }
        </style>
    </head>
    <body>
        <h2>Notion AI Agent API</h2>
        
        <p>A comprehensive API for interacting with Notion AI Agent with Notion workspace integration.</p>
        
        <h3>Available Endpoints:</h3>
        
        <p><strong>GET Requests:</strong></p>
        <ul>
            <li><code>/health</code> - Check API health status and uptime</li>
            <li><code>/api-docs</code> - Get comprehensive API documentation</li>
            <li><code>/docs</code> - Get comprehensive API documentation in JSON format</li>
            <li><code>/tool-schemas</code> - Get available tool schemas for the Notion agent</li>
        </ul>
        
        <p><strong>POST Requests:</strong></p>
        <ul>
            <li><code>/chat</code> - Main chat endpoint with Notion workspace integration</li>
            <li><code>/reset</code> - Reset Notion Agent's memory and conversation history</li>
        </ul>
        
        <div class="feature-list">
            <h3>Notion Integration:</h3>
            <ul>
                <li><strong>Page Management:</strong> Create, update, delete, and search Notion pages</li>
                <li><strong>Database Operations:</strong> Query and manipulate Notion databases</li>
                <li><strong>Content Management:</strong> Add text, images, and other content blocks</li>
                <li><strong>Workspace Navigation:</strong> Browse and organize Notion workspace</li>
            </ul>
        </div>
        
        <h3>Additional Features:</h3>
        <ul>
            <li>Text-based chat interactions</li>
            <li>Notion workspace full integration</li>
            <li>OpenAI GPT integration</li>
            <li>Composio tools integration</li>
            <li>Memory management and conversation reset</li>
            <li>Health monitoring and uptime tracking</li>
        </ul>
        
        <h3>Required API Keys:</h3>
        <ul>
            <li><strong>OpenAI API Key:</strong> For GPT language model</li>
            <li><strong>Composio Key:</strong> For Notion workspace integration</li>
        </ul>
    </body>
    </html>
    """

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8003)






