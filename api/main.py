from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.endpoints import auth, health, movies, studios, users

app = FastAPI(
    title="Movie Bot API",
    description="API для управления списком фильмов",
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем роутеры
app.include_router(health.router, tags=["health"])
app.include_router(movies.router, prefix="/movies", tags=["movies"])
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(auth.router, tags=["auth"])
app.include_router(studios.router)


@app.get("/")
async def root():
    return {"message": "Movie Bot API работает!"}
