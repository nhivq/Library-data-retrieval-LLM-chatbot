from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.books import router as books_router
from app.routes.bookmarks import router as bookmarks_router
from app.routes.auth import router as auth_router

app = FastAPI()

# Fix CORS issue
# By default, browsers only allow api calls on the same .com/ IP address
# Backend server grant permission to frontend using HTTP response headers,
# allow frontend to access API
app.add_middleware(
    CORSMiddleware,

    allow_origins=["*"], # Allow requests from ANY websites/ origin. This is for practice only, later -> specific origin

    allow_credentials=True, # Allow browser to include credentials

    allow_methods=["*"], # Allow all HTTP methods (Get, Post, Put, Patch, Delete, etc.)

    allow_headers=["*"] # Allow all request headers (Content-Type, Authorization)
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






