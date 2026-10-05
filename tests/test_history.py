"""Tests for app/history.py and chat titles.

PURPOSE: prove the chat display fixes: tool outputs and empty bubbles are
hidden, sources attach to the answer that used them, chats get readable
titles, and dollar signs don't turn into LaTeX.

Run with:  python -m pytest tests/test_history.py -v
"""

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from agent.graph import thread_title
from app.history import escape_markdown_dollars, extract_text, to_display_turns

# One document passage, as search_documents returns it in its artifact.
SOURCE = {"source": "report.pdf", "page": 12, "text": "Revenue was 100 crore."}


def tool_call_turn():
    """The messages the database stores for one question that used a tool:
    question -> AI asks for a tool -> tool result -> AI answer."""
    return [
        HumanMessage(content="What was revenue?"),
        # The AI's tool request: no text, just a tool call.
        AIMessage(
            content="",
            tool_calls=[{"name": "search_documents", "args": {"query": "revenue"}, "id": "c1"}],
        ),
        # The tool's result, with the passage in its artifact.
        ToolMessage(content="[report.pdf, page 12] ...", tool_call_id="c1", artifact=[SOURCE]),
        # The final answer, in Gemini's list-of-blocks format.
        AIMessage(content=[{"type": "text", "text": "Revenue was 100 crore (report.pdf, p. 12)."}]),
    ]


def test_tool_messages_and_empty_bubbles_are_hidden():
    """Bug fixed: reopening a chat used to show raw tool output and empty
    bubbles. Only the question and the final answer should appear."""
    turns = to_display_turns(tool_call_turn())

    assert [t["role"] for t in turns] == ["user", "assistant"]
    assert turns[1]["content"] == "Revenue was 100 crore (report.pdf, p. 12)."


def test_sources_attach_to_the_answer_that_used_them():
    """The passage belongs to the revenue answer only, not to a later answer
    that didn't search anything."""
    messages = tool_call_turn() + [HumanMessage(content="Thanks"), AIMessage(content="You're welcome!")]

    turns = to_display_turns(messages)

    assert turns[1]["sources"] == [SOURCE]  # revenue answer has the source
    assert turns[3]["sources"] == []  # "You're welcome!" has none


def test_duplicate_sources_are_shown_once():
    """If two searches return the same passage, the Sources box lists it once."""
    messages = tool_call_turn()
    # Insert a second tool result with the same passage, before the answer.
    messages.insert(3, ToolMessage(content="...", tool_call_id="c2", artifact=[SOURCE]))

    assert to_display_turns(messages)[1]["sources"] == [SOURCE]


def test_extract_text_handles_both_content_shapes():
    """Plain strings and Gemini's list-of-blocks both become plain text;
    non-text blocks (like images) are ignored."""
    assert extract_text("hi") == "hi"
    assert extract_text([{"type": "text", "text": "hi"}, {"type": "image"}]) == "hi"


def test_thread_title():
    """Bug fixed: the sidebar used to show UUIDs. Titles now come from the
    first question, shortened to 40 characters."""
    assert thread_title([HumanMessage(content="What was Infosys revenue in FY24?")]) == (
        "What was Infosys revenue in FY24?"
    )
    assert thread_title([HumanMessage(content="x" * 100)]).endswith("…")
    assert len(thread_title([HumanMessage(content="x" * 100)])) == 40
    assert thread_title([]) == "New chat"


def test_dollar_signs_are_escaped():
    """"$5B to $7B" must not be rendered as a maths formula by Streamlit."""
    assert escape_markdown_dollars("$5B to $7B") == "\\$5B to \\$7B"
