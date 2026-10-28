# ============================================================
# 1. IMPORT REQUIRED LIBRARIES AND MODULES
# ============================================================

import logging  # Provides logging functionality for monitoring application events.
import os  # Allows access to environment variables, such as API keys.
import uuid  # Generates unique and deterministic IDs for document chunks.

from dotenv import load_dotenv  # Loads environment variables from a .env file.
from fastapi import FastAPI  # Creates the FastAPI web application.

import inngest  # Provides Inngest workflow and event-handling functionality.
import inngest.fast_api  # Integrates Inngest functions with FastAPI.
from inngest.experimental import ai  # Provides AI inference functionality through Inngest.

# Import custom functions for loading PDFs, splitting text, and generating embeddings.
from data_loader import load_and_chunk_pdf, embed_texts

# Import the custom Qdrant storage class for managing vector data.
from vector_db import QdrantStorage

# Import custom data models for validating workflow inputs and outputs.
from custom_types import RAGChunkAndSrc, RAGSearchResult, RAGUpsertResult


# ============================================================
# 2. LOAD ENVIRONMENT VARIABLES
# ============================================================

# Read environment variables from the .env file.
# For example, OPENAI_API_KEY can be stored in this file.
load_dotenv()


# ============================================================
# 3. INITIALIZE THE INNGEST CLIENT
# ============================================================

# Create an Inngest client to register and execute background workflows.
inngest_client = inngest.Inngest(
    app_id="rag_app",  # Unique identifier for this application in Inngest.

    # Use Uvicorn's logger so workflow messages appear in application logs.
    logger=logging.getLogger("uvicorn"),

    # Disable production mode for local development.
    is_production=False,

    # Use Pydantic to serialize and deserialize workflow data.
    serializer=inngest.PydanticSerializer()
)


# ============================================================
# 4. PDF INGESTION WORKFLOW
# ============================================================

# Register a workflow that runs when an event named
# "rag/ingest_pdf" is received.
#
# Its responsibility is to:
# 1. Load a PDF.
# 2. Extract and split its text into chunks.
# 3. Generate embeddings for the chunks.
# 4. Store the vectors and their associated text in Qdrant.

@inngest_client.create_function(
    fn_id="RAG: Ingest PDF",  # Human-readable workflow identifier.

    # Defines the event that triggers this workflow.
    trigger=inngest.TriggerEvent(event="rag/ingest_pdf")
)
async def rag_ingest_pdf(ctx: inngest.Context):

    # --------------------------------------------------------
    # 4.1 LOAD AND SPLIT THE PDF INTO CHUNKS
    # --------------------------------------------------------

    # This synchronous helper reads the PDF path from the event,
    # extracts its text, and splits the text into smaller chunks.
    def _load() -> RAGChunkAndSrc:

        # Get the PDF file path from the incoming event data.
        pdf_path = ctx.event.data["pdf_path"]

        # Get the source identifier.
        # If source_id is not provided, use the PDF path as the identifier.
        source_id = ctx.event.data.get("source_id", pdf_path)

        # Load the PDF and divide its extracted text into chunks.
        chunks = load_and_chunk_pdf(pdf_path)

        # Return the chunks and source identifier using a Pydantic model.
        return RAGChunkAndSrc(
            chunks=chunks,
            source_id=source_id
        )

    # --------------------------------------------------------
    # 4.2 GENERATE EMBEDDINGS AND SAVE CHUNKS TO QDRANT
    # --------------------------------------------------------

    # Convert text chunks into numerical vectors and store them
    # alongside their original text and source metadata.
    def _upsert(chunk_and_src: RAGChunkAndSrc) -> RAGUpsertResult:

        # Extract the text chunks and document source identifier.
        chunks = chunk_and_src.chunks
        source_id = chunk_and_src.source_id

        # Convert every text chunk into a numerical embedding vector.
        # Similar meanings should generally have similar vector representations.
        vecs = embed_texts(chunks)

        # Generate a deterministic UUID for each chunk.
        # The same source_id and chunk index produce the same ID.
        # This can help prevent duplicate points when re-ingesting
        # the same unchanged document.
        ids = [
            str(uuid.uuid5(uuid.NAMESPACE_URL, f"{source_id}:{i}"))
            for i in range(len(chunks))
        ]

        # Prepare metadata for each vector.
        # Each payload stores the document source and original chunk text.
        payload = [
            {"source": source_id, "text": chunks[i]}
            for i in range(len(chunks))
        ]

        # Insert or update vectors and their payloads in Qdrant.
        QdrantStorage().upsert(ids, vecs, payload)

        # Return the number of chunks successfully submitted for storage.
        return RAGUpsertResult(ingested=len(chunks))

    # --------------------------------------------------------
    # 4.3 EXECUTE INGESTION STEPS THROUGH INNGEST
    # --------------------------------------------------------

    # Run the PDF-loading operation as a named Inngest step.
    # Inngest can persist step results and avoid repeating completed
    # steps when retrying a workflow.
    chunk_and_src = await ctx.step.run(
        "load-and-chunk",
        _load,
        output_type=RAGChunkAndSrc
    )

    # Run embedding generation and vector storage as a separate step.
    # Keeping these operations separate makes the workflow easier to
    # monitor, retry, and debug.
    ingested = await ctx.step.run(
        "embed-and-upsert",
        lambda: _upsert(chunk_and_src),
        output_type=RAGUpsertResult
    )

    # Convert the Pydantic result into a standard Python dictionary
    # and return it as the workflow output.
    return ingested.model_dump()


# ============================================================
# 5. PDF QUESTION-ANSWERING WORKFLOW
# ============================================================

# Register a second workflow that runs when an event named
# "rag/query_pdf_ai" is received.
#
# Its responsibility is to:
# 1. Receive a question.
# 2. Embed the question.
# 3. Retrieve relevant document chunks from Qdrant.
# 4. Send the retrieved context and question to an LLM.
# 5. Return an answer and its source information.

@inngest_client.create_function(
    fn_id="RAG: Query PDF",  # Human-readable workflow identifier.

    # Defines the event that triggers question answering.
    trigger=inngest.TriggerEvent(event="rag/query_pdf_ai")
)
async def rag_query_pdf_ai(ctx: inngest.Context):

    # --------------------------------------------------------
    # 5.1 EMBED THE QUESTION AND RETRIEVE RELEVANT CHUNKS
    # --------------------------------------------------------

    # Search Qdrant for document chunks that are semantically
    # similar to the user's question.
    def _search() -> RAGSearchResult:

        # Read the question from the incoming event.
        question = ctx.event.data["question"]

        # Read the maximum number of results to retrieve.
        # Use 5 if the event does not specify top_k.
        top_k = int(ctx.event.data.get("top_k", 5))

        # Convert the question into an embedding vector.
        # The first element is the vector for this single question.
        query_vec = embed_texts([question])[0]

        # Initialize the Qdrant storage helper.
        store = QdrantStorage()

        # Retrieve the most relevant chunks using the query vector.
        found = store.search(query_vec, top_k)

        # Validate and return the retrieved contexts and source details.
        return RAGSearchResult(
            contexts=found["contexts"],
            sources=found["sources"]
        )

    # Execute the embedding and retrieval operations as a named
    # Inngest step, with the result validated against RAGSearchResult.
    found = await ctx.step.run(
        "embed-and-search",
        _search,
        output_type=RAGSearchResult
    )

    # --------------------------------------------------------
    # 5.2 BUILD THE CONTEXT FOR THE LANGUAGE MODEL
    # --------------------------------------------------------

    # Combine retrieved text chunks into a single context string.
    # Separate each chunk with a blank line for readability.
    context_block = "\n\n".join(
        f" - {c}" for c in found.contexts
    )

    # Get the original question from the incoming event.
    question = ctx.event.data["question"]

    # Construct the prompt containing the retrieved context
    # and the user's question.
    user_content = (
        "Use the following context to answer the question.\n\n"
        f"Context: \n{context_block}\n\n"
        f"Question: {question}\n"
        "Answer concisely using the context above."
    )

    # --------------------------------------------------------
    # 5.3 CONFIGURE THE OPENAI MODEL
    # --------------------------------------------------------

    # Create an OpenAI adapter for making LLM inference requests.
    adapter = ai.openai.Adapter(
        # Retrieve the OpenAI API key from the environment.
        auth_key=os.getenv("OPENAI_API_KEY"),

        # Select the language model used to generate the answer.
        model="gpt-4o-mini"
    )

    # --------------------------------------------------------
    # 5.4 GENERATE AN ANSWER USING THE RETRIEVED CONTEXT
    # --------------------------------------------------------

    # Run the model inference through an Inngest AI step.
    # This allows the inference operation to participate in the
    # workflow's execution and observability features.
    res = await ctx.step.ai.infer(
        "llm-answer",  # Unique name for this inference step.

        # Specify the OpenAI adapter configured above.
        adapter=adapter,

        # Provide the model request parameters.
        body={
            # Maximum number of tokens requested for the completion.
            "max_tokens": 1024,

            # Lower temperature makes the output less random.
            "temperature": 0.2,

            # Provide system instructions and the user's context/question.
            "messages": [

                # System message defines the model's main behavior.
                {
                    "role": "system",
                    "content": (
                        "You answer questions using only the provided context."
                    )
                },

                # User message contains the retrieved document chunks
                # and the actual question.
                {
                    "role": "user",
                    "content": user_content
                }
            ]
        }
    )

    # --------------------------------------------------------
    # 5.5 EXTRACT AND RETURN THE ANSWER
    # --------------------------------------------------------

    # Extract the generated text from the model response.
    # strip() removes unnecessary whitespace at the beginning and end.
    answer = res["choices"][0]["message"]["content"].strip()

    # Return the answer, source information, and number of retrieved chunks.
    # Sources can help the application show where its answer came from.
    return {
        "answer": answer,
        "sources": found.sources,
        "num_contexts": len(found.contexts)
    }


# ============================================================
# 6. CREATE THE FASTAPI APPLICATION
# ============================================================

# Initialize the FastAPI application.
# FastAPI provides the HTTP server and application framework.
app = FastAPI()


# ============================================================
# 7. REGISTER INNGEST FUNCTIONS WITH FASTAPI
# ============================================================

# Connect the Inngest client and its registered workflows to FastAPI.
#
# This exposes the Inngest handler endpoint that receives workflow
# invocations and allows Inngest to execute the registered functions.
#
# Both the ingestion workflow and the question-answering workflow
# are made available through this integration.
inngest.fast_api.serve(
    app,
    inngest_client,
    [
        rag_ingest_pdf,
        rag_query_pdf_ai
    ]
)