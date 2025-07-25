import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from flask import Flask
from threading import Thread

# === Flask Web Server to Keep Bot Alive ===
app = Flask('')

@app.route('/')
def home():
    return "✅ Maharlika Bot is alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    Thread(target=run).start()

# === Bot Setup ===
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# === Data Files ===
XP_FILE = "xp_data.json"
RANK_FILE = "rank_roles.json"

if not os.path.exists(XP_FILE):
    with open(XP_FILE, 'w') as f:
        json.dump({}, f)

if not os.path.exists(RANK_FILE):
    with open(RANK_FILE, 'w') as f:
        json.dump({}, f)

def load_xp():
    with open(XP_FILE, 'r') as f:
        return json.load(f)

def save_xp(data):
    with open(XP_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def load_ranks():
    with open(RANK_FILE, 'r') as f:
        return json.load(f)

def save_ranks(data):
    with open(RANK_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def calculate_level(xp):
    level = 0
    required = 100
    while xp >= required:
        level += 1
        xp -= required
        required *= 2
    return level

# === On Bot Ready ===
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ Bot is ready. Logged in as {bot.user}.")

# === XP System ===
@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return

    data = load_xp()
    user_id = str(message.author.id)
    if user_id not in data:
        data[user_id] = {"xp": 0}

    data[user_id]["xp"] += 10
    old_level = calculate_level(data[user_id]["xp"] - 10)
    new_level = calculate_level(data[user_id]["xp"])

    if new_level > old_level:
        if isinstance(message.channel, discord.TextChannel):
            await message.channel.send(f"🎉 {message.author.mention} reached level {new_level}!")

        rank_data = load_ranks()
        guild_id = str(message.guild.id)
        if guild_id in rank_data:
            level_roles = rank_data[guild_id]
            roles_given = []
            roles_removed = []

            for role_id, required_level in level_roles.items():
                role = message.guild.get_role(int(role_id))
                if not role:
                    continue

                # Assign role if level met
                if new_level >= required_level and role not in message.author.roles:
                    await message.author.add_roles(role)
                    roles_given.append(role.name)

                # Remove role if no longer eligible (demotion)
                elif new_level < required_level and role in message.author.roles:
                    await message.author.remove_roles(role)
                    roles_removed.append(role.name)

            # Optional: Send log message in channel
            if roles_given or roles_removed:
                msg = ""
                if roles_given:
                    msg += f"🆕 Given roles: {', '.join(roles_given)}\n"
                if roles_removed:
                    msg += f"❌ Removed roles: {', '.join(roles_removed)}"
                if isinstance(message.channel, discord.TextChannel):
                    await message.channel.send(msg)

    save_xp(data)
    await bot.process_commands(message)

# === /rank Command ===
@bot.tree.command(name="rank", description="Show your current level and XP")
async def rank(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    data = load_xp()
    xp = data.get(user_id, {}).get("xp", 0)
    level = calculate_level(xp)
    await interaction.response.send_message(f"🧪 You are level {level} with {xp} XP.")

# === /leaderboard Command ===
@bot.tree.command(name="leaderboard", description="Show the top 5 XP holders")
async def leaderboard(interaction: discord.Interaction):
    data = load_xp()
    top = sorted(data.items(), key=lambda x: x[1]['xp'], reverse=True)[:5]

    msg = "🏆 **Top 5 XP Leaders**:\n"
    for i, (user_id, stats) in enumerate(top, start=1):
        user = await bot.fetch_user(int(user_id))
        msg += f"{i}. {user.name} - {stats['xp']} XP\n"

    await interaction.response.send_message(msg)

# === /addrr Command ===
@bot.tree.command(name="addrr", description="Set a role to be given at a specific level")
@app_commands.describe(role="Role to assign", level="Level to assign it at")
async def addrr(interaction: discord.Interaction, role: discord.Role, level: int):
    if not interaction.guild:
        await interaction.response.send_message("❌ This must be used in a server.", ephemeral=True)
        return

    member = interaction.guild.get_member(interaction.user.id)
    if not member or not member.guild_permissions.manage_roles:
        await interaction.response.send_message("❌ You need Manage Roles permission.", ephemeral=True)
        return

    data = load_ranks()
    guild_id = str(interaction.guild.id)
    if guild_id not in data:
        data[guild_id] = {}

    data[guild_id][str(role.id)] = level
    save_ranks(data)

    await interaction.response.send_message(f"✅ {role.mention} will now be awarded at level {level}.")

# === Keep Alive and Run ===
keep_alive()

# Make sure token is not None
token = os.getenv("DISCORD_BOT_TOKEN")
if not token:
    raise ValueError("❌ DISCORD_BOT_TOKEN is not set in environment variables.")

bot.run(token)