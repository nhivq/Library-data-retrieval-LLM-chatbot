import os

# python-dotenv reads key/value pairs from a local .env file.
from dotenv import load_dotenv

# The openai package can also talk to OpenRouter because OpenRouter exposes
# an OpenAI-compatible API.
from openai import OpenAI

# fastmcp provides the client used to discover and call MCP tools.
from fastmcp import Client

from app.mcp_integration.server import mcp


# Load values from .env before reading OPENROUTER_API_KEY.
load_dotenv()

# This key is used to authenticate requests sent to OpenRouter.
api_key = os.getenv("OPENROUTER_API_KEY")

# OpenRouter is OpenAI-compatible, so the OpenAI client can be reused here.
llm = OpenAI(
    api_key=api_key,
    base_url="https://openrouter.ai/api/v1"
)

# `mcp` is the FastMCP server object defined in server.py.
# This client talks to that server and lets Python code call its tools.
client = Client(mcp)
