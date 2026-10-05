"""Tools the agent can call.

PURPOSE: the agent's toolbox. The LLM reads each tool's name and docstring
to decide when to call it, so those docstrings are effectively part of the
prompt.

    search_documents  search the PDFs uploaded to this chat
    web_search        DuckDuckGo search for recent information
    get_stock_price   live share price from Alpha Vantage
    calculator        exact arithmetic (LLMs are unreliable at maths)

How a tool call works:
    1. The LLM replies with a "tool call" instead of text, e.g.
       {"name": "calculator", "args": {"first_num": 10, "second_num": 2, "operation": "div"}}
    2. LangGraph's ToolNode runs the matching Python function with those args
    3. The function's return value goes back to the LLM as a ToolMessage
    4. The LLM reads it and either answers or calls another tool
"""

from __future__ import annotations

import os

import requests
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from rag import store

# A ready-made LangChain tool, so we don't write it ourselves.
web_search = DuckDuckGoSearchRun(region="us-en")


# @tool turns a normal Python function into a tool the LLM can call. The
# LLM sees the function name, its parameters (from the type hints) and its
# docstring.
#
# response_format="content_and_artifact" means the function returns TWO
# things: (content, artifact).
#   content   text the LLM reads
#   artifact  extra data for our code only; the LLM never sees it
@tool(response_format="content_and_artifact")
def search_documents(query: str, config: RunnableConfig) -> tuple[str, list[dict]]:
    """Search the PDF documents uploaded to this chat (for example a company's
    annual report) and return the most relevant passages with page numbers."""
    # The thread id comes from the run config, set by the app, not from the
    # model. The model never sees it, so it cannot get it wrong or ask for
    # another chat's documents.
    #
    # How: a parameter typed `RunnableConfig` is special. LangChain hides it
    # from the LLM (the LLM only sees `query`) and fills it in automatically
    # with the config the app passed to chatbot.stream(...), which contains
    # {"configurable": {"thread_id": "..."}}.
    thread_id = config.get("configurable", {}).get("thread_id")
    if not thread_id:
        return "No chat is active, so there are no documents to search.", []

    docs = store.search(thread_id, query)
    if not docs:
        # This text goes to the LLM, which then tells the user to upload a PDF.
        return "No document has been uploaded in this chat. Ask the user to upload a PDF.", []

    # Structured list of the passages found, one dict per passage.
    sources = [
        {
            "source": doc.metadata.get("source"),  # filename
            "page": doc.metadata.get("page"),  # page number (1-based)
            "text": doc.page_content,  # the passage text
        }
        for doc in docs
    ]
    # The model reads `content`; the UI reads the `sources` artifact to show
    # citations without having to parse the model's answer.
    #
    # content looks like:
    #   [tcs.pdf, page 12]
    #   Revenue for FY24 was ...
    #
    #   [tcs.pdf, page 45]
    #   Net profit ...
    # The "[file, page N]" labels let the LLM cite pages in its answer.
    content = "\n\n".join(
        f"[{s['source']}, page {s['page']}]\n{s['text']}" for s in sources
    )
    return content, sources


@tool
def calculator(first_num: float, second_num: float, operation: str) -> dict:
    """
    Perform a basic arithmetic operation on two numbers.
    Supported operations: add, sub, mul, div
    """
    # Phase 2 upgrades this to handle full expressions like (26233/153670)*100.
    try:
        if operation == "add":
            result = first_num + second_num
        elif operation == "sub":
            result = first_num - second_num
        elif operation == "mul":
            result = first_num * second_num
        elif operation == "div":
            if second_num == 0:
                return {"error": "Division by zero is not allowed"}
            result = first_num / second_num
        else:
            return {"error": f"Unsupported operation '{operation}'"}

        # Return the inputs too, so the LLM can see exactly what was computed.
        return {
            "first_num": first_num,
            "second_num": second_num,
            "operation": operation,
            "result": result,
        }
    except Exception as e:
        # Errors are returned as data instead of raised, so the LLM can read
        # what went wrong and try again rather than the whole chat crashing.
        return {"error": str(e)}


@tool
def get_stock_price(symbol: str) -> dict:
    """
    Fetch latest stock price for a given symbol (e.g. 'AAPL', 'TSLA')
    using Alpha Vantage.
    """
    # The key is read from .env, never written in code (Phase 0 fix).
    api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
    if not api_key:
        return {"error": "ALPHA_VANTAGE_API_KEY is not set in .env"}

    url = "https://www.alphavantage.co/query"
    # Passing params separately lets requests build and URL-encode the query
    # string safely, instead of pasting values into the URL by hand.
    params = {"function": "GLOBAL_QUOTE", "symbol": symbol, "apikey": api_key}
    try:
        # timeout=10: give up after 10 seconds instead of hanging the chat
        # forever if Alpha Vantage doesn't respond.
        r = requests.get(url, params=params, timeout=10)
        return r.json()
    except requests.RequestException as e:
        # Network problems (no internet, timeout...) go back to the LLM as an
        # error message instead of crashing the app.
        return {"error": f"Stock price lookup failed: {e}"}


# The list of tools given to the agent (used in agent/graph.py).
TOOLS = [search_documents, web_search, get_stock_price, calculator]
