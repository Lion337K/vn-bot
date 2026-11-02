import discord
from discord.ext import commands, tasks
from discord import app_commands
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

# ───────────────────────────────────────────────
#  BUMP KONTROL DÖNGÜSÜ (HER 1 DAKİKADA BİR)
# ───────────────────────────────────────────────

@tasks.loop(minutes=1)
async def bump_check_loop():
    channel = bot.get_channel(BUMP_CHANNEL_ID)
    if not channel:
        return

    try:
        messages = [msg async for msg in channel.history(limit=30)]
        
        # 1. En son Disboard mesajını bul
        last_disboard_msg = None
        for msg in messages:
            if msg.author.id == BUMP_BOT_ID:
                last_disboard_msg = msg
                break
        
        if not last_disboard_msg:
            return # Kanalda hiç Disboard mesajı yok

        # 2. Son Disboard mesajından sonra bizim botumuz hatırlatma atmış mı kontrol et
        reminder_sent_after = False
        for msg in messages:
            if msg.id == last_disboard_msg.id:
                break # Disboard mesajına ulaştıysak geçmişe gitmeyi bırak
            if msg.author.id == bot.user.id:
                reminder_sent_after = True
                break

        # Eğer bu bump için zaten hatırlatma atıldıysa tekrar atma
        if reminder_sent_after:
            return

        # 3. Süreyi hesapla
        now = datetime.now(timezone.utc)
        elapsed = (now - last_disboard_msg.created_at).total_seconds()
        two_hours = 2 * 60 * 60  

        # 4. 2 saat dolmuşsa (veya bot kapalı kaldığı için süresi geçmişse) hemen yapıştır
        if elapsed >= two_hours:
            await channel.send(config["BUMP_MESSAGE"])
            print("📢 2 saatlik süre doldu (veya geçmişti), bump hatırlatması gönderildi.")

    except Exception as e:
        print(f"⚠️ Bump döngüsü hatası: {e}")

@bump_check_loop.before_loop
async def before_bump_check():
    await bot.wait_until_ready()

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

    # Periyodik bump kontrol döngüsünü başlat
    if not bump_check_loop.is_running():
        bump_check_loop.start()

@bot.event
async def on_member_join(member: discord.Member):
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if channel:
        msg = config["WELCOME_MESSAGE"].replace("{member}", member.mention)
        await channel.send(msg)

@bot.event
async def on_message(message: discord.Message):
    if message.author == bot.user:
        return

    # Medya Log Sistemi
    log_channel = bot.get_channel(IMAGE_LOG_CHANNEL_ID)
    if log_channel and message.channel.id != IMAGE_LOG_CHANNEL_ID and not message.author.bot:
        if message.attachments:
            for attachment in message.attachments:
                await log_channel.send(f"📎 **{message.author.display_name}**", file=await attachment.to_file())

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
    # Render web servisinin port gereksinimini karşılamak için Flask'i başlatıyoruz
    from flask import Flask
    import threading

    app = Flask('')

    @app.route('/')
    def home():
        return "Bot aktif ve ayakta!"

    def run_web():
        port = int(os.environ.get("PORT", 8080))
        app.run(host='0.0.0.0', port=port)

    t = threading.Thread(target=run_web)
    t.daemon = True
    t.start()

    if TOKEN:
        bot.run(TOKEN)
    else:
        print("HATA: DISCORD_TOKEN bulunamadı!")
