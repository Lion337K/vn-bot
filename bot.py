import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
import json
import threading
from datetime import datetime, timezone
import sys
sys.stdout.reconfigure(line_buffering=True)

# ───────────────────────────────────────────────
#  BOT YANITLARI VE MESAJLARI
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
    "err_generic": "hata olustu: {error}",
}

# ───────────────────────────────────────────────
#  AYARLAR VE ID'LER
# ───────────────────────────────────────────────

TOKEN = os.getenv("DISCORD_TOKEN")

GUILD_ID             = 1480303038408425764
WELCOME_CHANNEL_ID   = 1480314604713414757
BUMP_CHANNEL_ID      = 1381771230964748370
IMAGE_LOG_CHANNEL_ID = 1480317488456536166

BUMP_BOT_ID = 302050872383242240  # Disboard
CONFIG_FILE = "config.json"

# ───────────────────────────────────────────────
#  CONFIG (JSON)
# ───────────────────────────────────────────────

DEFAULT_CONFIG = {
    "WELCOME_MESSAGE": RESPONSES["welcome_message"],
    "BUMP_MESSAGE": RESPONSES["bump_message"],
}


def load_config():
    data = DEFAULT_CONFIG.copy()
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data.update(json.load(f))
        except Exception as e:
            print(f"⚠️ Config dosyası okunamadı: {e}")
    return data


def save_config(config_data):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config_data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"⚠️ Config kaydedilemedi: {e}")


config = load_config()

# ───────────────────────────────────────────────
#  BOT SETUP
# ───────────────────────────────────────────────

intents = discord.Intents.default()
intents.members = True          # Developer Portal'da da açık olmalı
intents.message_content = True  # Developer Portal'da da açık olmalı


class MyBot(commands.Bot):
    async def setup_hook(self):
        # Slash komutları sadece bir kez, bot bağlanırken senkronize edilir
        guild = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        try:
            synced = await self.tree.sync(guild=guild)
            print(f"✅ {len(synced)} komut senkronize edildi.")
        except Exception as e:
            print(f"⚠️ Komut senkronizasyon hatası: {e}")

        bump_check_loop.start()


bot = MyBot(command_prefix="!", intents=intents)

# ───────────────────────────────────────────────
#  BUMP KONTROL
# ───────────────────────────────────────────────


async def perform_bump_check():
    channel = bot.get_channel(BUMP_CHANNEL_ID)
    if channel is None:
        try:
            channel = await bot.fetch_channel(BUMP_CHANNEL_ID)
        except Exception as e:
            print(f"⚠️ Bump kanalı bulunamadı: {e}")
            return "Kanal bulunamadı (ID yanlış veya bot kanalı göremiyor)"

    try:
        messages = [msg async for msg in channel.history(limit=30)]

        last_disboard_msg = next(
            (m for m in messages if m.author.id == BUMP_BOT_ID), None
        )
        if not last_disboard_msg:
            return "Disboard mesajı yok"

        # Disboard mesajından sonra bot hatırlatma attı mı?
        for msg in messages:  # yeniden eskiye
            if msg.id == last_disboard_msg.id:
                break
            if msg.author.id == bot.user.id:
                return "Zaten hatırlatma atılmış"

        elapsed = (datetime.now(timezone.utc) - last_disboard_msg.created_at).total_seconds()

        if elapsed >= 2 * 60 * 60:
            await channel.send(config["BUMP_MESSAGE"])
            print("📢 2 saatlik süre dolmuş! Hatırlatma gönderildi.")
            return "Hatırlatma gönderildi"

        kalan = int((2 * 60 * 60 - elapsed) / 60)
        return f"Süre henüz dolmadı (~{kalan} dk kaldı)"

    except discord.Forbidden:
        return "Yetki hatası: botun kanalda 'Kanalı Gör', 'Mesaj Geçmişini Oku' ve 'Mesaj Gönder' yetkisi olmalı"
    except Exception as e:
        print(f"❌ Bump kontrolü hatası: {e}")
        return str(e)


@tasks.loop(minutes=1)
async def bump_check_loop():
    await perform_bump_check()


@bump_check_loop.before_loop
async def before_bump_check():
    await bot.wait_until_ready()

# ───────────────────────────────────────────────
#  EVENTS
# ───────────────────────────────────────────────


@bot.event
async def on_ready():
    print(f"✅ Giriş yapıldı: {bot.user} (ID: {bot.user.id})")
    guild = bot.get_guild(GUILD_ID)
    if guild is None:
        print("⚠️ Bot GUILD_ID'deki sunucuda değil veya ID yanlış!")


@bot.event
async def on_member_join(member: discord.Member):
    if member.guild.id != GUILD_ID:
        return
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if channel:
        try:
            msg = config["WELCOME_MESSAGE"].replace("{member}", member.mention)
            await channel.send(msg)
        except Exception as e:
            print(f"⚠️ Karşılama mesajı gönderilemedi: {e}")
    else:
        print("⚠️ WELCOME_CHANNEL_ID bulunamadı!")


@bot.event
async def on_message(message: discord.Message):
    if message.author == bot.user:
        return

    if (
        message.attachments
        and not message.author.bot
        and message.channel.id != IMAGE_LOG_CHANNEL_ID
    ):
        log_channel = bot.get_channel(IMAGE_LOG_CHANNEL_ID)
        if log_channel:
            for attachment in message.attachments:
                try:
                    await log_channel.send(
                        f"📎 **{message.author.display_name}**",
                        file=await attachment.to_file(),
                    )
                except Exception as e:
                    print(f"⚠️ Ek log kanalına gönderilemedi: {e}")

    await bot.process_commands(message)

# ───────────────────────────────────────────────
#  SLASH COMMANDS
# ───────────────────────────────────────────────


@bot.tree.command(name="setwelcome", description="Hoş geldin mesajını değiştirir. ({member} etiketi kullanabilirsiniz)")
@app_commands.checks.has_permissions(administrator=True)
async def set_welcome(interaction: discord.Interaction, yeni_mesaj: str):
    config["WELCOME_MESSAGE"] = yeni_mesaj
    save_config(config)
    await interaction.response.send_message(
        RESPONSES["setwelcome_success"].format(yeni_mesaj=yeni_mesaj), ephemeral=True
    )


@bot.tree.command(name="setbump", description="Bump hatırlatma mesajını değiştirir.")
@app_commands.checks.has_permissions(administrator=True)
async def set_bump(interaction: discord.Interaction, yeni_mesaj: str):
    config["BUMP_MESSAGE"] = yeni_mesaj
    save_config(config)
    await interaction.response.send_message(
        RESPONSES["setbump_success"].format(yeni_mesaj=yeni_mesaj), ephemeral=True
    )


@bot.tree.command(name="testwelcome", description="Hoş geldin mesajını test et.")
@app_commands.checks.has_permissions(administrator=True)
async def test_welcome(interaction: discord.Interaction):
    msg = config["WELCOME_MESSAGE"].replace("{member}", interaction.user.mention)
    await interaction.response.send_message(msg)


@bot.tree.command(name="sendmsg", description="Belirli bir kanala mesaj gönder.")
@app_commands.checks.has_permissions(administrator=True)
async def send_msg(interaction: discord.Interaction, channel_id: str, message: str):
    try:
        target = bot.get_channel(int(channel_id))
        if target is None:
            target = await bot.fetch_channel(int(channel_id))
    except Exception:
        await interaction.response.send_message(RESPONSES["sendmsg_not_found"], ephemeral=True)
        return

    try:
        await target.send(message)
        await interaction.response.send_message(RESPONSES["sendmsg_success"], ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(
            RESPONSES["sendmsg_error"].format(error=e), ephemeral=True
        )


@bot.tree.command(name="checkbump", description="Bump durumunu ve zamanlayıcıyı manuel test eder (Debug).")
@app_commands.checks.has_permissions(administrator=True)
async def check_bump(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    result = await perform_bump_check()
    await interaction.followup.send(f"🔍 **Debug Sonucu:**\n```text\n{result}\n```", ephemeral=True)

# ───────────────────────────────────────────────
#  HATA YAKALAYICI
# ───────────────────────────────────────────────


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        msg = RESPONSES["err_missing_permissions"]
    elif isinstance(error, app_commands.CommandOnCooldown):
        msg = RESPONSES["err_cooldown"].format(retry_after=round(error.retry_after, 1))
    else:
        print(f"❌ Komut hatası: {error!r}")
        msg = RESPONSES["err_generic"].format(error=error)

    # Cevap zaten verilmişse (defer vb.) followup kullan
    if interaction.response.is_done():
        await interaction.followup.send(msg, ephemeral=True)
    else:
        await interaction.response.send_message(msg, ephemeral=True)

# ───────────────────────────────────────────────
#  WEB SUNUCUSU (Render + UptimeRobot için)
# ───────────────────────────────────────────────


def run_web():
    from flask import Flask

    app = Flask(__name__)

    @app.route("/")
    def home():
        return "Bot aktif ve ayakta!"

    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)


if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()

    if not TOKEN:
        print("HATA: DISCORD_TOKEN bulunamadı! Render > Environment kısmından ekle.")
    else:
        bot.run(TOKEN)
