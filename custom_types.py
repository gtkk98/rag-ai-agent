import pydantic

class RAGChunkAndSrc(pydantic.BaseModel):
    chunks: list[str]
    source_id: str = None

class RAGUpsertResult(pydantic.BaseModel):
    ingested: int

class RAGSearchResuly(pydantic.BaseModel):
    contexts: list[str]
    sources: list[str]

class RAQQueryResult(pydantic.BaseModel):
    answer: str
    source: list[str]
    num_contexts: int