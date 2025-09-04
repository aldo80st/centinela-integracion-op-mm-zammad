import os, httpx, datetime

OP_BASE_URL = os.getenv("OP_BASE_URL", "http://localhost:8080")
OP_TOKEN = os.getenv("OP_TOKEN", "")

MM_WEBHOOK_URL = os.getenv("MM_WEBHOOK_URL", "")

ZAMMAD_BASE_URL = os.getenv("ZAMMAD_BASE_URL", "http://localhost:8081")
ZAMMAD_TOKEN = os.getenv("ZAMMAD_TOKEN", "")

class OpenProjectClient:
    def __init__(self, base_url=OP_BASE_URL, token=OP_TOKEN):
        self.base = base_url.rstrip("/")
        self.h = {"Authorization": f"Bearer {token}", "Content-Type":"application/json"}

    async def search_work_packages(self, query: str):
        # Búsqueda simple por 'subject' (para demo)
        url = f"{self.base}/api/v3/work_packages?filters=[{{"subject":{{"operator":"~","values":["{query}"]}}}}]"
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(url, headers=self.h)
            r.raise_for_status()
            return r.json()

    async def upsert_from_ticket(self, ticket: dict):
        # DEMO: crea siempre un WP mínimo con mapeo básico
        subject = ticket.get("title","Ticket sin título")
        description = f"Origen: Zammad\nTicket ID: {ticket.get('id')}\nEstado: {ticket.get('state')}"
        payload = {
            "subject": subject,
            "description": {"raw": description}
        }
        url = f"{self.base}/api/v3/work_packages"
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(url, headers=self.h, json=payload)
            r.raise_for_status()
            return r.json()

class MattermostClient:
    def __init__(self, webhook=MM_WEBHOOK_URL):
        self.webhook = webhook

    async def post_text(self, text: str):
        if not self.webhook:
            return {"status": "noop", "reason": "MM_WEBHOOK_URL not set"}
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(self.webhook, json={"text": text})
            r.raise_for_status()
            return {"status": "ok"}

class ZammadClient:
    def __init__(self, base_url=ZAMMAD_BASE_URL, token=ZAMMAD_TOKEN):
        self.base = base_url.rstrip("/")
        self.h = {"Authorization": f"Token token={token}", "Content-Type":"application/json"}

    # Espacio para futuras llamadas salientes a Zammad si se requiere.
