from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from minio import Minio
from redis import Redis
from app.config import settings
from app.db import engine
from app.features.products.routes import router

app = FastAPI(title="Knowledge Product Manager", version="0.1.0")
app.add_middleware(
    CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["*"], allow_headers=["*"]
)
app.include_router(router)
from app.features.products.onboarding import router as onboarding_router
app.include_router(onboarding_router)
from app.features.documents.routes import router as documents_router
from app.features.sources.routes import router as sources_router

app.include_router(documents_router)
app.include_router(sources_router)


@app.get("/api/health")
def health():
    probes = {}
    for name, probe in {
        "postgres": lambda: engine.connect(),
        "minio": lambda: Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=False,
        ).list_buckets(),
        "falkordb": lambda: Redis.from_url(settings.graph_url, socket_timeout=3).ping(),
    }.items():
        try:
            result = probe()
            if name == "postgres":
                result.execute(text("SELECT 1"))
                result.close()
            probes[name] = "ready"
        except Exception:
            probes[name] = "unavailable"
    return {"probes": probes, "identity_mode": "Synthetic demo identities"}


from app.features.ontology.routes import router as ontology_router

app.include_router(ontology_router)

from app.features.retrieval.routes import router as retrieval_router

app.include_router(retrieval_router)

from app.features.graph.routes import router as graph_router

app.include_router(graph_router)

from app.features.evaluations.routes import router as evaluations_router

app.include_router(evaluations_router)

from app.features.reviews.routes import router as reviews_router

app.include_router(reviews_router)

from app.features.releases.routes import router as releases_router

app.include_router(releases_router)

from app.features.consumers.routes import router as consumers_router

app.include_router(consumers_router)

from app.features.lineage.routes import router as lineage_router

app.include_router(lineage_router)

from app.features.overview.routes import router as overview_router

app.include_router(overview_router)

from app.features.chat.gateway import router as gateway_router
from app.features.chat.routes import router as chat_router

app.include_router(chat_router)
app.include_router(gateway_router)
