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


EVENT_LABELS = {
    "GROUP_STAGE_WIN": "won in the Group Stage",
    "GROUP_STAGE_DRAW": "drew in the Group Stage",
    "QUALIFY_TOP_2": "qualified from the group (top 2)",
    "QUALIFY_BEST_THIRD": "qualified as a best third",
    "LAST_32_WIN": "won the Round of 32",
    "LAST_16_WIN": "won the Round of 16",
    "QUARTER_FINALS_WIN": "won the Quarter-Final",
    "SEMI_FINALS_WIN": "won the Semi-Final",
    "THIRD_PLACE_WIN": "won the 3rd Place Play-off",
    "FINAL_WIN": "won the World Cup Final",
}

STAGE_LABELS = {
    "GROUP_STAGE": "Group Stage", "LAST_32": "Round of 32", "LAST_16": "Round of 16",
    "QUARTER_FINALS": "Quarter-Final", "SEMI_FINALS": "Semi-Final",
    "THIRD_PLACE": "3rd Place Play-off", "FINAL": "Final",
}

TOURNAMENT_START = "2026-06-11"

INK, CREAM, GOLD, TERRA, DEEP = "#22301f", "#f2efe6", "#d9a441", "#c98a5b", "#0b120d"
SERIF = "Georgia,'Times New Roman',serif"
SANS = "-apple-system,'Segoe UI',Arial,sans-serif"
MONO = "'Courier New',Courier,monospace"


def matchday_number(date_iso):
    from datetime import date
    d0 = date.fromisoformat(TOURNAMENT_START)
    d1 = date.fromisoformat(date_iso)
    return max(1, (d1 - d0).days + 1)


def build_subject(scores, today=None):
    from datetime import datetime, timezone
    today = today or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    ranked = sorted(scores["participants"].items(), key=lambda x: x[1]["total"], reverse=True)
    md = matchday_number(today)
    (n1, p1), (n2, p2) = ranked[0], ranked[1]
    gap = p1["total"] - p2["total"]
    if gap == 0:
        return f"Sweepstake — {n1} and {n2} level at the top (Matchday {md})"
    return f"Sweepstake — {n1} leads by {gap} (Matchday {md})"


def _flag_img(country, flag_codes):
    code = flag_codes.get(country)
    if not code:
        return ""
    return (f'<img src="{SITE_URL}/flags/png/{code}.png" width="18" height="13" '
            f'alt="{country} flag" style="vertical-align:-2px;border:0">')


def _stakes_rows(fixtures, owners, today, flag_codes):
    if not fixtures:
        return ""
    todays = [f for f in fixtures.get("fixtures", []) if f["utcDate"][:10] == today]
    if not todays:
        return ""
    rows = ""
    for f in todays[:4]:
        ho, ao = owners.get(f["homeTeam"]), owners.get(f["awayTeam"])
        if ho and ao and ho == ao:
            stake = f"{ho} derby — both teams are {ho}'s"
        elif ho and ao:
            stake = f"{ho}'s {f['homeTeam']} against {ao}'s {f['awayTeam']}"
        elif ho or ao:
            stake = f"{(ho or ao)}'s {(f['homeTeam'] if ho else f['awayTeam'])} in action"
        else:
            stake = "Neutral fixture"
        stage = STAGE_LABELS.get(f["stage"], f["stage"])
        rows += (
            f'<tr><td style="padding:9px 14px;border-bottom:1px solid #e5e0d1">'
            f'<div style="font-family:{MONO};font-size:0.68rem;letter-spacing:2px;'
            f'text-transform:uppercase;color:#8a9284">{stage}</div>'
            f'<div style="font-family:{SANS};font-weight:700;font-size:0.92rem;color:{INK};'
            f'padding-top:2px">{_flag_img(f["homeTeam"], flag_codes)} {f["homeTeam"]} v '
            f'{f["awayTeam"]} {_flag_img(f["awayTeam"], flag_codes)}</div>'
            f'<div style="font-family:{SANS};font-size:0.8rem;color:#5a6b52;padding-top:2px">'
            f'What\'s at stake: {stake}</div></td></tr>')
    return (
        f'<h2 style="font-family:{SERIF};color:{INK};font-size:1.05rem;font-weight:600;'
        f'margin:26px 0 10px">Today\'s <em style="color:{TERRA}">stakes</em></h2>'
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        f'style="background:{CREAM};border-radius:8px;border-collapse:separate;'
        f'overflow:hidden">{rows}</table>')


def build_email_html(scores, new_events, flag_codes=None, fixtures=None,
                     owners=None, today=None):
    from datetime import datetime, timezone
    flag_codes = flag_codes or {}
    owners = owners or {}
    now = datetime.now(timezone.utc)
    today = today or now.strftime("%Y-%m-%d")
    ranked = sorted(scores["participants"].items(), key=lambda x: x[1]["total"], reverse=True)
    md = matchday_number(today)
    leader_name, leader = ranked[0]
    gap = leader["total"] - ranked[1][1]["total"]

    gains = {}
    for e in new_events:
        gains[e["owner"]] = gains.get(e["owner"], 0) + e.get("points", 0)

    standings_rows = ""
    for rank, (name, data) in enumerate(ranked, 1):
        is_leader = rank == 1
        bg = "#faf3e0" if is_leader else "#ffffff"
        border = f'border-left:3px solid {GOLD};' if is_leader else ''
        gain = gains.get(name, 0)
        chip = (f' <span style="font-family:{MONO};font-size:0.7rem;color:#4a7d4f;'
                f'font-weight:700">&#9650; {gain} today</span>') if gain > 0 else ""
        standings_rows += (
            f'<tr style="background:{bg}">'
            f'<td style="{border}padding:12px 14px;font-family:{SERIF};font-style:italic;'
            f'font-size:1.05rem;color:{"#b3763f" if is_leader else "#8a9284"};width:26px">{rank}</td>'
            f'<td style="padding:12px 6px;font-family:{SANS};font-weight:700;'
            f'font-size:0.95rem;color:{INK}">{name}{chip}</td>'
            f'<td style="padding:12px 14px;font-family:{MONO};font-weight:700;'
            f'font-size:1.05rem;text-align:right;color:'
            f'{"#9a7118" if is_leader else INK}">{data["total"]}</td></tr>')

    events_rows = ""
    for e in new_events[:20]:
        label = EVENT_LABELS.get(e["event"], e["event"])
        is_qual = e["event"] in ("QUALIFY_TOP_2", "QUALIFY_BEST_THIRD")
        opp = f' vs {e["opponent"]}' if e.get("opponent") and not is_qual else ""
        events_rows += (
            f'<tr><td style="padding:9px 0 9px 14px;width:44px;vertical-align:top;'
            f'border-bottom:1px solid #f0ede4">'
            f'<span style="font-family:{MONO};background:{DEEP};color:#f2f0e9;'
            f'font-weight:700;padding:2px 7px;font-size:0.8rem">+{e["points"]}</span></td>'
            f'<td style="padding:9px 14px;font-family:{SANS};font-size:0.88rem;color:{INK};'
            f'border-bottom:1px solid #f0ede4"><strong>{e["owner"]}</strong> — '
            f'{_flag_img(e["country"], flag_codes)} {e["country"]} {label}{opp}'
            f'<span style="font-family:{MONO};font-size:0.7rem;color:#8a9284"> · '
            f'{e.get("date", "")}</span></td></tr>')
    if not events_rows:
        events_rows = (f'<tr><td style="padding:12px 14px;font-family:{SANS};color:#8a9284;'
                       f'font-style:italic;font-size:0.85rem">No new points since the last '
                       f'update.</td></tr>')

    stakes_html = _stakes_rows(fixtures, owners, today, flag_codes)
    day = format_day(now)
    gap_line = (f"{leader_name} leads by {gap}" if gap
                else f"{leader_name} level at the top")

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:24px 12px;background:#e8e4d8">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
    style="max-width:540px;margin:0 auto;background:#ffffff;border-collapse:separate;
    border-radius:12px;overflow:hidden">
    <tr><td style="background:{DEEP};padding:30px 28px">
      <div style="font-family:{MONO};font-size:0.66rem;letter-spacing:4px;
        text-transform:uppercase;color:{TERRA}">World Cup 2026 · Matchday {md}</div>
      <div style="font-family:{SERIF};font-size:1.5rem;color:#f2f0e9;padding-top:8px">
        McAndrew <em style="color:{GOLD}">Sweepstake</em></div>
      <div style="font-family:{MONO};font-size:0.7rem;color:#9aa89c;padding-top:8px;
        text-transform:uppercase;letter-spacing:2px">{day} {now.strftime('%B %Y')} ·
        {gap_line}</div>
    </td></tr>
    <tr><td style="padding:26px 28px">
      <h2 style="font-family:{SERIF};color:{INK};font-size:1.05rem;font-weight:600;
        margin:0 0 10px">The <em style="color:{TERRA}">standings</em></h2>
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
        style="border:1px solid #e5e0d1;border-radius:8px;border-collapse:separate;
        overflow:hidden">{standings_rows}</table>
      <h2 style="font-family:{SERIF};color:{INK};font-size:1.05rem;font-weight:600;
        margin:26px 0 10px">New <em style="color:{TERRA}">points</em></h2>
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0">{events_rows}</table>
      {stakes_html}
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
        <tr><td align="center" style="padding-top:30px">
          <a href="{SITE_URL}" style="display:inline-block;background:{DEEP};color:#f2f0e9;
            font-family:{SANS};font-weight:700;font-size:0.92rem;padding:14px 30px;
            border-radius:8px;text-decoration:none">View the live leaderboard &#8594;</a>
        </td></tr></table>
    </td></tr>
    <tr><td style="background:{CREAM};padding:14px 28px;text-align:center">
      <span style="font-family:{MONO};font-size:0.62rem;letter-spacing:2px;
        text-transform:uppercase;color:#8a9284">McAndrew Family · World Cup 2026</span>
    </td></tr>
  </table>
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
    test_mode = "--test" in sys.argv                     # NEW
    participants, _ = read_json("participants.json")
    scores, scores_sha = read_json("scores.json")

    try:                                                  # NEW (all optional data)
        flag_codes, _ = read_json("flag-codes.json")
    except Exception:
        flag_codes = {}
    try:
        fixtures, _ = read_json("fixtures.json")
    except Exception:
        fixtures = None

    new_events = new_events_since_last_email(scores)

    if not new_events and not (force or test_mode):
        print("No new points since last email. Skipping.")
        return

    subject = build_subject(scores)
    if test_mode:
        subject = f"[TEST] {subject}"

    recipients = [GMAIL_SENDER] if test_mode else list(participants["emails"].values())
    if not recipients:
        raise ValueError("No recipients found in participants.json emails")
    html_body = build_email_html(
        scores, new_events if new_events else [],
        flag_codes=flag_codes, fixtures=fixtures,
        owners=participants["countryToOwner"])
    send_email(subject, html_body, recipients)

    if test_mode:                                         # NEW: no state updates
        print(f"TEST email sent to {GMAIL_SENDER} only. State not updated.")
        return

    record_emailed(scores, new_events)
    scores["lastEmailAt"] = datetime.now(timezone.utc).isoformat()
    write_json("scores.json", scores, scores_sha, "Record email sent timestamp")
    print(f"Email sent to {len(recipients)} recipients.")


if __name__ == "__main__":
    main()
