from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from minio import Minio
from redis import Redis
from app.config import settings
from app.db import engine
from app.features.products.routes import router
app = FastAPI(title='Knowledge Product Manager',version='0.1.0')
app.add_middleware(CORSMiddleware,allow_origins=settings.cors_origins,allow_methods=['*'],allow_headers=['*'])
app.include_router(router)

@app.get('/api/health')
def health():
    probes = {}
    for name,probe in {
        'postgres':lambda: engine.connect(),
        'minio':lambda: Minio(settings.minio_endpoint,access_key=settings.minio_access_key,secret_key=settings.minio_secret_key,secure=False).list_buckets(),
        'falkordb':lambda: Redis.from_url(settings.graph_url,socket_timeout=3).ping(),
    }.items():
        try:
            result=probe()
            if name=='postgres':
                result.execute(text('SELECT 1')); result.close()
            probes[name]='ready'
        except Exception:
            probes[name]='unavailable'
    return {'probes':probes,'identity_mode':'Synthetic demo identities'}
