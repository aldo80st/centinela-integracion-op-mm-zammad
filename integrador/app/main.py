from fastapi import FastAPI, Request, Form
from pydantic import BaseModel
from .clients import OpenProjectClient, MattermostClient

app = FastAPI(title="Integrador OP↔Zammad con avisos a Mattermost", version="0.1.0")

class Ticket(BaseModel):
    id: int
    title: str
    state: str | None = None
    priority: str | None = None
    owner: str | None = None
    due_at: str | None = None

class ZammadWebhook(BaseModel):
    ticket: Ticket

@app.get("/health")
async def health():
    return {"status":"ok"}

@app.post("/zammad/webhook")
async def zammad_webhook(payload: ZammadWebhook):
    op = OpenProjectClient()
    mm = MattermostClient()
    wp = await op.upsert_from_ticket(payload.ticket.dict())
    await mm.post_text(f":rotating_light: Ticket #{payload.ticket.id} → WP #{wp.get('id')} creado/actualizado.")
    return {"ok": True, "wp_id": wp.get("id")}

@app.post("/slash/op")
async def slash_op(token: str = Form(...), text: str = Form("")):
    # DEMO: no validamos token; añade validación en producción
    op = OpenProjectClient()
    if text.lower().startswith("buscar"):
        q = text[6:].strip() or "PTZ"
        data = await op.search_work_packages(q)
        elements = data.get("_embedded",{}).get("elements",[])
        lines = [f"- #{e['id']} {e['subject']}" for e in elements[:5]]
        return {"response_type":"ephemeral", "text": "Resultados:\n" + ("\n".join(lines) or "Sin coincidencias.")}
    return {"response_type":"ephemeral","text":"Uso: `/op buscar <texto>`"}
