import os

# python-dotenv reads key/value pairs from a local .env file.
from dotenv import load_dotenv
from openai import OpenAI
from fastmcp import Client
from app.mcp_integration.server import mcp


load_dotenv()

api_key = os.getenv("OPENROUTER_API_KEY")

# OpenRouter is OpenAI-compatible, so the OpenAI client can be reused here.
llm = OpenAI(
    api_key=api_key,
    base_url="https://openrouter.ai/api/v1"
)

# This client talks to the in-process FastMCP server and lets Python code call
# the same tools the LLM sees.
client = Client(mcp)
