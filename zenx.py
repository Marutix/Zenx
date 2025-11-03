#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import os
import sys
import signal
from typing import List, Optional

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
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self.token = token
        self.spam_msg = message
        self.target_guild_id = guild_id
        self.running = True

    async def on_ready(self):
        print(f"{WHITE}│ [+] {self.user} online – activity set{RESET}")
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
                    if channel.permissions_for(guild.me).send_messages:
                        try:
                            await channel.send(self.spam_msg)
                        except (discord.Forbidden, discord.HTTPException):
                            pass  # ignore bans / rate-limits
                await asyncio.sleep(0.1)
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
            return len(MENU_ITEMS)  # treat Ctrl-C as exit

# ----------------------------------------------------------------------
# ── RAID FLOW ─────────────────────────────────────────────────────────
# ----------------------------------------------------------------------
async def start_client(client: RaidClient, token: str):
    """Start a client and handle connection"""
    try:
        await client.start(token)
    except Exception as e:
        print(f"{WHITE}│ [-] {client.user if client.user else 'Client'} failed: {e}{RESET}")

async def svr_raid(loop):
    # 1. tokens
    tokens_str = input(f"{WHITE}Comma-separated user tokens: {RESET}").strip()
    if not tokens_str:
        print(f"{WHITE}No tokens – aborting.{RESET}")
        return
    tokens = [t.strip() for t in tokens_str.split(",") if t.strip()]

    # Start all clients immediately
    clients: List[RaidClient] = []
    client_tasks = []
    
    print(f"{WHITE}│ Starting {len(tokens)} clients...{RESET}")
    
    for tok in tokens:
        # Create client with empty message for now
        client = RaidClient(tok, "", None)
        clients.append(client)
        # Start client in background
        task = loop.create_task(start_client(client, tok))
        client_tasks.append(task)
        await asyncio.sleep(0.5)  # Small delay between starting clients

    # Wait a moment for clients to connect
    print(f"{WHITE}│ Waiting for clients to come online...{RESET}")
    await asyncio.sleep(3)

    # Count how many clients successfully connected
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
        invite = f"https://discord.gg/{invite_code}"
        print(f"{WHITE}Joining via {invite} …{RESET}")

        # Join servers via invite
        for client in online_clients:
            try:
                await client.http.join_guild(invite_code)
                print(f"{WHITE}│ {client.user} joined via invite{RESET}")
            except Exception as e:
                print(f"{WHITE}│ {client.user} failed join: {e}{RESET}")
            await asyncio.sleep(0.5)

        # Fetch the guild id after joining (first client that succeeded)
        for client in online_clients:
            if client.guilds:
                guild_id = client.guilds[0].id
                print(f"{WHITE}│ Detected guild id: {guild_id}{RESET}")
                break

    # 3. message to spam
    message = input(f"{WHITE}Message to send: {RESET}").strip()
    if not message:
        print(f"{WHITE}Empty message – aborting.{RESET}")
        for client in clients:
            await client.close()
        return

    # Update all clients with final guild id and message
    for c in online_clients:
        c.target_guild_id = guild_id
        c.spam_msg = message

    print(f"{WHITE}Raid started – press Ctrl-C to stop.{RESET}")
    # keep the event loop alive
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        pass
    finally:
        # Cleanup
        for client in clients:
            await client.close()

# ----------------------------------------------------------------------
# ── MAIN LOOP ────────────────────────────────────────────────────────
# ----------------------------------------------------------------------
async def console_loop():
    while True:
        print_menu()
        choice = get_choice()
        if choice == 1:                     # Svr Raid
            await svr_raid(asyncio.get_event_loop())
            await asyncio.sleep(1)
        elif choice == 2:                   # exit
            print(f"{WHITE}Exiting…{RESET}")
            break

# ----------------------------------------------------------------------
# ── ENTRY POINT ───────────────────────────────────────────────────────
# ----------------------------------------------------------------------
if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Graceful Ctrl-C
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
