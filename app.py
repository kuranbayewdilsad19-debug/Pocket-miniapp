from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

app = FastAPI()

# Frontend (web/index.html)
app.mount("/", StaticFiles(directory="web", html=True), name="web")
