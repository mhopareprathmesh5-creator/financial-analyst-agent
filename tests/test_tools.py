"""Tests for agent/tools.py.

PURPOSE: prove the security fix: the LLM cannot see or choose the chat id,
the search tool gets it from the app's config, and a search only ever
returns documents from the current chat.

Run with:  python -m pytest tests/test_tools.py -v
"""

import pytest
from langchain_core.messages import AIMessage
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode

from agent.tools import search_documents
from rag import store

# Temporary index folder + fake embeddings + fake PDFs, for every test here.
pytestmark = pytest.mark.usefixtures("index_dir", "fake_pdf")


def test_model_cannot_see_or_set_thread_id():
    """Bug fixed: the old rag_tool had a thread_id parameter the LLM filled
    in itself, so it could get it wrong or be tricked into using another
    chat's id.

    tool_call_schema is exactly what the LLM is shown. It must contain only
    `query`; the hidden `config` parameter (which carries the thread id) must
    not appear.
    """
    # Only `query` is exposed to the LLM; the thread id is injected by code.
    assert set(search_documents.tool_call_schema.model_json_schema()["properties"]) == {"query"}


def run_search(thread_id: str, query: str = "revenue"):
    """Run the tool the way the app does: an AI tool call through a ToolNode
    inside a graph.

    We build a fake AI message that requests search_documents, send it
    through a one-node graph with a config holding the thread id (like the
    app does), and return the resulting ToolMessage.

    Why a graph: ToolNode relies on setup that only a running graph provides,
    so calling ToolNode on its own fails. A one-node graph matches how the
    real agent in agent/graph.py runs it.
    """
    graph = StateGraph(MessagesState)
    graph.add_node("tools", ToolNode([search_documents]))
    graph.add_edge(START, "tools")

    call = {"name": "search_documents", "args": {"query": query}, "id": "call-1", "type": "tool_call"}
    result = graph.compile().invoke(
        {"messages": [AIMessage(content="", tool_calls=[call])]},
        config={"configurable": {"thread_id": thread_id}},
    )
    # The last message is the tool's result (the first is our fake AI call).
    return result["messages"][-1]


def test_search_uses_thread_from_config():
    """The tool finds the PDF of the chat named in the config, and returns
    both the text for the LLM (content) and the sources for the UI (artifact)."""
    store.ingest_pdf(b"Revenue was 100 crore.", "thread-a", "report.pdf")

    message = run_search("thread-a")

    assert "[report.pdf, page 1]" in message.content  # what the LLM reads
    assert message.artifact[0]["source"] == "report.pdf"  # what the UI shows
    assert message.artifact[0]["page"] == 1


def test_search_in_chat_without_documents():
    """Searching from a chat with no PDF must not leak another chat's PDF;
    it tells the LLM to ask for an upload instead."""
    store.ingest_pdf(b"Revenue was 100 crore.", "thread-a", "report.pdf")

    message = run_search("thread-b")

    assert "No document has been uploaded" in message.content
    assert message.artifact == []
