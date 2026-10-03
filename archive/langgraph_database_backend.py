from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph.message import add_messages
from dotenv import load_dotenv
import sqlite3

# Load environment variables (e.g. GOOGLE_API_KEY) from a .env file 
# so the LLM client can authenticate without hardcoding secrets.
load_dotenv()

# Initialize the Gemini chat model that will generate responses.
llm = ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite-preview")

# Define the shape of the graph's state. LangGraph passes this dict-like 
# object between nodes. 'messages' holds the full conversation so far.
class ChatState(TypedDict):
    # Annotated[..., add_messages] tells LangGraph to use the add_messages 
    # reducer, which APPENDS new messages to the existing list instead of 
    # overwriting it, every time a node returns a 'messages' update.
    messages: Annotated[list[BaseMessage], add_messages]

# The single node in this graph: takes the current state, sends the full 
# message history to the LLM, and returns the LLM's reply as a new message.
def chat_node(state: ChatState):
    messages = state['messages']          # pull conversation history from state
    response = llm.invoke(messages)       # send it to Gemini and get a reply
    return {"messages": [response]}       # this gets merged into state via add_messages

# Open (or create) a local SQLite database file to persist conversation state.
# check_same_thread=False allows this connection to be used across threads, 
# which Streamlit needs since it doesn't guarantee the same thread per request.
conn = sqlite3.connect(database='chatbot.db', check_same_thread=False)

# Checkpointer: saves/restores graph state (message history) to/from SQLite, 
# keyed by thread_id. This is what makes conversations persist across reruns 
# and even across app restarts, since it's backed by a file rather than memory.
checkpointer = SqliteSaver(conn=conn)

# Build the graph: one node, wired straight from START to chat_node to END.
graph = StateGraph(ChatState)
graph.add_node("chat_node", chat_node)      # register the node
graph.add_edge(START, "chat_node")          # entry point -> chat_node
graph.add_edge("chat_node", END)            # chat_node -> exit

# Compile the graph into a runnable chatbot, wiring in the checkpointer so 
# state is automatically loaded/saved per thread_id on every invoke/stream call.
chatbot = graph.compile(checkpointer=checkpointer)

def retrieve_all_threads():
    all_threads = set()
    for checkpoint in checkpointer.list(None):
        all_threads.add(checkpoint.config['configurable']['thread_id'])

    return list(all_threads)