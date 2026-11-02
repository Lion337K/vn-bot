import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import os
import json
from datetime import datetime, timezone

# ───────────────────────────────────────────────
#  BOT YANITLARI VE MESAJLARI (Buradan kolayca değiştirebilirsin)
# ───────────────────────────────────────────────

RESPONSES = {
    "welcome_message": "{member} aramıza katıldı fln filan 😒",
    "bump_message": "buuuuump",
    "setwelcome_success": "✨ Karşılama mesajı güncellendi:\n> {yeni_mesaj}",
    "setbump_success": "⏳ Bump hatırlatma mesajı güncellendi:\n> {yeni_mesaj}",
    "sendmsg_not_found": "🌌 Böyle bir kanal bulunamadı.",
    "sendmsg_success": "🦋 Mesaj başarıyla gönderildi.",
    "sendmsg_error": "❌ Hata oluştu: {error}",
    "err_missing_permissions": "yetkin yok kullanamazsin.",
    "err_cooldown": "yavasla biraz. {retry_after} saniye sonra bidaha dene.",
    "err_generic": "hata olustu: {error}"
}

# ───────────────────────────────────────────────
#  AYARLAR VE ID'LER
# ───────────────────────────────────────────────

TOKEN = os.getenv("DISCORD_TOKEN")

GUILD_ID             = 1480303038408425764
WELCOME_CHANNEL_ID   = 1480314604713414757
BUMP_CHANNEL_ID      = 1517972647126761624
IMAGE_LOG_CHANNEL_ID = 1480317488456536166

BUMP_BOT_ID          = 302050872383242240 
CONFIG_FILE          = "config.json"

# ───────────────────────────────────────────────
#  DİNAMİK MESAJ SİSTEMİ (JSON KONTROLÜ)
# ───────────────────────────────────────────────

DEFAULT_CONFIG = {
    "WELCOME_MESSAGE": RESPONSES["welcome_message"],
    "BUMP_MESSAGE": RESPONSES["bump_message"]
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Config dosyası okunamadı: {e}")
    return DEFAULT_CONFIG.copy()

def save_config(config_data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config_data, f, ensure_ascii=False, indent=4)

config = load_config()

# ───────────────────────────────────────────────
#  BOT SETUP
# ───────────────────────────────────────────────

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

bump_task = None

# ───────────────────────────────────────────────
#  BUMP ZAMANLAYICI VE GEÇMİŞ KONTROLÜ
# ───────────────────────────────────────────────

async def schedule_bump_in(seconds: float):
    global bump_task
    try:
        await asyncio.sleep(seconds)
        channel = bot.get_channel(BUMP_CHANNEL_ID)
        if channel:
            await channel.send(config["BUMP_MESSAGE"])
            print("📢 Bump hatırlatma mesajı gönderildi.")
    except asyncio.CancelledError:
        pass

async def check_last_bump_and_schedule():
    global bump_task
    await asyncio.sleep(3) 
    
    channel = bot.get_channel(BUMP_CHANNEL_ID)
    if not channel:
        return

    try:
        async for message in channel.history(limit=50):
            # Doğrudan Disboard botunun attığı son mesaja bakıyoruz
            if message.author.id == BUMP_BOT_ID:
                now = datetime.now(timezone.utc)
                elapsed = (now - message.created_at).total_seconds()
                two_hours = 2 * 60 * 60  
                
                if bump_task and not bump_task.done():
                    bump_task.cancel()

                if elapsed >= two_hours:
                    await channel.send(config["BUMP_MESSAGE"])
                else:
                    remaining = two_hours - elapsed
                    bump_task = asyncio.ensure_future(schedule_bump_in(remaining))
                return
    except Exception as e:
        print(f"⚠️ Geçmiş kontrolü hatası: {e}")

# ───────────────────────────────────────────────
#  EVENTS (OLAYLAR)
# ───────────────────────────────────────────────

@bot.event
async def on_ready():
    print(f"✅ Giriş yapıldı: {bot.user}")
    
    try:
        guild = discord.Object(id=GUILD_ID)
        bot.tree.clear_commands(guild=guild)
        bot.tree.copy_global_to(guild=guild)
        await bot.tree.sync(guild=guild)
        print("✅ Komutlar senkronize edildi.")
    except Exception as e:
        print(f"⚠️ Senkronizasyon hatası: {e}")

    asyncio.ensure_future(check_last_bump_and_schedule())

@bot.event
async def on_member_join(member: discord.Member):
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if channel:
        msg = config["WELCOME_MESSAGE"].replace("{member}", member.mention)
        await channel.send(msg)

@bot.event
async def on_message(message: discord.Message):
    global bump_task
    if message.author == bot.user:
        return

    # Medya Log Sistemi
    log_channel = bot.get_channel(IMAGE_LOG_CHANNEL_ID)
    if log_channel and message.channel.id != IMAGE_LOG_CHANNEL_ID and not message.author.bot:
        if message.attachments:
            for attachment in message.attachments:
                await log_channel.send(f"📎 **{message.author.display_name}**", file=await attachment.to_file())

    # Disboard Bump Algılama (Doğrudan Disboard botundan gelen mesaj baz alınır)
    if message.channel.id == BUMP_CHANNEL_ID and message.author.id == BUMP_BOT_ID:
        if bump_task and not bump_task.done():
            bump_task.cancel() 
        bump_task = asyncio.ensure_future(schedule_bump_in(2 * 60 * 60))

    await bot.process_commands(message)

# ───────────────────────────────────────────────
#  SLASH COMMANDS (YÖNETİCİ KOMUTLARI)
# ───────────────────────────────────────────────

@bot.tree.command(name="setwelcome", description="Hoş geldin mesajını değiştirir. ({member} etiketi kullanabilirsiniz)")
@app_commands.checks.has_permissions(administrator=True)
async def set_welcome(interaction: discord.Interaction, yeni_mesaj: str):
    config["WELCOME_MESSAGE"] = yeni_mesaj
    save_config(config)
    await interaction.response.send_message(RESPONSES["setwelcome_success"].format(yeni_mesaj=yeni_mesaj), ephemeral=True)

@bot.tree.command(name="setbump", description="Bump hatırlatma mesajını değiştirir.")
@app_commands.checks.has_permissions(administrator=True)
async def set_bump(interaction: discord.Interaction, yeni_mesaj: str):
    config["BUMP_MESSAGE"] = yeni_mesaj
    save_config(config)
    await interaction.response.send_message(RESPONSES["setbump_success"].format(yeni_mesaj=yeni_mesaj), ephemeral=True)

@bot.tree.command(name="testwelcome", description="Hoş geldin mesajını test et.")
@app_commands.checks.has_permissions(administrator=True)
async def test_welcome(interaction: discord.Interaction):
    msg = config["WELCOME_MESSAGE"].replace("{member}", interaction.user.mention)
    await interaction.response.send_message(msg, ephemeral=False)

@bot.tree.command(name="sendmsg", description="Belirli bir kanala mesaj gönder.")
@app_commands.checks.has_permissions(administrator=True)
async def send_msg(interaction: discord.Interaction, channel_id: str, message: str):
    try:
        target_channel = bot.get_channel(int(channel_id))
        if not target_channel:
            await interaction.response.send_message(RESPONSES["sendmsg_not_found"], ephemeral=True)
            return
        await target_channel.send(message)
        await interaction.response.send_message(RESPONSES["sendmsg_success"], ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(RESPONSES["sendmsg_error"].format(error=e), ephemeral=True)

# ───────────────────────────────────────────────
#  HATA YAKALAYICI
# ───────────────────────────────────────────────

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message(RESPONSES["err_missing_permissions"], ephemeral=True)
    elif isinstance(error, app_commands.CommandOnCooldown):
        msg = RESPONSES["err_cooldown"].format(retry_after=round(error.retry_after, 1))
        await interaction.response.send_message(msg, ephemeral=True)
    else:
        await interaction.response.send_message(RESPONSES["err_generic"].format(error=error), ephemeral=True)

if __name__ == "__main__":
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("HATA: DISCORD_TOKEN bulunamadı!")
