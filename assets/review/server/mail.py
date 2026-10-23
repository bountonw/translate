"""The mailer: one small module that sends the site's few emails, through one of three providers.

config.json's "mail" chooses the provider and holds its settings (README.md, "Sign-in settings"):

    smtp    the standard library's smtplib: host (default 127.0.0.1), port (25, or 465 with ssl, 587 with
            starttls), security none, starttls or ssl, an optional user and password
    resend  Resend's HTTPS API (https://api.resend.com/emails) with api_key
    file    a stand-in that writes each message to a file in the data directory (dir, default DATA/mail);
            the tests and the dev server use it

Every provider needs "from", the address the mail comes from, and may give "from_name", the name shown with
it. The site sends a sign-in code to a reader, a note to a reader whose request was approved, a note to the
translator (config.json "notify"), and a test message from the admin routes. A send that fails raises
MailError with a plain sentence; the caller records it in mail_log and the site goes on working.

The words of the mails to readers are in server/mail-words.json, each with its English and its Thai; a mail
holds the Thai first when it is written, then the English.
"""
import json
import os
import re
import smtplib
import socket
import ssl
import threading
import urllib.error
import urllib.request
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import formataddr, formatdate, make_msgid
from pathlib import Path

PROVIDERS = ("smtp", "resend", "file")
SECURITY = ("none", "starttls", "ssl")
RESEND_URL = "https://api.resend.com/emails"
TIMEOUT = 10                     # seconds a mail server or Resend may take to answer
# The part before @ takes only A to Z, digits and . _ % + -, as most sites accept: no control, invisible or
# look-alike character, and none of the syntax of RFC 5322 (quotes, comments, groups) that would make the site
# keep one address and mail another. Addresses at Gmail and Outlook fit.
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]{1,64}@[A-Za-z0-9.-]{1,252}\.[A-Za-z]{2,63}")
WORDS = Path(__file__).with_name("mail-words.json")
KEYS = {"smtp": {"provider", "from", "from_name", "host", "port", "security", "user", "password"},
        "resend": {"provider", "from", "from_name", "api_key", "url"},
        "file": {"provider", "from", "from_name", "dir"}}


class MailError(Exception):
    """A mail that could not be sent, with a plain sentence saying why."""


def address(text):
    """An email address as the site keeps it: trimmed and in lower case; None when it is not an address."""
    if not isinstance(text, str):
        return None
    text = text.strip()
    if len(text) > 254 or not EMAIL_RE.fullmatch(text):
        return None
    return text.lower()


def is_local(url):
    """True for an http address on this machine, which a stand-in may use instead of https."""
    return bool(re.match(r"http://(127\.0\.0\.1|localhost)(:\d+)?(/|$)", url))


def load(cfg, data_dir, where):
    """The mail settings from config.json's "mail", checked: a dict with provider, sender and the provider's own
    settings, or None when there is no "mail". Raises ValueError with a plain sentence naming the setting."""
    if cfg is None:
        return None
    if not isinstance(cfg, dict):
        raise ValueError(f'{where}: "mail" must be an object such as {{"provider": "smtp", "from": '
                         '"review@forum.laoegw.com"}.')
    provider = cfg.get("provider")
    if provider not in PROVIDERS:
        raise ValueError(f'{where}: "mail.provider" must be smtp, resend or file, not {provider!r}.')
    unknown = sorted(set(cfg) - KEYS[provider])
    if unknown:
        raise ValueError(f'{where}: "mail" with the provider {provider} has no setting named {unknown[0]}. '
                         f"Its settings are {', '.join(sorted(KEYS[provider]))}.")
    out = {"provider": provider}
    sender = address(cfg.get("from"))
    if not sender:
        raise ValueError(f'{where}: "mail.from" must be the address the mail comes from, as '
                         '"review@forum.laoegw.com".')
    out["from"] = cfg["from"].strip()
    name = cfg.get("from_name", "Proofreading site")
    if not isinstance(name, str) or len(name) > 80 or any(c in name for c in "\r\n"):
        raise ValueError(f'{where}: "mail.from_name" must be a short name on one line.')
    out["from_name"] = name
    if provider == "smtp":
        security = cfg.get("security", "none")
        if security not in SECURITY:
            raise ValueError(f'{where}: "mail.security" must be none, starttls or ssl, not {security!r}.')
        port = cfg.get("port", {"none": 25, "starttls": 587, "ssl": 465}[security])
        if not isinstance(port, int) or isinstance(port, bool) or not 1 <= port <= 65535:
            raise ValueError(f'{where}: "mail.port" must be a port number, as 25.')
        host = cfg.get("host", "127.0.0.1")
        if not isinstance(host, str) or not re.fullmatch(r"[A-Za-z0-9.:-]{1,253}", host):
            raise ValueError(f'{where}: "mail.host" must be a host name or address, as 127.0.0.1.')
        user, password = cfg.get("user", ""), cfg.get("password", "")
        if not isinstance(user, str) or not isinstance(password, str) or bool(user) != bool(password):
            raise ValueError(f'{where}: "mail.user" and "mail.password" go together: give both, or neither.')
        if user and security == "none" and host not in ("127.0.0.1", "localhost", "::1"):
            raise ValueError(f'{where}: a mail password is sent to {host} only over starttls or ssl; set '
                             '"mail.security".')
        out.update(host=host, port=port, security=security, user=user, password=password)
    elif provider == "resend":
        key = cfg.get("api_key")
        if not isinstance(key, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{8,200}", key):
            raise ValueError(f'{where}: "mail.api_key" must be the API key that Resend gave, starting re_.')
        url = cfg.get("url", RESEND_URL)
        if not isinstance(url, str) or not (url.startswith("https://") or is_local(url)):
            raise ValueError(f'{where}: "mail.url" must be an https address.')
        out.update(api_key=key, url=url)
    else:
        folder = cfg.get("dir") or str(Path(data_dir) / "mail")
        if not isinstance(folder, str):
            raise ValueError(f'{where}: "mail.dir" must be a folder.')
        out["dir"] = folder
    return out


def describe(settings):
    """The mail settings as the admin routes show them: never the password or the API key."""
    if not settings:
        return None
    out = {k: v for k, v in settings.items() if k not in ("password", "api_key")}
    if settings["provider"] == "smtp":
        out["user"] = bool(settings["user"])
    return out


def words():
    """The words of the mails to readers: {key: {"en": ..., "th": ...}}."""
    return json.loads(WORDS.read_text())


def both(key, **values):
    """A text of mail-words.json in Thai, when it is written, then in English, with {name} filled in."""
    w = words()[key]
    parts = [w.get(lang, "") for lang in ("th", "en")]
    return "\n\n".join(p.format(**values) for p in parts if p)


def subject(key, **values):
    """A subject of mail-words.json: the Thai when it is written, else the English."""
    w = words()[key]
    return (w.get("th") or w["en"]).format(**values)


class Mailer:
    """Sends a plain-text mail through the provider config.json names."""

    def __init__(self, settings):
        self.settings = settings
        self.lock = threading.Lock()
        self.n = 0

    @property
    def provider(self):
        return self.settings["provider"]

    def message(self, to, title, text, cte=None):
        msg = EmailMessage()
        msg["From"] = formataddr((self.settings["from_name"], self.settings["from"]))
        msg["To"] = to
        msg["Subject"] = title
        msg["Date"] = formatdate(usegmt=True)
        msg["Message-ID"] = make_msgid(domain=self.settings["from"].rsplit("@", 1)[-1])
        if cte:
            msg.set_content(text, charset="utf-8", cte=cte)
        else:
            msg.set_content(text, charset="utf-8")
        return msg

    def send(self, to, title, text):
        """Send one mail; raises MailError with a plain sentence when it cannot."""
        try:
            getattr(self, "_" + self.provider)(to, title, text)
        except MailError:
            raise
        except (OSError, smtplib.SMTPException) as e:
            raise MailError(self.explain(e))

    def where(self, capital=True):
        """The mail server, Resend or the mail folder, as the subject of a sentence (capital) or inside one."""
        s = self.settings
        if s["provider"] == "smtp":
            text = f"the mail server at {s['host']}:{s['port']}"
        elif s["provider"] == "resend":
            return "Resend"
        else:
            text = f"the mail folder {s['dir']}"
        return text[0].upper() + text[1:] if capital else text

    def explain(self, e):
        """A plain sentence for an error of the mailer, with the mail server's own reply where it gave one, so
        that the translator sees what is wrong: a refused address, a server that will not pass mail on, a
        certificate for another name, or a server that does not answer."""
        where = self.where()
        if isinstance(e, (ConnectionRefusedError, socket.gaierror)):
            return f"{where} cannot be reached ({e})."
        if isinstance(e, TimeoutError) or (isinstance(e, smtplib.SMTPServerDisconnected) and "timed out" in str(e)):
            return f"{where} did not answer within {TIMEOUT} seconds."
        if isinstance(e, smtplib.SMTPAuthenticationError):
            return (f"{where} refused the user name or password in mail.user and mail.password: "
                    f"{reply(e.smtp_code, e.smtp_error)}.")
        if isinstance(e, smtplib.SMTPRecipientsRefused):
            code, text = next(iter(e.recipients.values()), (0, b""))
            return f"{where} refused to take the mail for that address: {reply(code, text)}." + relay_hint(text)
        if isinstance(e, smtplib.SMTPSenderRefused):
            return (f"{where} refused the address in mail.from: {reply(e.smtp_code, e.smtp_error)}."
                    + relay_hint(e.smtp_error))
        if isinstance(e, smtplib.SMTPResponseException):
            return f"{where} refused the mail: {reply(e.smtp_code, e.smtp_error)}." + relay_hint(e.smtp_error)
        if isinstance(e, ssl.SSLCertVerificationError):
            return (f"The secure connection to {self.where(False)} failed: {e.verify_message or e.reason}. Set "
                    "mail.host to the name on the server's certificate, as mail.example.org.")
        if isinstance(e, ssl.SSLError):
            return f"The secure connection to {self.where(False)} failed ({e.reason or e})."
        return f"{where} answered with an error ({e})."

    def check(self, rcpt=None):
        """(ok, a plain sentence): whether the provider takes a mail, without sending one. The mail server is
        asked to take a mail from mail.from to rcpt (the notes' address, else mail.from), and the mail is then
        dropped (RSET) before any of it is sent, so a server that will not pass mail on fails here too."""
        s = self.settings
        rcpt = rcpt or s["from"]
        try:
            if s["provider"] == "smtp":
                with self.smtp() as server:
                    code, text = server.mail(s["from"])
                    if code != 250:
                        raise smtplib.SMTPSenderRefused(code, text, s["from"])
                    code, text = server.rcpt(rcpt)
                    if code not in (250, 251):
                        raise smtplib.SMTPRecipientsRefused({rcpt: (code, text)})
                    server.rset()
                return True, (f"{self.where()} accepted the connection" + (", the login" if s["user"] else "")
                              + f" and a mail from {s['from']} to {rcpt}; no mail was sent.")
            if s["provider"] == "file":
                folder = Path(s["dir"])
                folder.mkdir(parents=True, exist_ok=True)
                return os.access(folder, os.W_OK), f"Mail is written to files in {folder}."
            return True, "Resend is set. Send a test mail to check the API key and the sending domain."
        except MailError as e:
            return False, str(e)
        except (OSError, smtplib.SMTPException) as e:
            return False, self.explain(e)

    # ---------- providers ----------

    def smtp(self):
        s = self.settings
        context = ssl.create_default_context()
        if s["security"] == "ssl":
            server = smtplib.SMTP_SSL(s["host"], s["port"], timeout=TIMEOUT, context=context)
        else:
            server = smtplib.SMTP(s["host"], s["port"], timeout=TIMEOUT)
        try:
            server.ehlo()
            if s["security"] == "starttls":
                server.starttls(context=context)
                server.ehlo()
            if s["user"]:
                server.login(s["user"], s["password"])
        except BaseException:
            server.close()
            raise
        return server

    def _smtp(self, to, title, text):
        with self.smtp() as server:
            # base64 keeps the Thai of a mail within 7-bit lines, which every mail server takes.
            server.send_message(self.message(to, title, text, cte="base64"))

    def _resend(self, to, title, text):
        s = self.settings
        body = json.dumps({"from": formataddr((s["from_name"], s["from"])), "to": [to], "subject": title,
                           "text": text}).encode()
        req = urllib.request.Request(s["url"], data=body, method="POST", headers={
            "Authorization": "Bearer " + s["api_key"], "Content-Type": "application/json",
            "User-Agent": "review-site/1"})
        handlers = [NoRedirect] + ([urllib.request.ProxyHandler({})] if is_local(s["url"]) else [])
        opener = urllib.request.build_opener(*handlers)
        try:
            with opener.open(req, timeout=TIMEOUT) as r:
                r.read()
        except urllib.error.HTTPError as e:
            try:
                with e:
                    why = json.loads(e.read().decode()).get("message") or ""
            except (ValueError, AttributeError, OSError):
                why = ""
            raise MailError(f"Resend answered {e.code}" + (f": {why}" if why else "."))
        except urllib.error.URLError as e:
            raise MailError(f"Resend cannot be reached ({e.reason}).")

    def _file(self, to, title, text):
        folder = Path(self.settings["dir"])
        folder.mkdir(parents=True, exist_ok=True)
        os.chmod(folder, 0o700)
        with self.lock:
            self.n += 1
            n = self.n
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
        path = folder / f"mail-{stamp}-{n}.eml"
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as f:
            f.write(self.message(to, title, text, cte="8bit").as_bytes())


def reply(code, text):
    """A mail server's reply as one line: "554 5.7.1 Relay access denied"."""
    if isinstance(text, bytes):
        text = text.decode("utf-8", "replace")
    text = " ".join(str(text or "").split())[:200]
    return f"{code} {text}".strip() if code else text or "no reply"


def relay_hint(text):
    """A sentence more when the server's reply is a refusal of policy (5.7.x), as a server that passes mail on
    to other domains only after a login."""
    if isinstance(text, bytes):
        text = text.decode("utf-8", "replace")
    if "5.7." in str(text) or "relay" in str(text).lower():
        return (" The server may pass mail on to other domains only after a login: set mail.user and "
                "mail.password, or use another mail server (deploy/DEPLOY.md, step 10.A).")
    return ""


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """Never follow a redirect: a key or a code goes only to the address in config.json."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None
