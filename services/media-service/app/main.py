import io
import uuid
import boto3
import structlog
from PIL import Image
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from botocore.client import Config
from app.config import get_settings
from app.core.deps import get_current_user, CurrentUser

settings = get_settings()
log      = structlog.get_logger()

# ── MinIO client ──────────────────────────────────────────────────────────────
def get_s3():
    return boto3.client(
        's3',
        endpoint_url          = settings.minio_endpoint,
        aws_access_key_id     = settings.minio_access_key,
        aws_secret_access_key = settings.minio_secret_key,
        config                = Config(signature_version='s3v4'),
        region_name           = 'us-east-1',
    )

def ensure_bucket():
    s3 = get_s3()
    try:
        s3.head_bucket(Bucket=settings.minio_bucket)
    except Exception:
        s3.create_bucket(Bucket=settings.minio_bucket)
        s3.put_bucket_policy(
            Bucket=settings.minio_bucket,
            Policy=f'{{"Version":"2012-10-17","Statement":[{{"Effect":"Allow",'
                   f'"Principal":"*","Action":"s3:GetObject",'
                   f'"Resource":"arn:aws:s3:::{settings.minio_bucket}/*"}}]}}',
        )
        log.info('minio.bucket.created', bucket=settings.minio_bucket)

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title='SMWCS Media Service',
    description='Image upload and storage for SMWCS Kenya',
    version='1.0.0',
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

@app.on_event('startup')
async def startup():
    ensure_bucket()
    log.info('media-service ready', endpoint=settings.minio_endpoint)

@app.get('/health')
async def health():
    return {'status': 'ok', 'service': settings.service_name}

@app.post('/api/v1/media/upload')
async def upload_image(
    file:    UploadFile = File(...),
    folder:  str        = 'general',
    _user:   CurrentUser = Depends(get_current_user),
):
    """
    Upload and compress an image to MinIO.
    Returns the public URL.
    Supports: JPEG, PNG, WEBP, GIF
    Max output size: 1920px on longest side, JPEG quality 82
    """
    if not file.content_type or not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail='File must be an image')

    contents = await file.read()
    if len(contents) > 20 * 1024 * 1024:
        raise HTTPException(status_code=400, detail='File too large (max 20 MB)')

    try:
        img = Image.open(io.BytesIO(contents))
        if img.mode in ('RGBA', 'P', 'LA'):
            img = img.convert('RGB')
        img.thumbnail((1920, 1920), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=82, optimize=True)
        buf.seek(0)
        compressed = buf.read()
    except Exception as e:
        log.error('image.compression.failed', error=str(e))
        raise HTTPException(status_code=400, detail=f'Invalid image: {e}')

    key = f'{folder}/{uuid.uuid4()}.jpg'
    try:
        s3 = get_s3()
        s3.put_object(
            Bucket      = settings.minio_bucket,
            Key         = key,
            Body        = compressed,
            ContentType = 'image/jpeg',
        )
    except Exception as e:
        log.error('minio.upload.failed', error=str(e))
        raise HTTPException(status_code=500, detail='Upload failed')

    url = f'{settings.minio_endpoint}/{settings.minio_bucket}/{key}'
    log.info('media.uploaded',
             key=key,
             original_bytes=len(contents),
             compressed_bytes=len(compressed))

    return {
        'url':              url,
        'key':              key,
        'original_bytes':   len(contents),
        'compressed_bytes': len(compressed),
        'compression_ratio': round(len(compressed) / len(contents) * 100, 1),
    }

@app.delete('/api/v1/media/{key:path}')
async def delete_image(
    key:   str,
    _user: CurrentUser = Depends(get_current_user),
):
    try:
        get_s3().delete_object(Bucket=settings.minio_bucket, Key=key)
        log.info('media.deleted', key=key)
        return {'message': 'Deleted', 'key': key}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
