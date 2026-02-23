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
# ÖPPNINGSMEDDELANDE (09:00)
# ==============================

async def post_opening():
    today = datetime.now(tz).date()

    if today.weekday() >= 5:
        print("Helg – ingen öppning")
        return

    ticker = yf.Ticker(TICKER)
    data = ticker.info

    last_close = data.get("regularMarketPreviousClose")

    days_left = get_days_until_report()
    next_report = min(
        [d for d in report_dates if d.date() >= today],
        default=None
    )

    embed = discord.Embed(
        title=f"{TICKER} • Öppning 🛎️",
        color=0x2F3136
    )

    embed.add_field(
        name="Senaste stängning",
        value=f"{last_close} SEK" if last_close else "N/A",
        inline=True
    )

    embed.add_field(
        name="Dagar till rapport",
        value=str(days_left),
        inline=True
    )

    embed.add_field(
        name="Nästa rapport",
        value=next_report.date() if next_report else "N/A",
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
# STÄNGNINGSMEDDELANDE (17:50)
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
    else:
        change_percent = None

    market_cap_msek = (
        f"{market_cap/1_000_000:,.1f} MSEK"
        if market_cap else "N/A"
    )

    volume_msek = (
        f"{volume*price/1_000_000:,.1f} MSEK"
        if volume and price else "N/A"
    )

    # ==============================
    # VWAP-BERÄKNING
    # ==============================

    try:
        df = ticker.history(period="1d", interval="1m")
        if not df.empty and df["Volume"].sum() != 0:
            vwap = (df["Close"] * df["Volume"]).sum() / df["Volume"].sum()
        else:
            vwap = None
    except Exception as e:
        print("VWAP-fel:", e)
        vwap = None

    embed = discord.Embed(
        title=f"{TICKER} • Stängning 💤",
        color=0x2F3136
    )

    embed.add_field(
        name="Kurs",
        value=f"{price} SEK ({change_percent:.2f}%)"
        if change_percent is not None else "N/A",
        inline=True
    )

    embed.add_field(
        name="Börsvärde",
        value=market_cap_msek,
        inline=True
    )

    embed.add_field(
        name="Dagens intervall",
        value=f"{day_low} – {day_high} SEK"
        if day_low and day_high else "N/A",
        inline=True
    )

    embed.add_field(
        name="Omsättning",
        value=f"{volume_msek} ({volume:,} st)"
        if volume and price else "N/A",
        inline=True
    )

    embed.add_field(
        name="VWAP",
        value=f"{vwap:.2f} SEK" if vwap else "N/A",
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
# SCHEMALÄGGNING (MED TIMEZONE FIX)
# ==============================

@tasks.loop(time=[dtime(hour=9, minute=25, tzinfo=tz)])
async def schedule_opening():
    await post_opening()

@tasks.loop(time=[dtime(hour=17, minute=50, tzinfo=tz)])
async def schedule_closing():
    await post_closing()

# ==============================
# TESTKOMMANDO
# ==============================

@bot.command()
async def test(ctx):
    await post_opening()
    await post_closing()

# ==============================
# ON READY
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