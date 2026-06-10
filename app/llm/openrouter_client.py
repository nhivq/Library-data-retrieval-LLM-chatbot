from app.llm.setup import llm

MODEL = "openai/gpt-4o-mini"


def call_llm(
        messages,
        tools=None
):
    return llm.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=tools
    )