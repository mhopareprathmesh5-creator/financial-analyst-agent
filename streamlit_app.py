"""Streamlit UI. Run with:  streamlit run streamlit_app.py

PURPOSE: the screen the user sees. The sidebar handles new chats, PDF upload
and past chats; the main area shows the conversation and streams answers.
It contains no agent logic itself: it calls agent/graph.py to answer,
rag/store.py to index PDFs and app/history.py to format messages.

Remember: Streamlit reruns this whole file top to bottom on every click or
message. Anything that must survive a rerun is kept in st.session_state.
"""

import uuid

import streamlit as st
from langchain_core.messages import AIMessageChunk, HumanMessage, ToolMessage

from agent.graph import get_chatbot, list_threads
from app.history import escape_markdown_dollars, extract_text, to_display_turns
from rag import store

# Browser tab title and icon. Must be the first Streamlit command.
st.set_page_config(page_title="Financial Analyst Agent", page_icon="📊")

# The agent. get_chatbot() is cached, so this is the same object on every rerun.
chatbot = get_chatbot()


# ======================= Helper functions =======================
def new_chat():
    """Start a fresh chat by giving it a new random id. Nothing is saved
    until the first message is sent."""
    st.session_state["thread_id"] = str(uuid.uuid4())


def open_chat(thread_id: str):
    """Switch to a past chat. Its messages are loaded from the database
    further down the script."""
    st.session_state["thread_id"] = thread_id


def render_sources(sources: list[dict]):
    """Show a collapsible "Sources" box under an answer, with the file, page
    and a short preview of each passage the answer was based on."""
    with st.expander(f"Sources ({len(sources)})"):
        for source in sources:
            st.markdown(f"**{source['source']}, page {source['page']}**")
            # Collapse whitespace and cut to 300 characters for a tidy preview.
            snippet = " ".join(source["text"].split())
            st.caption(escape_markdown_dollars(snippet[:300] + ("…" if len(snippet) > 300 else "")))


# ======================= Current chat =======================
# On the very first run there is no chat yet, so create one.
if "thread_id" not in st.session_state:
    new_chat()

thread_id = st.session_state["thread_id"]

# Passed to every agent call:
#   configurable.thread_id  tells the checkpointer which chat to load/save,
#                           and is what search_documents reads to know whose PDFs to search
#   metadata / run_name     labels for LangSmith traces, to find runs easily
run_config = {
    "configurable": {"thread_id": thread_id},
    "metadata": {"thread_id": thread_id},
    "run_name": "chat_turn",
}

# ============================ Sidebar ============================
with st.sidebar:
    st.title("📊 Financial Analyst")
    # on_click runs new_chat() BEFORE the rerun, so the page redraws with the
    # new chat straight away.
    st.button("➕ New chat", on_click=new_chat, use_container_width=True)

    st.subheader("Documents in this chat")
    # Keying the uploader by thread gives every chat its own empty uploader,
    # so a file from one chat is never silently indexed into the next.
    uploaded_pdf = st.file_uploader("Upload a PDF", type=["pdf"], key=f"uploader-{thread_id}")
    if uploaded_pdf is not None:
        # This block runs on every rerun while a file sits in the uploader.
        # That's fine: ingest_pdf recognises a file it already indexed by its
        # fingerprint and returns immediately.
        try:
            with st.spinner(f"Indexing {uploaded_pdf.name}…"):
                summary = store.ingest_pdf(uploaded_pdf.getvalue(), thread_id, uploaded_pdf.name)
            if not summary["already_indexed"]:
                st.success(f"Indexed {summary['filename']} ({summary['chunks']} chunks)")
        except ValueError as e:
            # e.g. empty file, or a scanned PDF with no text.
            st.error(str(e))

    # The document list comes from disk (documents.json), not session state,
    # so it is still correct after an app restart.
    documents = store.list_documents(thread_id)
    if documents:
        for doc in documents:
            st.markdown(f"- **{doc['filename']}** · {doc['pages']} pages, {doc['chunks']} chunks")
    else:
        st.caption("No PDF uploaded yet.")

    st.subheader("Past chats")
    threads = list_threads(chatbot)
    if not threads:
        st.caption("No past chats yet.")
    for thread in threads:
        st.button(
            thread["title"],
            # Every Streamlit widget needs a unique key; the thread id is unique.
            key=f"thread-{thread['thread_id']}",
            on_click=open_chat,
            args=(thread["thread_id"],),
            use_container_width=True,
            # Highlight the chat that's currently open.
            type="primary" if thread["thread_id"] == thread_id else "secondary",
        )

# ============================ Chat ============================
st.title("Financial Analyst Agent")

# The saved graph state is the single source of truth for the conversation,
# so reopening a chat (even after a restart) shows exactly what happened.
# (The old app kept a second copy in session_state, which could get out of sync.)
messages = chatbot.get_state(run_config).values.get("messages", [])
for turn in to_display_turns(messages):
    with st.chat_message(turn["role"]):
        st.markdown(escape_markdown_dollars(turn["content"]))
        if turn["sources"]:
            render_sources(turn["sources"])

# The chat box at the bottom. Returns the typed text once, when Enter is pressed.
user_input = st.chat_input("Ask about your document")
if user_input:
    # Show the question immediately, before the agent starts working.
    with st.chat_message("user"):
        st.markdown(escape_markdown_dollars(user_input))

    with st.chat_message("assistant"):
        # A dict, so the inner function below can update it.
        status = {"box": None}

        def stream_answer():
            """Run the agent and yield the answer text piece by piece, so it
            appears word by word on screen.

            stream_mode="messages" makes chatbot.stream() yield every message
            piece as it's produced: (chunk, metadata) pairs.
            """
            for chunk, metadata in chatbot.stream(
                {"messages": [HumanMessage(content=user_input)]},
                config=run_config,
                stream_mode="messages",
            ):
                if isinstance(chunk, ToolMessage):
                    # A tool just finished: show which one, e.g. "🔧 Used `calculator`".
                    label = f"🔧 Used `{chunk.name}`"
                    if status["box"] is None:
                        status["box"] = st.status(label, state="complete")
                    else:
                        status["box"].update(label=label)
                elif isinstance(chunk, AIMessageChunk) and metadata.get("langgraph_node") == "chat_node":
                    # A piece of the LLM's answer. Tool-call-only pieces have
                    # no text, so they're skipped by the `if text` check.
                    text = extract_text(chunk.content)
                    if text:
                        yield escape_markdown_dollars(text)

        try:
            # st.write_stream displays each yielded piece as it arrives.
            st.write_stream(stream_answer())
        except Exception as e:
            # e.g. no internet, invalid API key, or Gemini quota exceeded.
            st.error(f"Something went wrong: {e}")
            st.stop()

    # Redraw from saved state so the new answer shows its sources and the
    # chat appears in the sidebar.
    st.rerun()
