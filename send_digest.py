import os
import sys
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timezone
from dotenv import load_dotenv
from github_utils import read_json, write_json

load_dotenv()

GMAIL_SENDER = os.getenv("GMAIL_SENDER", "edward.mcandrew20@gmail.com")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")

if not GMAIL_APP_PASSWORD:
    raise ValueError("GMAIL_APP_PASSWORD must be set in .env")

SITE_URL = "https://BandyBarbecue.github.io/mcandrew-sweepstake-2026"

RANK_EMOJI = {1: "🏆", 2: "🥈", 3: "🥉", 4: "😅"}

COUNTRY_FLAGS = {
    "Qatar": "🇶🇦", "Uruguay": "🇺🇾", "Morocco": "🇲🇦", "Argentina": "🇦🇷",
    "Norway": "🇳🇴", "Iran": "🇮🇷", "Croatia": "🇭🇷", "Spain": "🇪🇸",
    "Belgium": "🇧🇪", "Ivory Coast": "🇨🇮", "Mexico": "🇲🇽", "Czechia": "🇨🇿",
    "Bosnia & Herz.": "🇧🇦", "Japan": "🇯🇵", "Panama": "🇵🇦", "Senegal": "🇸🇳",
    "DR Congo": "🇨🇩", "Canada": "🇨🇦", "Cape Verde": "🇨🇻", "Jordan": "🇯🇴",
    "USA": "🇺🇸", "South Africa": "🇿🇦", "England": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "Colombia": "🇨🇴",
    "Haiti": "🇭🇹", "Brazil": "🇧🇷", "Sweden": "🇸🇪", "France": "🇫🇷",
    "South Korea": "🇰🇷", "Ecuador": "🇪🇨", "New Zealand": "🇳🇿",
    "Saudi Arabia": "🇸🇦", "Netherlands": "🇳🇱", "Turkey": "🇹🇷",
    "Paraguay": "🇵🇾", "Iraq": "🇮🇶",
    "Scotland": "🏴󠁧󠁢󠁳󠁣󠁴󠁿", "Egypt": "🇪🇬", "Australia": "🇦🇺", "Curaçao": "🇨🇼",
    "Ghana": "🇬🇭", "Austria": "🇦🇹", "Germany": "🇩🇪", "Tunisia": "🇹🇳",
    "Algeria": "🇩🇿", "Portugal": "🇵🇹", "Switzerland": "🇨🇭", "Uzbekistan": "🇺🇿",
}

EVENT_LABELS = {
    "GROUP_STAGE_WIN": "won in Group Stage",
    "GROUP_STAGE_DRAW": "drew in Group Stage",
    "QUALIFY_TOP_2": "qualified from Group (Top 2)",
    "QUALIFY_BEST_THIRD": "qualified as Best 3rd Place",
    "LAST_32_WIN": "won Round of 32",
    "LAST_16_WIN": "won Round of 16",
    "QUARTER_FINALS_WIN": "won Quarter-Final",
    "SEMI_FINALS_WIN": "won Semi-Final",
    "THIRD_PLACE_WIN": "won 3rd Place Play-off",
    "FINAL_WIN": "WON THE WORLD CUP! 🏆",
}


def event_key(owner, entry):
    """Stable identity for a log entry, used to track what has been emailed."""
    return f"{owner}|{entry.get('country', '')}|{entry.get('event', '')}|{entry.get('matchId', '')}"


def all_log_events(scores):
    events = []
    for owner, data in scores["participants"].items():
        for entry in data.get("log", []):
            events.append({"owner": owner, **entry})
    return events


def new_events_since_last_email(scores):
    """Return log entries not announced in any previous email.

    Events are matched by identity (emailedEvents), not by date: a date cutoff
    drops events processed the morning after they were played, because the
    match date equals the previous email's date.
    """
    events = all_log_events(scores)
    if "emailedEvents" in scores:
        emailed = set(scores["emailedEvents"])
        fresh = [e for e in events if event_key(e["owner"], e) not in emailed]
    elif scores.get("lastEmailAt"):
        # Legacy state without tracking: apply the old date cutoff once so the
        # first tracked run doesn't re-announce the whole tournament.
        cutoff = scores["lastEmailAt"][:10]
        fresh = [e for e in events if e.get("date", "") > cutoff]
    else:
        fresh = events
    return sorted(fresh, key=lambda e: e.get("date", ""), reverse=True)


def record_emailed(scores, new_events):
    """Mark new_events (and, on first migration, all historic events) as emailed."""
    emailed = set(scores.get("emailedEvents", []))
    if "emailedEvents" not in scores:
        cutoff = (scores.get("lastEmailAt") or "")[:10]
        for e in all_log_events(scores):
            if e.get("date", "") <= cutoff:
                emailed.add(event_key(e["owner"], e))
    emailed.update(event_key(e["owner"], e) for e in new_events)
    scores["emailedEvents"] = sorted(emailed)


def format_day(dt):
    """Return day number without leading zero, cross-platform."""
    return str(int(dt.strftime("%d")))


def build_email_html(scores, new_events):
    ranked = sorted(scores["participants"].items(), key=lambda x: x[1]["total"], reverse=True)
    now = datetime.now(timezone.utc)
    today = f"{format_day(now)} {now.strftime('%B %Y')}"

    # Points gained per player in this digest, shown as a chip in the standings
    gains = {}
    for e in new_events:
        gains[e["owner"]] = gains.get(e["owner"], 0) + e.get("points", 0)

    # Standings rows
    standings_rows = ""
    for rank, (name, data) in enumerate(ranked, 1):
        bg = "#1a472a" if rank == 1 else ("#f9f9f9" if rank % 2 == 0 else "#ffffff")
        color = "#ffffff" if rank == 1 else "#333333"
        emoji = RANK_EMOJI.get(rank, "")
        gain = gains.get(name, 0)
        if gain > 0:
            chip_style = ("background:rgba(245,197,24,0.25);color:#f5c518" if rank == 1
                          else "background:#e8f3ec;color:#1a472a")
            gain_chip = (f' <span style="{chip_style};font-weight:800;font-size:0.72rem;'
                         f'padding:2px 7px;border-radius:10px;white-space:nowrap">▲ {gain}</span>')
        else:
            gain_chip = ""
        standings_rows += f"""
        <tr style="background:{bg};color:{color};">
          <td style="padding:10px 14px;font-size:1rem;width:1%">{emoji}</td>
          <td style="padding:10px 14px;font-weight:700;font-size:0.95rem">{name}{gain_chip}</td>
          <td style="padding:10px 14px;font-weight:800;font-size:1rem;text-align:right;white-space:nowrap;color:{'#f5c518' if rank==1 else '#1a472a'}">{data['total']} pts</td>
        </tr>"""

    # Events rows
    events_rows = ""
    for e in new_events[:20]:
        flag = COUNTRY_FLAGS.get(e["country"], "🏳")
        label = EVENT_LABELS.get(e["event"], e["event"])
        opp = e.get("opponent", "")
        opp_flag = COUNTRY_FLAGS.get(opp, "")
        is_qualification = e["event"] in ("QUALIFY_TOP_2", "QUALIFY_BEST_THIRD")
        opp_part = f" vs {opp_flag} {opp}" if opp and not is_qualification else ""
        pts = e["points"]
        badge_bg = "#1a472a" if pts >= 4 else "#888888"
        events_rows += f"""
        <tr>
          <td style="padding:8px 14px;white-space:nowrap;width:1%;border-bottom:1px solid #f0f0f0;vertical-align:top">
            <span style="background:{badge_bg};color:#fff;font-weight:800;padding:2px 8px;border-radius:4px;font-size:0.85rem">+{pts}</span>
          </td>
          <td style="padding:8px 14px;font-size:0.9rem;border-bottom:1px solid #f0f0f0;word-break:break-word">
            <strong>{e['owner']}</strong> — {flag} {e['country']} {label}{opp_part}
          </td>
          <td style="padding:8px 14px;color:#888;font-size:0.78rem;white-space:nowrap;text-align:right;width:1%;border-bottom:1px solid #f0f0f0;vertical-align:top">{e.get('date','')}</td>
        </tr>"""

    if not events_rows:
        events_rows = '<tr><td colspan="3" style="padding:12px 14px;color:#888;text-align:center;font-style:italic">No new points since last update</td></tr>'

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:20px;background:#f0f2f0;font-family:-apple-system,'Segoe UI',Arial,sans-serif">
  <div style="max-width:520px;margin:0 auto;background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 2px 16px rgba(0,0,0,0.12)">

    <div style="background:#1a472a;padding:28px 24px;text-align:center;background-image:repeating-linear-gradient(0deg,rgba(255,255,255,0.03) 0px,rgba(255,255,255,0.03) 20px,transparent 20px,transparent 40px)">
      <div style="font-size:2.2rem;margin-bottom:4px">⚽</div>
      <div style="color:#ffffff;font-weight:800;font-size:1.1rem;letter-spacing:2px;text-transform:uppercase">McAndrew Family</div>
      <div style="color:#f5c518;font-size:0.75rem;letter-spacing:3px;text-transform:uppercase;margin-top:2px">WORLD CUP 2026 · SWEEPSTAKE</div>
      <div style="color:rgba(255,255,255,0.55);font-size:0.75rem;margin-top:6px">{today}</div>
    </div>

    <div style="padding:24px">
      <h2 style="color:#1a472a;font-size:1rem;font-weight:700;margin:0 0 12px">📊 Current Standings</h2>
      <table style="width:100%;border-collapse:collapse;border-radius:8px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,0.08)">
        {standings_rows}
      </table>

      <h2 style="color:#1a472a;font-size:1rem;font-weight:700;margin:22px 0 12px">⚡ Points Update</h2>
      <table style="width:100%;border-collapse:collapse">
        {events_rows}
      </table>

      <div style="text-align:center;margin-top:28px">
        <a href="{SITE_URL}"
           style="display:inline-block;background:#1a472a;color:#ffffff;font-weight:700;
                  font-size:0.95rem;padding:13px 28px;border-radius:8px;text-decoration:none;
                  letter-spacing:0.5px">
          View Live Leaderboard →
        </a>
      </div>
    </div>

    <div style="background:#f7f7f7;padding:12px 24px;text-align:center;color:#aaa;font-size:0.75rem;border-top:1px solid #eee">
      McAndrew Family World Cup 2026 Sweepstake
    </div>
  </div>
</body>
</html>"""


def send_email(subject, html_body, recipients):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = GMAIL_SENDER
    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText(html_body, "html", "utf-8"))
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_SENDER, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_SENDER, recipients, msg.as_string())
    except smtplib.SMTPException as e:
        raise RuntimeError(f"Failed to send email: {e}") from e


def main():
    force = "--force" in sys.argv
    participants, _ = read_json("participants.json")
    scores, scores_sha = read_json("scores.json")

    new_events = new_events_since_last_email(scores)

    if not new_events and not force:
        print("No new points since last email. Skipping.")
        return

    now = datetime.now(timezone.utc)
    today_str = f"{format_day(now)} {now.strftime('%B')}"
    subject = f"⚽ Sweepstake Update — {today_str}"

    recipients = list(participants["emails"].values())
    if not recipients:
        raise ValueError("No recipients found in participants.json emails")
    html_body = build_email_html(scores, new_events if new_events else [])
    send_email(subject, html_body, recipients)

    record_emailed(scores, new_events)
    scores["lastEmailAt"] = datetime.now(timezone.utc).isoformat()
    write_json("scores.json", scores, scores_sha, "Record email sent timestamp")
    print(f"Email sent to {len(recipients)} recipients.")


if __name__ == "__main__":
    main()
