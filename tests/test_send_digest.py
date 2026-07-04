import re
import send_digest as sd

SCORES = {
    "participants": {
        "Kenny": {"total": 89, "countries": {"Spain": {"points": 18}},
                  "log": [{"country": "Spain", "event": "LAST_32_WIN", "points": 4,
                           "date": "2026-07-02", "opponent": "Austria", "matchId": 1}]},
        "Fiona": {"total": 74, "countries": {}, "log": []},
        "Alex": {"total": 60, "countries": {}, "log": []},
        "Edward": {"total": 59, "countries": {}, "log": []},
    },
}
NEW_EVENTS = [{"owner": "Kenny", "country": "Spain", "event": "LAST_32_WIN",
               "points": 4, "date": "2026-07-02", "opponent": "Austria", "matchId": 1}]
FLAG_CODES = {"Spain": "es", "Austria": "at", "England": "gb-eng", "Japan": "jp"}
FIXTURES = {"fixtures": [{"matchId": 9, "homeTeam": "England", "awayTeam": "Japan",
                          "utcDate": "2026-07-03T16:00:00Z", "stage": "LAST_32"}]}
OWNERS = {"England": "Fiona", "Japan": "Fiona", "Spain": "Kenny", "Austria": "Alex"}

EMOJI_RX = re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF⭐⚽]")

def _html(**kw):
    return sd.build_email_html(SCORES, NEW_EVENTS, flag_codes=FLAG_CODES,
                               fixtures=FIXTURES, owners=OWNERS, **kw)

def test_no_emoji_anywhere():
    html = _html()
    assert not EMOJI_RX.search(html)
    assert not EMOJI_RX.search(sd.build_subject(SCORES))

def test_brand_and_content():
    html = _html()
    assert "#0b120d" in html
    assert "Kenny" in html and "89" in html
    assert "flags/png/es.png" in html
    assert "won the Round of 32" in html

def test_gap_line_and_subject():
    assert "leads by 15" in sd.build_subject(SCORES)
    assert "Matchday" in sd.build_subject(SCORES)

def test_stakes_block_present_and_absent():
    assert "England" in _html(today="2026-07-03")
    html_no = sd.build_email_html(SCORES, NEW_EVENTS, flag_codes=FLAG_CODES,
                                  fixtures=None, owners=OWNERS, today="2026-07-03")
    # NOTE: deviates from the plan's literal `"stake" not in html_no.lower()` —
    # that substring is always present via the "McAndrew Sweepstake" brand
    # header, so the assertion as written could never pass. Checking the
    # stakes-block-specific phrase instead preserves the acceptance criterion
    # ("today's stakes" block silently omitted when there are no fixtures).
    assert "what's at stake" not in html_no.lower()
