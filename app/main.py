from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.routes.books import router as books_router
from app.routes.bookmarks import router as bookmarks_router
from app.routes.authors import router as authors_router
from app.routes.auth import router as auth_router
from app.routes.chat import router as chat_router
from app.routes.conversation import router as conversation_router
from app.routes.admin import router as admin_router
from app.core.config import SESSION_SECRET_KEY

app = FastAPI()


# SessionMiddleware is required by the Google OAuth flow because Authlib stores
# temporary OAuth state in the signed session between redirect and callback.
app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET_KEY,
    same_site="lax",
    https_only=False
)

# CORS tells browsers which frontend origins may call this API.
# Keep production and local development origins explicit so credentials are not
# exposed to every website.
app.add_middleware(
    CORSMiddleware,

    allow_origins=[
        "https://library-data-retrieval-llm-chatbot.vercel.app",
        "http://localhost:5500/frontend"
        ], 
    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"]
)


# Routers are kept in separate modules by domain so service logic and HTTP
# wiring stay easier to maintain independently.
app.include_router(
    books_router
)

app.include_router(
    bookmarks_router
)

app.include_router(
    authors_router
)

app.include_router(
    auth_router
)

app.include_router(
    chat_router
)

app.include_router(
    conversation_router
)

app.include_router(
    admin_router
)




