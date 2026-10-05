"""System prompt for the agent.

PURPOSE: the instructions sent to the LLM before every conversation, telling
it how to behave and when to use which tool. Kept in its own file so prompt
versions can be compared in evals. Phase 2 turns this into the financial
analyst prompt.
"""

# agent/graph.py puts this at the start of the message list on every LLM
# call, as a SystemMessage. It is not saved in the chat history, so changing
# this text affects old chats too.
#
# The "\" at the end of the first line joins it with the next line, so the
# long first sentence is one line for the LLM.
SYSTEM_PROMPT = """You are a helpful assistant that answers questions about the PDF documents \
the user uploads, and can also search the web, look up stock prices and do arithmetic.

- For any question about the uploaded documents, call `search_documents` first.
- When you use document passages, cite them inline as (filename, p. N).
- If no document has been uploaded and the question needs one, ask the user to upload a PDF.
- Use the calculator for arithmetic rather than computing in your head."""
