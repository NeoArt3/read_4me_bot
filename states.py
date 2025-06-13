from aiogram.fsm.state import State, StatesGroup
import asyncio
from datetime import datetime, timedelta

class ScheduleForm(StatesGroup):
    start_time = State()
    end_time = State()
    interval = State()

async def set_schedule(user_id: int, start_time: str, end_time: str, interval: int, bot, callback):
    async def schedule_task():
        start_h, start_m = map(int, start_time.split(':'))
        end_h, end_m = map(int, end_time.split(':'))
        while True:
            now = datetime.now()
            start_today = now.replace(hour=start_h, minute=start_m, second=0, microsecond=0)
            end_today = now.replace(hour=end_h, minute=end_m, second=0, microsecond=0)
            if end_today < start_today:
                end_today += timedelta(days=1)
            if start_today <= now <= end_today:
                await callback(user_id)
                await asyncio.sleep(interval * 3600)
            else:
                wait_until = start_today if now < start_today else start_today + timedelta(days=1)
                wait_seconds = (wait_until - now).total_seconds()
                await asyncio.sleep(wait_seconds)
    asyncio.create_task(schedule_task())