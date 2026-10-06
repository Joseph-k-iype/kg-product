from functools import lru_cache
import math
from app.config import settings
from app.domain.contracts import ModelRef

MODEL_NAME='sentence-transformers/all-MiniLM-L6-v2'
MODEL_REVISION='1110a243fdf4706b3f48f1d95db1a4f5529b4d41'
@lru_cache(maxsize=2)
def load_model(name,revision):
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(name,revision=revision,cache_folder=settings.model_cache,trust_remote_code=False,local_files_only=True)

class EmbeddingProvider:
    def embed(self,texts:list[str],model:ModelRef)->list[list[float]]:
        if model.name!=MODEL_NAME or model.dimension!=384 or model.revision!=MODEL_REVISION:
            raise ValueError('Configure the supported 384-dimensional local model before preparing knowledge.')
        try:
            encoder=load_model(model.name,model.revision)
            vectors=encoder.encode(texts,normalize_embeddings=True).tolist()
            if any(len(v)!=model.dimension or any(not math.isfinite(x) for x in v) for v in vectors):
                raise ValueError('Embedding provider returned incompatible vectors')
            return vectors
        except Exception as e:
            raise RuntimeError('Local search model unavailable. Run make model to download the pinned model, then retry.') from e
