#!/usr/bin/env python3
"""
Job Watcher Agent
Searches multiple job sources for any postings that match keywords like
"python", "django", "fast job", "freelancing job" and notifies you.

Features:
- Pluggable sources (RemoteOK API, Indeed RSS, and custom URLs)
- Optional local SQLite DB (disabled by default in this copy)
- Notifications via Telegram bot or SMTP email
- Single-run script suitable for running as a cron job or scheduler

Usage:
1. Edit the CONFIG section below with your notification settings.
2. Install dependencies: pip install requests feedparser beautifulsoup4
3. Run: python job_agent.py
4. To run continuously, install as cron or systemd timer (example in comments).

Note: This script doesn't bypass any site's anti-scraping rules. If you need
heavy usage, check each site's terms and prefer official APIs where available.
"""

import requests
import feedparser
import time
import smtplib
from email.mime.text import MIMEText
from email.header import Header
from typing import List, Dict
import hashlib
import os

# ========================= CONFIG ==========================
DB_PATH = "jobs_seen.db"  # DB support left in file but disabled by default
KEYWORDS = ["python", "django","fastapi", "fast job", "freelancing job", "freelance"]
SOURCES = {
    "remoteok": True,  # Disabled due to PythonAnywhere proxy issues
    "custom_feeds": True,
}
CUSTOM_FEEDS = [
    # Verified working RSS feeds from global platforms
    'https://weworkremotely.com/categories/remote-programming-jobs.rss',
    'https://stackoverflow.com/jobs/feed?tags=python;django&sort=i',
    'https://remotive.io/remote-jobs/software-dev.rss',
    'https://pythonjobs.github.io/feed.xml',
    'https://jobs.github.com/positions.atom?description=python&location=',
    # Additional global Python/Django job feeds
    'https://www.django-coders.com/jobs/rss',
    'https://www.djangojobs.net/feed/',
    'https://pythonremotejobs.com/feed/',
    'https://www.workintech.io/jobs/feed/?categories=python',
    'https://www.freedjangojobs.com/feed/',
    'https://remote4me.com/remote-dev-jobs/rss/',
]

# Notification via Telegram (recommended)
TELEGRAM_BOT_TOKEN = ""  # put your bot token here
TELEGRAM_CHAT_ID = ""    # chat id to send messages to

# Notification via email (fallback)
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587  # Gmail uses 587
SMTP_USER = ""
SMTP_PASS = ""
EMAIL_TO = ""
EMAIL_FROM = SMTP_USER

# Matching behaviour
MIN_KEYWORD_MATCH = 1  # number of keywords that must match (1 means any)
USER_AGENT = "JobWatcherBot/1.0 (+https://example.com)"
# ===========================================================


# init_db DISABLED (not saving to DB by default)
def init_db(path: str = DB_PATH):
    """Return None when DB is disabled. If you want DB functionality,
    replace this function with a working sqlite3-based implementation.
    """
    return None  # No database used in this variant


def make_id(text: str) -> str:
    return hashlib.sha1((text or "").encode('utf-8')).hexdigest()


# seen_contains DISABLED — always treat as new (returns False)
def seen_contains(conn, _id: str) -> bool:
    # When DB is disabled, always indicate the job is new so it will be shown.
    return False


# mark_seen DISABLED — do nothing
def mark_seen(conn, _id: str, title: str, link: str, source: str):
    # No-op when DB is disabled. Kept around so code can call it safely.
    pass


def keywords_match(text: str, keywords: List[str], min_match: int = MIN_KEYWORD_MATCH) -> List[str]:
    text_l = (text or "").lower()
    found = [k for k in keywords if k.lower() in text_l]
    return found if len(found) >= min_match else []


# -------------------- Source fetchers --------------------

def fetch_remoteok(keywords: List[str]) -> List[Dict]:
    """Fetch RemoteOK API and return job dicts containing title, link, id, description"""
    url = "https://remoteok.com/api"
    headers = {"User-Agent": USER_AGENT}
    try:
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        data = r.json()
        results = []
        # RemoteOK returns a list of job dicts, with the first element often being metadata
        for item in data:
            if not isinstance(item, dict):
                continue
            if 'position' in item or 'title' in item:
                title = item.get('position') or item.get('title') or ''
                description = item.get('description', '')
                company = item.get('company', '')
                link = item.get('url') or item.get('apply_url') or ''
                combined = f"{title} {company} {description}"
                matches = keywords_match(combined, keywords)
                if matches:
                    results.append({
                        'id': make_id(link or title),
                        'title': title,
                        'link': link,
                        'description': description,
                        'source': 'remoteok',
                        'matches': matches,
                    })
        return results
    except Exception as e:
        print(f"RemoteOK fetch error: {e}")
        return []


def fetch_rss_feed(feed_url: str, keywords: List[str]) -> List[Dict]:
    try:
        feed = feedparser.parse(feed_url)
        results = []
        for entry in getattr(feed, 'entries', []):
            title = entry.get('title', '')
            link = entry.get('link', '')
            summary = entry.get('summary', '')
            combined = f"{title} {summary}"
            matches = keywords_match(combined, keywords)
            if matches:
                results.append({
                    'id': make_id(link or title),
                    'title': title,
                    'link': link,
                    'description': summary,
                    'source': feed_url,
                    'matches': matches,
                })
        return results
    except Exception as e:
        print(f"RSS fetch error for {feed_url}: {e}")
        return []


def fetch_indeed_rss(keywords: List[str]) -> List[Dict]:
    # Construct a simple indeed rss query (this may require adjusting the domain per country)
    q = "+".join([k.replace(' ', '+') for k in keywords if ' ' not in k])
    # We'll search for 'python django' as the primary phrase; Indeed's query format may vary by region
    feed_url = f"https://www.indeed.com/rss?q=python+django"
    return fetch_rss_feed(feed_url, keywords)


def fetch_custom_feeds(feeds: List[str], keywords: List[str]) -> List[Dict]:
    results = []
    for f in feeds:
        results.extend(fetch_rss_feed(f, keywords))
    return results


# -------------------- Notification helpers --------------------

def notify_telegram(bot_token: str, chat_id: str, text: str) -> bool:
    if not bot_token or not chat_id:
        return False
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    try:
        r = requests.post(url, json=payload, timeout=10)
        r.raise_for_status()
        return True
    except Exception as e:
        print(f"Telegram notify failed: {e}")
        return False


def notify_email(smtp_host: str, smtp_port: int, user: str, password: str, frm: str, to: str, subject: str, body: str) -> bool:
    try:
        msg = MIMEText(body, "html", "utf-8")
        msg['Subject'] = Header(subject, 'utf-8')
        msg['From'] = frm
        msg['To'] = to
        s = smtplib.SMTP(smtp_host, smtp_port, timeout=15)
        s.starttls()
        s.login(user, password)
        s.sendmail(frm, [to], msg.as_string())
        s.quit()
        return True
    except Exception as e:
        print(f"Email notify failed: {e}")
        return False


# -------------------- Main agent --------------------

def run_once():
    """Run a single pass: fetch jobs from enabled sources, collect matches, and notify."""
    conn = None  # DB disabled
    found_new = []

    # 1) RemoteOK
    if SOURCES.get('remoteok'):
        print("Checking RemoteOK...")
        jobs = fetch_remoteok(KEYWORDS)
        for j in jobs:
            # DB disabled — treating as new
            mark_seen(conn, j['id'], j['title'], j['link'], j['source'])
            found_new.append(j)

    # 2) Indeed RSS
    if SOURCES.get('indeed_rss'):
        print("Checking Indeed RSS...")
        jobs = fetch_indeed_rss(KEYWORDS)
        for j in jobs:
            # DB disabled — treating as new
            mark_seen(conn, j['id'], j['title'], j['link'], j['source'])
            found_new.append(j)

    # 3) Custom feeds
    if CUSTOM_FEEDS:
        print("Checking custom RSS feeds...")
        jobs = fetch_custom_feeds(CUSTOM_FEEDS, KEYWORDS)
        for j in jobs:
            # DB disabled — treating as new
            mark_seen(conn, j['id'], j['title'], j['link'], j['source'])
            found_new.append(j)

    # Summary and notifications
    if not found_new:
        print("No new matching jobs found.")
        return

    print(f"Found {len(found_new)} new matching jobs")
    # Build message
    lines = []
    for j in found_new:
        lines.append(f"<b>{j['title']}</b>\nMatches: {', '.join(j.get('matches', []))}\n{j['link']}")
    body = "<br><br>".join(lines)
    subject = f"{len(found_new)} New Job(s) Matching Your Keywords"

    sent = False
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        text = "\n\n".join([f"{j['title']} - {j['link']}\nMatches: {', '.join(j.get('matches', []))}" for j in found_new])
        sent = notify_telegram(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, text)
        if sent:
            print("Notified via Telegram")

    if not sent and SMTP_USER and SMTP_PASS:
        sent_email = notify_email(SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, EMAIL_FROM, EMAIL_TO, subject, body)
        if sent_email:
            print("Notified via Email")

    if not sent:
        print("Notifications not sent: configure TELEGRAM or SMTP settings in the script.")


# -------------------- Basic tests --------------------

def _run_basic_tests():
    """Simple unit checks to ensure core utilities behave as expected.

    These tests are lightweight and don't hit external networks. They simply
    validate keyword matching and id generation.
    """
    # Test keywords_match
    assert keywords_match("Senior Python Django developer", ["python", "django"]) != []
    assert keywords_match("No match here", ["python"]) == []

    # Test make_id determinism
    a = make_id("https://example.com/job/1")
    b = make_id("https://example.com/job/1")
    assert a == b

    # mark_seen and seen_contains are no-ops / deterministic when DB disabled
    assert seen_contains(None, "someid") is False
    try:
        mark_seen(None, "someid", "title", "link", "src")
    except Exception as e:
        raise AssertionError(f"mark_seen raised an exception: {e}")

    print("Basic tests passed.")


if __name__ == '__main__':
    # Run basic tests only if the environment variable RUN_JOB_AGENT_TESTS is set to '1'
    if os.environ.get('RUN_JOB_AGENT_TESTS') == '1':
        _run_basic_tests()

    run_once()


# ================== Example cron entry ==================
# Run every 15 minutes (edit path to python and file):
# */15 * * * * /usr/bin/python3 /home/youruser/job_agent.py >> /var/log/job_agent.log 2>&1
# =======================================================
