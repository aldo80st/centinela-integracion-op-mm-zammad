import asyncio
from .utils import log
from ..clients import MattermostClient

async def run():
    mm = MattermostClient()
    await mm.post_text(":alarm_clock: Recordatorio SLA (demo).")
    log("sla_reminders complete")

if __name__ == "__main__":
    asyncio.run(run())
