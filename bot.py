import discord
from discord.ext import commands, tasks
import yfinance as yf
from datetime import datetime, time as dtime
import pytz
import os

# ==============================
# INSTÄLLNINGAR
# ==============================

TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = 1474470635198484716
TICKER = "HAMLET-B.ST"

tz = pytz.timezone("Europe/Stockholm")

report_dates = [
    datetime(2026, 5, 22),
    datetime(2026, 8, 28),
    datetime(2026, 11, 13)
]

# ==============================
# BOT SETUP
# ==============================

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# ==============================
# HJÄLPFUNKTIONER
# ==============================

def get_days_until_report():
    today = datetime.now(tz).date()
    future_reports = [d for d in report_dates if d.date() >= today]
    if future_reports:
        return (future_reports[0].date() - today).days
    return "Ingen kommande rapport"

# ==============================
# ÖPPNING
# ==============================

async def post_opening():
    today = datetime.now(tz).date()

    if today.weekday() >= 5:
        print("Helg – ingen öppning")
        return

    ticker = yf.Ticker(TICKER)
    data = ticker.info

    open_price = data.get("regularMarketOpen")
    prev_close = data.get("regularMarketPreviousClose")

    days_left = get_days_until_report()
    future_reports = [d for d in report_dates if d.date() >= today]
    next_report = future_reports[0].strftime("%Y-%m-%d") if future_reports else "N/A"

    embed = discord.Embed(
        title=f"{TICKER} • Öppning 🛎️",
        color=0xFFA500
    )

    embed.add_field(
        name="Öppningskurs",
        value=f"{open_price} SEK" if open_price else "N/A",
        inline=True
    )

    embed.add_field(
        name="Föreg. stängning",
        value=f"{prev_close} SEK" if prev_close else "N/A",
        inline=True
    )

    embed.add_field(
        name="Dagar till rapport",
        value=str(days_left),
        inline=True
    )

    embed.add_field(
        name="Nästa rapport",
        value=next_report,
        inline=True
    )

    embed.add_field(
        name="Postad",
        value=datetime.now(tz).strftime("%Y-%m-%d %H:%M %Z"),
        inline=False
    )

    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        await channel.send(embed=embed)

# ==============================
# STÄNGNING
# ==============================

async def post_closing():
    today = datetime.now(tz).date()

    if today.weekday() >= 5:
        print("Helg – ingen stängning")
        return

    ticker = yf.Ticker(TICKER)
    data = ticker.info

    price = data.get("regularMarketPrice")
    prev_close = data.get("regularMarketPreviousClose")
    volume = data.get("volume")
    market_cap = data.get("marketCap")
    day_low = data.get("dayLow")
    day_high = data.get("dayHigh")

    if price and prev_close:
        change_percent = ((price - prev_close) / prev_close) * 100
        color = 0x00FF00 if change_percent >= 0 else 0xFF0000
    else:
        change_percent = 0
        color = 0xFFA500

    market_cap_msek = f"{market_cap/1_000_000:,.1f} MSEK" if market_cap else "N/A"
    volume_msek = f"{(volume * price)/1_000_000:,.1f} MSEK" if volume and price else "N/A"

    embed = discord.Embed(
        title=f"{TICKER} • Stängning 💤",
        color=color
    )

    embed.add_field(
        name="Kurs",
        value=f"{price} SEK ({change_percent:.2f}%)" if price else "N/A",
        inline=True
    )

    embed.add_field(
        name="Börsvärde",
        value=market_cap_msek,
        inline=True
    )

    embed.add_field(
        name="Dagens intervall",
        value=f"{day_low} – {day_high} SEK" if day_low and day_high else "N/A",
        inline=True
    )

    embed.add_field(
        name="Omsättning",
        value=f"{volume_msek} ({volume:,} st)" if volume and price else "N/A",
        inline=True
    )

    embed.add_field(
        name="Postad",
        value=datetime.now(tz).strftime("%Y-%m-%d %H:%M %Z"),
        inline=False
    )

    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        await channel.send(embed=embed)

# ==============================
# SCHEMALÄGGNING (SVENSK TID)
# ==============================

@tasks.loop(time=[dtime(hour=9, minute=45, tzinfo=tz)])
async def schedule_opening():
    await post_opening()

@tasks.loop(time=[dtime(hour=17, minute=45, tzinfo=tz)])
async def schedule_closing():
    await post_closing()

# ==============================
# START
# ==============================

@bot.event
async def on_ready():
    print(f"Inloggad som {bot.user}")
    schedule_opening.start()
    schedule_closing.start()

bot.run(TOKEN)