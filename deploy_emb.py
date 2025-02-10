import logging
import uvicorn
from pydantic import BaseModel
from fastapi import FastAPI, APIRouter, Request
from sentence_transformers import SentenceTransformer, CrossEncoder
from contextlib import asynccontextmanager
from environs import Env
import torch
import time
import threading

# Initialize environment variables
env = Env()
env.read_env()

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s:%(lineno)d - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Check if GPU is available
device = "cuda" if torch.cuda.is_available() else "cpu"
logger.info(f"Using device: {device}")

# Environment variables
DEFAULT_EMBEDDING_MODEL = env.str("DEFAULT_EMBEDDING_MODEL", default="BAAI/bge-m3")
DEFAULT_RERANKER_MODEL = env.str(
    "DEFAULT_RERANKER_MODEL", default="BAAI/bge-reranker-v2-m3"
)

# Initialize FastAPI app and router
app = FastAPI()
router = APIRouter()

# Global dictionaries to store loaded models
EMBEDDING_MODEL_DICT: dict[str, SentenceTransformer] = {}
RERANKER_MODEL_DICT: dict[str, CrossEncoder] = {}

# Track the last API call time
last_call_time = time.time()

# Lock for thread-safe access to models
model_lock = threading.Lock()

# Idle timeout in seconds (10 minutes)
IDLE_TIMEOUT = 600  # 10 minutes


def unload_models():
    """Unload models if idle for more than 10 minutes."""
    global EMBEDDING_MODEL_DICT, RERANKER_MODEL_DICT, last_call_time
    while True:
        time.sleep(60)  # Check every minute
        with model_lock:
            if time.time() - last_call_time > IDLE_TIMEOUT:
                logger.info("Unloading models due to inactivity")
                EMBEDDING_MODEL_DICT.clear()
                RERANKER_MODEL_DICT.clear()


# Start the idle timeout thread
idle_thread = threading.Thread(target=unload_models, daemon=True)
idle_thread.start()


@router.get("/healthz")
def healthz():
    return "OK"


def get_embedding_model(model_name: str) -> SentenceTransformer:
    global EMBEDDING_MODEL_DICT, last_call_time
    with model_lock:
        last_call_time = time.time()  # Update last call time
        embed_model = EMBEDDING_MODEL_DICT.get(model_name)
        if not embed_model:
            logger.info(f"Loading embedding model: {model_name} on device: {device}")
            embed_model = SentenceTransformer(
                model_name_or_path=model_name,
                trust_remote_code=True,
                device=device,  # Use GPU if available, otherwise CPU
            )
            EMBEDDING_MODEL_DICT[model_name] = embed_model
        return embed_model


def get_reranker_model(model_name: str) -> CrossEncoder:
    global RERANKER_MODEL_DICT, last_call_time
    with model_lock:
        last_call_time = time.time()  # Update last call time
        reranker_model = RERANKER_MODEL_DICT.get(model_name)
        if not reranker_model:
            logger.info(f"Loading reranker model: {model_name} on device: {device}")
            reranker_model = CrossEncoder(
                model_name=model_name,
                automodel_args={"torch_dtype": "auto"},  # Remove 'device' from here
                trust_remote_code=True,
            )
            # Move the model to the specified device (GPU or CPU)
            reranker_model.model.to(device)
            RERANKER_MODEL_DICT[model_name] = reranker_model
        return reranker_model


class EmbeddingRequest(BaseModel):
    sentences: list[str]
    model: str = DEFAULT_EMBEDDING_MODEL
    normalize_embeddings: bool = True


class EmbeddingResponse(BaseModel):
    model: str
    embeddings: list[list]


@router.post("/embedding")
def get_texts_embedding(request: EmbeddingRequest) -> EmbeddingResponse:
    embed_model = get_embedding_model(model_name=request.model)
    logger.info(f"Encoding sentences using model: {request.model} on device: {device}")
    embeddings = embed_model.encode(
        sentences=request.sentences,
        normalize_embeddings=request.normalize_embeddings,
    )
    return EmbeddingResponse(
        model=request.model,
        embeddings=embeddings.tolist(),
    )


class RerankerRequest(BaseModel):
    model: str = DEFAULT_RERANKER_MODEL
    query: str
    passages: list[str]


class RerankerResponse(BaseModel):
    model: str
    scores: list[float]


@router.post("/reranker")
def reranker_texts(request: RerankerRequest) -> RerankerResponse:
    reranker_model = get_reranker_model(request.model)
    logger.info(f"Reranking using model: {request.model} on device: {device}")
    sentence_pairs = [(request.query, p) for p in request.passages]
    scores = reranker_model.predict(sentence_pairs, convert_to_tensor=True)
    return RerankerResponse(model=request.model, scores=scores.tolist())


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Check if models should be pre-loaded
    if env.bool("PRE_LOAD_DEFAULT_EMBEDDING_MODEL", default=False):
        logger.info(f"Loading default embedding model: {DEFAULT_EMBEDDING_MODEL}")
        get_embedding_model(DEFAULT_EMBEDDING_MODEL)
        logger.info("Default embedding model loaded")
    if env.bool("PRE_LOAD_DEFAULT_RERANKER_MODEL", default=False):
        logger.info(f"Loading default reranker model: {DEFAULT_RERANKER_MODEL}")
        get_reranker_model(DEFAULT_RERANKER_MODEL)
        logger.info("Default reranker model loaded")
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(router=router, prefix="/api/v1")


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=5001, reload=True)
