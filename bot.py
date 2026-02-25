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
# BOT SETUP (inga privileged intents)
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
# ÖPPNING 09:00
# ==============================

async def post_opening():
    today = datetime.now(tz).date()
    if today.weekday() >= 5:
        return

    ticker = yf.Ticker(TICKER)

    # HÄR ÄR ENDA ÄNDRINGEN (history istället för info)
    df = ticker.history(period="5d", interval="1d")
    if not df.empty:
        last_close = df["Close"].iloc[-1]
    else:
        last_close = None

    days_left = get_days_until_report()
    next_report = min([d for d in report_dates if d.date() >= today], default=None)

    embed = discord.Embed(
        title=f"{TICKER} • Öppning 🛎️",
        color=0xF5A623
    )

    embed.add_field(
        name="Senaste stängning",
        value=f"{last_close:.2f} SEK" if last_close else "N/A",
        inline=False
    )

    embed.add_field(
        name="Dagar till rapport",
        value=str(days_left),
        inline=False
    )

    embed.add_field(
        name="Nästa rapport",
        value=next_report.strftime("%Y-%m-%d") if next_report else "N/A",
        inline=False
    )

    embed.add_field(
        name="Postad",
        value=datetime.now(tz).strftime("%Y-%m-%d %H:%M CET"),
        inline=False
    )

    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        await channel.send(embed=embed)

# ==============================
# STÄNGNING 17:50
# ==============================

async def post_closing():
    today = datetime.now(tz).date()
    if today.weekday() >= 5:
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
    else:
        change_percent = 0

    if change_percent > 0:
        embed_color = 0x2ECC71
    elif change_percent < 0:
        embed_color = 0xE74C3C
    else:
        embed_color = 0xF5A623

    market_cap_msek = f"{market_cap/1_000_000:,.1f} MSEK" if market_cap else "N/A"

    volume_msek = f"{volume*price/1_000_000:,.1f} MSEK" if price and volume else "N/A"
    volume_formatted = f"{volume:,}".replace(",", " ") if volume else "N/A"

    try:
        df = ticker.history(period="1d", interval="1m")
        if not df.empty and df["Volume"].sum() != 0:
            vwap = (df["Close"] * df["Volume"]).sum() / df["Volume"].sum()
        else:
            vwap = None
    except:
        vwap = None

    embed = discord.Embed(
        title=f"{TICKER} • Stängning 💤",
        color=embed_color
    )

    embed.add_field(
        name="Kurs",
        value=f"{price:.2f} SEK ({change_percent:.2f}%)" if price else "N/A",
        inline=False
    )

    embed.add_field(
        name="Börsvärde",
        value=market_cap_msek,
        inline=False
    )

    embed.add_field(
        name="Dagens intervall",
        value=f"{day_low:.2f} – {day_high:.2f} SEK" if day_low and day_high else "N/A",
        inline=False
    )

    embed.add_field(
        name="Omsättning",
        value=f"{volume_msek} ({volume_formatted} st)" if volume else "N/A",
        inline=False
    )

    embed.add_field(
        name="VWAP",
        value=f"{vwap:.2f} SEK" if vwap else "N/A",
        inline=False
    )

    embed.add_field(
        name="Postad",
        value=datetime.now(tz).strftime("%Y-%m-%d %H:%M CET"),
        inline=False
    )

    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        await channel.send(embed=embed)

# ==============================
# SCHEMALÄGGNING
# ==============================

@tasks.loop(time=[dtime(hour=8, minute=53, tzinfo=tz)])
async def schedule_opening():
    await post_opening()

@tasks.loop(time=[dtime(hour=17, minute=45, tzinfo=tz)])
async def schedule_closing():
    await post_closing()

# ==============================
# ON_READY
# ==============================

@bot.event
async def on_ready():
    print(f"Inloggad som {bot.user}")
    schedule_opening.start()
    schedule_closing.start()

# ==============================
# STARTA BOTEN
# ==============================

bot.run(TOKEN)