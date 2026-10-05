"""Turns the agent's saved messages into what the chat window shows.

PURPOSE: the database stores everything, including the LLM's internal tool
requests and raw tool outputs. This file picks out only what a person should
see (questions and answers) and attaches the document passages each answer
was based on, so the UI can show them as sources.

Kept free of Streamlit so it can be unit tested.

Functions in this file:
    extract_text()             message content -> plain text
    unique_sources()           remove duplicate passages
    to_display_turns()         saved messages -> chat bubbles with sources
    escape_markdown_dollars()  stop "$" turning into maths formatting
"""

from __future__ import annotations

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage


def extract_text(content) -> str:
    """Message content can be a plain string or a list of content blocks like
    [{'type': 'text', 'text': 'Hello'}], depending on the provider. Normalise
    both to plain text.

    Gemini often returns the list form. Showing it directly would print the
    raw dicts instead of the answer.
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        # Keep only the text blocks and join their text together.
        return "".join(
            block.get("text", "")
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        )
    return str(content)


def unique_sources(sources: list[dict]) -> list[dict]:
    """Drop repeated passages (same file, page and text), keeping first-seen order.

    Happens when the agent searches twice and gets some of the same passages back.
    """
    seen = set()  # passages already added, as (file, page, text) tuples
    result = []
    for source in sources:
        key = (source.get("source"), source.get("page"), source.get("text"))
        if key not in seen:
            seen.add(key)
            result.append(source)
    return result


def to_display_turns(messages: list[BaseMessage]) -> list[dict]:
    """User messages and the assistant's text replies, each reply carrying the
    document passages retrieved for it.

    Hidden: tool outputs, and AI messages that only request a tool call (they
    have no text and used to show up as empty bubbles).

    Example. Saved messages for one question:
        HumanMessage  "What was revenue?"
        AIMessage     ""  (tool call: search_documents)     <- hidden
        ToolMessage   "[tcs.pdf, page 12] ..."              <- hidden, but its
                                                               sources are kept
        AIMessage     "Revenue was ₹2,40,893 crore (p. 12)"

    becomes two bubbles:
        {"role": "user",      "content": "What was revenue?",  "sources": []}
        {"role": "assistant", "content": "Revenue was ...",    "sources": [page 12 passage]}
    """
    turns: list[dict] = []
    # Passages collected from tool results since the last answer. They get
    # attached to the next assistant answer, which is the one that used them.
    pending_sources: list[dict] = []

    for message in messages:
        if isinstance(message, HumanMessage):
            # A new question: show it, and start collecting sources afresh.
            turns.append({"role": "user", "content": extract_text(message.content), "sources": []})
            pending_sources = []
        elif isinstance(message, ToolMessage):
            # Don't show tool output, but keep its sources. Only
            # search_documents returns a list artifact; other tools return
            # None here and are skipped.
            if isinstance(message.artifact, list):
                pending_sources.extend(message.artifact)
        elif isinstance(message, AIMessage):
            text = extract_text(message.content)
            # AI messages that only call a tool have no text, so skip them
            # (these were the empty bubbles in the old app).
            if text.strip():
                turns.append(
                    {"role": "assistant", "content": text, "sources": unique_sources(pending_sources)}
                )
                pending_sources = []

    return turns


def escape_markdown_dollars(text: str) -> str:
    """Streamlit renders $...$ as LaTeX, which garbles answers like
    "revenue rose from $5B to $7B". Escape dollar signs so they show as-is.

    "\\$" in Markdown means "a literal dollar sign, not maths".
    """
    return text.replace("$", "\\$")
