from logging import exception
import discord
from discord.ext import commands
from discord import app_commands
import requests
import os
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import asyncio
from datetime import time
import json
from utils import log, get_cod, start_cod, genRcdb, parse_time_from_argument, daily_rcdb_gen, get_cod_task_manager


load_dotenv()
TOKEN = os.environ['DISCORD_TOKEN']

intents = discord.Intents.all()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree


@bot.event
async def on_ready():
    log(f'We have logged in as {bot.user}')
    try:
        synced = await bot.tree.sync()
        log(f"Synced {len(synced)} command(s)")
    except Exception as e:
        log(e)
    
    if not os.path.exists("cod.txt"):
        log("cod.txt not found, generating...")
        
        with open ("cod.txt", 'w') as file:
            file.write(genRcdb())
        
        log("cod.txt created")
    try:
        log("Starting cod services")
        asyncio.create_task(daily_rcdb_gen()) 
        asyncio.create_task(start_cod(bot=bot))
        log("Cod services started!")
    except Exception as e:
        log("Failed starting Coaster of the Day messages")
        log(e)


@bot.tree.command()
async def rcdb(ctx):
    res = genRcdb()
    await ctx.response.send_message(res)


@bot.tree.command()
async def rcdblist(ctx, amount: int):
    res = ""
    i = 1
    while i <= amount:
        page = requests.get("https://rcdb.com")
        soup = BeautifulSoup(page.content, 'html.parser')
        item = soup.find(id="rrc_text").find('p')
        a = item.find('a')
        res += f"* **{i}**  [{a.text}](<https://rcdb.com{a['href']}>) \n"
        i += 1

    await ctx.response.send_message(res)

@commands.has_permissions(manage_guild=True)
@bot.tree.command()
async def cod(ctx, utc_time: str):
    parsed_time = parse_time_from_argument(utc_time)
    
    if parsed_time == None:
        await ctx.response.send_message("Wrong format, use `HH:MM` with EU time (don't use AM, or PM). Example: 9:00", ephemeral=True)
        return
    
    with open("cod/channels.json", "r") as file:
        data = json.load(file)
        data[f"{ctx.channel.id}"] = utc_time
        
    with open("cod/channels.json", "w") as file:
        json.dump(data, file, indent=4)
    
    get_cod_task_manager().start_cod(channel_id=ctx.channel.id, target_time=parsed_time, bot=bot)
    
    await ctx.response.send_message(f"You will recieve the coaster of the day every day at {utc_time} (utc) in this channel. If there already was a cod task present, the time for that task got updated.", ephemeral=True)

@commands.has_permissions(manage_guild=True)
@bot.tree.command()
async def cancelcod(ctx):
    with open("cod/channels.json", "r") as file:
        data = json.load(file)
        channel_id = str(ctx.channel.id)
        if channel_id in data:
            del data[channel_id]
        else:
            await ctx.response.send_message("The channel didn't doesn't have a cod task running, if this is a mistake, please contact sqnder_ on discord.", ephemeral=True)
            return
        
    with open("cod/channels.json", "w") as file:
        json.dump(data, file, indent=4)
        
    get_cod_task_manager().stop_cod(ctx.channel.id)
    
    await ctx.response.send_message("The cod task for this channel was successfully canceled.", ephemeral=True)

bot.run(TOKEN)
