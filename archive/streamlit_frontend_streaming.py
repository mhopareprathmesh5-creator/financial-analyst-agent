import streamlit as st
from langgraph_backend import chatbot
from langchain_core.messages import HumanMessage

# st.session_state is Streamlit's built-in dict-like object used to persist 
# data across reruns. Streamlit reruns the entire script top-to-bottom on every 
# interaction, so without session_state, variables like chat history would reset each time.

# CONFIG is passed to the LangGraph chatbot to identify which conversation "thread" 
# this is. LangGraph uses this to fetch/save the correct checkpointed state 
# (memory) for this specific chat session.
CONFIG = {'configurable': {'thread_id': 'thread-1'}}

# Initialize message_history in session_state the first time the app runs.
# This list stores the full chat as a sequence of {'role': ..., 'content': ...} dicts,
# so it survives Streamlit reruns and can be redrawn on screen every time.
if 'message_history' not in st.session_state:
    st.session_state['message_history'] = []

# Redraw the entire past conversation on every rerun (since Streamlit reruns 
# the whole script each time). Without this loop, old messages would disappear 
# from the UI as soon as the user sends a new one.
for message in st.session_state['message_history']:
    with st.chat_message(message['role']):
        st.text(message['content'])

# Example of what message_history entries look like:
#{'role': 'user', 'content': 'Hi'}
#{'role': 'assistant', 'content': 'Hi=ello'}

# Renders a chat input box at the bottom of the page. Returns None until the 
# user types something and hits enter, at which point it returns the typed text.
user_input = st.chat_input('Type here')

if user_input:
    # Save the user's message to history first, then display it immediately 
    # so it appears in the chat window right away.
    st.session_state['message_history'].append({'role': 'user', 'content': user_input})
    with st.chat_message('user'):
        st.text(user_input)

    with st.chat_message('assistant'):

        def stream_text_chunks():
            """
            Generator that wraps chatbot.stream() and yields only clean text.

            Why this is needed: chatbot.stream(..., stream_mode='messages') yields 
            (message_chunk, metadata) tuples. Depending on the model/provider, 
            message_chunk.content can be:
              1. A plain string, e.g. "Hello"
              2. A list of content blocks, e.g. [{'type': 'text', 'text': 'Hello', 'index': 0}]

            st.write_stream() expects plain string chunks. If we pass it raw dicts/lists,
            it prints their Python repr instead of clean text (which is the bug seen 
            in the screenshot). This function normalizes both formats into plain text.
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

    # Now that the assistant's full response is available, save it to history 
    # so it's included in the redraw loop at the top on the next rerun.
    st.session_state['message_history'].append({'role': 'assistant', 'content': ai_message})