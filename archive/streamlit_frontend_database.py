import streamlit as st
from langgraph_database_backend import chatbot, retrieve_all_threads
from langchain_core.messages import HumanMessage
import uuid

# **************************************** utility functions *************************

def generate_thread_id():
    # Each conversation ("thread") needs a unique id so LangGraph's checkpointer
    # can store/retrieve its own separate message history in the database.
    thread_id = uuid.uuid4()
    return thread_id

def reset_chat():
    # Called when the user clicks "New Chat". Swaps in a brand-new thread_id
    # and clears the on-screen history so the UI starts a fresh conversation,
    # while the old thread's messages remain saved in the DB under its old id.
    thread_id = generate_thread_id()
    st.session_state['thread_id'] = thread_id
    add_thread(st.session_state['thread_id'])
    st.session_state['message_history'] = []

def add_thread(thread_id):
    # Keeps the sidebar's thread list (chat_threads) in sync. Only appends if
    # this thread_id isn't already tracked, so we don't get duplicate sidebar buttons.
    if thread_id not in st.session_state['chat_threads']:
        st.session_state['chat_threads'].append(thread_id)

def load_conversation(thread_id):
    # Pulls the full saved message list for a given thread out of the
    # checkpointer/database (this is what makes past conversations persist
    # across app restarts, unlike the in-memory-only version of this app).
    state = chatbot.get_state(config={'configurable': {'thread_id': thread_id}})
    # Check if messages key exists in state values, return empty list if not
    return state.values.get('messages', [])

def extract_text(content):
    # LangChain message .content isn't always a plain string. Depending on the
    # model/provider it can be:
    #   1. A plain string, e.g. "Hello"
    #   2. A list of content blocks, e.g. [{'type': 'text', 'text': 'Hello', 'index': 0}]
    # Streamlit's st.text()/st.write_stream() expect plain strings — if you hand
    # them the raw list, they render it as ugly JSON/dict output instead of text.
    # This normalizes both shapes down to a clean string so the UI stays readable,
    # whether the message came from a live stream or was reloaded from the DB.
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return ''.join(
            block.get('text', '')
            for block in content
            if isinstance(block, dict) and block.get('type') == 'text'
        )
    return str(content)


# **************************************** Session Setup ******************************

# st.session_state persists data across Streamlit reruns (Streamlit reruns the
# whole script top-to-bottom on every interaction), so these should only be
# initialized once per browser session, hence the "if not in session_state" guards.

# Holds the messages shown in the CURRENTLY OPEN conversation, as a list of
# {'role': ..., 'content': ...} dicts, so the chat redraws correctly on every rerun.
if 'message_history' not in st.session_state:
    st.session_state['message_history'] = []

# Which conversation ("thread") is currently active. All chatbot calls are tagged
# with this id so LangGraph knows which saved history to read from / write to.
if 'thread_id' not in st.session_state:
    st.session_state['thread_id'] = generate_thread_id()

# The list of all past thread ids, shown as buttons in the sidebar. Loaded once
# from the database on first run so old conversations survive an app restart.
if 'chat_threads' not in st.session_state:
    st.session_state['chat_threads'] = retrieve_all_threads()

# Make sure the current thread always shows up in the sidebar, even brand-new ones.
add_thread(st.session_state['thread_id'])


# **************************************** Sidebar UI *********************************

st.sidebar.title('LangGraph Chatbot')

if st.sidebar.button('New Chat'):
    reset_chat()

st.sidebar.header('My Conversations')

# [::-1] reverses the list so the most recently created thread appears at the top.
for thread_id in st.session_state['chat_threads'][::-1]:
    if st.sidebar.button(str(thread_id)):
        # User clicked a past conversation: switch the active thread and pull its
        # saved messages back out of the DB so they can be redrawn on screen.
        st.session_state['thread_id'] = thread_id
        messages = load_conversation(thread_id)

        temp_messages = []

        for msg in messages:
            # LangChain uses different message classes per role; HumanMessage means
            # the user sent it, anything else here (AIMessage) is the assistant's reply.
            if isinstance(msg, HumanMessage):
                role='user'
            else:
                role='assistant'
            # extract_text() normalizes msg.content in case it's Gemini's block-list
            # format rather than a plain string (see extract_text docstring above).
            temp_messages.append({'role': role, 'content': extract_text(msg.content)})

        st.session_state['message_history'] = temp_messages


# **************************************** Main UI ************************************

# Redraw the entire current conversation on every rerun (Streamlit reruns the whole
# script each time), otherwise old messages would vanish as soon as a new one is sent.
for message in st.session_state['message_history']:
    with st.chat_message(message['role']):
        st.text(message['content'])

# Renders the chat input box at the bottom of the page. Returns None until the
# user types something and hits enter, at which point it returns the typed text.
user_input = st.chat_input('Type here')

if user_input:

    # Save the user's message to history first, then display it immediately so
    # it appears in the chat window right away (before waiting on the model).
    st.session_state['message_history'].append({'role': 'user', 'content': user_input})
    with st.chat_message('user'):
        st.text(user_input)

    #CONFIG = {'configurable': {'thread_id': st.session_state['thread_id']}}

    # thread_id under "configurable" is what LangGraph's checkpointer uses to know
    # which conversation's state to load/save. The extra "metadata"/"run_name" keys
    # aren't required by LangGraph itself — they just get attached to LangSmith traces
    # (if tracing is enabled) so runs are easier to identify/filter by thread there.
    CONFIG = {
        "configurable": {"thread_id": st.session_state["thread_id"]},
        "metadata": {
            "thread_id": st.session_state["thread_id"]
        },
        "run_name": "chat_turn",
    }

    # first add the message to message_history
    with st.chat_message('assistant'):

        def stream_text_chunks():
            """
            Generator that wraps chatbot.stream() and yields only clean text.

            chatbot.stream(..., stream_mode='messages') yields (message_chunk, metadata)
            tuples token-by-token. message_chunk.content can be a plain string or a
            list of blocks (see extract_text() above for why). st.write_stream()
            expects plain string chunks, so this normalizes each chunk before
            yielding it — otherwise the UI shows raw JSON instead of the reply text.
            """
            for message_chunk, metadata in chatbot.stream(
                {'messages': [HumanMessage(content=user_input)]},  # send user's message to the graph
                config=CONFIG,                                      # thread_id so LangGraph tracks this session's memory
                stream_mode='messages'                               # stream token-by-token message chunks
            ):
                content = message_chunk.content  # extract the content payload from this chunk

                if isinstance(content, str):
                    # Case 1: content is already a plain string chunk (e.g. "Hel", "lo!")
                    if content:  # skip empty strings so we don't yield blank pieces
                        yield content

                elif isinstance(content, list):
                    # Case 2: content is a list of structured blocks like
                    # [{'type': 'text', 'text': 'Hello!', 'index': 0}]
                    for block in content:
                        if isinstance(block, dict) and block.get('type') == 'text':
                            text = block.get('text', '')
                            if text:  # only yield non-empty text pieces
                                yield text

        # st.write_stream consumes the generator above, renders each text piece
        # live in the UI as it streams in, and returns the full concatenated
        # string once streaming finishes.
        ai_message = st.write_stream(stream_text_chunks())

    # Now that the assistant's full response is available, save it to history so
    # it's included in the redraw loop above on the next rerun. Note: LangGraph's
    # checkpointer already persisted this turn to the DB via chatbot.stream() above —
    # this line only updates what's shown in THIS session's UI right now.
    st.session_state['message_history'].append({'role': 'assistant', 'content': ai_message})
