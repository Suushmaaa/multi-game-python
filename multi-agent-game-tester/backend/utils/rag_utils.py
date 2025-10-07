from typing import List, Dict, Any, Optional
import json
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings

try:
    from langchain_openai import OpenAIEmbeddings
    from langchain_community.vectorstores import FAISS
    from langchain.docstore.document import Document
    RAG_AVAILABLE = True
except (ImportError, TypeError) as e:
    print(f"RAG dependencies not available: {e}")
    RAG_AVAILABLE = False
    OpenAIEmbeddings = None
    FAISS = None
    Document = None

class TestPatternRAG:
    """RAG system for retrieving relevant test patterns"""

    def __init__(self):
        self.vectorstore = None
        self.embeddings = None
        self.db_path = Path("test_patterns_db")
        self._initialized = False

        if RAG_AVAILABLE and settings.openai_api_key:
            try:
                self.embeddings = OpenAIEmbeddings(
                    openai_api_key=settings.openai_api_key,
                    model="text-embedding-ada-002"
                )
                self._load_or_create_vectorstore()
                self._initialized = True
            except Exception as e:
                print(f"Failed to initialize RAG: {e}")
        else:
            print("RAG not available - missing dependencies or API key")

    def _load_or_create_vectorstore(self):
        """Load existing vectorstore or create new one"""
        if self.db_path.exists():
            try:
                self.vectorstore = FAISS.load_local(str(self.db_path), self.embeddings)
            except Exception as e:
                print(f"Failed to load vectorstore: {e}")
                self.vectorstore = None
        else:
            # Create empty vectorstore
            self.vectorstore = FAISS.from_texts(["dummy"], self.embeddings)
            self.vectorstore.save_local(str(self.db_path))

    def add_test_patterns(self, test_patterns: List[Dict[str, Any]]):
        """Add test patterns to the vectorstore"""
        if not self._initialized or not test_patterns:
            return

        documents = []
        for pattern in test_patterns:
            # Create document from test pattern
            content = f"""
            Test Title: {pattern.get('title', '')}
            Description: {pattern.get('description', '')}
            Test Type: {pattern.get('test_type', '')}
            Priority: {pattern.get('priority', '')}
            Tags: {', '.join(pattern.get('tags', []))}
            Expected Outcome: {pattern.get('expected_outcome', '')}
            Quality Score: {pattern.get('quality_score', 0)}
            """

            metadata = {
                "test_id": pattern.get("test_id", ""),
                "quality_score": pattern.get("quality_score", 0),
                "test_type": pattern.get("test_type", ""),
                "priority": pattern.get("priority", "")
            }

            doc = Document(page_content=content.strip(), metadata=metadata)
            documents.append(doc)

        if documents:
            if self.vectorstore is None:
                self.vectorstore = FAISS.from_documents(documents, self.embeddings)
            else:
                self.vectorstore.add_documents(documents)

            # Save updated vectorstore
            self.vectorstore.save_local(str(self.db_path))

    def retrieve_relevant_patterns(self, query: str, k: int = 3) -> List[Dict[str, Any]]:
        """Retrieve relevant test patterns for a query"""
        if not self._initialized or self.vectorstore is None:
            return []

        try:
            docs = self.vectorstore.similarity_search(query, k=k)
            patterns = []
            for doc in docs:
                pattern = {
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "score": getattr(doc, 'score', 0)  # If available
                }
                patterns.append(pattern)
            return patterns
        except Exception as e:
            print(f"Failed to retrieve patterns: {e}")
            return []

    def get_stats(self) -> Dict[str, Any]:
        """Get RAG system statistics"""
        if not self._initialized:
            return {"status": "not_initialized"}

        return {
            "status": "active",
            "vectorstore_exists": self.vectorstore is not None,
            "db_path": str(self.db_path)
        }

# Global RAG instance
rag_system = TestPatternRAG()
