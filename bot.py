import discord
from discord.ext import commands, tasks
import yfinance as yf
from datetime import datetime, time as dtime
import pytz
import os

# ==============================
# INSTÄLLNINGAR
# ==============================

TOKEN = os.getenv("DISCORD_TOKEN")    # Din token hämtas från miljövariabel
CHANNEL_ID = 1474470635198484716      # Discord-kanal-ID där meddelandet ska skickas
TICKER = "HAMLET-B.ST"                # Hamlet Biopharma ticker

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
# ÖPPNING / STÄNGNING
# ==============================

async def post_opening():
    today = datetime.now(tz).date()
    if today.weekday() >= 5:  # Hoppa över helger
        print("Helg – ingen öppning")
        return

    ticker = yf.Ticker(TICKER)
    data = ticker.info

    last_close = data.get("regularMarketPreviousClose", "N/A")

    days_left = get_days_until_report()
    next_report = min([d for d in report_dates if d.date() >= today], default="N/A")

    embed = discord.Embed(
        title=f"{TICKER} • **Öppning 🛎️**",
        color=0xFFA500
    )
    embed.add_field(name="Senaste stängning", value=f"{last_close} SEK" if last_close != "N/A" else "N/A", inline=True)
    embed.add_field(name="Dagar till rapport", value=str(days_left), inline=True)
    embed.add_field(name="Nästa rapport", value=next_report if next_report != "N/A" else "N/A", inline=True)
    embed.add_field(name="Volatilitet", value="N/A", inline=True)
    embed.add_field(name="Postad", value=datetime.now(tz).strftime("%Y-%m-%d %H:%M %Z"), inline=False)

    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        await channel.send(embed=embed)

async def post_closing():
    today = datetime.now(tz).date()
    if today.weekday() >= 5:  # Hoppa över helger
        print("Helg – ingen stängning")
        return

    ticker = yf.Ticker(TICKER)
    data = ticker.info

    price = data.get("regularMarketPrice", "N/A")
    prev_close = data.get("regularMarketPreviousClose", "N/A")
    volume = data.get("volume", "N/A")
    market_cap = data.get("marketCap", "N/A")
    day_low = data.get("dayLow", "N/A")
    day_high = data.get("dayHigh", "N/A")

    if price != "N/A" and prev_close != "N/A":
        change_percent = ((price - prev_close) / prev_close) * 100
    else:
        change_percent = 0

    market_cap_msek = f"{market_cap/1_000_000:,.1f} MSEK" if market_cap != "N/A" else "N/A"
    volume_msek = f"{volume*price/1_000_000:,.1f} MSEK" if price != "N/A" and volume != "N/A" else "N/A"

    # ==============================
    # VWAP-BERÄKNING
    # ==============================
    try:
        df = ticker.history(period="1d", interval="1m")
        if not df.empty:
            vwap = (df["Close"] * df["Volume"]).sum() / df["Volume"].sum()
        else:
            vwap = None
    except Exception as e:
        print("Fel vid VWAP-beräkning:", e)
        vwap = None

    embed = discord.Embed(
        title=f"{TICKER} • **Stängning 💤**",
        color=0xFFA500
    )
    embed.add_field(name="Kurs", value=f"{price} SEK ({change_percent:.2f}%)", inline=True)
    embed.add_field(name="Börsvärde", value=market_cap_msek, inline=True)
    embed.add_field(name="Dagens intervall", value=f"{day_low} – {day_high} SEK", inline=True)
    embed.add_field(name="Omsättning", value=f"{volume_msek} ({volume:,} st)" if volume != "N/A" else "N/A", inline=True)
    embed.add_field(name="VWAP", value=f"{vwap:.2f} SEK" if vwap else "N/A", inline=True)
    embed.add_field(name="Postad", value=datetime.now(tz).strftime("%Y-%m-%d %H:%M %Z"), inline=False)

    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        await channel.send(embed=embed)

# ==============================
# SCHEMALÄGGNING
# ==============================

@tasks.loop(time=[dtime(hour=9, minute=0)])
async def schedule_opening():
    await post_opening()

@tasks.loop(time=[dtime(hour=17, minute=50)])
async def schedule_closing():
    await post_closing()

# ==============================
# ON_READY
# ==============================

@bot.event
async def on_ready():
    print(f"Inloggad som {bot.user}")
    await post_opening()   # Skicka direkt vid start
    await post_closing()   # Skicka direkt vid start
    schedule_opening.start()
    schedule_closing.start()

# ==============================
# STARTA BOTEN
# ==============================

bot.run(TOKEN)