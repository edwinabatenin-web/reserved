"""
Email notification service — Reserved™.

Sends founder notifications when feedback or early-access registrations arrive.

Configuration (environment variables):
    SMTP_HOST      — SMTP server hostname (e.g. smtp.gmail.com)
    SMTP_PORT      — SMTP port, default 587 (STARTTLS)
    SMTP_USER      — SMTP login username
    SMTP_PASS      — SMTP login password
    NOTIFY_EMAIL   — destination address for notifications

If SMTP_HOST is not set the notification is written to the application log
at INFO level instead of raising an error.  This allows the app to start
and run without email configured (local dev, early staging).
"""

from __future__ import annotations

import html as _html
import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

log = logging.getLogger(__name__)


def _smtp_configured() -> bool:
    return bool(os.environ.get("SMTP_HOST") and os.environ.get("NOTIFY_EMAIL"))


def _send(subject: str, body_text: str, body_html: str | None = None) -> bool:
    """
    Send an email via SMTP.  Returns True on success, False on failure.
    Never raises — all exceptions are caught and logged.
    """
    host      = os.environ.get("SMTP_HOST", "")
    port      = int(os.environ.get("SMTP_PORT", "587"))
    user      = os.environ.get("SMTP_USER", "")
    password  = os.environ.get("SMTP_PASS", "")
    recipient = os.environ.get("NOTIFY_EMAIL", "")
    sender    = user or recipient

    if not host or not recipient:
        log.info("SMTP not configured — notification logged only.\nSubject: %s\n%s", subject, body_text)
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"Reserved™ Notifications <{sender}>"
        msg["To"]      = recipient

        msg.attach(MIMEText(body_text, "plain", "utf-8"))
        if body_html:
            msg.attach(MIMEText(body_html, "html", "utf-8"))

        with smtplib.SMTP(host, port, timeout=10) as smtp:
            smtp.ehlo()
            if port != 465:
                smtp.starttls()
                smtp.ehlo()
            if user and password:
                smtp.login(user, password)
            smtp.sendmail(sender, [recipient], msg.as_string())

        log.info("Notification email sent: %s", subject)
        return True

    except Exception as exc:  # noqa: BLE001
        log.warning("Failed to send notification email (%s): %s", subject, exc)
        return False


# ── Public helpers ────────────────────────────────────────────────────────────

def notify_feedback(data: dict) -> bool:
    """Send a founder notification for a new feedback submission."""
    subject = "Reserved™ — New feedback received"

    # Plain-text body — no escaping needed
    lines = [
        "New feedback submission",
        "=" * 40,
        f"Intuitive:   {data.get('intuitive', '—')} / 5",
        f"Useful:      {data.get('useful', '—')} / 5",
        f"Trustworthy: {data.get('trustworthy', '—')} / 5",
        f"Would use:   {data.get('would_use', '—')}",
        f"Area:        {data.get('area', '—')}",
        "",
        "Comments:",
        data.get("comments") or "(none)",
        "",
        f"Email:       {data.get('email') or '(not provided)'}",
        f"Browser:     {data.get('browser', '—')}",
        f"Device:      {data.get('device', '—')}",
        f"Page:        {data.get('page_url') or '—'}",
    ]
    body = "\n".join(lines)

    # HTML body — all user-supplied values must be escaped to prevent XSS
    # if the email is rendered in a webmail client that interprets HTML.
    e = _html.escape
    intuitive_h    = e(str(data.get("intuitive",    "—")))
    useful_h       = e(str(data.get("useful",       "—")))
    trustworthy_h  = e(str(data.get("trustworthy",  "—")))
    would_use_h    = e(str(data.get("would_use",    "") or "—"))
    area_h         = e(str(data.get("area",         "") or "—"))
    email_h        = e(str(data.get("email",        "") or ""))
    browser_h      = e(str(data.get("browser",      "") or "—"))
    device_h       = e(str(data.get("device",       "") or "—"))
    page_url_h     = e(str(data.get("page_url",     "") or "—"))
    comments_h     = e(str(data.get("comments",     "") or ""))

    html = f"""
<html><body style="font-family:sans-serif;color:#1a1a2e;max-width:520px;">
<h2 style="color:#10264a;">New feedback — Reserved™</h2>
<table style="width:100%;border-collapse:collapse;">
  <tr><td style="padding:6px 0;color:#666;width:130px;">Intuitive</td><td><strong>{intuitive_h}</strong> / 5</td></tr>
  <tr><td style="padding:6px 0;color:#666;">Useful</td><td><strong>{useful_h}</strong> / 5</td></tr>
  <tr><td style="padding:6px 0;color:#666;">Trustworthy</td><td><strong>{trustworthy_h}</strong> / 5</td></tr>
  <tr><td style="padding:6px 0;color:#666;">Would use</td><td>{would_use_h}</td></tr>
  <tr><td style="padding:6px 0;color:#666;">Area</td><td>{area_h}</td></tr>
  <tr><td style="padding:6px 0;color:#666;">Email</td><td>{email_h or '<em>(not provided)</em>'}</td></tr>
  <tr><td style="padding:6px 0;color:#666;">Browser</td><td>{browser_h}</td></tr>
  <tr><td style="padding:6px 0;color:#666;">Device</td><td>{device_h}</td></tr>
  <tr><td style="padding:6px 0;color:#666;">Page</td><td>{page_url_h}</td></tr>
</table>
<h3 style="margin-top:20px;">Comments</h3>
<p style="background:#f5f5f8;padding:12px;border-radius:8px;">{comments_h or '<em>(none)</em>'}</p>
</body></html>"""

    return _send(subject, body, html)


def notify_early_access(data: dict) -> bool:
    """Send a founder notification for a new early-access registration."""
    subject = f"Reserved™ — Early access: {data.get('name', 'New registration')}"

    # Plain-text body
    lines = [
        "New early-access registration",
        "=" * 40,
        f"Name:             {data.get('name', '—')}",
        f"Email:            {data.get('email', '—')}",
        f"Occupation:       {data.get('occupation') or '—'}",
        f"Working style:    {data.get('working_style') or '—'}",
        f"Referral source:  {data.get('referral_source') or '—'}",
        "",
        "Comments:",
        data.get("comments") or "(none)",
    ]
    body = "\n".join(lines)

    # HTML body — escape all user-supplied values
    e = _html.escape
    name_h         = e(str(data.get("name",           "") or "—"))
    email_raw      = str(data.get("email",             "") or "")
    email_h        = e(email_raw)
    occupation_h   = e(str(data.get("occupation",      "") or "—"))
    working_h      = e(str(data.get("working_style",   "") or "—"))
    referral_h     = e(str(data.get("referral_source", "") or "—"))
    comments_h     = e(str(data.get("comments",        "") or ""))
    mailto_h       = e(email_raw)  # also escape the mailto: href value

    html = f"""
<html><body style="font-family:sans-serif;color:#1a1a2e;max-width:520px;">
<h2 style="color:#10264a;">New early-access registration — Reserved™</h2>
<table style="width:100%;border-collapse:collapse;">
  <tr><td style="padding:6px 0;color:#666;width:160px;">Name</td><td><strong>{name_h}</strong></td></tr>
  <tr><td style="padding:6px 0;color:#666;">Email</td><td><a href="mailto:{mailto_h}">{email_h}</a></td></tr>
  <tr><td style="padding:6px 0;color:#666;">Occupation</td><td>{occupation_h}</td></tr>
  <tr><td style="padding:6px 0;color:#666;">Working style</td><td>{working_h}</td></tr>
  <tr><td style="padding:6px 0;color:#666;">Referral source</td><td>{referral_h}</td></tr>
</table>
<h3 style="margin-top:20px;">Comments</h3>
<p style="background:#f5f5f8;padding:12px;border-radius:8px;">{comments_h or '<em>(none)</em>'}</p>
</body></html>"""

    return _send(subject, body, html)
