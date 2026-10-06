from app.adapters.embeddings import MODEL_NAME,MODEL_REVISION
from app.config import settings
from sentence_transformers import SentenceTransformer
model=SentenceTransformer(MODEL_NAME,revision=MODEL_REVISION,cache_folder=settings.model_cache,trust_remote_code=False)
assert model.get_sentence_embedding_dimension()==384
print('Pinned local search model downloaded. Dimension: 384')
