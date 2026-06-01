#!/usr/bin/env python3
"""
RSS更新メール通知スクリプト
対象: https://channel-tono.blog.jp/
宛先: yoshiki.nakmr@gmail.com
"""

import json
import os
import smtplib
import sys
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import feedparser

# ===== 設定 =====
RSS_URL = "https://channel-tono.blog.jp/index.rdf"
TO_EMAIL = "yoshiki.nakmr@gmail.com"
FROM_EMAIL = "yoshiki.nakmr@gmail.com"  # 送信元（同じGmailアドレス）

# Gmailアプリパスワード（環境変数から読む）
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")

# 既読記事IDの保存ファイル
SEEN_FILE = Path(__file__).parent / "seen_entries.json"
# =================


def load_seen() -> set:
    """既読記事IDを読み込む"""
    if SEEN_FILE.exists():
        with open(SEEN_FILE) as f:
            return set(json.load(f))
    return set()


def save_seen(seen: set):
    """既読記事IDを保存する"""
    # 最新1000件だけ保持（肥大化防止）
    seen_list = list(seen)[-1000:]
    with open(SEEN_FILE, "w") as f:
        json.dump(seen_list, f)


def send_email(subject: str, body: str):
    """Gmailでメール送信"""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = FROM_EMAIL
    msg["To"] = TO_EMAIL

    msg.attach(MIMEText(body, "plain", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(FROM_EMAIL, GMAIL_APP_PASSWORD)
        server.sendmail(FROM_EMAIL, TO_EMAIL, msg.as_string())


def main():
    if not GMAIL_APP_PASSWORD:
        print("エラー: 環境変数 GMAIL_APP_PASSWORD が設定されていません。")
        print("設定方法: export GMAIL_APP_PASSWORD='xxxx xxxx xxxx xxxx'")
        sys.exit(1)

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] RSSチェック開始...")

    feed = feedparser.parse(RSS_URL)
    if feed.bozo:
        print(f"警告: RSS取得に問題がありました: {feed.bozo_exception}")

    seen = load_seen()
    new_entries = []

    for entry in feed.entries:
        entry_id = entry.get("id") or entry.get("link") or entry.get("title")
        if entry_id not in seen:
            new_entries.append(entry)
            seen.add(entry_id)

    if not new_entries:
        print("新着記事なし。")
        return

    print(f"新着 {len(new_entries)} 件を送信します...")

    for entry in reversed(new_entries):  # 古い順に送信
        title = entry.get("title", "(タイトルなし)")
        link = entry.get("link", "")
        published = entry.get("published", "")

        # 本文を取得（summary または content）
        content = ""
        if hasattr(entry, "content"):
            content = entry.content[0].value
        elif hasattr(entry, "summary"):
            content = entry.summary

        # HTMLタグを簡易除去
        import re
        content_plain = re.sub(r"<[^>]+>", "", content).strip()
        content_plain = re.sub(r"\n{3,}", "\n\n", content_plain)

        subject = f"【channel-tono更新】{title}"
        body = f"""{title}
{'=' * 40}
{published}

{content_plain}

{'=' * 40}
元記事: {link}
"""
        send_email(subject, body)
        print(f"  送信済み: {title}")

    save_seen(seen)
    print("完了！")


if __name__ == "__main__":
    main()
