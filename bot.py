import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
import os
import asyncio
import requests
import re
import time
import random
import aiohttp

# ────────────────────────────  Setup  ────────────────────────────
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

bot = commands.Bot(
    command_prefix='!',
    intents=discord.Intents.all(),
    help_command=None
)

# per‑feature storage
daily_trivia_scores = {}
voice_channel_alerts_subscribers: set[int] = set()
countdown_task: asyncio.Task | None = None

# ───────────────────────  Small utilities  ───────────────────────

BAR_LENGTH = 20          # number of ▮ / ▯ characters in the bar


def build_progress_bar(elapsed: int, total: int) -> str:
    """Return a unicode bar such as ▮▮▮▯▯… for the given progress."""
    filled = round(BAR_LENGTH * elapsed / total) if total else BAR_LENGTH
    return '▮' * filled + '▯' * (BAR_LENGTH - filled)


def format_time(seconds: int) -> str:
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f'{hours}h {minutes}m {seconds}s'
    return f'{minutes}m {seconds}s'


def parse_time(time_str: str) -> int | None:
    """Convert strings like 20s / 5m / 1h to seconds; returns None on bad input."""
    match = re.fullmatch(r'(\d+)([smhd])?', time_str.strip().lower())
    if not match:
        return None

    amount, unit = int(match.group(1)), match.group(2) or 's'
    return amount * {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}[unit]


# ────────────────────────────  Events  ────────────────────────────
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')


@bot.event
async def on_voice_state_update(member, before, after):
    # DM all subscribers when someone joins a voice channel
    if before.channel is None and after.channel is not None:
        for uid in voice_channel_alerts_subscribers:
            try:
                user = await bot.fetch_user(uid)
                await user.send(f'{member.name} joined **{after.channel.name}**.')
            except Exception as e:
                print(f'Failed to DM {uid}: {e}')


# ────────────────────────────  Commands  ────────────────────────────
@bot.command()
async def help(ctx, *, command_name=None):
    """Custom help command."""
    if command_name is None:
        embed = discord.Embed(
            title="Help",
            description="Use `!help <command>` for details.",
            color=0x00ff00
        )
        embed.add_field(name="poll", value="Create a 👍 / 👎 poll.", inline=False)
        embed.add_field(name="remindme", value="Set a reminder. `!remindme 5m Take a break`", inline=False)
        embed.add_field(name="count", value="Countdown timer. `!count 30s`", inline=False)
        embed.add_field(name="predict", value="Guess nationality by name. `!predict Maria`", inline=False)
        embed.add_field(name="emojistats", value="Show top emojis in channel.", inline=False)
        embed.add_field(name="dailytrivia", value="One‑question trivia challenge.", inline=False)
        embed.add_field(name="anime", value="Quick anime lookup via Jikan.", inline=False)
        embed.add_field(name="voicealerts", value="DM alerts on VC join. `!voicealerts subscribe`", inline=False)
        await ctx.send(embed=embed)
        return

    command = bot.get_command(command_name)
    if command:
        await ctx.send(embed=discord.Embed(
            title=f'Help: {command_name}',
            description=command.help or 'No description.',
            color=0x00ff00))
    else:
        await ctx.send("Command not found.")


# ───────────  Polls  ───────────
@bot.command()
async def poll(ctx, *, question: str):
    """Create a poll with 👍 / 👎 reactions."""
    embed = discord.Embed(title="Poll", description=question, color=0x00ff00)
    embed.set_footer(text="React with 👍 or 👎")
    msg = await ctx.send(embed=embed)
    await msg.add_reaction('👍')
    await msg.add_reaction('👎')


# ───────────  Reminders  ───────────
@bot.command()
async def remindme(ctx, duration: str, *, reminder: str | None = None):
    """Set a reminder: `!remindme 10m stretch`"""
    if reminder is None:
        await ctx.send("Usage: `!remindme <time> <message>`")
        return

    seconds = parse_time(duration)
    if seconds is None:
        await ctx.send("Invalid time – use formats like 30s, 5m, 1h.")
        return

    await ctx.send(f'⏰ I\'ll remind you in {duration}.')
    await asyncio.sleep(seconds)
    await ctx.send(f'{ctx.author.mention} Reminder: {reminder}')


# ───────────  Countdown  ───────────
@bot.command(name='count')
async def count(ctx, duration: str):
    """Start a live countdown: `!count 45s` or `!count 2m`"""
    global countdown_task

    # cancel any existing timer
    if countdown_task and not countdown_task.done():
        countdown_task.cancel()

    seconds = parse_time(duration)
    if seconds is None or seconds == 0:
        await ctx.send("Invalid time – use 30s, 5m, 1h, etc.")
        return

    countdown_task = bot.loop.create_task(run_countdown(ctx, seconds))


async def run_countdown(ctx, total_seconds: int):
    """Edits one message every second with a two‑line progress display."""
    try:
        msg = await ctx.send("Preparing countdown…")
        start = time.monotonic()

        while True:
            elapsed   = int(time.monotonic() - start)
            remaining = max(total_seconds - elapsed, 0)

            bar = build_progress_bar(elapsed, total_seconds)
            content = (
                f"Countdown: {bar}\n"
                f"{format_time(remaining)}{' – finished!' if remaining == 0 else ' remaining'}"
            )
            await msg.edit(content=content)

            if remaining == 0:
                break
            await asyncio.sleep(1)

        await ctx.send(f'{ctx.author.mention} Countdown finished!')

    except asyncio.CancelledError:
        # Clean cancellation if a new !count starts
        await msg.edit(content="⏹️ Countdown cancelled.")
        raise


# ───────────  Emoji statistics  ───────────
@bot.command()
async def emojistats(ctx):
    """Show the most used custom emojis in the last 1 000 messages."""
    counts = {}
    async for m in ctx.channel.history(limit=1000):
        for e in m.guild.emojis:
            if str(e) in m.content:
                counts[e] = counts.get(e, 0) + 1

    if not counts:
        await ctx.send("No emoji usage data found.")
        return

    info = '\n'.join(f'{e} : {c}' for e, c in sorted(counts.items(), key=lambda x: x[1], reverse=True))
    await ctx.send(f'Most used emojis:\n{info}')


# ───────────  Daily trivia  ───────────
@bot.command()
async def dailytrivia(ctx):
    """Participate in a single‑question trivia challenge (OpenTDB)."""
    async with aiohttp.ClientSession() as session:
        async with session.get('https://opentdb.com/api.php?amount=1&type=multiple') as resp:
            data = await resp.json()

    q = data['results'][0]
    question = q['question']
    correct  = q['correct_answer']
    options  = q['incorrect_answers'] + [correct]
    random.shuffle(options)

    embed = discord.Embed(title="Daily Trivia!", description=question, color=0x00ff00)
    for i, ans in enumerate(options, 1):
        embed.add_field(name=f'Option {i}', value=ans, inline=False)

    await ctx.send(embed=embed)

    def check(m): return m.author == ctx.author and m.channel == ctx.channel

    try:
        reply = await bot.wait_for('message', check=check, timeout=30)
    except asyncio.TimeoutError:
        await ctx.send(f'Time\'s up! The correct answer was **{correct}**.')
        return

    if reply.content.lower() == correct.lower():
        daily_trivia_scores[ctx.author.id] = daily_trivia_scores.get(ctx.author.id, 0) + 1
        await ctx.send(f'✅ Correct! Score today: {daily_trivia_scores[ctx.author.id]}')
    else:
        await ctx.send(f'❌ Sorry, the correct answer was **{correct}**.')


# ───────────  Anime search  ───────────
@bot.command()
async def anime(ctx, *, title: str):
    """Quick anime lookup via Jikan API."""
    r = requests.get(f'https://api.jikan.moe/v4/anime?q={title}&limit=1').json()
    if not r['data']:
        await ctx.send("No results.")
        return

    d = r['data'][0]
    embed = discord.Embed(
        title=d['title'], url=d['url'], description=d['synopsis'][:1000] + '…',
        color=0x00ff00
    )
    embed.set_thumbnail(url=d['images']['jpg']['image_url'])
    embed.add_field(name='Episodes', value=d['episodes'])
    embed.add_field(name='Score', value=d['score'])
    embed.add_field(name='Aired', value=f"{d['aired']['from'][:10]} → {d['aired']['to'][:10]}")
    await ctx.send(embed=embed)


# ───────────  Voice‑channel join alerts  ───────────
@bot.command()
async def voicealerts(ctx, action: str | None = None):
    """`!voicealerts subscribe` or `!voicealerts unsubscribe`"""
    if action == 'subscribe':
        if ctx.author.id in voice_channel_alerts_subscribers:
            await ctx.send("You’re already subscribed.")
        else:
            voice_channel_alerts_subscribers.add(ctx.author.id)
            await ctx.send("🔔 Subscribed to voice‑channel join alerts.")
    elif action == 'unsubscribe':
        if ctx.author.id in voice_channel_alerts_subscribers:
            voice_channel_alerts_subscribers.remove(ctx.author.id)
            await ctx.send("❎ Unsubscribed from voice‑channel join alerts.")
        else:
            await ctx.send("You’re not subscribed.")
    else:
        await ctx.send("Usage: `!voicealerts <subscribe|unsubscribe>`")


# ────────────────────────────  Run  ────────────────────────────
bot.run(TOKEN)
