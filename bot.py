import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
import threading
from datetime import datetime, timezone
import sys
sys.stdout.reconfigure(line_buffering=True)

# ───────────────────────────────────────────────
#  BOT YANITLARI VE MESAJLARI
# ───────────────────────────────────────────────

RESPONSES = {
    "welcome_message": "{member} aramiza katildi fln filan 😒",
    "bump_message": "buuuuump",
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

GUILD_ID             = 1381768080610426930
WELCOME_CHANNEL_ID   = 1480314604713414757
BUMP_CHANNEL_ID      = 1381771230964748370
IMAGE_LOG_CHANNEL_ID = 1480317488456536166

BUMP_BOT_ID = 302050872383242240  # Disboard

# Extensions used as a fallback when Discord doesn't send a content type
MEDIA_EXTENSIONS = (
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".heic", ".avif",
    ".mp4", ".mov", ".webm", ".mkv", ".avi", ".m4v",
)

# ───────────────────────────────────────────────
#  MESAJ AYARLARI (değiştirmek için yukarıdaki RESPONSES'u düzenle)
# ───────────────────────────────────────────────

config = {
    "WELCOME_MESSAGE": RESPONSES["welcome_message"],
    "BUMP_MESSAGE": RESPONSES["bump_message"],
}

# ───────────────────────────────────────────────
#  BOT SETUP
# ───────────────────────────────────────────────

intents = discord.Intents.default()
intents.members = True          # Developer Portal'da da açık olmalı (Server Members Intent)
intents.message_content = True  # Developer Portal'da da açık olmalı (ek dosyaları görmek için de gerekli)


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
#  YARDIMCI FONKSİYONLAR
# ───────────────────────────────────────────────


async def get_channel_safe(channel_id: int):
    """Cache'te yoksa API'den çekmeyi dener. Bulamazsa None döner."""
    channel = bot.get_channel(channel_id)
    if channel is not None:
        return channel
    try:
        return await bot.fetch_channel(channel_id)
    except Exception as e:
        print(f"⚠️ Kanal {channel_id} alınamadı: {e!r}")
        return None


def is_media(attachment: discord.Attachment) -> bool:
    content_type = (attachment.content_type or "").lower()
    if content_type.startswith(("image/", "video/")):
        return True
    return attachment.filename.lower().endswith(MEDIA_EXTENSIONS)

# ───────────────────────────────────────────────
#  MEDYA LOG SİSTEMİ
# ───────────────────────────────────────────────


async def log_media(message: discord.Message):
    media = [a for a in message.attachments if is_media(a)]
    if not media:
        return

    log_channel = await get_channel_safe(IMAGE_LOG_CHANNEL_ID)
    if log_channel is None:
        print("⚠️ Log kanalı bulunamadı veya botun görme yetkisi yok.")
        return

    header = (
        f"📎 **Gönderen:** {message.author.mention} (`{message.author}`)\n"
        f"📍 **Kanal:** {message.channel.mention}\n"
        f"🔗 {message.jump_url}"
    )
    no_pings = discord.AllowedMentions.none()
    size_limit = log_channel.guild.filesize_limit

    for attachment in media:
        try:
            if attachment.size > size_limit:
                # Too big to re-upload, so link to the original instead
                await log_channel.send(
                    f"{header}\n⚠️ Dosya çok büyük, yeniden yüklenemedi: {attachment.url}",
                    allowed_mentions=no_pings,
                )
            else:
                await log_channel.send(
                    header,
                    file=await attachment.to_file(),
                    allowed_mentions=no_pings,
                )
        except Exception as e:
            print(f"⚠️ '{attachment.filename}' log kanalına gönderilemedi: {e!r}")
            # Last resort: at least log who sent it and where, with the link
            try:
                await log_channel.send(
                    f"{header}\n⚠️ Dosya yüklenemedi: {attachment.url}",
                    allowed_mentions=no_pings,
                )
            except Exception as e2:
                print(f"❌ Yedek log mesajı da gönderilemedi: {e2!r}")

# ───────────────────────────────────────────────
#  BUMP KONTROL
# ───────────────────────────────────────────────


async def perform_bump_check():
    channel = await get_channel_safe(BUMP_CHANNEL_ID)
    if channel is None:
        return "Kanal bulunamadı (ID yanlış veya bot kanalı göremiyor)"

    try:
        messages = [msg async for msg in channel.history(limit=100)]

        last_disboard_msg = next(
            (m for m in messages if m.author.id == BUMP_BOT_ID), None
        )
        if not last_disboard_msg:
            return "Disboard mesajı yok"

        # Disboard mesajından sonra bot hatırlatma attı mı?
        for msg in messages:  # yeniden eskiye
            if msg.id == last_disboard_msg.id:
                break
            if msg.author.id == bot.user.id and msg.content == config["BUMP_MESSAGE"]:
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
        return

    # Startup self-check: reports missing channels/permissions in the logs
    checks = {
        "Karşılama kanalı": (WELCOME_CHANNEL_ID, ["view_channel", "send_messages"]),
        "Log kanalı": (IMAGE_LOG_CHANNEL_ID, ["view_channel", "send_messages", "attach_files"]),
        "Bump kanalı": (BUMP_CHANNEL_ID, ["view_channel", "send_messages", "read_message_history"]),
    }
    for name, (channel_id, needed) in checks.items():
        channel = guild.get_channel(channel_id)
        if channel is None:
            print(f"⚠️ {name} ({channel_id}) bulunamadı: ID yanlış ya da bot kanalı göremiyor.")
            continue
        perms = channel.permissions_for(guild.me)
        missing = [p for p in needed if not getattr(perms, p)]
        if missing:
            print(f"⚠️ {name} (#{channel.name}) için eksik yetkiler: {', '.join(missing)}")
        else:
            print(f"✅ {name} (#{channel.name}) tamam.")


@bot.event
async def on_member_join(member: discord.Member):
    print(f"👋 Yeni üye: {member} (sunucu: {member.guild.id})")
    if member.guild.id != GUILD_ID:
        return

    channel = await get_channel_safe(WELCOME_CHANNEL_ID)
    if channel is None:
        print("⚠️ Karşılama kanalı bulunamadı veya botun görme yetkisi yok.")
        return

    try:
        msg = config["WELCOME_MESSAGE"].replace("{member}", member.mention)
        await channel.send(msg)
        print("✅ Karşılama mesajı gönderildi.")
    except discord.Forbidden:
        print("⚠️ Karşılama mesajı gönderilemedi: botun kanalda 'Mesaj Gönder' yetkisi yok.")
    except Exception as e:
        print(f"⚠️ Karşılama mesajı gönderilemedi: {e!r}")


@bot.event
async def on_message(message: discord.Message):
    if message.author == bot.user:
        return

    if (
        message.guild is not None
        and message.guild.id == GUILD_ID
        and not message.author.bot
        and message.channel.id != IMAGE_LOG_CHANNEL_ID
        and message.attachments
    ):
        await log_media(message)

    await bot.process_commands(message)

# ───────────────────────────────────────────────
#  SLASH COMMANDS
# ───────────────────────────────────────────────


@bot.tree.command(name="testwelcome", description="Hoş geldin mesajını test et.")
@app_commands.checks.has_permissions(administrator=True)
async def test_welcome(interaction: discord.Interaction):
    msg = config["WELCOME_MESSAGE"].replace("{member}", interaction.user.mention)
    await interaction.response.send_message(msg)


@bot.tree.command(name="sendmsg", description="Belirli bir kanala mesaj gönder.")
@app_commands.checks.has_permissions(administrator=True)
async def send_msg(interaction: discord.Interaction, channel_id: str, message: str):
    try:
        target = await get_channel_safe(int(channel_id))
    except ValueError:
        target = None
    if target is None:
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
