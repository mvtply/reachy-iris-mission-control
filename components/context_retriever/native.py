"""Context Retriever MCP connection placeholder.

The generated tool names and arguments come from the deployed service. A
separate surface ID is not needed for its MCP URL.
"""
from __future__ import annotations


class NativeContextRetriever:
    def __init__(self, endpoint: str, agent_key: str):
        if not all((endpoint, agent_key)):
            raise ValueError("IRIS_CONTEXT_RETRIEVER_URL and AGENT_KEY are required")
        self.endpoint, self.agent_key = endpoint, agent_key

    def retrieve(self, question: str):
        raise RuntimeError("Bind the verified generated MCP search tool and event cleanup before enabling native retrieval")
