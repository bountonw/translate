#!/usr/bin/env python3
"""A small PDF reader for the Thai printed edition of The Great Controversy.

The print PDF stores its Thai in subsetted BrowalliaUPC fonts with Identity-H
encoding and no ToUnicode CMap, so no general-purpose text extractor reads it
correctly: poppler falls back to reinterpreting each CID as a Latin codepoint,
which silently drops every digit and every period.  This module parses the
page content streams directly, so that each glyph keeps its CID, its position
and the font it was set in, and a caller can apply the CID table harvested by
gc_th_cidmap.py.

It expects the PDF already normalised by:

    qpdf --qdf --object-streams=disable --stream-data=uncompress IN OUT

Only the parts of PDF syntax this book actually uses are implemented.
"""

import re
import zlib


# ─── object model ────────────────────────────────────────────────────────────


class Name(str):
    """A PDF name, kept distinct from a PDF string."""

    __slots__ = ()


class Ref:
    __slots__ = ("num",)

    def __init__(self, num):
        self.num = num

    def __repr__(self):
        return f"Ref({self.num})"


DELIM = b"()<>[]{}/%"
WS = b"\x00\t\n\x0c\r "


class Lexer:
    def __init__(self, data, pos=0):
        self.d = data
        self.i = pos

    def skip_ws(self):
        d, n = self.d, len(self.d)
        while self.i < n:
            c = d[self.i]
            if c in WS:
                self.i += 1
            elif c == 0x25:  # '%' comment
                while self.i < n and d[self.i] not in b"\r\n":
                    self.i += 1
            else:
                return

    def parse(self):
        """Parse one object; return (value, is_keyword)."""
        self.skip_ws()
        d, n = self.d, len(self.d)
        if self.i >= n:
            return None, False
        c = d[self.i]

        if c == 0x2F:  # /
            self.i += 1
            start = self.i
            while self.i < n and d[self.i] not in WS and d[self.i] not in DELIM:
                self.i += 1
            return Name(self._unescape_name(d[start : self.i])), False

        if c == 0x28:  # (
            return self._string(), False

        if c == 0x3C:  # <
            if self.i + 1 < n and d[self.i + 1] == 0x3C:
                self.i += 2
                return self._dict(), False
            return self._hex_string(), False

        if c == 0x5B:  # [
            self.i += 1
            arr = []
            while True:
                self.skip_ws()
                if self.i >= n:
                    break
                if d[self.i] == 0x5D:
                    self.i += 1
                    break
                v, kw = self.parse()
                if kw and v == "R" and len(arr) >= 2:
                    arr[-2:] = [Ref(int(arr[-2]))]
                else:
                    arr.append(v)
            return arr, False

        if c == 0x5D or c == 0x3E or c == 0x7B or c == 0x7D:
            self.i += 1
            return None, False

        start = self.i
        while self.i < n and d[self.i] not in WS and d[self.i] not in DELIM:
            self.i += 1
        tok = d[start : self.i].decode("latin-1")
        if not tok:
            self.i += 1
            return None, False
        if re.fullmatch(r"[+-]?\d+", tok):
            return int(tok), False
        if re.fullmatch(r"[+-]?(\d*\.\d*|\d+)", tok):
            try:
                return float(tok), False
            except ValueError:
                return 0.0, False
        if tok == "true":
            return True, False
        if tok == "false":
            return False, False
        if tok == "null":
            return None, False
        return tok, True

    @staticmethod
    def _unescape_name(raw):
        out = bytearray()
        i = 0
        while i < len(raw):
            if raw[i] == 0x23 and i + 2 < len(raw):
                try:
                    out.append(int(raw[i + 1 : i + 3], 16))
                    i += 3
                    continue
                except ValueError:
                    pass
            out.append(raw[i])
            i += 1
        return out.decode("latin-1")

    def _dict(self):
        d = {}
        items = []
        n = len(self.d)
        while True:
            self.skip_ws()
            if self.i >= n:
                break
            if self.d[self.i] == 0x3E and self.i + 1 < n and self.d[self.i + 1] == 0x3E:
                self.i += 2
                break
            v, kw = self.parse()
            if kw and v == "R" and len(items) >= 2:
                items[-2:] = [Ref(int(items[-2]))]
            else:
                items.append(v)
        for k in range(0, len(items) - 1, 2):
            if isinstance(items[k], Name):
                d[str(items[k])] = items[k + 1]
        return d

    def _string(self):
        self.i += 1
        depth = 1
        out = bytearray()
        d, n = self.d, len(self.d)
        while self.i < n:
            c = d[self.i]
            if c == 0x5C:  # backslash
                self.i += 1
                if self.i >= n:
                    break
                e = d[self.i]
                mapping = {0x6E: 10, 0x72: 13, 0x74: 9, 0x62: 8, 0x66: 12}
                if e in mapping:
                    out.append(mapping[e])
                    self.i += 1
                elif 0x30 <= e <= 0x37:
                    oct_digits = ""
                    while self.i < n and len(oct_digits) < 3 and 0x30 <= d[self.i] <= 0x37:
                        oct_digits += chr(d[self.i])
                        self.i += 1
                    out.append(int(oct_digits, 8) & 0xFF)
                elif e in b"\r\n":
                    self.i += 1
                    if self.i < n and d[self.i] == 0x0A and e == 0x0D:
                        self.i += 1
                else:
                    out.append(e)
                    self.i += 1
                continue
            if c == 0x28:
                depth += 1
            elif c == 0x29:
                depth -= 1
                if depth == 0:
                    self.i += 1
                    break
            out.append(c)
            self.i += 1
        return bytes(out)

    def _hex_string(self):
        self.i += 1
        d, n = self.d, len(self.d)
        digits = []
        while self.i < n and d[self.i] != 0x3E:
            c = chr(d[self.i])
            if c in "0123456789abcdefABCDEF":
                digits.append(c)
            self.i += 1
        self.i += 1
        if len(digits) % 2:
            digits.append("0")
        return bytes(int("".join(digits[k : k + 2]), 16) for k in range(0, len(digits), 2))


# ─── document ────────────────────────────────────────────────────────────────

OBJ_HEAD = re.compile(rb"(?m)^(\d+)\s+(\d+)\s+obj\b")


class Pdf:
    def __init__(self, path):
        with open(path, "rb") as fh:
            self.data = fh.read()
        self.offsets = {}
        for m in OBJ_HEAD.finditer(self.data):
            self.offsets[int(m.group(1))] = m.end()
        self._cache = {}
        self.pages = self._page_list()

    def obj(self, num):
        if num in self._cache:
            return self._cache[num]
        pos = self.offsets.get(num)
        if pos is None:
            return None
        lex = Lexer(self.data, pos)
        val, _ = lex.parse()
        lex.skip_ws()
        if self.data[lex.i : lex.i + 6] == b"stream":
            j = lex.i + 6
            if self.data[j : j + 2] == b"\r\n":
                j += 2
            elif self.data[j : j + 1] in (b"\n", b"\r"):
                j += 1
            end = self.data.find(b"endstream", j)
            raw = self.data[j:end]
            if raw.endswith(b"\r\n"):
                raw = raw[:-2]
            elif raw.endswith(b"\n") or raw.endswith(b"\r"):
                raw = raw[:-1]
            val = Stream(val if isinstance(val, dict) else {}, raw, self)
        self._cache[num] = val
        return val

    def resolve(self, v):
        seen = 0
        while isinstance(v, Ref) and seen < 32:
            v = self.obj(v.num)
            seen += 1
        return v

    def get(self, d, key, default=None):
        if not isinstance(d, dict):
            return default
        return self.resolve(d.get(key, default))

    def _page_list(self):
        root = None
        m = re.search(rb"/Type\s*/Catalog", self.data)
        if m:
            start = self.data.rfind(b" obj", 0, m.start())
            head = OBJ_HEAD.search(self.data, max(0, self.data.rfind(b"\n", 0, start) - 40))
        for num in self.offsets:
            o = self.obj(num)
            if isinstance(o, dict) and o.get("Type") == "Catalog":
                root = o
                break
        pages = []
        if root is None:
            return pages
        node = self.resolve(root.get("Pages"))

        def walk(nd, inherited):
            if not isinstance(nd, dict):
                return
            inh = dict(inherited)
            for k in ("Resources", "MediaBox", "CropBox", "Rotate"):
                if k in nd:
                    inh[k] = nd[k]
            if nd.get("Type") == "Page" or ("Kids" not in nd and "Contents" in nd):
                page = dict(nd)
                for k, v in inh.items():
                    page.setdefault(k, v)
                pages.append(page)
                return
            for kid in self.resolve(nd.get("Kids")) or []:
                walk(self.resolve(kid), inh)

        walk(node, {})
        return pages

    def page_content(self, page):
        c = self.resolve(page.get("Contents"))
        parts = []
        if isinstance(c, Stream):
            parts.append(c.data())
        elif isinstance(c, list):
            for item in c:
                s = self.resolve(item)
                if isinstance(s, Stream):
                    parts.append(s.data())
        return b"\n".join(parts)


class Stream:
    def __init__(self, d, raw, pdf):
        self.dict = d
        self.raw = raw
        self.pdf = pdf

    def get(self, k, default=None):
        return self.dict.get(k, default)

    def data(self):
        filt = self.pdf.resolve(self.dict.get("Filter"))
        if filt is None:
            return self.raw
        names = [filt] if isinstance(filt, str) else list(filt)
        out = self.raw
        for f in names:
            if f == "FlateDecode":
                try:
                    out = zlib.decompress(out)
                except zlib.error:
                    try:
                        out = zlib.decompressobj().decompress(out)
                    except zlib.error:
                        return b""
            else:
                return b""
        return out


# ─── fonts ───────────────────────────────────────────────────────────────────

STD_ENC_EXTRA = {
    0x91: "‘", 0x92: "’", 0x93: "“", 0x94: "”",
    0x96: "–", 0x97: "—", 0x85: "…", 0xA0: " ",
}


class Font:
    """One /Font resource, reduced to what decoding and advancing need."""

    def __init__(self, pdf, fdict, cidmap):
        self.pdf = pdf
        self.d = fdict
        self.cidmap = cidmap
        self.base = str(pdf.get(fdict, "BaseFont", "") or "")
        self.subtype = str(pdf.get(fdict, "Subtype", "") or "")
        self.two_byte = False
        self.widths = {}
        self.default_width = 500.0
        self.tounicode = {}
        self.diff = {}
        self.is_cid_thai = False
        self._load()

    # -- setup ---------------------------------------------------------------
    def _load(self):
        pdf = self.pdf
        tou = pdf.get(self.d, "ToUnicode")
        if isinstance(tou, Stream):
            self.tounicode = parse_cmap_bytes(tou.data())

        if self.subtype == "Type0":
            enc = pdf.get(self.d, "Encoding")
            self.two_byte = True  # Identity-H and Identity-V are the only ones here
            desc_list = pdf.get(self.d, "DescendantFonts") or []
            desc = pdf.resolve(desc_list[0]) if desc_list else {}
            self.default_width = float(pdf.get(desc, "DW", 1000) or 1000)
            self._load_w(pdf.get(desc, "W") or [])
            self.is_cid_thai = "Browallia" in self.base
            if str(enc) not in ("Identity-H", "Identity", "Identity-V"):
                # No other CMap occurs in this book; treat as identity but flag it.
                self.note = f"unexpected Type0 encoding {enc}"
        else:
            fc = pdf.get(self.d, "FirstChar")
            ws = pdf.get(self.d, "Widths")
            if isinstance(fc, (int, float)) and isinstance(ws, list):
                for k, w in enumerate(ws):
                    w = pdf.resolve(w)
                    if isinstance(w, (int, float)):
                        self.widths[int(fc) + k] = float(w)
            fd = pdf.get(self.d, "FontDescriptor") or {}
            mw = pdf.get(fd, "MissingWidth")
            self.default_width = float(mw) if isinstance(mw, (int, float)) else 500.0
            enc = pdf.get(self.d, "Encoding")
            if isinstance(enc, dict):
                cur = None
                for item in pdf.get(enc, "Differences") or []:
                    item = pdf.resolve(item)
                    if isinstance(item, (int, float)):
                        cur = int(item)
                    elif isinstance(item, str) and cur is not None:
                        self.diff[cur] = str(item)
                        cur += 1

    def _load_w(self, w):
        pdf = self.pdf
        w = [pdf.resolve(x) for x in w]
        k = 0
        while k < len(w):
            first = w[k]
            if k + 1 < len(w) and isinstance(w[k + 1], list):
                arr = [pdf.resolve(x) for x in w[k + 1]]
                for off, val in enumerate(arr):
                    if isinstance(val, (int, float)):
                        self.widths[int(first) + off] = float(val)
                k += 2
            elif k + 2 < len(w):
                last, val = w[k + 1], w[k + 2]
                if isinstance(first, (int, float)) and isinstance(last, (int, float)) and isinstance(val, (int, float)):
                    lo, hi = int(first), int(last)
                    if hi - lo <= 65535:
                        for c in range(lo, hi + 1):
                            self.widths[c] = float(val)
                k += 3
            else:
                break

    # -- use -----------------------------------------------------------------
    def codes(self, raw):
        if self.two_byte:
            return [(raw[i] << 8) | raw[i + 1] for i in range(0, len(raw) - 1, 2)]
        return list(raw)

    def width(self, code):
        return self.widths.get(code, self.default_width)

    def decode(self, code):
        """Return (text, status) where status is 'ok' or 'unmapped'."""
        if self.is_cid_thai:
            if code in self.cidmap:
                return self.cidmap[code], "ok"
            if code in self.tounicode and _sane(self.tounicode[code]):
                return self.tounicode[code], "ok"
            return "", "unmapped"
        if code in self.tounicode:
            return self.tounicode[code], "ok"
        if code in self.diff:
            ch = glyphname_to_char(self.diff[code])
            if ch:
                return ch, "ok"
        if 32 <= code < 127:
            return chr(code), "ok"
        if code in STD_ENC_EXTRA:
            return STD_ENC_EXTRA[code], "ok"
        return "", "unmapped"


def _sane(s):
    return all(not (0x0100 <= ord(c) <= 0x02FF) for c in s) and s != "�"


GLYPH_NAMES = {
    "space": " ", "exclam": "!", "quotedbl": '"', "numbersign": "#", "dollar": "$",
    "percent": "%", "ampersand": "&", "quotesingle": "'", "parenleft": "(",
    "parenright": ")", "asterisk": "*", "plus": "+", "comma": ",", "hyphen": "-",
    "period": ".", "slash": "/", "zero": "0", "one": "1", "two": "2", "three": "3",
    "four": "4", "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9",
    "colon": ":", "semicolon": ";", "less": "<", "equal": "=", "greater": ">",
    "question": "?", "at": "@", "bracketleft": "[", "backslash": "\\",
    "bracketright": "]", "asciicircum": "^", "underscore": "_", "grave": "`",
    "braceleft": "{", "bar": "|", "braceright": "}", "asciitilde": "~",
    "quoteleft": "‘", "quoteright": "’", "quotedblleft": "“",
    "quotedblright": "”", "endash": "–", "emdash": "—",
    "ellipsis": "…", "bullet": "•", "eacute": "é",
}


def glyphname_to_char(name):
    if name in GLYPH_NAMES:
        return GLYPH_NAMES[name]
    if len(name) == 1:
        return name
    m = re.fullmatch(r"uni([0-9A-Fa-f]{4})", name)
    if m:
        return chr(int(m.group(1), 16))
    return ""


def parse_cmap_bytes(data):
    text = data.decode("latin-1")
    table = {}
    for block in re.findall(r"beginbfchar(.*?)endbfchar", text, re.S):
        for src, dst in re.findall(r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", block):
            table[int(src, 16)] = _hexstr(dst)
    for block in re.findall(r"beginbfrange(.*?)endbfrange", text, re.S):
        for lo, hi, dst in re.findall(
            r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", block
        ):
            lo_i, hi_i, base = int(lo, 16), int(hi, 16), int(dst, 16)
            if 0 <= hi_i - lo_i <= 0xFFFF:
                for k in range(lo_i, hi_i + 1):
                    table[k] = chr(base + (k - lo_i))
        for lo, hi, arr in re.findall(
            r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*\[(.*?)\]", block, re.S
        ):
            lo_i = int(lo, 16)
            for off, d in enumerate(re.findall(r"<([0-9A-Fa-f]+)>", arr)):
                table[lo_i + off] = _hexstr(d)
    return table


def _hexstr(h):
    if len(h) % 4:
        h = h.zfill((len(h) + 3) // 4 * 4)
    return "".join(chr(int(h[i : i + 4], 16)) for i in range(0, len(h), 4))


# ─── content stream text extraction ──────────────────────────────────────────


def mat_mul(a, b):
    return (
        a[0] * b[0] + a[1] * b[2],
        a[0] * b[1] + a[1] * b[3],
        a[2] * b[0] + a[3] * b[2],
        a[2] * b[1] + a[3] * b[3],
        a[4] * b[0] + a[5] * b[2] + b[4],
        a[4] * b[1] + a[5] * b[3] + b[5],
    )


class Glyph:
    __slots__ = ("x", "y", "size", "font", "text", "code", "status", "adv")

    def __init__(self, x, y, size, font, text, code, status, adv=0.0):
        self.x, self.y, self.size = x, y, size
        self.font, self.text, self.code, self.status = font, text, code, status
        self.adv = adv


def page_glyphs(pdf, page, cidmap, font_cache):
    """Return the page's glyphs in content-stream order with device positions."""
    res = pdf.get(page, "Resources") or {}
    fonts_dict = pdf.get(res, "Font") or {}
    fonts = {}
    for key, ref in fonts_dict.items():
        cache_key = ref.num if isinstance(ref, Ref) else (id(page), key)
        if cache_key not in font_cache:
            font_cache[cache_key] = Font(pdf, pdf.resolve(ref), cidmap)
        fonts[key] = font_cache[cache_key]

    content = pdf.page_content(page)
    lex = Lexer(content, 0)
    stack = []
    ctm = (1, 0, 0, 1, 0, 0)
    tm = tlm = (1, 0, 0, 1, 0, 0)
    font = None
    size = 0.0
    tc = tw = 0.0
    th = 1.0
    tl = 0.0
    ts = 0.0
    operands = []
    out = []
    n = len(content)

    def show(raw):
        nonlocal tm
        if font is None:
            return
        for code in font.codes(raw):
            text, status = font.decode(code)
            trm = mat_mul((size * th, 0, 0, size, 0, ts), mat_mul(tm, ctm))
            eff = (trm[2] ** 2 + trm[3] ** 2) ** 0.5
            w0 = font.width(code) / 1000.0
            adv = (w0 * size + tc + (tw if (code == 32 and not font.two_byte) else 0)) * th
            # The advance reported on the glyph excludes character and word
            # spacing, because this book encodes some of its word spaces by
            # inflating the advance of the glyph before them rather than by
            # setting a space, and the caller has to be able to see that.
            nominal = mat_mul(
                (size * th, 0, 0, size, 0, ts),
                mat_mul(mat_mul((1, 0, 0, 1, w0 * size * th, 0), tm), ctm),
            )
            tm = mat_mul((1, 0, 0, 1, adv, 0), tm)
            if text or status == "unmapped":
                out.append(
                    Glyph(trm[4], trm[5], eff, font, text, code, status, nominal[4] - trm[4])
                )

    while lex.i < n:
        val, is_kw = lex.parse()
        if val is None and not is_kw:
            if lex.i >= n:
                break
            continue
        if not is_kw:
            operands.append(val)
            if len(operands) > 32:
                del operands[:-32]
            continue

        op = val
        try:
            if op == "q":
                stack.append(ctm)
            elif op == "Q":
                if stack:
                    ctm = stack.pop()
            elif op == "cm" and len(operands) >= 6:
                ctm = mat_mul(tuple(float(x) for x in operands[-6:]), ctm)
            elif op == "BT":
                tm = tlm = (1, 0, 0, 1, 0, 0)
            elif op == "Tf" and len(operands) >= 2:
                font = fonts.get(str(operands[-2]))
                size = float(operands[-1])
            elif op == "Td" and len(operands) >= 2:
                tlm = mat_mul((1, 0, 0, 1, float(operands[-2]), float(operands[-1])), tlm)
                tm = tlm
            elif op == "TD" and len(operands) >= 2:
                tl = -float(operands[-1])
                tlm = mat_mul((1, 0, 0, 1, float(operands[-2]), float(operands[-1])), tlm)
                tm = tlm
            elif op == "Tm" and len(operands) >= 6:
                tm = tlm = tuple(float(x) for x in operands[-6:])
            elif op == "T*":
                tlm = mat_mul((1, 0, 0, 1, 0, -tl), tlm)
                tm = tlm
            elif op == "TL" and operands:
                tl = float(operands[-1])
            elif op == "Tc" and operands:
                tc = float(operands[-1])
            elif op == "Tw" and operands:
                tw = float(operands[-1])
            elif op == "Tz" and operands:
                th = float(operands[-1]) / 100.0
            elif op == "Ts" and operands:
                ts = float(operands[-1])
            elif op == "Tj" and operands:
                show(operands[-1])
            elif op == "'" and operands:
                tlm = mat_mul((1, 0, 0, 1, 0, -tl), tlm)
                tm = tlm
                show(operands[-1])
            elif op == '"' and len(operands) >= 3:
                tw = float(operands[-3])
                tc = float(operands[-2])
                tlm = mat_mul((1, 0, 0, 1, 0, -tl), tlm)
                tm = tlm
                show(operands[-1])
            elif op == "TJ" and operands:
                arr = operands[-1]
                if isinstance(arr, list):
                    for item in arr:
                        if isinstance(item, bytes):
                            show(item)
                        elif isinstance(item, (int, float)):
                            tm = mat_mul(
                                (1, 0, 0, 1, -item / 1000.0 * size * th, 0), tm
                            )
        except (TypeError, ValueError, IndexError):
            pass
        operands = []

    return out


def load_cidmap(path):
    table = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("#") or not line.strip():
                continue
            parts = line.rstrip("\n").split("\t")
            if len(parts) >= 2:
                table[int(parts[0])] = parts[1]
    return table
