from fastapi import APIRouter, UploadFile, File, Form
from server.agent_controller import run_agent
from server.audit import log
import shutil, uuid, os

router = APIRouter()

@router.post("/upload_document")
async def upload_document(file: UploadFile = File(...), user_id: str | None = Form(None)):
    ext = os.path.splitext(file.filename)[1]
    dest = f"./uploads/{uuid.uuid4().hex}{ext}"
    os.makedirs("./uploads", exist_ok=True)
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)
    log("upload", {"file": dest, "filename": file.filename}, user_id=user_id)
    return {"file_path": dest}

@router.post("/ask")
async def ask(question: str = Form(...), user_id: str | None = Form(None)):
    res = run_agent(question, user_id=user_id)
    return {"answer": res}
