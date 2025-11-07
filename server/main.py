# server/main.py
from fastapi import FastAPI
from server.api import router
from server.audit import init_db

app = FastAPI(title="Finwise Agent Backend")
app.include_router(router)

@app.on_event("startup")
def startup():
    init_db()
