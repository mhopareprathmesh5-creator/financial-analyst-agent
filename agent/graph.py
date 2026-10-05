"""The LangGraph agent: an LLM node that can call tools, with SQLite-backed memory.

PURPOSE: the "brain". It wires the LLM, the system prompt and the tools into
a loop, and saves every conversation to SQLite so chats survive restarts:

    START -> chat_node (LLM decides) -> tool needed? -> tools -> chat_node -> ... -> answer

Also provides helpers for the sidebar: listing past chats and giving each one
a readable title.

Functions in this file:
    build_graph()    assemble the agent from an LLM and a checkpointer
    get_chatbot()    the real agent used by the app (Gemini + SQLite), created once
    thread_title()   short title for a chat, from its first question
    list_threads()   all saved chats for the sidebar
"""

from __future__ import annotations

import sqlite3
from functools import lru_cache
from typing import Annotated, TypedDict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode, tools_condition

import config
from agent.prompts import SYSTEM_PROMPT
from agent.tools import TOOLS


class ChatState(TypedDict):
    """The data passed between nodes: the full list of messages so far.

    Annotated[..., add_messages] tells LangGraph that when a node returns
    {"messages": [new_message]}, it should APPEND to the list rather than
    replace it.
    """

    messages: Annotated[list[BaseMessage], add_messages]


def build_graph(llm: BaseChatModel, checkpointer: BaseCheckpointSaver) -> CompiledStateGraph:
    """Assemble the agent graph.

    The LLM and checkpointer are passed in (rather than created here) so that
    evals and tests can build the same graph with a different model or an
    in-memory checkpointer.
    """
    # bind_tools sends the tools' names, parameters and docstrings to the LLM
    # with every request, so it knows which tools exist and can call them.
    llm_with_tools = llm.bind_tools(TOOLS)

    def chat_node(state: ChatState):
        """Node 1: send the system prompt + conversation to the LLM.

        The LLM's reply is either a text answer, or a tool call request
        ("please run search_documents with query=...").
        """
        messages = [SystemMessage(content=SYSTEM_PROMPT), *state["messages"]]
        return {"messages": [llm_with_tools.invoke(messages)]}

    graph = StateGraph(ChatState)
    graph.add_node("chat_node", chat_node)
    # Node 2: ToolNode runs whichever tools the LLM asked for and adds their
    # results to the messages as ToolMessages.
    graph.add_node("tools", ToolNode(TOOLS))

    graph.add_edge(START, "chat_node")  # every turn starts at the LLM
    # tools_condition looks at the LLM's last reply:
    #   asked for a tool -> go to "tools"
    #   gave a text answer -> go to END (the turn is finished)
    graph.add_conditional_edges("chat_node", tools_condition)
    # After running tools, go back to the LLM so it can read the results.
    # This loop is what lets the agent use several tools in a row
    # (e.g. search the PDF, then the calculator).
    graph.add_edge("tools", "chat_node")

    # The checkpointer saves the state after every step, keyed by thread_id.
    return graph.compile(checkpointer=checkpointer)


@lru_cache(maxsize=1)
def get_chatbot() -> CompiledStateGraph:
    """The app's agent, created once and reused across Streamlit reruns.

    Streamlit reruns the whole script on every click; @lru_cache makes sure
    we don't open a new database connection and LLM client each time.
    """
    from langchain_google_genai import ChatGoogleGenerativeAI

    llm = ChatGoogleGenerativeAI(model=config.CHAT_MODEL)
    # check_same_thread=False: Streamlit may use different threads across
    # reruns, and SQLite would otherwise refuse a connection made in another thread.
    conn = sqlite3.connect(database=str(config.DB_PATH), check_same_thread=False)
    return build_graph(llm, SqliteSaver(conn=conn))


def thread_title(messages: list[BaseMessage], max_len: int = 40) -> str:
    """Short sidebar label for a chat, taken from its first user message.

    Example: "What was Infosys revenue in FY24?" instead of a UUID.
    Long questions are cut to max_len characters and end with "…".
    """
    for message in messages:
        if isinstance(message, HumanMessage):
            text = message.content if isinstance(message.content, str) else ""
            # split() + join() collapses newlines and repeated spaces into
            # single spaces, so the title stays on one line.
            text = " ".join(text.split())
            if text:
                return text if len(text) <= max_len else text[: max_len - 1] + "…"
    return "New chat"


def list_threads(chatbot: CompiledStateGraph) -> list[dict]:
    """All saved chats, most recently active first, with a readable title.

    Returns e.g. [{"thread_id": "3f2a...", "title": "What was TCS revenue?"}, ...]
    """
    thread_ids: list[str] = []
    # checkpointer.list(None) returns every saved checkpoint of every chat.
    # Checkpoint ids are time-ordered and listed newest first, so the first
    # time we see a thread is its most recent activity.
    for checkpoint in chatbot.checkpointer.list(None):
        thread_id = checkpoint.config["configurable"]["thread_id"]
        if thread_id not in thread_ids:
            thread_ids.append(thread_id)

    threads = []
    for thread_id in thread_ids:
        # get_state loads the latest saved messages of that chat, so we can
        # build its title from the first question.
        state = chatbot.get_state({"configurable": {"thread_id": thread_id}})
        messages = state.values.get("messages", [])
        threads.append({"thread_id": thread_id, "title": thread_title(messages)})
    return threads
