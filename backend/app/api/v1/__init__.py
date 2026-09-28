from fastapi import APIRouter
from backend.app.api.v1.health import router as health_router
from backend.app.api.v1.projects import router as projects_router
from backend.app.api.v1.documents import router as documents_router
from backend.app.api.v1.extraction import router as extraction_router
from backend.app.api.v1.datasets import router as datasets_router
from backend.app.api.v1.records import router as records_router
from backend.app.api.v1.validation import router as validation_router
from backend.app.api.v1.review import router as review_router
from backend.app.api.v1.exports import router as exports_router
from backend.app.api.v1.activity import router as activity_router
from backend.app.api.v1.llm import router as llm_router
from backend.app.api.v1.system import router as system_router
from backend.app.api.v1.curation import router as curation_router

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(health_router)
api_v1_router.include_router(projects_router)
api_v1_router.include_router(documents_router)
api_v1_router.include_router(extraction_router)
api_v1_router.include_router(datasets_router)
api_v1_router.include_router(records_router)
api_v1_router.include_router(validation_router)
api_v1_router.include_router(review_router)
api_v1_router.include_router(exports_router)
api_v1_router.include_router(activity_router)
api_v1_router.include_router(llm_router)
api_v1_router.include_router(system_router)
api_v1_router.include_router(curation_router)
