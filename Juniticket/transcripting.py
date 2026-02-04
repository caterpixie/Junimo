import html
import os
import re
from pathlib import Path
from datetime import datetime
import discord
import secrets
import boto3

TRANSCRIPT_DIR = "transcripts"

def safe_filename(name: str, max_len: int = 80) -> str:
    name = name.lower()
    name = re.sub(r"[^a-z0-9\-_.]+", "-", name)
    name = re.sub(r"-{2,}", "-", name).strip("-_.")
    return (name[:max_len] or "ticket")

def fmt_dt(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC")

async def export_ticket_to_html(channel: discord.TextChannel) -> str:
    """
    Discord dark transcript:
    - Header: guild icon + guild name + channel name + message count
    - Messages: avatar, username, BOT badge, timestamp
    - Replies: small "reply to message" line + left indent bar
    - Embeds: grey box with colored left border (approx)
    """
    Path(TRANSCRIPT_DIR).mkdir(parents=True, exist_ok=True)

    slug = secrets.token_urlsafe(16)
    fname = f"{slug}.html"
    out_path = Path(TRANSCRIPT_DIR) / fname

    guild = channel.guild
    guild_name = html.escape(guild.name if guild else "Unknown Guild")
    guild_icon = ""
    if guild and guild.icon:
        guild_icon = html.escape(guild.icon.url)

    msg_count = 0
    async for _ in channel.history(limit=None):
        msg_count += 1

    def esc(s: str) -> str:
        return html.escape(s or "")

    def is_image(filename: str) -> bool:
        fn = (filename or "").lower()
        return fn.endswith((".png", ".jpg", ".jpeg", ".webp", ".gif"))

    with out_path.open("w", encoding="utf-8") as f:
        f.write("<!doctype html><html><head><meta charset='utf-8'>\n")
        f.write("<meta name='viewport' content='width=device-width, initial-scale=1' />\n")
        f.write(f"<title>{esc(channel.name)} — Transcript</title>\n")

        f.write("""
<style>
:root{
  --bg: #0f131a;
  --bg2:#121826;
  --text:#e6e6e6;
  --muted:#9aa3b2;
  --link:#4db5ff;
  --line:#2a3140;
  --bubble:#171f2d;
  --embed:#1a2232;
}
*{box-sizing:border-box}
body{
  margin:0;
  font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
  background: #0f131a; /* solid Discord-like dark */
  color:var(--text);
}
a{ color:var(--link); text-decoration:none }
a:hover{ text-decoration:underline }

.wrapper{
  max-width: 1400px;
  margin: 0 auto;
  padding: 18px 24px 60px;
}

.header{
  display:flex;
  align-items:flex-start;
  gap: 12px;
  margin-bottom: 18px;
}
.gicon{
  width: 34px; height: 34px;
  border-radius: 10px;
  background: #0b0f18;
  border: 1px solid var(--line);
  flex: 0 0 auto;
}
.htext .gname{
  font-size: 22px;
  font-weight: 800;
  line-height: 1.1;
}
.htext .cname{
  font-size: 18px;
  margin-top: 2px;
  color: var(--text);
}
.htext .count{
  font-size: 18px;
  margin-top: 2px;
  color: var(--text);
}

.log{ margin-top: 12px; }

.msg{
  display:flex;
  gap: 12px;
  padding: 14px 0;
}
.avatar{
  width: 44px; height: 44px;
  border-radius: 50%;
  border: 1px solid var(--line);
  background: #0b0f18;
  flex: 0 0 auto;
}
.main{ min-width:0; width:100%; }

.topline{
  display:flex;
  align-items:baseline;
  flex-wrap:wrap;
  gap: 8px;
}
.name{
  font-weight: 800;
  font-size: 16px;
}
.badge{
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 6px;
  background: #3b82f6;
  color: #fff;
  font-weight: 800;
}
.time{
  font-size: 12px;
  color: var(--muted);
}

.content{
  margin-top: 4px;
  font-size: 14px;
  line-height: 1.35;
  white-space: pre-wrap;
  overflow-wrap:anywhere;
}

.replyWrap{
  margin-top: 6px;
  padding-left: 18px;
  border-left: 2px solid var(--line);
}
.replyLine{
  font-size: 12px;
  color: var(--muted);
  margin-bottom: 6px;
  display:flex;
  gap:6px;
  align-items:center;
}
.replyDot{
  width: 10px; height: 10px;
  border-left: 2px solid var(--line);
  border-bottom: 2px solid var(--line);
  border-bottom-left-radius: 6px;
  margin-left: -20px;
}

.embed{
  margin-top: 8px;
  background: rgba(255,255,255,0.04);
  border: 1px solid var(--line);
  border-left: 4px solid #ef4444; /* default-ish; we vary it if embed has color */
  border-radius: 6px;
  padding: 10px 12px;
  max-width: 860px;
}
.embed .etitle{
  font-weight: 800;
  margin-bottom: 4px;
}
.embed .edesc{
  color: var(--text);
  font-size: 13px;
  white-space: pre-wrap;
}
.attachments{
  margin-top: 8px;
  display:flex;
  flex-direction:column;
  gap: 8px;
  max-width: 860px;
}
.file{
  background: rgba(255,255,255,0.04);
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 8px 10px;
  font-size: 13px;
  color: var(--muted);
}
.preview{
  display:block;
  max-width: 860px;
  border-radius: 8px;
  border: 1px solid var(--line);
}
</style>
</head><body>
""")

        # --- Header ---
        f.write("<div class='wrapper'>\n")
        f.write("<div class='header'>\n")
        if guild_icon:
            f.write(f"<img class='gicon' src='{guild_icon}' alt='Guild icon' />\n")
        else:
            f.write("<div class='gicon'></div>\n")
        f.write("<div class='htext'>\n")
        f.write(f"<div class='gname'>{guild_name}</div>\n")
        f.write(f"<div class='cname'>{esc(channel.name)}</div>\n")
        f.write(f"<div class='count'>{msg_count} messages</div>\n")
        f.write("</div></div>\n")

        f.write("<div class='log'>\n")

        # --- Render messages ---
        async for m in channel.history(limit=None, oldest_first=True):
            author = m.author
            display_name = esc(getattr(author, "display_name", str(author)))
            author_tag = esc(str(author))
            avatar_url = esc(author.display_avatar.url) if getattr(author, "display_avatar", None) else ""
            timestamp = esc(fmt_dt(m.created_at))
            is_bot = bool(getattr(author, "bot", False))

            # message wrapper
            f.write("<div class='msg'>\n")
            if avatar_url:
                f.write(f"<img class='avatar' src='{avatar_url}' alt='avatar' />\n")
            else:
                f.write("<div class='avatar'></div>\n")

            f.write("<div class='main'>\n")
            f.write("<div class='topline'>\n")
            f.write(f"<span class='name'>{display_name}</span>\n")
            if is_bot:
                f.write("<span class='badge'>BOT</span>\n")
            f.write(f"<span class='time'>{timestamp}</span>\n")
            f.write("</div>\n")

            # Reply
            if m.reference and m.reference.message_id:
                f.write("<div class='replyWrap'>\n")
                f.write("<div class='replyLine'>\n")
                f.write("<span class='replyDot'></span>\n")
                f.write(f"<span>reply to message ({m.reference.message_id})</span>\n")
                f.write("</div>\n")

                # main content inside replyWrap
                content = esc(m.content or "")
                if content.strip():
                    f.write(f"<div class='content'>{content}</div>\n")
                f.write("</div>\n")  # replyWrap
            else:
                content = esc(m.content or "")
                if content.strip():
                    f.write(f"<div class='content'>{content}</div>\n")

            # Embeds
            if m.embeds:
                for e in m.embeds:
                    etitle = esc(getattr(e, "title", "") or "")
                    edesc = esc(getattr(e, "description", "") or "")
                    # Try to use embed color if present
                    left_color = "#ef4444"
                    try:
                        if e.color and e.color.value:
                            left_color = f"#{e.color.value:06x}"
                    except Exception:
                        pass

                    if etitle or edesc:
                        f.write(f"<div class='embed' style='border-left-color:{left_color}'>\n")
                        if etitle:
                            f.write(f"<div class='etitle'>{etitle}</div>\n")
                        if edesc:
                            f.write(f"<div class='edesc'>{edesc}</div>\n")
                        f.write("</div>\n")

            # Attachments
            if m.attachments:
                f.write("<div class='attachments'>\n")
                for a in m.attachments:
                    url = esc(a.url)
                    name = esc(a.filename)
                    f.write(f"<div class='file'>📎 <a href='{url}' target='_blank'>{name}</a></div>\n")
                    if is_image(a.filename):
                        f.write(f"<a href='{url}' target='_blank'><img class='preview' src='{url}' alt='{name}' /></a>\n")
                f.write("</div>\n")

            f.write("</div>\n</div>\n") 

        f.write("</div>\n</div>\n</body></html>")

    return str(out_path), slug

async def upload_transcript_to_r2(local_path: str, slug: str) -> str:
    """
    Upload transcript HTML to Cloudflare R2 using the S3-compatible API.
    Returns a public URL (public bucket / r2.dev or custom domain).
    """

    account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID")
    access_key = os.getenv("R2_ACCESS_KEY_ID")
    secret_key = os.getenv("R2_SECRET_ACCESS_KEY")
    bucket = os.getenv("R2_BUCKET")
    public_base = os.getenv("R2_PUBLIC_BASE")  # e.g. https://<your-bucket>.<something>.r2.dev
    prefix = os.getenv("R2_PREFIX", "transcripts")

    if not all([account_id, access_key, secret_key, bucket, public_base]):
        raise RuntimeError("Missing env vars: CLOUDFLARE_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET, R2_PUBLIC_BASE")

    endpoint_url = f"https://{account_id}.r2.cloudflarestorage.com"
    key = f"{prefix}/{slug}.html".replace("\\", "/")

    s3 = boto3.client(
        service_name="s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name="auto",
    )

    with open(local_path, "rb") as f:
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=f,
            ContentType="text/html; charset=utf-8",
        )

    return f"{public_base.rstrip('/')}/{key}"

def cleanup_file(path: str) -> None:
    try:
        os.remove(path)
    except FileNotFoundError:
        pass