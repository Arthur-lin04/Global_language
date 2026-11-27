# -*- coding: utf-8 -*-
"""第 12 週重新切塊 (re-chunking)：Docling Markdown → 以「條」為單位的 chunks → data/processed_v2/

教師提供，學生只需要執行，不需要讀懂。

用法（在專案根目錄的終端機，確認有 (.venv)）：
    python src/rechunk_v2.py               # 預設：每塊最多 500 字
    python src/rechunk_v2.py --max 800     # 改成每塊最多 800 字
或在 notebook 中：
    from rechunk_v2 import rechunk_all

處理步驟（每一份 data/interim/<cluster>/raw_*.md，整份法規一個檔案；沒有 raw_*.md 時改讀 cleaned_*.md）：
    ① clean_lines()     清理：刪頁首頁尾、頁碼、目錄、修訂日期；接回 PDF 斷行造成的斷字與斷句
    ② segment()         分段：封面 / 依「第N條」分成條文 / 附件（空白表單預設略過）
    ③ 每一條條文（chunk_document）：
         a. split_bilingual() + is_zh()  每一行分到中文 zh 或英文 en
         b. make_header()                標題列【法規｜篇｜章】第N條；條文第一行的「第N條」刪掉（DEDUP_LABEL）
         c. pack()                       只量「標題列 + 上下文 + 中文」的長度：
                                         ≤ MAX_CHARS（500）→ 整條一塊；
                                         超過 → 依 一、→（一）→ 1. → 句號 遞迴切開，
                                         每塊都重複條文開頭那句（例如「凡有下列各款情形之一者，予以大過處分。」）
                                         英文跟著對應的中文款項；款數對不上時，英文另成 article_en 塊（≤ MAX_EN_CHARS）
         d. 組合：text       = 標題列 + 上下文 + 中文 + 英文
                  embed_text = 標題列 + 上下文 + 中文（不含英文）；只有英文的 article_en 塊 → embed_text = text
       → 因為 c 只量中文那一側，embed_text 一定 ≤ 500 字；text 可以更長（加上英文）
    ④ rechunk_all()     寫到 data/processed_v2/<cluster>/v2_*.json

每個 chunk：
    text        中英對照全文（給語言模型看、引用條文）
    embed_text  標題列 + 中文內容（算向量用；bge-small-zh 一次約讀 512 token）；只有英文的少數 chunk 就是英文
    metadata    source_file, doc_code, doc_title, cluster, chunk_type, article_no, article_title,
                part, chapter, piece, chunk_id, char_length, embed_length
                char_length = len(text)；embed_length = len(embed_text)（字元數，含標點、換行，不是向量長度）
                piece = 同一條切成多塊時的編號 0, 1, 2…

設定（第 12 週教師測試後決定）：每塊 500 字、不重複「第N條 標題」、保留【法規｜篇｜章】標題列、
略過空白申請表。
"""
import re
import json
from collections import Counter
from pathlib import Path

MAX_CHARS = 500          # 每個 chunk 的 embed_text 最多幾個字（bge-small-zh 一次約讀 512 token）
FRONT_MAX = 400          # 封面、修訂記錄最多保留幾個字
DEDUP_LABEL = True       # 條文第一行不再重複「第N條 標題」（標題列已經有）
KEEP_FORMS = False       # 空白申請表、表單：預設不放進 chunks（只有欄位名稱，會干擾檢索）
FORM_RE = re.compile(r"(申請書|申請表|申請單|報告書|說明表|減損單|範本|自評表|表號|Form)")
MAX_EN_CHARS = 1500      # 只有英文的 chunk 最多幾個字元（英文約 4 字元 = 1 token）

SCHOOL_NAMES = ["明志科技大學", "Ming Chi University of Technology", "MING CHI UNIVERSITY OF TECHNOLOGY"]

CJK = r"㐀-鿿"
CJK_PUNCT = r"　-〿＀-￯、。，；：「」『』（）"
CN_NUM = r"[零〇一二三四五六七八九十百廿卅兩0-9]+"
MARK = r"(?:#{1,6}\s*|[-*]\s+|\d+\.\s+)?"          # Docling 的 ## / - / 1. 前綴

ARTICLE_RE = re.compile(rf"^{MARK}第\s*({CN_NUM})\s*條")
EN_ARTICLE_RE = re.compile(rf"^{MARK}Article\s+(\d+)\b")
CHAPTER_RE = re.compile(rf"^{MARK}(第\s*{CN_NUM}\s*[篇章])\s*([^/|]*)")
EN_CHAPTER_RE = re.compile(r"^(?:#{1,6}\s*)?(Part|Chapter)\s+\d+\b")
APPENDIX_RE = re.compile(r"(申請書|申請表|申請單|報告書|參考表|範本|說明表|減損單|告知聲明|表號|附件|Attachment|Form No)")
REVISION_RE = re.compile(
    r"^(?:\d{2,3}[.年]\s*\d{1,2}[.月]\s*\d{1,2}日?\s*\S{0,12}(?:會議|校長|委員會)\S{0,6}"
    r"|(?:Amended|Revised|Established|Formulated|Prepared|Compiled|Approved|Amendment)\b.{0,90}"
    r"(?:Meeting|Committee|Council|President|Recordation|\d{4}))")
NOISE_LINE_RE = re.compile(r"^(?:<!--.*?-->\s*/?\s*|-\s*\[\s*\]\s.*|#{1,6}\s*\d{1,3}|\d{1,3}|著作權人.*|Copyright.*|Copyrighted.*)$")

ZH_LEVELS = [
    re.compile(rf"^{MARK}[一二三四五六七八九十]+\s*、"),
    re.compile(r"^(?:[-*]\s+|#{1,6}\s*)?[（(][一二三四五六七八九十]+[)）]"),
    re.compile(r"^(?:[-*]\s+|#{1,6}\s*)?\d+[.、]\s*"),
]
EN_LEVELS = [
    re.compile(r"^(?:[-*]\s+|#{1,6}\s*)?\d+\.\s"),
    re.compile(r"^(?:[-*]\s+|#{1,6}\s*)?\((?:\d+|[ivx]+)\)\s"),
    re.compile(r"^(?:[-*]\s+|#{1,6}\s*)?[ivx]+\.\s"),
]


# ---------------------------------------------------------------- helpers
def cn2int(s):
    s = s.replace("廿", "二十").replace("卅", "三十").replace("兩", "二")
    if s.isdigit():
        return int(s)
    digits = {"零": 0, "〇": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
    total, num = 0, 0
    for ch in s:
        if ch in digits:
            num = digits[ch]
        elif ch == "十":
            total += (num or 1) * 10
            num = 0
        elif ch == "百":
            total += (num or 1) * 100
            num = 0
    return total + num


def cjk_ratio(text):
    zh = len(re.findall(rf"[{CJK}]", text))
    en = len(re.findall(r"[A-Za-z]", text))
    return zh / (zh + en) if zh + en else 0.0


def is_zh(text):
    return cjk_ratio(text) >= 0.3


def join_cjk_spaces(line):
    """PDF 斷行留下的空白：「繼續修習課 程」→「繼續修習課程」。"""
    return re.sub(rf"(?<=[{CJK}{CJK_PUNCT}])[ \t]+(?=[{CJK}{CJK_PUNCT}])", "", line)


def strip_mark(line):
    return re.sub(r"^(?:#{1,6}\s*|[-*]\s+)", "", line).strip()


def doc_info(path):
    """cleaned_A231060004_學生申請期中停修課程實施要點.md → ('A231060004', '學生申請期中停修課程實施要點')"""
    stem = re.sub(r"^(raw|cleaned)_", "", Path(path).stem)
    m = re.match(r"([A-Z]\d+)_(.+)", stem)
    return (m.group(1), m.group(2)) if m else ("", stem)


# ---------------------------------------------------------------- cleaning
def running_headers(lines, zh_title):
    """頁首頁尾：法規名稱、英文名稱、校名，以及重複出現的短英文行。"""
    heads = set(SCHOOL_NAMES) | {zh_title}
    first = next((l for l in lines if l.startswith("#")), "")
    for seg in first.lstrip("# ").split(" / "):
        if seg and not is_zh(seg) and len(seg) > 15:
            heads.add(seg.strip())
    counts = Counter(strip_mark(l) for l in lines if l.strip())
    for text, n in counts.items():
        if n >= 2 and 15 <= len(text) <= 90 and re.fullmatch(r"[A-Za-z ,'&-]+", text) and not text.startswith(("Article", "Chapter", "Part")):
            heads.add(text)
    return sorted(heads, key=len, reverse=True)


def clean_lines(md, zh_title):
    lines = [join_cjk_spaces(l.rstrip()) for l in md.splitlines()]
    # 條號黏在英文行尾：「...on Aug. 08, 2017 第一條 目的」→ 換行
    expanded = []
    for l in lines:
        if l.strip().startswith("頁次") or len(re.findall(r"第[一二三四五六七八九十百]+條", l)) >= 3:
            continue  # 目錄
        expanded.extend(re.sub(r"(?<=[A-Za-z0-9.,)])\s+(第[一二三四五六七八九十百]+條)", r"\n\1", l).split("\n"))
    heads = running_headers(expanded, zh_title)
    head_alt = "|".join(re.escape(h) for h in heads)
    out = []
    for l in expanded:
        s = l.strip()
        if not s or NOISE_LINE_RE.match(s) or s == "```":
            continue
        if re.fullmatch(rf"{MARK}第{CN_NUM}條\S{{0,20}}\s*\.*\s*\d{{1,3}}", s):
            continue  # 目錄中的一行：「第二條 適用範圍 1」
        # 整行只剩頁首/頁碼 → 刪除
        rest = re.sub(head_alt, "", strip_mark(s))
        if not s.startswith("|") and not re.sub(r"[\d\s/]", "", rest):
            continue
        # 行首帶著頁首（例如「Work Specification ... / i. Chinese ...」）→ 去掉前綴
        s = re.sub(rf"^(?:#{{1,6}}\s*)?(?:\d+\s*)?(?:(?:{head_alt})\s*\d*\s*/?\s*)+", "", s) or s
        s = re.sub(r"<!--.*?-->\s*/?\s*", "", s).strip()
        if s:
            out.append(s)
    return join_continuations(out)


def join_continuations(lines):
    """Docling 把一句話拆成兩個清單項目：「- 本校學生電子郵件帳號…提供本校學」「- 生及校友…」→ 合併。"""
    out = []
    for l in lines:
        body = re.sub(r"^(?:[-*]\s+|\d+\.\s+)", "", l)
        prev = out[-1] if out else ""
        prev_is_head = prev.startswith(("#", "|")) or ARTICLE_RE.match(prev) or CHAPTER_RE.match(prev) or any(p.match(prev) for p in ZH_LEVELS[:2]) and len(prev) < 20
        if out and not l.startswith(("#", "|")) and not prev_is_head:
            zh_cont = (re.search(rf"[{CJK}，、（「]$", prev) and re.match(rf"[{CJK}]", body)
                       and not ARTICLE_RE.match(l) and not any(p.match(l) for p in ZH_LEVELS[:2])
                       and not CHAPTER_RE.match(l))
            en_cont = re.match(r"[a-z]", body) and re.search(r"[A-Za-z,]$", prev)
            if zh_cont or en_cont:
                out[-1] = prev + ("" if zh_cont else " ") + body
                continue
        out.append(l)
    return out


def split_bilingual(line):
    """「…學。 / Article 11 Students shall…」→ 拆成中文段、英文段。"""
    parts = [p.strip() for p in line.split(" / ") if p.strip()]
    if len(parts) > 1 and len({is_zh(p) for p in parts}) > 1:
        return parts
    return [line]


def clean_table(lines):
    rows = []
    for l in lines:
        if re.fullmatch(r"\|?[\s|:-]+\|?", l):
            continue
        cells, seen = [], set()
        for c in (c.strip() for c in l.strip("|").split("|")):
            if not c or re.fullmatch(r"[.\s…]+\d*", c):
                continue
            if len(c) > 3 and c in seen:   # Docling 把合併儲存格重複多次；數字欄不去重
                continue
            cells.append(c)
            seen.add(c)
        if cells:
            rows.append("｜".join(cells))
    return rows


# ---------------------------------------------------------------- segmentation
def find_article_starts(lines):
    """第一輪：找出每一條的起點（條號必須遞增，避免把目錄或引用「第十條」誤認為新條文）。"""
    starts, last_no = [], 0
    for i, l in enumerate(lines):
        if l.startswith("|"):
            continue
        m = ARTICLE_RE.match(l)
        no = cn2int(m.group(1)) if m else None
        if no is None:
            em = EN_ARTICLE_RE.match(l)
            # 中文條文被 Docling 弄丟（formula-not-decoded），只剩英文 Article N
            if em and int(em.group(1)) == last_no + 1:
                no = int(em.group(1))
        if no is not None and no > last_no:
            title = ""
            if m:
                after = l[m.end():].strip()
                if after and len(after) <= 20 and "。" not in after:
                    title = after.rstrip("：:")
            label = re.sub(r"\s+", "", m.group(0).lstrip("#-*0123456789. ")) if m else f"第{no}條"
            starts.append((i, no, title, label))
            last_no = no
    return starts


def find_appendix_start(lines, starts):
    """最後一條之後：遇到「申請表、表號、附件…」的短標題，或英文條文之後的表格 → 附件開始。"""
    if not starts:
        return len(lines)
    last_i = starts[-1][0]
    en_seen = False
    for i in range(last_i + 1, len(lines)):
        l = lines[i]
        if EN_ARTICLE_RE.match(l):
            en_seen = True
            continue
        short = (l.startswith("#") or len(l) < 40) and "。" not in l
        if short and APPENDIX_RE.search(l):
            return i
        if en_seen and l.startswith("|"):
            return i
        if short and l.startswith("#") and is_zh(l) and i > last_i + 2 and en_seen:
            return i
    return len(lines)


def segment(lines):
    """把一份法規切成：front（封面）、articles（條文）、appendix（附表、表單）。"""
    starts = find_article_starts(lines)
    app_i = find_appendix_start(lines, starts)
    start_at = {i: (no, title, label) for i, no, title, label in starts}
    front, articles = [], []
    part = chapter = ""
    cur = None
    for i, l in enumerate(lines[:app_i]):
        m = CHAPTER_RE.match(l)
        if m and not ARTICLE_RE.match(l) and not l.startswith("|"):
            label = (re.sub(r"\s+", "", m.group(1)) + " " + m.group(2).strip()).strip()
            if "篇" in m.group(1):
                part, chapter = label, ""
            else:
                chapter = label
            continue
        if cur and EN_CHAPTER_RE.match(l) and not EN_ARTICLE_RE.match(l):
            continue
        if cur and REVISION_RE.match(strip_mark(l)):
            continue  # 換頁時插入的「88.09.01教務會議訂定」等修訂日期
        if i in start_at:
            no, title, label = start_at[i]
            cur = {"article_no": no, "label": label, "title": title, "part": part, "chapter": chapter, "lines": [l]}
            articles.append(cur)
        elif cur is None:
            front.append(l)
        else:
            cur["lines"].append(l)
    return front, articles, lines[app_i:]


def pack(header, ctx, zh, en, level=0):
    """遞迴切分：一、 → （一） → 1. → 句號。回傳 [(ctx, zh_lines, en_lines), ...]"""
    def size(lines):
        return len(header) + len(ctx) + sum(len(x) + 1 for x in lines)

    if size(zh) <= MAX_CHARS or not zh:
        return [(ctx, zh, en)]
    if level >= len(ZH_LEVELS):
        # 最後手段：先整行打包；單行太長才依句號切
        room = MAX_CHARS - len(header) - len(ctx) - 1
        units_ = []
        for x in zh:
            if len(x) <= room:
                units_.append(x)
            else:
                units_ += [p_ + "。" for p_ in x.split("。") if p_]
        pieces, cur = [], []
        for u in units_:
            if cur and size(cur + [u]) > MAX_CHARS:
                pieces.append((ctx, cur, []))
                cur = []
            cur.append(u)
        pieces.append((ctx, cur, []))
        pieces[0] = (pieces[0][0], pieces[0][1], en)
        return pieces

    def units(lines, pat):
        intro, groups = [], []
        for x in lines:
            if pat.match(x):
                groups.append([x])
            elif groups:
                groups[-1].append(x)
            else:
                intro.append(x)
        return intro, groups

    zh_intro, zh_groups = units(zh, ZH_LEVELS[level])
    if len(zh_groups) < 2:
        return pack(header, ctx, zh, en, level + 1)
    en_intro, en_groups = units(en, EN_LEVELS[level])
    paired = len(en_groups) == len(zh_groups)
    intro_txt = "".join(strip_mark(x) for x in zh_intro)
    new_ctx = (ctx + " " if ctx else "") + (intro_txt[:60] + ("…" if len(intro_txt) > 60 else ""))
    new_ctx = new_ctx.strip()

    # 第一段（「一、」之前的文字）完整保留在第一塊；之後各塊只帶前 60 字當作上下文
    items = [(zh_intro, en_intro if paired else [])] if zh_intro else []
    items += [(g, en_groups[i] if paired else []) for i, g in enumerate(zh_groups)]
    pieces, cur_zh, cur_en, cur_intro = [], [], [], False

    def fits(lines, with_intro):
        return len(header) + len(ctx if with_intro else new_ctx) + sum(len(x) + 1 for x in lines) <= MAX_CHARS

    for g, eg in items:
        is_intro = g is zh_intro
        if fits(cur_zh + g, cur_intro or is_intro):
            cur_zh, cur_en, cur_intro = cur_zh + g, cur_en + eg, cur_intro or is_intro
            continue
        if cur_zh:
            pieces.append((ctx if cur_intro else new_ctx, cur_zh, cur_en))
        cur_zh, cur_en, cur_intro = [], [], False
        if not fits(g, is_intro):
            if is_intro:
                pieces += pack(header, ctx, g, eg, len(ZH_LEVELS))   # 很長的第一段：依句號切
            else:
                sub_ctx = (new_ctx + " " + strip_mark(g[0])[:30]).strip()
                pieces += pack(header, sub_ctx, g[1:], eg[1:] if eg else [], level + 1)
        else:
            cur_zh, cur_en, cur_intro = list(g), list(eg), is_intro
    if cur_zh:
        pieces.append((ctx if cur_intro else new_ctx, cur_zh, cur_en))
    if not paired and (en_intro or en_groups):
        # 英文條目數量對不上中文（Docling 編號錯亂）→ 英文另外成塊，每塊最多 MAX_EN_CHARS 字元
        cur = []
        for x in en_intro + [x for g in en_groups for x in g]:
            if cur and sum(len(y) + 1 for y in cur + [x]) > MAX_EN_CHARS:
                pieces.append(("__EN__", [], cur))
                cur = []
            cur.append(x)
        if cur:
            pieces.append(("__EN__", [], cur))
    return pieces


def make_header(title, art):
    ctx = "｜".join(x for x in [title, art.get("part", ""), art.get("chapter", "")] if x)
    head = f"【{ctx}】{art['label']}"
    if art.get("title"):
        head += " " + art["title"]
    return head


def chunk_document(md, path, cluster):
    code, title = doc_info(path)
    lines = clean_lines(md, title)
    front, articles, appendix = segment(lines)
    base = {"source_file": Path(path).name, "doc_code": code, "doc_title": title, "cluster": cluster}
    chunks = []

    # 1) 封面：只留非表格文字，最多 FRONT_MAX 字
    front_txt = " ".join(x for x in front if not x.startswith("|"))
    if front_txt:
        front_txt = front_txt[:FRONT_MAX]
        head = f"【{title}】規章基本資料"
        chunks.append({"text": head + "\n" + front_txt, "embed_text": head + "\n" + front_txt,
                       "metadata": {**base, "chunk_type": "front", "article_no": 0}})

    # 2) 條文
    for art in articles:
        zh, en = [], []
        for l in art["lines"]:
            if l.startswith("|"):
                for row in clean_table([l]):   # 中英對照的表格列：有中文就放中文側
                    (zh if len(re.findall(rf"[{CJK}]", row)) >= 4 else en).append(row)
                continue
            for seg in split_bilingual(strip_mark(l)):
                (zh if is_zh(seg) else en).append(seg)
        header = make_header(title, art)
        if DEDUP_LABEL and zh:
            first = re.sub(r"\s+", "", zh[0])
            lead = art["label"] + (art["title"] or "")
            if first.startswith(lead):
                rest = first[len(lead):].lstrip("：:")
                zh = ([rest] if rest else []) + zh[1:]
            elif first.startswith(art["label"]):
                zh = [first[len(art["label"]):]] + zh[1:]
        for k, (ctx, z, e) in enumerate(pack(header, "", zh, en)):
            en_only = ctx == "__EN__"
            ctx = "" if en_only else ctx
            body_zh = "\n".join(z)
            body_en = "\n".join(e)
            text = "\n".join(x for x in [header, ctx, body_zh, body_en] if x)
            embed = "\n".join(x for x in [header, ctx, body_zh] if x) if body_zh else text
            chunks.append({"text": text, "embed_text": embed,
                           "metadata": {**base, "chunk_type": "article_en" if en_only else "article",
                                        "article_no": art["article_no"], "article_title": art["title"],
                                        "part": art["part"], "chapter": art["chapter"], "piece": k}})

    # 3) 附件：依 ## 標題分段；表格整理成「欄｜欄」；沒有中文的段落（英文版表單）略過
    sections, cur = [], []
    for l in appendix:
        if (l.startswith("#") or l.startswith("表號")) and cur:
            sections.append(cur)
            cur = []
        cur.append(l)
    if cur:
        sections.append(cur)
    for sec in sections:
        body = []   # (文字, 是否為表格列)
        table = []
        for l in sec + ["<END>"]:
            if l.startswith("|"):
                table.append(l)
                continue
            if table:
                body.extend((r, True) for r in clean_table(table))
                table = []
            if l != "<END>":
                body.append((strip_mark(l), False))
        # 保留：中文行、表格列（含純數字的對照表）；略過：英文版表單
        zh_body = [b for b, is_row in body if is_row or is_zh(b)]
        if sum(len(re.findall(rf"[{CJK}]", b)) for b in zh_body) < 15:
            continue
        sec_title = next((strip_mark(x) for x in sec if not x.startswith("|")), "表單")[:40]
        is_form = bool(FORM_RE.search(sec_title)) or sum(b.count("□") for b in zh_body) >= 3
        if is_form and not KEEP_FORMS:
            continue
        header = f"【{title}】附件：{sec_title}"
        if zh_body and zh_body[0].startswith(sec_title[:10]):
            zh_body = zh_body[1:] or zh_body
        groups, cur = [], []
        for b in zh_body:  # 附件依「行」打包（表格一列一行），每塊不超過 MAX_CHARS
            if cur and len(header) + sum(len(x) + 1 for x in cur + [b]) > MAX_CHARS:
                groups.append(cur)
                cur = []
            cur.append(b[:MAX_CHARS])
        if cur:
            groups.append(cur)
        for k, z in enumerate(groups):
            text = "\n".join([header] + z)
            chunks.append({"text": text, "embed_text": text,
                           "metadata": {**base, "chunk_type": "form" if is_form else "appendix",
                                        "article_no": None, "piece": k}})

    for i, c in enumerate(chunks):
        c["metadata"]["chunk_id"] = f"{code}#{i}"
        c["metadata"]["char_length"] = len(c["text"])
        c["metadata"]["embed_length"] = len(c["embed_text"])
    return chunks


def rechunk_all(interim_dir, out_dir, pattern="raw_*.md", fallback="cleaned_*.md"):
    interim_dir, out_dir = Path(interim_dir), Path(out_dir)
    files = sorted(interim_dir.glob(f"*/{pattern}")) or sorted(interim_dir.glob(f"*/{fallback}"))
    all_chunks = []
    for f in files:
        chunks = chunk_document(f.read_text(encoding="utf-8"), f, f.parent.name)
        d = out_dir / f.parent.name
        d.mkdir(parents=True, exist_ok=True)
        stem = re.sub(r"^(raw|cleaned)_", "", f.stem)
        (d / f"v2_{stem}.json").write_text(json.dumps(chunks, ensure_ascii=False, indent=2), encoding="utf-8")
        all_chunks += chunks
    return files, all_chunks


if __name__ == "__main__":
    import sys
    if "--max" in sys.argv:
        MAX_CHARS = int(sys.argv[sys.argv.index("--max") + 1])
    root = Path(__file__).resolve().parents[1]          # src/ 的上一層 = 專案根目錄
    files, chunks = rechunk_all(root / "data" / "interim", root / "data" / "processed_v2")
    kinds = Counter(c["metadata"]["chunk_type"] for c in chunks)
    longest = max(c["metadata"]["embed_length"] for c in chunks if c["metadata"]["chunk_type"] != "article_en")
    print(f"讀取 {len(files)} 份法規 → {len(chunks)} 個 chunks（MAX_CHARS = {MAX_CHARS}）")
    print("類型：", dict(kinds))
    print("中文 chunk 最長：", longest, "字")
    print("輸出：", root / "data" / "processed_v2")

