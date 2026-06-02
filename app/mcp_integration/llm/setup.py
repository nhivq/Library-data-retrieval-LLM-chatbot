import os

from dotenv import load_dotenv
from openai import OpenAI
from fastmcp import Client

from app.mcp_integration.server import mcp


load_dotenv()

api_key = os.getenv("OPENROUTER_API_KEY")

llm = OpenAI(
    api_key=api_key,
    base_url="https://openrouter.ai/api/v1"
)

client = Client(mcp)
