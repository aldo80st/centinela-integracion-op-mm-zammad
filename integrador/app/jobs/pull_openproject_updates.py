import asyncio, os
from .utils import log
from ..clients import OpenProjectClient, MattermostClient

async def run():
    op = OpenProjectClient()
    mm = MattermostClient()
    # DEMO: consulta un término genérico y notifica cantidad (como "pull" periódico)
    data = await op.search_work_packages("PTZ")
    count = len(data.get("_embedded",{}).get("elements",[]))
    await mm.post_text(f":information_source: Pull OP: encontrados {count} work packages con 'PTZ'.")
    log("pull_openproject_updates complete")

if __name__ == "__main__":
    asyncio.run(run())
