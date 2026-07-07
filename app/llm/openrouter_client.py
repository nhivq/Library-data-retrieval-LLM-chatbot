from app.llm.setup import llm

MODEL = "openai/gpt-4o-mini"


def call_llm(
        messages,
        tools=None,
        stream=False
):
    """Call OpenRouter through the OpenAI-compatible client."""

    response = llm.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=tools,
        stream=stream
    )
    
    return response
