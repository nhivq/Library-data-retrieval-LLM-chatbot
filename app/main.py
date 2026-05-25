from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.books import router as books_router
from app.routes.bookmarks import router as bookmarks_router
from app.routes.auth import router as auth_router

app = FastAPI()

# Fix CORS issue
app.add_middleware(
    CORSMiddleware,

    allow_origins=["*"],

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"]
)

app.include_router(
    books_router
)

app.include_router(
    bookmarks_router
)

app.include_router(
    auth_router
)






