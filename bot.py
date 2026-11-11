import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
import os
import re
import threading
import time
from typing import Optional
from datetime import datetime, timezone
from urllib.parse import urlparse
import sys
sys.stdout.reconfigure(line_buffering=True)

# ───────────────────────────────────────────────
#  BOT YANITLARI VE MESAJLARI
# ───────────────────────────────────────────────

RESPONSES = {
    "welcome_message": "{member} aramiza katildi fln filan 😒",
    "bump_message": "buuuuump",
    "startup_message": "p",
    "sendmsg_not_found": "🌌 Böyle bir kanal bulunamadı.",
    "sendmsg_success": "🦋 Mesaj başarıyla gönderildi.",
    "sendmsg_error": "❌ Hata oluştu: {error}",
    "err_missing_permissions": "yetkin yok kullanamazsin.",
    "err_cooldown": "yavasla biraz. {retry_after} saniye sonra bidaha dene.",
    "err_generic": "hata olustu: {error}",
    "err_not_posting_owner": "bu komutu sadece bu posting kanalının sahibi kullanabilir.",
    "err_not_voice_owner": "bu komutu sadece bu ses kanalının sahibi kullanabilir.",
    "not_yours": "Bu butonlar sana ait değil.",

    # ── Ortak (posting + ses) ──
    "rate_limited": "⏳ Discord çok sık değişikliğe izin vermiyor, birkaç dakika sonra tekrar dene.",
    "no_permission": "❌ Botun bunu yapmaya yetkisi yok.",
    "edit_error": "❌ Hata oluştu: {error}",
    "target_invalid": "❌ Bu komut kendin ya da bir bot için kullanılamaz.",
    "list_full": "❌ Liste dolu (en fazla {limit} kişi).",
    "view_given": "✅ {member} artık kanalı görebilir.",
    "view_already": "ℹ️ {member} zaten görme iznine sahip.",
    "view_taken": "🚫 {member} artık kanalı göremez.",
    "view_taken_already": "ℹ️ {member} zaten engelli.",

    # ── Posting sistemi ──
    "posting_panel_message": "posting olusturmak icin tiklayin",
    "posting_button_label": "olustur",
    "posting_created": "✅ Posting kanalın hazır: {channel}",
    "posting_already_owner": "📮 Zaten bir posting kanalın var: {channel}",
    "posting_creating": "⏳ Kanalın zaten oluşturuluyor, biraz bekle.",
    "posting_create_error": "❌ Posting kanalı oluşturulamadı, biraz sonra tekrar dene.",
    "posting_category_full": "❌ Posting kategorisi dolu, bir yönetici ile iletişime geç.",
    "posting_not_ready": "⏳ Sistem hâlâ hazırlanıyor, birkaç saniye sonra tekrar dene.",
    "posting_button_cooldown": "⏳ Çok hızlı tıklıyorsun, {seconds} saniye sonra tekrar dene.",
    "posting_channel_unsupported": "❌ Bu komut bu kanal türünde kullanılamaz.",
    "posting_desc_updated": "✅ Kanal açıklaması güncellendi.",
    "posting_hidden": "🙈 Kanalın artık gizli (sen ve izin verdiklerin görebilir).",
    "posting_shown": "👀 Kanalın tekrar herkese açık.",
    "posting_already_hidden": "ℹ️ Kanal zaten gizli.",
    "posting_already_visible": "ℹ️ Kanal zaten herkese açık.",
    "posting_write_given": "✅ {member} artık kanalında yazabilir.",
    "posting_write_already": "ℹ️ {member} zaten yazabiliyor.",
    "posting_write_taken": "✅ {member} için yazma izni kaldırıldı.",
    "posting_write_none": "ℹ️ {member} için verilmiş bir yazma izni yok.",
    "posting_write_blocked": "❌ {member} engelli. Önce `/postizin ver` ile engeli kaldır.",
    "posting_nsfw_on": "🔞 Kanal NSFW olarak işaretlendi.",
    "posting_nsfw_off": "✅ Kanalın NSFW işareti kaldırıldı.",
    "posting_nsfw_already_on": "ℹ️ Kanal zaten NSFW.",
    "posting_nsfw_already_off": "ℹ️ Kanal zaten NSFW değil.",
    "posting_delete_confirm": "⚠️ Posting kanalın kalıcı olarak silinecek. Emin misin?",
    "posting_delete_working": "⏳ Posting siliniyor...",
    "posting_delete_done": "🗑️ Posting silindi. İstersen yeniden oluşturabilirsin.",
    "posting_delete_cancelled": "↩️ Vazgeçildi.",
    "posting_delete_error": "❌ Posting silinirken hata oluştu: {error}",

    # ── Ses kanalı sistemi ──
    "voice_welcome": "{member} ses kanalın hazır! Komutların (bu kanalın yazı sohbetinde kullan): `/sesaciklama` `/sesdurum` `/sesizin`",
    "voice_status_updated": "✅ Ses kanalı durumu güncellendi.",
    "voice_hidden": "🙈 Ses kanalın artık gizli (sen ve izin verdiklerin görebilir).",
    "voice_shown": "👀 Ses kanalın tekrar herkese açık.",
    "voice_already_hidden": "ℹ️ Ses kanalı zaten gizli.",
    "voice_already_visible": "ℹ️ Ses kanalı zaten herkese açık.",
    "voice_channel_unsupported": "❌ Bu komut sadece ses kanalının yazı sohbetinde kullanılabilir.",
}

# ───────────────────────────────────────────────
#  AYARLAR VE ID'LER
# ───────────────────────────────────────────────

TOKEN = os.getenv("DISCORD_TOKEN")

GUILD_ID             = 1381768080610426930
WELCOME_CHANNEL_ID   = 1480314604713414757
BUMP_CHANNEL_ID      = 1381771230964748370
IMAGE_LOG_CHANNEL_ID = 1480317488456536166   # medya / dosya / GIF logları + açılış mesajı

BUMP_BOT_ID = 302050872383242240  # Disboard

# ── Posting sistemi ──
POSTING_CREATE_CHANNEL_ID = 1522166468936990841   # "olustur" butonunun olduğu kanal
POSTING_CATEGORY_ID       = 1566119110880788642   # posting kanalları bu kategoride açılır
POSTING_DATA_CHANNEL_ID   = 1568588462884520066   # posting kayıtlarının yazıldığı kanal
POSTING_BUTTON_ID         = "posting:create"      # sürümler arasında ASLA değiştirme
POSTING_BUTTON_COOLDOWN   = 30      # aynı kişi butona en erken kaç saniye sonra tekrar basabilir
POSTING_RECORD_TITLE      = "📮 **Posting kaydı**"
POSTING_DELETED_TITLE     = "🗑️ **Posting silindi**"
POSTING_RECORD_SCAN_LIMIT = 3000    # açılışta kayıtlar için geriye doğru taranacak mesaj sayısı
POSTING_CHECK_MINUTES     = 5       # yetki kontrolünün çalışma aralığı
LIST_LIMIT                = 25      # görebilenler / yazabilenler / engellenenler en fazla bu kadar kişi olabilir
POSTING_DISPLAY_LIMIT     = 5       # kayıt mesajında her listede en fazla kaç kişi etiketle gösterilsin

# ── Ses kanalı sistemi ──
VOICE_CREATE_CHANNEL_ID = 1533980022572843058     # bu kanala giren kişiye ses kanalı açılır
VOICE_CATEGORY_ID       = 1569826585949900992     # ses kanalları bu kategoride açılır
VOICE_JOIN_COOLDOWN     = 10        # aynı kişi oluşturma kanalına en erken kaç saniye sonra tekrar girebilir
VOICE_SWEEP_MINUTES     = 10        # boş kalmış ses kanallarını süpüren döngünün aralığı

# Posting sahibinin kanalındaki yetkileri
OWNER_PERMS = dict(
    view_channel=True,
    send_messages=True,
    send_messages_in_threads=True,
    create_public_threads=True,
    create_private_threads=True,
    manage_messages=True,
)
if hasattr(discord.Permissions, "pin_messages"):   # eski discord.py sürümlerinde yok
    OWNER_PERMS["pin_messages"] = True

# Ses kanalı sahibinin yetkileri. manage_messages ayrıca "sahip işareti"dir:
# bot yeniden başlarsa sahibi bu yetkiden tanır, o yüzden başkasına verme.
VOICE_OWNER_PERMS = dict(
    view_channel=True,
    connect=True,
    send_messages=True,
    manage_messages=True,
)

# @everyone'dan her zaman alınan yazma yetkileri (kimse izinsiz yazamasın)
POSTING_WRITE_PERMS = (
    "send_messages",
    "send_messages_in_threads",
    "create_public_threads",
    "create_private_threads",
)

# GIF linkleri (Discord'un GIF seçicisi bunları yollar) ve doğrudan .gif linkleri
GIF_HOSTS = ("tenor.com", "giphy.com")
URL_RE = re.compile(r"https?://[^\s<>]+", re.IGNORECASE)
MAX_GIFS_PER_MESSAGE = 5

# ───────────────────────────────────────────────
#  MESAJ AYARLARI (değiştirmek için yukarıdaki RESPONSES'u düzenle)
# ───────────────────────────────────────────────

config = {
    "WELCOME_MESSAGE": RESPONSES["welcome_message"],
    "BUMP_MESSAGE": RESPONSES["bump_message"],
}

# ───────────────────────────────────────────────
#  DURUM (bellekte; açılışta yeniden kurulur)
# ───────────────────────────────────────────────

gif_logged = set()         # GIF'i loglanmış mesaj id'leri (çift loglamayı önler)

# kanal id -> {"channel_id", "owner_id", "writers", "viewers", "blocked", "hidden", "message_id"}
posting_records = {}
posting_state = {"initialized": False, "loaded": False}
creating_postings = set()  # şu an kanalı oluşturulan kullanıcı id'leri (çift tıklamayı önler)
button_cooldowns = {}      # kullanıcı id -> butona son basış zamanı (time.monotonic)

# kanal id -> {"channel_id", "owner_id", "viewers", "blocked", "hidden"}
voice_records = {}
creating_voices = set()    # şu an ses kanalı oluşturulan kullanıcı id'leri
voice_cooldowns = {}       # kullanıcı id -> oluşturma kanalına son giriş zamanı

POSTING_RECORD_RE = re.compile(
    r"POSTING_DATA channel=(\d+) owner=(\d+) hidden=([01]) writers=([\d,]*) blocked=([\d,]*)"
    r"(?: viewers=([\d,]*))?"
)
POSTING_DELETED_RE = re.compile(r"POSTING_DELETED channel=(\d+)")

NO_PINGS = discord.AllowedMentions.none()

# ───────────────────────────────────────────────
#  BOT SETUP
# ───────────────────────────────────────────────

intents = discord.Intents.default()   # voice_states varsayılan olarak açık
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

        # Kalıcı buton: bot yeniden başlasa da eski mesajdaki buton çalışır
        self.add_view(CreatePostingView())

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


def tweak_overwrite(overwrites: dict, target, **perms):
    """Overwrite sözlüğünde bir hedefin yetkilerini günceller; boş kalırsa kaldırır."""
    ow = overwrites[target] if target in overwrites else discord.PermissionOverwrite()
    ow.update(**perms)
    if ow.is_empty():
        overwrites.pop(target, None)
    else:
        overwrites[target] = ow


async def run_guarded(coro, timeout: float = 30):
    """Discord isteğini zaman aşımı ve hata yakalamayla çalıştırır. Hata metni ya da None döner."""
    try:
        await asyncio.wait_for(coro, timeout)
        return None
    except asyncio.TimeoutError:
        return RESPONSES["rate_limited"]
    except discord.Forbidden:
        return RESPONSES["no_permission"]
    except Exception as e:
        print(f"❌ Komut hatası: {e!r}")
        return RESPONSES["edit_error"].format(error=e)


def prune_cooldowns(table: dict, window: float):
    """Süresi dolmuş cooldown kayıtlarını temizler (sözlük şişmesin)."""
    if len(table) < 500:
        return
    now = time.monotonic()
    for key in [k for k, t in table.items() if now - t > window]:
        table.pop(key, None)


def target_for(guild: discord.Guild, user_id: int):
    """Üye sunucudaysa Member, değilse Member tipinde Object döner (yetkisi korunur, geri gelince çalışır)."""
    member = guild.get_member(user_id)
    return member if member is not None else discord.Object(id=user_id, type=discord.Member)


def copy_category_overwrites(category: discord.CategoryChannel) -> dict:
    return {
        target: discord.PermissionOverwrite.from_pair(*ow.pair())
        for target, ow in category.overwrites.items()
    }


def set_view_access(record: dict, user_id: int, give: bool) -> str:
    """
    Görme izni verir ya da alır (posting ve ses için ortak). Sonuç: "done" | "already" | "full".
      ver -> engelden çıkarır, görebilenlere ekler
      al  -> görebilenlerden ve yazabilenlerden çıkarır, engellenenlere ekler
    """
    viewers, blocked = record["viewers"], record["blocked"]
    writers = record.get("writers")
    if give:
        if user_id in viewers and user_id not in blocked:
            return "already"
        if user_id in blocked:
            blocked.remove(user_id)
        if user_id not in viewers:
            if len(viewers) >= LIST_LIMIT:
                return "full"
            viewers.append(user_id)
        return "done"

    if user_id in blocked:
        return "already"
    if len(blocked) >= LIST_LIMIT:
        return "full"
    if user_id in viewers:
        viewers.remove(user_id)
    if writers is not None and user_id in writers:
        writers.remove(user_id)
    blocked.append(user_id)
    return "done"

# ───────────────────────────────────────────────
#  MEDYA / DOSYA LOG SİSTEMİ
# ───────────────────────────────────────────────


def log_header(message: discord.Message) -> str:
    return (
        f"📎 **Gönderen:** {message.author.mention} (`{message.author}`)\n"
        f"📍 **Kanal:** {message.channel.mention}\n"
        f"🔗 {message.jump_url}"
    )


async def log_attachments(message: discord.Message):
    """Mesajdaki TÜM ekleri loglar: resim, video, ses, belge, arşiv... (tür sınırı yok)."""
    attachments = list(message.attachments)
    if not attachments:
        return

    log_channel = await get_channel_safe(IMAGE_LOG_CHANNEL_ID)
    if log_channel is None:
        print("⚠️ Log kanalı bulunamadı veya botun görme yetkisi yok.")
        return

    header = log_header(message)
    size_limit = log_channel.guild.filesize_limit

    for attachment in attachments:
        info = f"{header}\n📄 **Dosya:** {discord.utils.escape_markdown(attachment.filename)}"
        try:
            if attachment.size > size_limit:
                # Too big to re-upload, so link to the original instead
                await log_channel.send(
                    f"{info}\n⚠️ Dosya çok büyük, yeniden yüklenemedi: {attachment.url}",
                    allowed_mentions=NO_PINGS,
                )
            else:
                await log_channel.send(
                    info,
                    file=await attachment.to_file(),
                    allowed_mentions=NO_PINGS,
                )
        except Exception as e:
            print(f"⚠️ '{attachment.filename}' log kanalına gönderilemedi: {e!r}")
            # Last resort: at least log who sent it and where, with the link
            try:
                await log_channel.send(
                    f"{info}\n⚠️ Dosya yüklenemedi: {attachment.url}",
                    allowed_mentions=NO_PINGS,
                )
            except Exception as e2:
                print(f"❌ Yedek log mesajı da gönderilemedi: {e2!r}")


def is_gif_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    host = (parsed.hostname or "").lower()
    if any(host == h or host.endswith("." + h) for h in GIF_HOSTS):
        return True
    return parsed.path.lower().endswith(".gif")


def collect_gif_urls(message: discord.Message) -> list:
    """Mesajdaki GIF linklerini bulur: önce metindeki linkler, yoksa gifv embed'leri."""
    urls = []
    for url in URL_RE.findall(message.content or ""):
        url = url.rstrip(".,;:!?)\"'")
        if is_gif_url(url):
            urls.append(url)
    if not urls:
        for embed in message.embeds:
            if embed.url and (
                embed.type == "gifv" or (embed.type == "image" and is_gif_url(embed.url))
            ):
                urls.append(embed.url)
    return list(dict.fromkeys(urls))[:MAX_GIFS_PER_MESSAGE]


async def log_gifs(message: discord.Message):
    if message.id in gif_logged:
        return
    urls = collect_gif_urls(message)
    if not urls:
        return

    log_channel = await get_channel_safe(IMAGE_LOG_CHANNEL_ID)
    if log_channel is None:
        print("⚠️ Log kanalı bulunamadı veya botun görme yetkisi yok.")
        return

    gif_logged.add(message.id)
    if len(gif_logged) > 5000:
        gif_logged.clear()

    header = log_header(message)
    for url in urls:
        try:
            # Link olarak atılır, Discord log kanalında GIF'i kendisi gösterir
            await log_channel.send(f"{header}\n🎞️ **GIF:** {url}", allowed_mentions=NO_PINGS)
        except Exception as e:
            print(f"⚠️ GIF log kanalına gönderilemedi: {e!r}")


async def announce_startup():
    """Bot ilk aktif olduğunda log kanalına kısa bir mesaj atar (Render loguna bakmadan anlamak için)."""
    channel = await get_channel_safe(IMAGE_LOG_CHANNEL_ID)
    if channel is None:
        return
    try:
        await channel.send(RESPONSES["startup_message"], allowed_mentions=NO_PINGS)
    except Exception as e:
        print(f"⚠️ Açılış mesajı gönderilemedi: {e!r}")

# ───────────────────────────────────────────────
#  POSTING SİSTEMİ
# ───────────────────────────────────────────────
#  Bir posting kanalı tek kişiye aittir; başkası yazamaz (sahip izin verene kadar).
#  Kanalın bütün yetkileri şu kaynaklardan HESAPLANIR (build_posting_overwrites):
#     kategori yetkileri  +  @everyone (etiket + yazma kapalı, gizliyse görme kapalı)
#     +  bot  +  görebilenler  +  yazabilenler  +  sahip  +  engellenenler
#  Kontrol döngüsü kanalın gerçek yetkilerini bununla karşılaştırır, farklıysa düzeltir.
# ───────────────────────────────────────────────


def new_posting_record(owner_id: int, channel_id: int = 0) -> dict:
    return {
        "channel_id": channel_id,
        "owner_id": owner_id,
        "writers": [],
        "viewers": [],
        "blocked": [],
        "hidden": False,
        "message_id": None,
    }


def get_posting(channel):
    """Kanalın posting kaydını döndürür (posting kanalı değilse None)."""
    return posting_records.get(getattr(channel, "id", 0))


def get_posting_by_owner(user_id: int):
    for record in posting_records.values():
        if record["owner_id"] == user_id:
            return record
    return None


def postings_involving(user_id: int) -> list:
    """Bu kişinin sahip / yazabilen / görebilen / engelli olarak geçtiği postingler."""
    return [
        r for r in posting_records.values()
        if user_id == r["owner_id"]
        or user_id in r["writers"] or user_id in r["viewers"] or user_id in r["blocked"]
    ]


class NotPostingOwner(app_commands.CheckFailure):
    pass


def posting_owner_only():
    """Posting sahibi komutları için dekoratör."""
    async def predicate(interaction: discord.Interaction) -> bool:
        record = get_posting(interaction.channel)
        if record is not None and interaction.user.id == record["owner_id"]:
            return True
        raise NotPostingOwner()
    return app_commands.check(predicate)


# ── Yetki hesaplama ──


def build_posting_overwrites(guild: discord.Guild, category: discord.CategoryChannel, record: dict) -> dict:
    """Kaydın olması gereken yetki tablosunu hesaplar."""
    # 1) Kategorinin yetkilerini kopyala (kategoride @everyone için yaptığın değişiklikler buradan gelir)
    ows = copy_category_overwrites(category)

    # 2) @everyone: herkesi etiketleyemesin, yazamasın; gizliyse görmesin
    everyone = guild.default_role
    tweak_overwrite(ows, everyone, mention_everyone=False, **{p: False for p in POSTING_WRITE_PERMS})
    if record["hidden"]:
        tweak_overwrite(ows, everyone, view_channel=False)

    # 3) Bot her durumda görebilsin ve yazabilsin
    if guild.me is not None:
        tweak_overwrite(ows, guild.me, view_channel=True, send_messages=True)

    owner_id = record["owner_id"]
    blocked = set(record["blocked"]) - {owner_id}

    # 4) Görme izni verilenler (engelliyse yok sayılır)
    for user_id in record["viewers"]:
        if user_id == owner_id or user_id in blocked:
            continue
        tweak_overwrite(ows, target_for(guild, user_id), view_channel=True)

    # 5) Yazma izni verilenler (engelliyse yok sayılır)
    for user_id in record["writers"]:
        if user_id == owner_id or user_id in blocked:
            continue
        tweak_overwrite(
            ows, target_for(guild, user_id),
            view_channel=True, send_messages=True, send_messages_in_threads=True,
        )

    # 6) Sahip
    tweak_overwrite(ows, target_for(guild, owner_id), **OWNER_PERMS)

    # 7) Engellenenler kanalı göremez
    for user_id in blocked:
        tweak_overwrite(ows, target_for(guild, user_id), view_channel=False)

    return {t: ow for t, ow in ows.items() if not ow.is_empty()}


def posting_overwrites_match(channel: discord.abc.GuildChannel, desired: dict) -> bool:
    """Kanalın gerçek yetkileri hesaplananla aynı mı? (sunucuda olmayan üyeler karşılaştırılamaz, atlanır)"""
    actual = {
        target.id: tuple(p.value for p in ow.pair())
        for target, ow in channel.overwrites.items()
        if not ow.is_empty()
    }
    wanted = {
        target.id: tuple(p.value for p in ow.pair())
        for target, ow in desired.items()
        if not isinstance(target, discord.Object)
    }
    return actual == wanted


# ── Kayıt mesajı (kayıt kanalında) ──


def build_posting_record(record: dict, compact: bool = False) -> str:
    owner_id = record["owner_id"]
    channel_id = record["channel_id"]

    def people(ids: list) -> str:
        if not ids:
            return "—"
        if compact:
            return f"{len(ids)} kişi"
        shown = " ".join(f"<@{i}>" for i in ids[:POSTING_DISPLAY_LIMIT])
        extra = len(ids) - POSTING_DISPLAY_LIMIT
        return shown + (f" (+{extra} kişi daha)" if extra > 0 else "")

    def csv(ids: list) -> str:
        return ",".join(str(i) for i in ids)

    return (
        f"{POSTING_RECORD_TITLE}\n"
        f"Kanal: <#{channel_id}> (`{channel_id}`)\n"
        f"Sahip: <@{owner_id}> (`{owner_id}`)\n"
        f"Gizli: {'evet' if record['hidden'] else 'hayır'}\n"
        f"Görebilenler: {people(record['viewers'])}\n"
        f"Yazabilenler: {people(record['writers'])}\n"
        f"Engellenenler: {people(record['blocked'])}\n"
        f"`POSTING_DATA channel={channel_id} owner={owner_id} hidden={int(record['hidden'])} "
        f"writers={csv(record['writers'])} blocked={csv(record['blocked'])} viewers={csv(record['viewers'])}`"
    )


def posting_record_content(record: dict) -> str:
    content = build_posting_record(record)
    if len(content) > 1990:   # çok kalabalık listelerde etiketler yerine sayıları göster
        content = build_posting_record(record, compact=True)
    return content


async def save_posting_record(record: dict):
    """Kaydı kayıt kanalına yazar. Mesaj varsa düzenler, yoksa yeni mesaj atar."""
    data_channel = await get_channel_safe(POSTING_DATA_CHANNEL_ID)
    if data_channel is None:
        raise RuntimeError("posting kayıt kanalı bulunamadı")

    content = posting_record_content(record)
    message_id = record.get("message_id")
    if message_id and record.get("_last") == content:
        return  # değişen bir şey yok

    if message_id:
        try:
            await data_channel.get_partial_message(message_id).edit(
                content=content, allowed_mentions=NO_PINGS
            )
            record["_last"] = content
            return
        except discord.NotFound:
            pass  # mesaj silinmiş, aşağıda yenisi atılır

    message = await data_channel.send(content, allowed_mentions=NO_PINGS)
    record["message_id"] = message.id
    record["_last"] = content


async def mark_posting_deleted(record: dict):
    """Kanalı silinmiş bir postingin kaydını 'silindi' olarak işaretler ve bellekten çıkarır."""
    if record.get("_deleted"):
        return
    record["_deleted"] = True
    channel_id = record["channel_id"]
    posting_records.pop(channel_id, None)
    content = (
        f"{POSTING_DELETED_TITLE}\n"
        f"Kanal: `{channel_id}`\n"
        f"Sahip: <@{record['owner_id']}> (`{record['owner_id']}`)\n"
        f"`POSTING_DELETED channel={channel_id}`"
    )
    try:
        data_channel = await get_channel_safe(POSTING_DATA_CHANNEL_ID)
        if data_channel is None:
            return
        if record.get("message_id"):
            try:
                await data_channel.get_partial_message(record["message_id"]).edit(
                    content=content, allowed_mentions=NO_PINGS
                )
                return
            except discord.NotFound:
                pass
        await data_channel.send(content, allowed_mentions=NO_PINGS)
    except Exception as e:
        print(f"⚠️ Silinme kaydı yazılamadı: {e!r}")


async def load_posting_records() -> bool:
    """Açılışta kayıt kanalından postingleri okur. Aynı kanal için en yeni mesaj geçerlidir."""
    data_channel = await get_channel_safe(POSTING_DATA_CHANNEL_ID)
    if data_channel is None:
        return False

    loaded = {}
    seen = set()  # son durumu belli olan kanallar (kayıt ya da silinmiş işareti)
    try:
        async for msg in data_channel.history(limit=POSTING_RECORD_SCAN_LIMIT):
            if msg.author.id != bot.user.id:
                continue
            if msg.content.startswith(POSTING_DELETED_TITLE):
                match = POSTING_DELETED_RE.search(msg.content)
                if match:
                    seen.add(int(match.group(1)))
                continue
            if not msg.content.startswith(POSTING_RECORD_TITLE):
                continue
            match = POSTING_RECORD_RE.search(msg.content)
            if not match:
                continue
            channel_id, owner_id = int(match.group(1)), int(match.group(2))
            if channel_id in seen:
                continue
            seen.add(channel_id)
            loaded[channel_id] = {
                "channel_id": channel_id,
                "owner_id": owner_id,
                "hidden": match.group(3) == "1",
                "writers": [int(x) for x in match.group(4).split(",") if x],
                "blocked": [int(x) for x in match.group(5).split(",") if x],
                "viewers": [int(x) for x in (match.group(6) or "").split(",") if x],
                "message_id": msg.id,
            }
    except Exception as e:
        print(f"⚠️ Posting kayıtları okunamadı: {e!r}")
        return False

    posting_records.clear()
    posting_records.update(loaded)
    posting_state["loaded"] = True
    print(f"✅ {len(posting_records)} posting kaydı yüklendi.")
    return True


# ── Kanal oluşturma ──


class PostingCategoryFull(Exception):
    pass


def clean_channel_part(text: str) -> str:
    """Kanal adı için temizler: küçük harf, boşluk -> '-', emoji/özel karakterler atılır."""
    text = re.sub(r"\s+", "-", text.strip().lower())
    text = re.sub(r"[^\w.\-]", "", text)
    return re.sub(r"-{2,}", "-", text).strip("-")


def posting_channel_name(member: discord.Member, with_at: bool = True) -> str:
    """﹛@görünen-ad-posting﹜ biçiminde, 100 karakter sınırına uyacak şekilde."""
    prefix = "﹛@" if with_at else "﹛"
    suffix = "-posting﹜"
    base = clean_channel_part(member.display_name) or clean_channel_part(member.name) or str(member.id)
    return prefix + base[: 100 - len(prefix) - len(suffix)] + suffix


async def create_posting(guild: discord.Guild, member: discord.Member) -> discord.TextChannel:
    """Kategorinin yetkileriyle senkron + sahip yetkileriyle kanal açar ve kaydı yazar."""
    category = guild.get_channel(POSTING_CATEGORY_ID)
    if not isinstance(category, discord.CategoryChannel):
        raise RuntimeError("posting kategorisi bulunamadı")
    if len(category.channels) >= 50:
        raise PostingCategoryFull()
    if len(guild.channels) > 495:
        raise RuntimeError("sunucu kanal limitine çok yakın")

    record = new_posting_record(member.id)
    overwrites = build_posting_overwrites(guild, category, record)
    reason = f"Posting kanalı: {member}"

    channel = None
    try:
        try:
            channel = await category.create_text_channel(
                posting_channel_name(member, with_at=True), overwrites=overwrites, reason=reason
            )
        except discord.HTTPException as e:
            if e.status != 400:
                raise
            # Discord isimdeki '@' karakterini kabul etmediyse onsuz dene
            channel = await category.create_text_channel(
                posting_channel_name(member, with_at=False), overwrites=overwrites, reason=reason
            )

        record["channel_id"] = channel.id
        await save_posting_record(record)   # yazılamazsa kanal geri alınır
        posting_records[channel.id] = record
        return channel
    except Exception:
        if channel is not None:
            try:
                await channel.delete(reason="Posting oluşturma başarısız, geri alınıyor")
            except Exception as cleanup_error:
                print(f"⚠️ Geri alma hatası: {cleanup_error!r}")
        raise


# ── Kontrol / onarım ──


async def resolve_posting_channel(guild: discord.Guild, channel_id: int):
    """(kanal, silinmiş_mi) döndürür. Emin değilsek silinmiş saymayız."""
    channel = guild.get_channel(channel_id)
    if channel is not None:
        return channel, False
    try:
        return await bot.fetch_channel(channel_id), False
    except discord.NotFound:
        return None, True
    except Exception as e:
        print(f"⚠️ Posting kanalı {channel_id} kontrol edilemedi: {e!r}")
        return None, False


async def reconcile_posting(guild: discord.Guild, record: dict, reason: str = "Posting yetki kontrolü") -> bool:
    """Kanalın yetkilerini kayıtla karşılaştırır, farklıysa düzeltir. Düzeltme yapıldıysa True."""
    category = guild.get_channel(POSTING_CATEGORY_ID)
    if not isinstance(category, discord.CategoryChannel):
        return False

    channel, gone = await resolve_posting_channel(guild, record["channel_id"])
    if gone:
        await mark_posting_deleted(record)
        return False
    if not isinstance(channel, discord.TextChannel):
        return False

    desired = build_posting_overwrites(guild, category, record)
    if posting_overwrites_match(channel, desired):
        return False

    await channel.edit(overwrites=desired, reason=reason)
    print(f"🔧 Posting yetkileri düzeltildi: #{channel.name} ({channel.id})")
    return True


async def commit_posting(guild: discord.Guild, record: dict):
    """Bir kaydı değiştirdikten sonra çağır: kayıt mesajını günceller ve yetkileri kanala uygular."""
    await save_posting_record(record)
    await reconcile_posting(guild, record, reason="Posting ayarı değişti")


@tasks.loop(minutes=POSTING_CHECK_MINUTES)
async def posting_check_loop():
    if not posting_state["loaded"]:
        await load_posting_records()
    guild = bot.get_guild(GUILD_ID)
    if guild is None or not posting_state["loaded"]:
        return

    for record in list(posting_records.values()):
        try:
            if await reconcile_posting(guild, record):
                await asyncio.sleep(1)   # art arda düzenlemelerde rate limit'e girmemek için
        except discord.Forbidden:
            print(f"⚠️ Posting {record['channel_id']} için yetki düzeltilemedi: botun 'Rolleri Yönet' yetkisi yok.")
        except Exception as e:
            print(f"⚠️ Posting {record['channel_id']} kontrolü başarısız: {e!r}")


@posting_check_loop.before_loop
async def before_posting_check():
    await bot.wait_until_ready()


# ── Eski postingleri sisteme alma ──


def infer_posting_record(guild: discord.Guild, channel: discord.TextChannel, owner_id: Optional[int] = None):
    """
    Var olan bir kanalın yetkilerinden posting kaydı çıkarır. Sahip verilmediyse tahmin eder:
    kanalda yazma izni açık TEK bir üye varsa (ya da birden fazlaysa tek bir 'mesaj yönet' sahibi varsa) odur.
    Tahmin edilemezse None döner.
    """
    members = [
        (t, ow) for t, ow in channel.overwrites.items()
        if isinstance(t, discord.Member) and not t.bot
    ]

    if owner_id is None:
        candidates = [t for t, ow in members if ow.send_messages is True]
        if len(candidates) > 1:
            narrowed = [t for t in candidates if channel.overwrites_for(t).manage_messages is True]
            if len(narrowed) == 1:
                candidates = narrowed
        if len(candidates) != 1:
            return None
        owner_id = candidates[0].id

    record = new_posting_record(owner_id, channel.id)
    record["hidden"] = channel.overwrites_for(guild.default_role).view_channel is False
    for target, ow in members:
        if target.id == owner_id:
            continue
        if ow.view_channel is False:
            record["blocked"].append(target.id)
        elif ow.send_messages is True:
            record["writers"].append(target.id)
        elif ow.view_channel is True:
            record["viewers"].append(target.id)
    for key in ("blocked", "writers", "viewers"):
        record[key] = record[key][:LIST_LIMIT]
    return record


# ── Buton ve panel ──


class CreatePostingView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def on_error(self, interaction: discord.Interaction, error: Exception, item):
        print(f"❌ Buton hatası: {error!r}")
        try:
            if interaction.response.is_done():
                await interaction.followup.send(RESPONSES["posting_create_error"], ephemeral=True)
            else:
                await interaction.response.send_message(RESPONSES["posting_create_error"], ephemeral=True)
        except Exception:
            pass

    @discord.ui.button(
        label=RESPONSES["posting_button_label"],
        style=discord.ButtonStyle.success,
        custom_id=POSTING_BUTTON_ID,
    )
    async def create_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Önce hemen yanıt ver (3 saniye sınırı), sonra kontrolleri yap
        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        member = interaction.user
        if guild is None or not isinstance(member, discord.Member):
            await interaction.followup.send(RESPONSES["posting_create_error"], ephemeral=True)
            return
        if guild.id != GUILD_ID:
            print(f"⚠️ Yanlış sunucu: {guild.id} != {GUILD_ID}")
            await interaction.followup.send(RESPONSES["posting_create_error"], ephemeral=True)
            return

        # Cooldown: aynı kişi art arda basamasın
        now = time.monotonic()
        wait = POSTING_BUTTON_COOLDOWN - (now - button_cooldowns.get(member.id, -1e9))
        if wait > 0:
            await interaction.followup.send(
                RESPONSES["posting_button_cooldown"].format(seconds=int(wait) + 1), ephemeral=True
            )
            return
        button_cooldowns[member.id] = now
        prune_cooldowns(button_cooldowns, POSTING_BUTTON_COOLDOWN)

        if not posting_state["loaded"]:
            await interaction.followup.send(RESPONSES["posting_not_ready"], ephemeral=True)
            return

        existing = get_posting_by_owner(member.id)
        if existing is not None:
            await interaction.followup.send(
                RESPONSES["posting_already_owner"].format(channel=f"<#{existing['channel_id']}>"),
                ephemeral=True,
            )
            return
        if member.id in creating_postings:
            await interaction.followup.send(RESPONSES["posting_creating"], ephemeral=True)
            return

        creating_postings.add(member.id)   # araya await girmeden işaretle: çift tıklama ikinci kanal açmasın
        try:
            channel = await create_posting(guild, member)
        except PostingCategoryFull:
            await interaction.followup.send(RESPONSES["posting_category_full"], ephemeral=True)
        except Exception as e:
            print(f"❌ Posting oluşturulamadı: {e!r}")
            await interaction.followup.send(RESPONSES["posting_create_error"], ephemeral=True)
        else:
            await interaction.followup.send(
                RESPONSES["posting_created"].format(channel=channel.mention), ephemeral=True
            )
        finally:
            creating_postings.discard(member.id)


def is_posting_panel(msg: discord.Message) -> bool:
    """Mesaj botun gönderdiği posting paneli mi? (metne ya da butonun custom_id'sine göre)"""
    if msg.author.id != bot.user.id:
        return False
    if msg.content == RESPONSES["posting_panel_message"]:
        return True
    # Metni eski sürümde değişmiş panelleri de yakala
    for row in msg.components:
        for child in getattr(row, "children", []):
            if getattr(child, "custom_id", None) == POSTING_BUTTON_ID:
                return True
    return False


async def ensure_posting_panel():
    """Her açılışta paneli yeni sürümün butonuyla yeniler; fazlalıkları siler."""
    channel = await get_channel_safe(POSTING_CREATE_CHANNEL_ID)
    if channel is None:
        print("⚠️ Posting oluşturma kanalı bulunamadı.")
        return
    try:
        panels = [m async for m in channel.history(limit=50) if is_posting_panel(m)]
        if panels:
            keep, *extras = panels  # en yenisi kalır
            await keep.edit(content=RESPONSES["posting_panel_message"], view=CreatePostingView())
            for m in extras:
                try:
                    await m.delete()
                except Exception:
                    pass
            print("✅ Posting paneli yenilendi.")
        else:
            await channel.send(RESPONSES["posting_panel_message"], view=CreatePostingView())
            print("✅ Posting paneli gönderildi.")
    except Exception as e:
        print(f"⚠️ Posting paneli güncellenemedi: {e!r}")


# ── Silme onayı ──


class ConfirmPostingDeleteView(discord.ui.View):
    def __init__(self, invoker_id: int, channel_id: int):
        super().__init__(timeout=60)
        self.invoker_id = invoker_id
        self.channel_id = channel_id
        self.done = False

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.invoker_id:
            await interaction.response.send_message(RESPONSES["not_yours"], ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Evet, sil", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.done:
            return
        self.done = True
        self.stop()
        await interaction.response.edit_message(content=RESPONSES["posting_delete_working"], view=None)

        guild = interaction.guild
        channel = guild.get_channel(self.channel_id) if guild else None
        record = posting_records.get(self.channel_id)
        if channel is None or record is None or record["owner_id"] != interaction.user.id:
            await interaction.edit_original_response(content=RESPONSES["err_not_posting_owner"])
            return

        try:
            await channel.delete(reason=f"/postsil: {interaction.user}")
        except Exception as e:
            print(f"❌ Posting silinemedi: {e!r}")
            await interaction.edit_original_response(
                content=RESPONSES["posting_delete_error"].format(error=e)
            )
            return

        await mark_posting_deleted(record)
        try:
            # Kanal silindiği için bu mesaj güncellenemeyebilir, sorun değil
            await interaction.edit_original_response(content=RESPONSES["posting_delete_done"])
        except Exception:
            pass

    @discord.ui.button(label="Vazgeç", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.done = True
        self.stop()
        await interaction.response.edit_message(content=RESPONSES["posting_delete_cancelled"], view=None)

# ───────────────────────────────────────────────
#  SES KANALI SİSTEMİ
# ───────────────────────────────────────────────
#  Oluşturma kanalına giren kişiye kendi ses kanalı açılır, oraya taşınır ve etiketlenir.
#  Kanaldan herkes çıkınca kanal silinir. Kayıtlar bellekte tutulur; bot yeniden başlarsa
#  sahip, kanaldaki 'mesaj yönet' yetkisinden tanınır (rebuild_voice_records).
# ───────────────────────────────────────────────


def new_voice_record(owner_id: int, channel_id: int = 0) -> dict:
    return {"channel_id": channel_id, "owner_id": owner_id, "viewers": [], "blocked": [], "hidden": False}


def get_voice(channel):
    return voice_records.get(getattr(channel, "id", 0))


def get_voice_by_owner(user_id: int):
    for record in voice_records.values():
        if record["owner_id"] == user_id:
            return record
    return None


class NotVoiceOwner(app_commands.CheckFailure):
    pass


def voice_owner_only():
    """Ses kanalı sahibi komutları için dekoratör."""
    async def predicate(interaction: discord.Interaction) -> bool:
        record = get_voice(interaction.channel)
        if record is not None and interaction.user.id == record["owner_id"]:
            return True
        raise NotVoiceOwner()
    return app_commands.check(predicate)


class VoiceCategoryFull(Exception):
    pass


def humans_in(channel) -> list:
    """Kanaldaki botlar hariç kişiler."""
    return [m for m in channel.members if not m.bot]


def voice_channel_name(member: discord.Member) -> str:
    """@görünen-ad ses kanali"""
    prefix, suffix = "@", " ses kanali"
    name = re.sub(r"[\x00-\x1f]", "", member.display_name).strip() or member.name
    return prefix + name[: 100 - len(prefix) - len(suffix)] + suffix


def build_voice_overwrites(guild: discord.Guild, category: discord.CategoryChannel, record: dict) -> dict:
    ows = copy_category_overwrites(category)

    everyone = guild.default_role
    tweak_overwrite(ows, everyone, mention_everyone=False)
    if record["hidden"]:
        tweak_overwrite(ows, everyone, view_channel=False)

    if guild.me is not None:
        tweak_overwrite(ows, guild.me, view_channel=True, connect=True, send_messages=True)

    owner_id = record["owner_id"]
    blocked = set(record["blocked"]) - {owner_id}

    for user_id in record["viewers"]:
        if user_id == owner_id or user_id in blocked:
            continue
        tweak_overwrite(ows, target_for(guild, user_id), view_channel=True)

    tweak_overwrite(ows, target_for(guild, owner_id), **VOICE_OWNER_PERMS)

    for user_id in blocked:
        tweak_overwrite(ows, target_for(guild, user_id), view_channel=False)

    return {t: ow for t, ow in ows.items() if not ow.is_empty()}


async def apply_voice(guild: discord.Guild, record: dict, reason: str = "Ses kanalı ayarı değişti"):
    channel = guild.get_channel(record["channel_id"])
    if channel is None:
        return
    category = guild.get_channel(VOICE_CATEGORY_ID)
    if not isinstance(category, discord.CategoryChannel):
        category = channel.category
    if category is None:
        return
    await channel.edit(overwrites=build_voice_overwrites(guild, category, record), reason=reason)


async def create_voice(guild: discord.Guild, member: discord.Member):
    category = guild.get_channel(VOICE_CATEGORY_ID)
    if not isinstance(category, discord.CategoryChannel):
        raise RuntimeError("ses kategorisi bulunamadı")
    if len(category.channels) >= 50:
        raise VoiceCategoryFull()
    if len(guild.channels) > 495:
        raise RuntimeError("sunucu kanal limitine çok yakın")

    record = new_voice_record(member.id)
    channel = await category.create_voice_channel(
        voice_channel_name(member),
        overwrites=build_voice_overwrites(guild, category, record),
        reason=f"Ses kanalı: {member}",
    )
    record["channel_id"] = channel.id
    voice_records[channel.id] = record
    return channel


async def delete_voice(channel):
    voice_records.pop(channel.id, None)
    try:
        await channel.delete(reason="Ses kanalı boşaldı")
    except discord.NotFound:
        pass
    except Exception as e:
        print(f"⚠️ Ses kanalı silinemedi ({channel.id}): {e!r}")


async def handle_voice_create(member: discord.Member):
    """Oluşturma kanalına giren kişiye ses kanalı açar, taşır ve etiketler."""
    guild = member.guild

    # Cooldown: art arda girip çıkarak kanal açıp kapatmasın
    now = time.monotonic()
    if now - voice_cooldowns.get(member.id, -1e9) < VOICE_JOIN_COOLDOWN:
        try:
            await member.move_to(None, reason="Ses kanalı cooldown")
        except Exception:
            pass
        return
    voice_cooldowns[member.id] = now
    prune_cooldowns(voice_cooldowns, VOICE_JOIN_COOLDOWN)

    if member.id in creating_voices:
        return
    creating_voices.add(member.id)
    try:
        # Zaten ses kanalı varsa yenisini açma, onu kullan
        existing = get_voice_by_owner(member.id)
        if existing is not None:
            old = guild.get_channel(existing["channel_id"])
            if old is not None:
                await member.move_to(old, reason="Mevcut ses kanalına taşındı")
                return
            voice_records.pop(existing["channel_id"], None)

        channel = await create_voice(guild, member)
        try:
            await member.move_to(channel, reason="Ses kanalı oluşturuldu")
        except Exception as e:
            # Kişi bu arada çıkmış olabilir: boşta kanal kalmasın
            print(f"⚠️ {member} ses kanalına taşınamadı: {e!r}")
            await delete_voice(channel)
            return

        try:
            await channel.send(
                RESPONSES["voice_welcome"].format(member=member.mention),
                allowed_mentions=discord.AllowedMentions(users=[member], roles=False, everyone=False),
            )
        except Exception as e:
            print(f"⚠️ Ses kanalına karşılama mesajı gönderilemedi: {e!r}")
    except VoiceCategoryFull:
        print("⚠️ Ses kategorisi dolu.")
        try:
            await member.move_to(None, reason="Ses kategorisi dolu")
        except Exception:
            pass
    except Exception as e:
        print(f"❌ Ses kanalı oluşturulamadı: {e!r}")
    finally:
        creating_voices.discard(member.id)


def infer_voice_record(guild: discord.Guild, channel: discord.VoiceChannel):
    """Yeniden başlatma sonrası: sahibi 'mesaj yönet' yetkisi olan üyeden tanır. Bizim kanalımız değilse None."""
    me_id = guild.me.id if guild.me is not None else 0
    owner_id = None
    for target, ow in channel.overwrites.items():
        if isinstance(target, discord.Member) and target.id != me_id and ow.manage_messages is True:
            owner_id = target.id
            break
    if owner_id is None:
        return None

    record = new_voice_record(owner_id, channel.id)
    record["hidden"] = channel.overwrites_for(guild.default_role).view_channel is False
    for target, ow in channel.overwrites.items():
        if not isinstance(target, discord.Member) or target.bot or target.id in (owner_id, me_id):
            continue
        if ow.view_channel is False:
            record["blocked"].append(target.id)
        elif ow.view_channel is True:
            record["viewers"].append(target.id)
    record["blocked"] = record["blocked"][:LIST_LIMIT]
    record["viewers"] = record["viewers"][:LIST_LIMIT]
    return record


async def rebuild_voice_records(guild: discord.Guild):
    """Açılışta: kategorideki bizim ses kanallarını geri yükler, boş kalanları siler."""
    category = guild.get_channel(VOICE_CATEGORY_ID)
    if not isinstance(category, discord.CategoryChannel):
        print("⚠️ Ses kategorisi bulunamadı.")
        return

    voice_records.clear()
    restored = removed = 0
    for channel in list(category.voice_channels):
        if channel.id == VOICE_CREATE_CHANNEL_ID:
            continue
        record = infer_voice_record(guild, channel)
        if record is None:
            continue   # bizim açtığımız bir kanal değil, dokunma
        if not humans_in(channel):
            try:
                await channel.delete(reason="Boş ses kanalı temizlendi")
                removed += 1
            except Exception as e:
                print(f"⚠️ Boş ses kanalı silinemedi ({channel.id}): {e!r}")
            continue
        voice_records[channel.id] = record
        restored += 1
    print(f"✅ {restored} ses kanalı geri yüklendi, {removed} boş ses kanalı silindi.")


@tasks.loop(minutes=VOICE_SWEEP_MINUTES)
async def voice_sweep_loop():
    """Bir sebeple silinememiş boş ses kanallarını toplar."""
    guild = bot.get_guild(GUILD_ID)
    if guild is None:
        return
    for record in list(voice_records.values()):
        channel = guild.get_channel(record["channel_id"])
        if channel is None:
            voice_records.pop(record["channel_id"], None)
            continue
        if humans_in(channel):
            continue
        age = (datetime.now(timezone.utc) - channel.created_at).total_seconds()
        if age < 60:
            continue   # yeni açıldı, kişi henüz taşınıyor olabilir
        await delete_voice(channel)


@voice_sweep_loop.before_loop
async def before_voice_sweep():
    await bot.wait_until_ready()

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
    gp = guild.me.guild_permissions
    for perm in ("manage_channels", "manage_roles", "move_members"):
        if not (getattr(gp, perm) or gp.administrator):
            print(f"⚠️ Botun sunucu genelinde '{perm}' yetkisi yok (posting / ses sistemi için gerekli).")

    checks = {
        "Karşılama kanalı": (WELCOME_CHANNEL_ID, ["view_channel", "send_messages"]),
        "Log kanalı": (IMAGE_LOG_CHANNEL_ID, ["view_channel", "send_messages", "attach_files"]),
        "Bump kanalı": (BUMP_CHANNEL_ID, ["view_channel", "send_messages", "read_message_history"]),
        "Posting kayıt kanalı": (POSTING_DATA_CHANNEL_ID, ["view_channel", "send_messages", "read_message_history"]),
        "Posting kategorisi": (POSTING_CATEGORY_ID, ["view_channel", "manage_channels", "manage_roles"]),
        "Posting oluşturma kanalı": (POSTING_CREATE_CHANNEL_ID, ["view_channel", "send_messages", "read_message_history"]),
        "Ses oluşturma kanalı": (VOICE_CREATE_CHANNEL_ID, ["view_channel", "connect", "move_members"]),
        "Ses kategorisi": (VOICE_CATEGORY_ID, ["view_channel", "manage_channels", "manage_roles", "move_members"]),
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

    # on_ready yeniden bağlanmalarda tekrar tetiklenir; kurulum ve açılış mesajı bir kez yapılır
    if not posting_state["initialized"]:
        posting_state["initialized"] = True
        await announce_startup()
        await load_posting_records()
        await ensure_posting_panel()
        await rebuild_voice_records(guild)
        if not posting_check_loop.is_running():
            posting_check_loop.start()
        if not voice_sweep_loop.is_running():
            voice_sweep_loop.start()


@bot.event
async def on_member_join(member: discord.Member):
    print(f"👋 Yeni üye: {member} (sunucu: {member.guild.id})")
    if member.guild.id != GUILD_ID:
        return

    # Geri dönen üyenin posting yetkilerini (sahip / yazabilen / görebilen / engelli) hemen geri ver
    for record in postings_involving(member.id):
        try:
            await reconcile_posting(member.guild, record, reason=f"Üye geri döndü: {member}")
        except Exception as e:
            print(f"⚠️ {member} için posting yetkileri geri verilemedi: {e!r}")

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
    ):
        if message.attachments:
            await log_attachments(message)
        await log_gifs(message)

    await bot.process_commands(message)


@bot.event
async def on_raw_message_edit(payload: discord.RawMessageUpdateEvent):
    # Discord, link önizlemelerini (GIF embed'lerini) mesajdan sonra düzenleme olarak ekler
    if payload.guild_id != GUILD_ID or payload.message_id in gif_logged:
        return
    if payload.channel_id == IMAGE_LOG_CHANNEL_ID:
        return
    embeds = payload.data.get("embeds") or []
    if not any(e.get("type") in ("gifv", "image") for e in embeds):
        return

    channel = await get_channel_safe(payload.channel_id)
    if channel is None:
        return
    try:
        message = await channel.fetch_message(payload.message_id)
    except Exception:
        return
    if message.author.bot:
        return
    await log_gifs(message)


@bot.event
async def on_guild_channel_create(channel):
    """Sunucuda açılan HER kanalda @everyone'ın herkesi etiketleme yetkisini kapatır."""
    guild = channel.guild
    if guild.id != GUILD_ID:
        return
    everyone = guild.default_role
    overwrite = channel.overwrites_for(everyone)
    if overwrite.mention_everyone is False:
        return   # zaten kapalı (botun kendi açtığı kanallar böyle gelir)
    overwrite.mention_everyone = False
    try:
        await channel.set_permissions(
            everyone, overwrite=overwrite, reason="Yeni kanal: @everyone etiket yetkisi kapatıldı"
        )
    except Exception as e:
        print(f"⚠️ #{channel.name} için @everyone etiket yetkisi kapatılamadı: {e!r}")


@bot.event
async def on_guild_channel_delete(channel):
    if channel.guild.id != GUILD_ID:
        return
    voice_records.pop(channel.id, None)
    record = posting_records.get(channel.id)
    if record is not None:
        await mark_posting_deleted(record)


@bot.event
async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    if member.guild.id != GUILD_ID:
        return
    left, joined = before.channel, after.channel

    # Oluşturma kanalına girdi -> ses kanalı aç
    if (
        not member.bot
        and joined is not None
        and joined.id == VOICE_CREATE_CHANNEL_ID
        and (left is None or left.id != joined.id)
    ):
        await handle_voice_create(member)

    # Bir ses kanalından ayrıldı -> kimse kalmadıysa sil
    if (
        left is not None
        and left.id in voice_records
        and (joined is None or joined.id != left.id)
        and not humans_in(left)
    ):
        await delete_voice(left)

# ───────────────────────────────────────────────
#  SLASH COMMANDS — GENEL / YÖNETİCİ
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


@bot.tree.command(
    name="postingkaydet",
    description="Eski posting kanallarını sisteme alır ve kayıt kanalına loglar.",
)
@app_commands.describe(
    kanal="Kaydedilecek kanal (boş bırakırsan kategorideki kayıtsız tüm kanallar taranır)",
    sahip="Kanalın sahibi (boş bırakırsan kanalın yetkilerinden tahmin edilir)",
    onizleme="Evet dersen hiçbir şey kaydetmez, sadece ne yapacağını gösterir",
)
@app_commands.checks.has_permissions(administrator=True)
async def posting_kaydet(
    interaction: discord.Interaction,
    kanal: Optional[discord.TextChannel] = None,
    sahip: Optional[discord.Member] = None,
    onizleme: bool = False,
):
    if sahip is not None and kanal is None:
        await interaction.response.send_message("❌ Sahip seçtiysen kanalı da seçmelisin.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild
    category = guild.get_channel(POSTING_CATEGORY_ID)
    if not posting_state["loaded"]:
        await interaction.followup.send(RESPONSES["posting_not_ready"], ephemeral=True)
        return
    if not isinstance(category, discord.CategoryChannel):
        await interaction.followup.send("❌ Posting kategorisi bulunamadı.", ephemeral=True)
        return

    # Taranmayacak özel kanallar (panel, kayıt, log vb.)
    special = {POSTING_CREATE_CHANNEL_ID, POSTING_DATA_CHANNEL_ID, IMAGE_LOG_CHANNEL_ID}
    if kanal is not None:
        targets = [kanal]
    else:
        targets = [c for c in category.text_channels if c.id not in special and c.id not in posting_records]

    lines = []
    registered = 0
    for channel in targets:
        if channel.id in posting_records:
            lines.append(f"⏭️ {channel.mention}: zaten kayıtlı")
            continue
        if channel.id in special:
            lines.append(f"⏭️ {channel.mention}: özel kanal, atlandı")
            continue

        record = infer_posting_record(guild, channel, sahip.id if sahip else None)
        if record is None:
            lines.append(f"❓ {channel.mention}: sahibi tahmin edilemedi (`/postingkaydet kanal sahip` ile elle ver)")
            continue
        if get_posting_by_owner(record["owner_id"]) is not None:
            lines.append(f"⏭️ {channel.mention}: <@{record['owner_id']}> kişisinin zaten bir postingi kayıtlı")
            continue

        if onizleme:
            lines.append(f"👁️ {channel.mention} → <@{record['owner_id']}> olarak kaydedilecek")
            continue

        try:
            await save_posting_record(record)
            posting_records[channel.id] = record
            await reconcile_posting(guild, record, reason="Eski posting sisteme alındı")
            registered += 1
            lines.append(f"✅ {channel.mention} → <@{record['owner_id']}>")
        except Exception as e:
            print(f"❌ Posting kaydedilemedi ({channel.id}): {e!r}")
            lines.append(f"⚠️ {channel.mention}: kaydedilemedi ({e})")
        await asyncio.sleep(1)   # art arda yazmalarda rate limit'e girmemek için

    if not lines:
        lines.append("ℹ️ Kaydedilecek kayıtsız kanal bulunamadı.")
    header = "🔍 **Önizleme**" if onizleme else f"📥 **{registered} posting kaydedildi**"
    text = header + "\n" + "\n".join(lines)
    if len(text) > 1900:
        text = text[:1890].rsplit("\n", 1)[0] + "\n… (liste kısaltıldı)"
    await interaction.followup.send(text, ephemeral=True)

# ───────────────────────────────────────────────
#  SLASH COMMANDS — POSTING SAHİBİ (sadece kendi postinginde)
# ───────────────────────────────────────────────


@bot.tree.command(name="postaciklama", description="Posting kanalının açıklamasını değiştirir.")
@app_commands.describe(aciklama="Yeni kanal açıklaması")
@posting_owner_only()
async def post_aciklama(interaction: discord.Interaction, aciklama: app_commands.Range[str, 1, 1024]):
    channel = interaction.channel
    if not isinstance(channel, discord.TextChannel):
        await interaction.response.send_message(RESPONSES["posting_channel_unsupported"], ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    error = await run_guarded(channel.edit(topic=aciklama, reason=f"/postaciklama: {interaction.user}"))
    await interaction.followup.send(error or RESPONSES["posting_desc_updated"], ephemeral=True)


@bot.tree.command(name="postdurum", description="Posting kanalını herkesten gizler ya da tekrar açar.")
@app_commands.describe(durum="gizli ya da acik")
@app_commands.choices(durum=[
    app_commands.Choice(name="gizli", value="gizli"),
    app_commands.Choice(name="acik", value="acik"),
])
@posting_owner_only()
async def post_durum(interaction: discord.Interaction, durum: app_commands.Choice[str]):
    record = get_posting(interaction.channel)
    want_hidden = durum.value == "gizli"
    if record["hidden"] == want_hidden:
        key = "posting_already_hidden" if want_hidden else "posting_already_visible"
        await interaction.response.send_message(RESPONSES[key], ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    record["hidden"] = want_hidden
    error = await run_guarded(commit_posting(interaction.guild, record), timeout=60)
    await interaction.followup.send(
        error or RESPONSES["posting_hidden" if want_hidden else "posting_shown"], ephemeral=True
    )


@bot.tree.command(name="postizin", description="Birine kanalı görme izni verir ya da alır (alırsan kanalı göremez).")
@app_commands.describe(islem="ver ya da al", kullanici="İşlem yapılacak kişi")
@app_commands.choices(islem=[
    app_commands.Choice(name="ver", value="ver"),
    app_commands.Choice(name="al", value="al"),
])
@posting_owner_only()
async def post_izin(
    interaction: discord.Interaction,
    islem: app_commands.Choice[str],
    kullanici: discord.Member,
):
    record = get_posting(interaction.channel)
    if kullanici.bot or kullanici.id == record["owner_id"]:
        await interaction.response.send_message(RESPONSES["target_invalid"], ephemeral=True)
        return

    giving = islem.value == "ver"
    result = set_view_access(record, kullanici.id, giving)
    if result == "full":
        await interaction.response.send_message(RESPONSES["list_full"].format(limit=LIST_LIMIT), ephemeral=True)
        return
    if result == "already":
        key = "view_already" if giving else "view_taken_already"
        await interaction.response.send_message(RESPONSES[key].format(member=kullanici.mention), ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    error = await run_guarded(commit_posting(interaction.guild, record), timeout=60)
    key = "view_given" if giving else "view_taken"
    await interaction.followup.send(error or RESPONSES[key].format(member=kullanici.mention), ephemeral=True)


@bot.tree.command(name="postmisafir", description="Birine kanalda yazma izni verir ya da alır.")
@app_commands.describe(islem="ver ya da al", kullanici="İşlem yapılacak kişi")
@app_commands.choices(islem=[
    app_commands.Choice(name="ver", value="ver"),
    app_commands.Choice(name="al", value="al"),
])
@posting_owner_only()
async def post_misafir(
    interaction: discord.Interaction,
    islem: app_commands.Choice[str],
    kullanici: discord.Member,
):
    record = get_posting(interaction.channel)
    if kullanici.bot or kullanici.id == record["owner_id"]:
        await interaction.response.send_message(RESPONSES["target_invalid"], ephemeral=True)
        return

    giving = islem.value == "ver"
    writers = record["writers"]
    mention = kullanici.mention
    if giving:
        if kullanici.id in record["blocked"]:
            await interaction.response.send_message(RESPONSES["posting_write_blocked"].format(member=mention), ephemeral=True)
            return
        if kullanici.id in writers:
            await interaction.response.send_message(RESPONSES["posting_write_already"].format(member=mention), ephemeral=True)
            return
        if len(writers) >= LIST_LIMIT:
            await interaction.response.send_message(RESPONSES["list_full"].format(limit=LIST_LIMIT), ephemeral=True)
            return
        writers.append(kullanici.id)
    else:
        if kullanici.id not in writers:
            await interaction.response.send_message(RESPONSES["posting_write_none"].format(member=mention), ephemeral=True)
            return
        writers.remove(kullanici.id)

    await interaction.response.defer(ephemeral=True)
    error = await run_guarded(commit_posting(interaction.guild, record), timeout=60)
    key = "posting_write_given" if giving else "posting_write_taken"
    await interaction.followup.send(error or RESPONSES[key].format(member=mention), ephemeral=True)


@bot.tree.command(name="postnsfw", description="Posting kanalını NSFW (yaş sınırlı) olarak işaretler ya da işareti kaldırır.")
@app_commands.describe(durum="evt = NSFW yap, hyr = NSFW'yi kaldır")
@app_commands.choices(durum=[
    app_commands.Choice(name="evt", value="evt"),
    app_commands.Choice(name="hyr", value="hyr"),
])
@posting_owner_only()
async def post_nsfw(interaction: discord.Interaction, durum: app_commands.Choice[str]):
    channel = interaction.channel
    if not isinstance(channel, discord.TextChannel):
        await interaction.response.send_message(RESPONSES["posting_channel_unsupported"], ephemeral=True)
        return

    want_nsfw = durum.value == "evt"
    if channel.nsfw == want_nsfw:
        key = "posting_nsfw_already_on" if want_nsfw else "posting_nsfw_already_off"
        await interaction.response.send_message(RESPONSES[key], ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    error = await run_guarded(channel.edit(nsfw=want_nsfw, reason=f"/postnsfw: {interaction.user}"))
    await interaction.followup.send(
        error or RESPONSES["posting_nsfw_on" if want_nsfw else "posting_nsfw_off"], ephemeral=True
    )


@bot.tree.command(name="postsil", description="Posting kanalını kalıcı olarak siler.")
@posting_owner_only()
async def post_sil(interaction: discord.Interaction):
    view = ConfirmPostingDeleteView(interaction.user.id, interaction.channel.id)
    await interaction.response.send_message(RESPONSES["posting_delete_confirm"], view=view, ephemeral=True)

# ───────────────────────────────────────────────
#  SLASH COMMANDS — SES KANALI SAHİBİ (sadece kendi ses kanalının yazı sohbetinde)
# ───────────────────────────────────────────────


@bot.tree.command(name="sesaciklama", description="Ses kanalının durum mesajını değiştirir.")
@app_commands.describe(mesaj="Yeni durum mesajı")
@voice_owner_only()
async def ses_aciklama(interaction: discord.Interaction, mesaj: app_commands.Range[str, 1, 500]):
    channel = interaction.channel
    if not isinstance(channel, discord.VoiceChannel):
        await interaction.response.send_message(RESPONSES["voice_channel_unsupported"], ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    route = discord.http.Route("PUT", "/channels/{channel_id}/voice-status", channel_id=channel.id)
    error = await run_guarded(bot.http.request(route, json={"status": mesaj}))
    await interaction.followup.send(error or RESPONSES["voice_status_updated"], ephemeral=True)


@bot.tree.command(name="sesdurum", description="Ses kanalını herkesten gizler ya da tekrar açar.")
@app_commands.describe(durum="gizli ya da acik")
@app_commands.choices(durum=[
    app_commands.Choice(name="gizli", value="gizli"),
    app_commands.Choice(name="acik", value="acik"),
])
@voice_owner_only()
async def ses_durum(interaction: discord.Interaction, durum: app_commands.Choice[str]):
    record = get_voice(interaction.channel)
    want_hidden = durum.value == "gizli"
    if record["hidden"] == want_hidden:
        key = "voice_already_hidden" if want_hidden else "voice_already_visible"
        await interaction.response.send_message(RESPONSES[key], ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    record["hidden"] = want_hidden
    error = await run_guarded(apply_voice(interaction.guild, record), timeout=60)
    await interaction.followup.send(
        error or RESPONSES["voice_hidden" if want_hidden else "voice_shown"], ephemeral=True
    )


@bot.tree.command(name="sesizin", description="Birine ses kanalını görme izni verir ya da alır (alırsan kanalı göremez).")
@app_commands.describe(islem="ver ya da al", kullanici="İşlem yapılacak kişi")
@app_commands.choices(islem=[
    app_commands.Choice(name="ver", value="ver"),
    app_commands.Choice(name="al", value="al"),
])
@voice_owner_only()
async def ses_izin(
    interaction: discord.Interaction,
    islem: app_commands.Choice[str],
    kullanici: discord.Member,
):
    record = get_voice(interaction.channel)
    if kullanici.bot or kullanici.id == record["owner_id"]:
        await interaction.response.send_message(RESPONSES["target_invalid"], ephemeral=True)
        return

    giving = islem.value == "ver"
    result = set_view_access(record, kullanici.id, giving)
    if result == "full":
        await interaction.response.send_message(RESPONSES["list_full"].format(limit=LIST_LIMIT), ephemeral=True)
        return
    if result == "already":
        key = "view_already" if giving else "view_taken_already"
        await interaction.response.send_message(RESPONSES[key].format(member=kullanici.mention), ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    error = await run_guarded(apply_voice(interaction.guild, record), timeout=60)
    if error:
        await interaction.followup.send(error, ephemeral=True)
        return

    # Görme izni alınan kişi kanaldaysa bağlantısını kes
    if not giving and kullanici.voice is not None and kullanici.voice.channel is not None \
            and kullanici.voice.channel.id == record["channel_id"]:
        try:
            await kullanici.move_to(None, reason="Ses kanalından engellendi")
        except Exception:
            pass

    key = "view_given" if giving else "view_taken"
    await interaction.followup.send(RESPONSES[key].format(member=kullanici.mention), ephemeral=True)

# ───────────────────────────────────────────────
#  HATA YAKALAYICI
# ───────────────────────────────────────────────


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        msg = RESPONSES["err_missing_permissions"]
    elif isinstance(error, NotPostingOwner):
        msg = RESPONSES["err_not_posting_owner"]
    elif isinstance(error, NotVoiceOwner):
        msg = RESPONSES["err_not_voice_owner"]
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
