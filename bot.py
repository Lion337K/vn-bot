import os
import asyncio
from datetime import datetime, timedelta, timezone
import discord
from discord.ext import commands, tasks
from aiohttp import web

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.reactions = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ID Tanımlamaları
LOG_CHANNEL_ID = 1381770621054091306       # Medya loglarının atılacağı kanal
WELCOME_CHANNEL_ID = 1488662459009994965   # Giriş ve çıkış mesajlarının atılacağı kanal
BUMP_CHANNEL_ID = 1381768080610426930      # Disboard ve bump hatırlatmalarının yapılacağı kanal

DISBOARD_BOT_ID = 302050872383242240       # Disboard Bot ID

join_messages = {}

# ==================== WEB SUNUCUSU (Render / Uptime için) ====================
async def handle(request):
    return web.Response(text="Bot is running!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print("Web sunucusu baslatildi.")

# ==================== BUMP KONTROL VE HATIRLATMA SİSTEMİ ====================
async def check_disboard_bump():
    channel = bot.get_channel(BUMP_CHANNEL_ID)
    if not channel:
        return

    now = datetime.now(timezone.utc)
    
    last_disboard_msg = None
    last_reminder_msg = None
    last_angry_msg = None

    # Kanal geçmişindeki son 50 mesajı tara
    async for msg in channel.history(limit=50):
        # 1. En son başarılı Disboard mesajını bul
        if not last_disboard_msg and msg.author.id == DISBOARD_BOT_ID:
            for embed in msg.embeds:
                desc = embed.description or ""
                if "Bump done" in desc or "başarıyla" in desc.lower():
                    last_disboard_msg = msg
                    break
        
        # 2. Botun son attığı "buuump" hatırlatmasını bul
        if not last_reminder_msg and msg.author.id == bot.user.id and msg.content == "buuump":
            last_reminder_msg = msg

        # 3. Botun son attığı "yapsaniza lan" mesajını bul
        if not last_angry_msg and msg.author.id == bot.user.id and msg.content == "yapsaniza lan":
            last_angry_msg = msg

        # Hepsi bulunduysa döngüden çık
        if last_disboard_msg and last_reminder_msg and last_angry_msg:
            break

    if not last_disboard_msg:
        return

    disboard_time = last_disboard_msg.created_at
    
    # Hatırlatma mesajı en son Disboard mesajından SONRA mı atılmış?
    reminder_is_after_bump = last_reminder_msg and last_reminder_msg.created_at > disboard_time

    # --- 1. AŞAMA: 2 Saatlik Hatırlatma Kontrolü ---
    if (now - disboard_time).total_seconds() >= 7200: # 7200 saniye = 2 saat
        if not reminder_is_after_bump:
            await channel.send("buuump")
            print(f"[{datetime.now()}] 2 saatlik bump hatırlatması gönderildi.")
            return

    # --- 2. AŞAMA: 8 Saatlik "Yapsanıza Lan" Kontrolü ---
    if reminder_is_after_bump:
        reminder_time = last_reminder_msg.created_at
        
        # Hatırlatmadan sonra yeni bir bump atılmış mı? (Disboard mesajı hatırlatmadan sonraysa yeni bump yapılmıştır)
        new_bump_after_reminder = disboard_time > reminder_time

        if not new_bump_after_reminder:
            # Hatırlatmanın üzerinden 8 saat (28800 saniye) geçmiş mi?
            if (now - reminder_time).total_seconds() >= 28800:
                # "yapsaniza lan" bu hatırlatmadan sonra daha önce gönderilmiş mi?
                angry_is_after_reminder = last_angry_msg and last_angry_msg.created_at > reminder_time
                
                if not angry_is_after_reminder:
                    await channel.send("yapsaniza lan")
                    print(f"[{datetime.now()}] 8 saat geçtiği için 'yapsaniza lan' gönderildi.")

# Periyodik kontrol görevi (Her 1 dakikada bir çalışır)
@tasks.loop(minutes=1)
async def bump_check_loop():
    await check_disboard_bump()

# ==================== BOT ETKİNLİKLERİ ====================
@bot.event
async def on_ready():
    print(f"Bot giris yapti: {bot.user.name} (ID: {bot.user.id})")
    
    try:
        bot.tree.clear_commands(guild=None)
        await bot.tree.sync()
        print("Tüm slaş komutları temizlendi.")
    except Exception as e:
        print(f"Slaş komutları temizlenirken hata: {e}")

    # Bot aktif olduğu an kanalı kontrol et ve eksik bir durum varsa anında aksiyon al
    await check_disboard_bump()

    # Döngüyü başlat
    if not bump_check_loop.is_running():
        bump_check_loop.start()

    # Log kanalına "p" mesajı gönder
    try:
        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            await log_channel.send("p")
    except Exception as e:
        print(f"Log kanalına 'p' mesajı gönderilemedi: {e}")

# ==================== GİRİŞ / ÇIKIŞ BİLDİRİMLERİ ====================
@bot.event
async def on_member_join(member):
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if channel:
        msg = await channel.send(f"{member.mention} aramiza katildi fln filan 😒")
        join_messages[member.id] = msg

@bot.event
async def on_member_remove(member):
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if channel:
        if member.id in join_messages:
            try:
                msg = join_messages[member.id]
                await msg.edit(content=f"{member.mention} geri gitti... 😳")
                del join_messages[member.id]
                return
            except Exception:
                pass
        
        await channel.send(f"{member.mention} geri gitti... 😳")

# ==================== MEDYA LOG SİSTEMİ ====================
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Görsel ve video log sistemi (Doğrudan URL ile Cloudflare filtresi aşılır)
    if message.channel.id != LOG_CHANNEL_ID and message.attachments:
        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            for attachment in message.attachments:
                if any(attachment.filename.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.mp4', '.mov', '.webm']):
                    log_text = f"Kullanıcı: {message.author} (`{message.author.id}`)\nKanal: {message.channel.mention}\n{attachment.url}"
                    try:
                        await log_channel.send(content=log_text)
                    except Exception as e:
                        print(f"Medya loglanırken hata oluştu: {e}")

    await bot.process_commands(message)

# ==================== ANA ÇALIŞTIRMA FONKSİYONU ====================
async def main():
    TOKEN = os.environ.get("DISCORD_TOKEN")
    if not TOKEN:
        print("HATA: DISCORD_TOKEN bulunamadi!")
        return

    await start_web_server()
    await bot.start(TOKEN)

if __name__ == "__main__":
    print("Bot baslatiliyor, sistem kontrol ediliyor...")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot kapatılıyor...")
