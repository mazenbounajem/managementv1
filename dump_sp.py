import asyncio
from database_manager import db_manager

async def main():
    rows = await db_manager.execute_query_async("sp_helptext 'pb_run_fiscal_year_rollover'")
    with open('sp_dump.sql', 'w') as f:
        for r in rows:
            f.write(r[0])

asyncio.run(main())
