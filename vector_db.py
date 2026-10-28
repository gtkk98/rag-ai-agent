# ============================================================
# 1. IMPORT REQUIRED QDRANT COMPONENTS
# ============================================================

# QdrantClient connects to and communicates with the Qdrant database.
from qdrant_client import QdrantClient

# Distance defines the similarity metric used to compare vectors.
# PointStruct represents a vector record, including its ID and metadata.
# VectorParams defines the vector size and similarity metric for a collection.
from qdrant_client.models import Distance, PointStruct, VectorParams


# ============================================================
# 2. DEFINE THE QDRANT STORAGE CLASS
# ============================================================

# This class manages vector storage and similarity searches.
# It provides methods to insert document chunks and retrieve relevant chunks.
class QdrantStorage:

    # --------------------------------------------------------
    # 2.1 INITIALIZE THE QDRANT CONNECTION
    # --------------------------------------------------------

    def __init__(self, url="http://localhost:6333", collection="docs", dim=3072):

        # Connect to the Qdrant server.
        # The timeout specifies the maximum time to wait for a request.
        self.client = QdrantClient(url=url, timeout=30)

        # Store the name of the Qdrant collection used by this application.
        # A collection is similar to a table in a relational database.
        self.collection = collection

        # Check whether the collection already exists.
        # Create it only if it does not exist.
        if not self.client.collection_exists(self.collection):

            # Create a collection to store document embedding vectors.
            self.client.create_collection(
                collection_name=self.collection,

                # Configure the vector size and similarity calculation.
                vectors_config=VectorParams(
                    size=dim,                 # Expected embedding dimensions.
                    distance=Distance.COSINE  # Compare vectors using cosine similarity.
                ),
            )

    # --------------------------------------------------------
    # 2.2 INSERT OR UPDATE DOCUMENT CHUNKS
    # --------------------------------------------------------

    # Store document vectors and their metadata in Qdrant.
    # Qdrant calls this operation "upsert":
    # insert a new point or replace an existing point with the same ID.
    def upsert(self, ids, vectors, payloads):

        # Build a list of Qdrant points.
        # Each point combines:
        # - A unique ID.
        # - An embedding vector.
        # - A payload containing the original text and source information.
        points = [
            PointStruct(
                id=ids[i],
                vector=vectors[i],
                payload=payloads[i]
            )
            for i in range(len(ids))
        ]

        # Upload all points to the configured collection.
        self.client.upsert(self.collection, points)

    # --------------------------------------------------------
    # 2.3 SEARCH FOR RELEVANT DOCUMENT CHUNKS
    # --------------------------------------------------------

    # Retrieve the text chunks most similar to the question's embedding.
    # top_k determines the maximum number of matching points to retrieve.
    def search(self, query_vector, top_k: int = 5):

        # Search the collection using the question's embedding vector.
        response = self.client.query_points(
            collection_name=self.collection,  # Collection to search.

            query=query_vector,                # Embedding of the user's question.

            with_payload=True,                 # Include stored text and source metadata.

            limit=top_k,                       # Maximum number of results.
        )

        # Lists used to collect the retrieved text and source identifiers.
        contexts = []
        sources = []

        # Process each matching point returned by Qdrant.
        for r in response.points:

            # Retrieve the point's metadata.
            # Use an empty dictionary if the payload is missing or None.
            payload = getattr(r, "payload", None) or {}

            # Extract the original document text from the payload.
            # Return an empty string if the text field is missing.
            text = payload.get("text", "")

            # Extract the document's source identifier.
            # Return an empty string if the source field is missing.
            source = payload.get("source", "")

            # Only include results that contain actual text.
            if text:
                contexts.append(text)
                sources.append(source)

        # Return the retrieved text chunks and their corresponding sources.
        # The calling workflow uses these values to construct the LLM prompt.
        return {
            "contexts": contexts,
            "sources": sources
        }