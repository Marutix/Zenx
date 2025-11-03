#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import os
import sys
import signal
from typing import List, Optional

# Use discord.py-self for selfbot support
import discord
from discord.ext import commands

# ----------------------------------------------------------------------
# ── COLOUR CODES (ANSI) ───────────────────────────────────────────────
# ----------------------------------------------------------------------
PURPLE = "\033[95m"   # banner
WHITE  = "\033[97m"   # menu / prompt
RESET  = "\033[0m"

# ----------------------------------------------------------------------
# ── ASCII BANNER ───────────────────────────────────────────────────────
# ----------------------------------------------------------------------
BANNER = f"""{PURPLE}
▒███████▒   ▓█████     ███▄    █    
▒ ▒ ▒ ▄▀░   ▓█   ▀     ██ ▀█   █    
░ ▒ ▄▀▒░    ▒███      ▓██  ▀█ ██▒   
  ▄▀▒   ░   ▒▓█  ▄    ▓██▒  ▐▌██▒   
▒███████▒   ░▒████▒   ▒██░   ▓██░   
░▒▒ ▓░▒░▒   ░░ ▒░ ░   ░ ▒░   ▒ ▒    
░░▒ ▒ ░ ▒    ░ ░  ░   ░ ░░   ░ ▒░   
░ ░ ░ ░ ░      ░         ░   ░ ░    
  ░ ░          ░  ░            ░    
░                                   
{RESET}"""

# ----------------------------------------------------------------------
# ── MENU ───────────────────────────────────────────────────────────────
# ----------------------------------------------------------------------
MENU_ITEMS = [
    ("svrraid", "Svr Raid"),
    ("exit",    "Exit the tool"),
]

# ----------------------------------------------------------------------
# ── DISCORD CLIENT (per token) ────────────────────────────────────────
# ----------------------------------------------------------------------
class RaidClient(discord.Client):
    def __init__(self, token: str, message: str, guild_id: Optional[int] = None):
        intents = discord.Intents.all()
        super().__init__(intents=intents)
        self.token = token
        self.spam_msg = message
        self.target_guild_id = guild_id
        self.running = True

    async def on_ready(self):
        print(f"{WHITE}│ [+] {self.user} online{RESET}")
        await self.change_presence(
            activity=discord.Game(name="Maruti /wya [zombie]")
        )
        # start spamming as soon as we are ready
        self.loop.create_task(self.spam_task())

    async def spam_task(self):
        while self.running:
            try:
                guild = self.get_guild(self.target_guild_id) if self.target_guild_id else None
                if not guild:
                    await asyncio.sleep(1)
                    continue

                for channel in guild.text_channels:
                    try:
                        await channel.send(self.spam_msg)
                        await asyncio.sleep(0.5)
                    except Exception:
                        pass
            except Exception:
                await asyncio.sleep(1)

    async def close(self):
        self.running = False
        await super().close()

# ----------------------------------------------------------------------
# ── UI HELPERS ────────────────────────────────────────────────────────
# ----------------------------------------------------------------------
def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_menu():
    clear_screen()
    print(BANNER)
    line = WHITE
    for i, (name, _) in enumerate(MENU_ITEMS, 1):
        line += f"{i}.{name}  "
    line = line.rstrip() + RESET
    print(line)
    cols = os.get_terminal_size().columns
    print("─" * cols)
    print(f"{WHITE}enter option>> {RESET}", end="")

def get_choice() -> int:
    while True:
        try:
            ch = input().strip()
            if ch.isdigit():
                val = int(ch)
                if 1 <= val <= len(MENU_ITEMS):
                    return val
            print(f"{WHITE}Pick 1-{len(MENU_ITEMS)}{RESET}")
        except (EOFError, KeyboardInterrupt):
            return len(MENU_ITEMS)

# ----------------------------------------------------------------------
# ── RAID FLOW ─────────────────────────────────────────────────────────
# ----------------------------------------------------------------------
async def start_client(client: RaidClient, token: str):
    """Start a client and handle connection"""
    try:
        await client.start(token)
    except Exception as e:
        print(f"{WHITE}│ [-] Connection failed: {e}{RESET}")

async def svr_raid(loop):
    # 1. tokens
    tokens_str = input(f"{WHITE}Comma-separated user tokens: {RESET}").strip()
    if not tokens_str:
        print(f"{WHITE}No tokens – aborting.{RESET}")
        return
    tokens = [t.strip() for t in tokens_str.split(",") if t.strip()]

    # Start all clients immediately
    clients: List[RaidClient] = []
    
    print(f"{WHITE}│ Starting {len(tokens)} clients...{RESET}")
    
    for tok in tokens:
        client = RaidClient(tok, "", None)
        clients.append(client)
        loop.create_task(start_client(client, tok))
        await asyncio.sleep(1)

    # Wait for clients to connect
    print(f"{WHITE}│ Waiting for clients to come online...{RESET}")
    await asyncio.sleep(5)

    online_clients = [c for c in clients if c.is_ready()]
    print(f"{WHITE}│ {len(online_clients)}/{len(clients)} clients online{RESET}")

    if not online_clients:
        print(f"{WHITE}│ No clients connected – aborting.{RESET}")
        for client in clients:
            await client.close()
        return

    # 2. ask if already in server
    while True:
        in_srv = input(f"{WHITE}Is every user in the server? (y/n): {RESET}").strip().lower()
        if in_srv in ("y", "n"):
            break
        print(f"{WHITE}Type y or n.{RESET}")

    guild_id = None
    if in_srv == "y":
        while True:
            gid = input(f"{WHITE}Server (guild) ID: {RESET}").strip()
            if gid.isdigit():
                guild_id = int(gid)
                break
            print(f"{WHITE}Must be a number.{RESET}")
    else:
        invite_code = input(f"{WHITE}discord.gg/ invite code: {RESET}").strip()
        print(f"{WHITE}│ Note: Selfbots cannot join servers via invite automatically{RESET}")
        print(f"{WHITE}│ Please join the server manually first, then use option 'y'{RESET}")
        return

    # 3. message to spam
    message = input(f"{WHITE}Message to send: {RESET}").strip()
    if not message:
        print(f"{WHITE}Empty message – aborting.{RESET}")
        for client in clients:
            await client.close()
        return

    # Update all clients
    for c in online_clients:
        c.target_guild_id = guild_id
        c.spam_msg = message

    print(f"{WHITE}Raid started – press Ctrl-C to stop.{RESET}")
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        pass
    finally:
        for client in clients:
            await client.close()

# ----------------------------------------------------------------------
# ── MAIN LOOP ────────────────────────────────────────────────────────
# ----------------------------------------------------------------------
async def console_loop():
    while True:
        print_menu()
        choice = get_choice()
        if choice == 1:
            await svr_raid(asyncio.get_event_loop())
            await asyncio.sleep(1)
        elif choice == 2:
            print(f"{WHITE}Exiting…{RESET}")
            break

# ----------------------------------------------------------------------
# ── ENTRY POINT ───────────────────────────────────────────────────────
# ----------------------------------------------------------------------
if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def _shutdown(*_):
        print(f"\n{WHITE}Shutting down…{RESET}")
        for task in asyncio.all_tasks(loop):
            task.cancel()
    signal.signal(signal.SIGINT, _shutdown)

    try:
        loop.run_until_complete(console_loop())
    finally:
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()
