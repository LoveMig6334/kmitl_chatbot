"""Answer layer: retrieved chunks -> grounded, cited, streamed ThaiLLM answer.

Public pieces:
- ``rag.retriever``: ``Chunk``, ``Retriever`` protocol, ``FixtureRetriever``, ``get_retriever``
- ``rag.answerer``: ``RagAnswerer`` (implements ``api.answerer.Answerer``)
"""
