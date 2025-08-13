import requests
from bs4 import BeautifulSoup
import asyncio
import json
from datetime import datetime, time, timedelta, timezone

class CodTaskManager():
    def __init__(self, *args, **kwargs):
        self.task_map = {}
        
    def start_cod(self, channel_id: int, target_time: time, bot):
        key = f"{channel_id}"
        task = self.task_map.get(key)
        
        # Cancel the task if already running
        if task:
            task.cancel()
        
        self.task_map[f"{channel_id}"] = asyncio.create_task(send_cod(channel_id, target_time, bot))
    
    def stop_cod(self, channel_id: int):
        self.task_map[f"{channel_id}"].cancel()
        

cod_task_manager = CodTaskManager()

def get_cod_task_manager(): return cod_task_manager

def log(message):
    print(f"[{datetime.now(timezone.utc).strftime('%X %x')}]: {message}")

def get_next_execution_datetime(exec_time: time) -> datetime:
    now = datetime.now(timezone.utc)
    today_exec = datetime.combine(now.date(), exec_time, tzinfo=timezone.utc)
    return today_exec if today_exec > now else today_exec + timedelta(days=1)

def genRcdb():
    page = requests.get("https://rcdb.com")
    soup = BeautifulSoup(page.content, 'html.parser')
    parent = soup.find(id="rrc_text")

    res = "# Random Roller Coaster\n"
    coaster_link = None

    for p in parent.find_all('p'):
        span = p.find('span')
        if span:
            label = span.get_text(strip=True)
            if label == "Roller Coaster":
                coaster_tag = p.find('a')
                if coaster_tag:
                    coaster_name = coaster_tag.get_text(strip=True)
                    coaster_link = "https://rcdb.com" + coaster_tag['href']
                    res += f"**Roller Coaster:** [{coaster_name}]({coaster_link})\n"
            else:
                # All other properties
                properties = [
                    element.get_text(strip=True)
                    for element in p.find_all(['a', 'span']) if element != span
                ]
                property_text = ", ".join(properties)
                res += f"**{label}**: {property_text}\n"
    return res

async def start_cod(bot):
    log("initiated cod services")
    data = None
    with open('cod/channels.json', 'r') as file:
        data = json.load(file)
    
    log("Data not found" if data == None else "Data found")
    for channel, str_time in data.items():
        execution_time = parse_time_from_argument(str_time)
        if execution_time is None:
            log(f"Skipping channel {channel}: invalid time format '{str_time}'")
            continue

        # Using single quotes inside strftime to avoid f-string quote collision
        log(f"Setting cod up for: {channel} on {execution_time.strftime('%H:%M')}")

        cod_task_manager.start_cod(channel_id=int(channel), target_time=execution_time, bot=bot)


async def send_cod(channel_id, target_time: time, bot):
    while True:
        try: 
            time_delta = get_next_execution_datetime(target_time) - datetime.now(timezone.utc)
            await asyncio.sleep(time_delta.total_seconds())
            
            channel = bot.get_channel(channel_id)
            
            log(f"Trying to send cod in: {channel.name if channel else 'unknown'}")
            if channel:
                await channel.send(get_cod())
                log(f"Cod sent in {channel.name}")
            else:
                log(f"Channel {channel_id} not found. Breaking...")
                break
        except asyncio.CancelledError:
            log(f"COD was cancelled for {channel.name}")
        except Exception as e:
            log(f"Error in send_cod for channel {channel_id}: {e}")

def get_cod():
    with open("cod.txt", "r") as file:
        cod_message = file.read()
    return cod_message

def parse_time_from_argument(argument):
    try:
        hour, minute = map(int, argument.strip().split(":"))
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError
        return time(hour=hour, minute=minute)
    except ValueError:
        return None

async def daily_rcdb_gen():
    while True:
        delta = time_until_end_of_day()
        await asyncio.sleep(delta.total_seconds())
        
        next_coaster = genRcdb()
        with open("cod.txt", "w") as file:
            file.write(next_coaster)
    

def time_until_end_of_day(dt=None):
    if dt is None:
        dt = datetime.now(timezone.utc)
    tomorrow = dt + timedelta(days=1)
    return datetime.combine(tomorrow, time.min, tzinfo=timezone.utc) - dt