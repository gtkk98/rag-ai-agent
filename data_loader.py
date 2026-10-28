# ============================================================
# 1. IMPORT REQUIRED LIBRARIES
# ============================================================

# OpenAI client for generating text embeddings.
from openai import OpenAI

# PDFReader extracts text and document content from PDF files.
from llama_index.readers.file import PDFReader

# SentenceSplitter divides long text into smaller, overlapping chunks.
from llama_index.core.node_parser import SentenceSplitter

# Loads environment variables from the .env file.
from dotenv import load_dotenv


# ============================================================
# 2. LOAD ENVIRONMENT VARIABLES
# ============================================================

# Load configuration values, including OPENAI_API_KEY,
# from the project's .env file into the environment.
load_dotenv()


# ============================================================
# 3. INITIALIZE THE OPENAI CLIENT
# ============================================================

# Create an OpenAI client.
# By default, it reads OPENAI_API_KEY from the environment.
# The API key should be stored securely in the .env file.
client = OpenAI()


# ============================================================
# 4. CONFIGURE THE EMBEDDING MODEL
# ============================================================

# Specify the OpenAI embedding model used to convert text
# into numerical vectors.
EMBED_MODEL = "text-embedding-3-large"

# This model supports 3072-dimensional embeddings by default.
# This value must match the vector dimension configured in Qdrant.
EMBED_DIM = 3072


# ============================================================
# 5. CONFIGURE THE TEXT CHUNK SPLITTER
# ============================================================

# Create a SentenceSplitter to divide extracted PDF text into chunks.
splitter = SentenceSplitter(
    chunk_size=1000,      # Target chunk size, measured in tokens.
    chunk_overlap=200     # Overlap between neighboring chunks, in tokens.
)

# Chunk overlap helps preserve context between adjacent chunks.
# For example, information near the end of one chunk may also
# appear at the beginning of the next chunk.


# ============================================================
# 6. LOAD A PDF AND SPLIT ITS TEXT INTO CHUNKS
# ============================================================

# Accepts a PDF file path and returns a list of text chunks.
def load_and_chunk_pdf(path: str):

    # Read the PDF and extract its content.
    # PDFReader commonly returns document objects, often separated
    # by page, depending on the reader and PDF structure.
    docs = PDFReader().load_data(file=path)

    # Extract non-empty text from the returned document objects.
    # getattr() safely checks whether each object has a text attribute.
    texts = [
        d.text
        for d in docs
        if getattr(d, "text", None)
    ]

    # Create a list to hold the final text chunks.
    chunks = []

    # Process each extracted text section separately.
    for t in texts:

        # Split the text into smaller, overlapping chunks
        # using the configured SentenceSplitter.
        chunks.extend(splitter.split_text(t))

    # Return all generated chunks to the ingestion workflow.
    return chunks


# ============================================================
# 7. CONVERT TEXT INTO EMBEDDING VECTORS
# ============================================================

# Accepts a list of text strings and returns a list of vectors.
# Each vector represents the semantic meaning of one text input.
def embed_texts(texts: list[str]) -> list[list[float]]:

    # Send the text inputs to OpenAI's embeddings API.
    response = client.embeddings.create(
        model=EMBED_MODEL,  # Embedding model to use.
        input=texts         # Text chunks or a user question.
    )

    # Extract the numerical embedding from each API response item.
    # Return one vector for each input text.
    return [
        item.embedding
        for item in response.data
    ]