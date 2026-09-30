"""환경 변수 SHEET_CSV_URL의 CSV를 읽어 하루 한 문장 화면을 만듭니다. 외부 패키지 불필요."""

import argparse
import csv
from datetime import date, datetime, timedelta
from html import escape
import io
import os
from pathlib import Path
import re
import sys
import tempfile
from urllib.parse import urlsplit
import urllib.error
import urllib.request
from zoneinfo import ZoneInfo


KST = ZoneInfo("Asia/Seoul")
ENV_FILE = Path(__file__).with_name(".env")
URL_ENV_NAME = "SHEET_CSV_URL"
# 시트와 화면이 함께 지키는 열 약속. 하나라도 없으면 화면을 만들지 않습니다.
REQUIRED_COLUMNS = ("제목", "내용", "분류", "링크", "공개")
HEADER_ROW = 1          # 시트에서 열 이름이 있는 줄 번호
FIRST_DATA_ROW = 2      # 시트에서 첫 데이터가 있는 줄 번호
PUBLIC_MARK = "Y"
FETCH_TIMEOUT = 20
NO_TITLE = "(제목 없음)"
NO_CATEGORY = "기타"


def load_env_file(filepath=ENV_FILE, environment=None):
    """.env에 적어 둔 값을 읽습니다. 이미 환경 변수에 있으면 그 값을 그대로 둡니다."""
    environment = os.environ if environment is None else environment
    path = Path(filepath)
    if not path.is_file():
        return environment
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, value = line.partition("=")
        name = name.strip()
        value = value.strip().strip('"').strip("'")
        if name and name not in environment:
            environment[name] = value
    return environment


def resolve_source(environment=None):
    """CSV 주소는 환경 변수나 .env에서만 받습니다. 화면 코드에는 적지 않습니다."""
    environment = os.environ if environment is None else environment
    source = (environment.get(URL_ENV_NAME) or "").strip()
    if not source:
        raise ValueError(
            f"{URL_ENV_NAME}이(가) 비어 있습니다. "
            f".env 파일이나 GitHub Secrets에 시트 CSV 주소를 넣으세요."
        )
    return source


def read_csv_text(source, timeout=FETCH_TIMEOUT):
    """주소면 내려받고, 파일 경로면 그대로 읽습니다. 확인용 CSV도 같은 방법으로 씁니다."""
    if source.startswith(("http://", "https://")):
        request = urllib.request.Request(source, headers={"User-Agent": "daily-quote-project"})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read()
        except urllib.error.HTTPError as error:
            raise ValueError(
                f"CSV를 내려받지 못했습니다(HTTP {error.code}). "
                f"시트가 '웹에 게시'되어 있고 주소 끝이 output=csv인지 확인하세요."
            ) from error
        except urllib.error.URLError as error:
            raise ValueError(f"CSV 주소에 연결하지 못했습니다: {error.reason}") from error
        return raw.decode("utf-8-sig")
    path = Path(source)
    if not path.is_file():
        raise ValueError(f"CSV 파일을 찾지 못했습니다: {source}")
    return path.read_text(encoding="utf-8-sig")


def safe_link(value):
    """javascript: 같은 주소가 화면에 들어가지 않도록 http·https만 통과시킵니다."""
    value = (value or "").strip()
    if not value:
        return ""
    return value if urlsplit(value).scheme in ("http", "https") else ""


def parse_rows(text):
    """열 약속을 검사하고 공개=Y 행만 남깁니다. 건너뛴 줄은 줄 번호와 함께 돌려줍니다."""
    reader = csv.DictReader(io.StringIO(text))
    names = reader.fieldnames
    if not names:
        raise ValueError("CSV가 비어 있습니다. 시트 1행에 열 이름이 있는지 확인하세요.")
    names = [(name or "").strip().lstrip("﻿") for name in names]
    reader.fieldnames = names
    missing = [name for name in REQUIRED_COLUMNS if name not in names]
    if missing:
        raise ValueError(
            f"CSV에 필요한 열이 없습니다: {', '.join(missing)}. "
            f"시트 {HEADER_ROW}행의 현재 열: {', '.join(names) or '(없음)'}"
        )

    items = []
    skipped = []
    last_row = HEADER_ROW
    for row_number, row in enumerate(reader, start=FIRST_DATA_ROW):
        last_row = row_number
        cell = {name: (row.get(name) or "").strip() for name in REQUIRED_COLUMNS}
        if cell["공개"].upper() != PUBLIC_MARK:
            continue
        if not cell["내용"]:
            skipped.append(f"{row_number}번 행: 공개=Y인데 내용이 비어 있어 건너뜁니다.")
            continue
        if not cell["제목"]:
            skipped.append(f"{row_number}번 행: 제목이 비어 있어 '{NO_TITLE}'으로 표시합니다.")
        items.append({
            "row": row_number,
            "title": cell["제목"] or NO_TITLE,
            "body": cell["내용"],
            "category": cell["분류"] or NO_CATEGORY,
            "link": safe_link(cell["링크"]),
        })

    if not items:
        if last_row < FIRST_DATA_ROW:
            raise ValueError(f"CSV에 데이터 행이 없습니다. 시트 {HEADER_ROW}행에 열 이름만 있습니다.")
        raise ValueError(
            f"공개={PUBLIC_MARK}인 행이 없습니다. "
            f"검사한 데이터 행 {FIRST_DATA_ROW}~{last_row}번 가운데 쓸 수 있는 행이 0개입니다."
        )
    return items, skipped


def load_items(source=None, environment=None):
    """주소 찾기 → 내려받기 → 검사까지 한 번에 합니다."""
    if source is None:
        source = resolve_source(environment)
    return parse_rows(read_csv_text(source))


def parse_preview_date(value):
    """입력은 정확히 YYYY-MM-DD 형식으로 받고 존재하는 날짜인지 확인합니다."""
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise argparse.ArgumentTypeError("날짜는 YYYY-MM-DD 형식으로 입력하세요.")
    try:
        result = date.fromisoformat(value)
        if result == date.min:
            raise ValueError("어제 날짜를 계산할 수 없습니다.")
        return result
    except ValueError as error:
        raise argparse.ArgumentTypeError(f"사용할 수 없는 날짜입니다: {value}") from error


def choose_date(preview_date, generated_at):
    """생성 시각이 UTC여도 날짜 선택은 한국시간으로 합니다."""
    return preview_date if preview_date is not None else generated_at.astimezone(KST).date()


def pick_item(items, target_date):
    """날짜 순번으로 목록을 순환합니다. 같은 날짜와 같은 목록이면 같은 항목입니다."""
    return items[(target_date.toordinal() - 1) % len(items)]


def link_tag(url, label, class_name):
    """링크 열이 비어 있으면 아무것도 넣지 않습니다."""
    if not url:
        return ""
    return (f'<a class="{class_name}" href="{escape(url)}" '
            f'target="_blank" rel="noopener noreferrer">{escape(label)}</a>')


def build_filters(items):
    """분류 버튼은 시트의 분류 값에서 나온 순서 그대로 만듭니다."""
    categories = []
    for item in items:
        if item["category"] not in categories:
            categories.append(item["category"])
    chips = ['<button type="button" class="chip is-on" data-category="">전체</button>']
    for name in categories:
        chips.append(f'<button type="button" class="chip" data-category="{escape(name)}">'
                     f'{escape(name)}</button>')
    return "\n        ".join(chips)


def build_items(items):
    """검색은 제목·내용·분류를 한 줄로 합쳐 둔 data-search에서 찾습니다."""
    cards = []
    for item in items:
        haystack = f"{item['title']} {item['body']} {item['category']}".lower()
        cards.append(
            f'<li class="item" data-category="{escape(item["category"])}" '
            f'data-search="{escape(haystack)}">'
            f'<p class="item-title">{escape(item["title"])}</p>'
            f'<p class="item-body">{escape(item["body"])}</p>'
            f'<p class="item-meta"><span class="item-tag">{escape(item["category"])}</span>'
            f'{link_tag(item["link"], "링크 열기", "item-link")}</p>'
            f'</li>'
        )
    return "\n        ".join(cards)


# 중괄호가 많아 f-string 밖에 따로 둡니다. 화면 코드에는 주소나 인증키를 넣지 않습니다.
LIST_STYLE = """
    .browse { text-align: left; background: #ffffff05; border: 1px solid #ffffff14;
      border-radius: 20px; padding: 26px 28px 24px; margin-bottom: 23px; }
    .browse-head { display: flex; align-items: baseline; justify-content: space-between;
      gap: 12px; flex-wrap: wrap; margin-bottom: 16px; }
    .browse-title { font-size: 15px; font-weight: 650; margin: 0; }
    .browse-count { font-size: 12px; color: #a8b4c8; margin: 0; }
    .search-box { margin-bottom: 14px; }
    .search-box input { width: 100%; padding: 11px 15px; border-radius: 12px;
      border: 1px solid #ffffff26; background: #0c1022a8; color: #f1f5f9;
      font-size: 14px; font-family: inherit; }
    .search-box input::placeholder { color: #8d99ae; }
    .search-box input:focus { outline: 2px solid var(--accent); outline-offset: 1px; }
    .chips { display: flex; flex-wrap: wrap; gap: 7px; margin-bottom: 18px; }
    .chip { padding: 6px 13px; border-radius: 20px; border: 1px solid #ffffff26;
      background: #ffffff08; color: #cbd5e1; font-size: 12px; font-family: inherit;
      cursor: pointer; }
    .chip:hover { border-color: var(--accent); }
    .chip.is-on { background: var(--accent); border-color: var(--accent); color: #11152b;
      font-weight: 650; }
    .item-list { list-style: none; margin: 0; padding: 0; display: flex;
      flex-direction: column; gap: 11px; }
    .item { border: 1px solid #ffffff12; border-radius: 14px; padding: 15px 18px;
      background: #ffffff04; }
    .item-title { font-size: 14px; font-weight: 650; margin: 0 0 6px; overflow-wrap: anywhere; }
    .item-body { font-size: 13px; line-height: 1.7; color: #cbd5e1; margin: 0 0 10px;
      word-break: keep-all; overflow-wrap: anywhere; }
    .item-meta { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin: 0; }
    .item-tag { font-size: 11px; color: var(--accent); border: 1px solid #ffffff1c;
      border-radius: 20px; padding: 3px 9px; }
    .item-link { font-size: 11px; color: #a8b4c8; }
    .empty-note { display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
      font-size: 13px; color: #d8b4fe; margin: 14px 0 0; word-break: keep-all; }
    .card-title { font-size: 13px; color: #cbd5e1; margin: 0 0 14px; overflow-wrap: anywhere; }
    .card-link { font-size: 12px; color: #a8b4c8; display: inline-block; margin-top: 10px; }
    .sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }
    [hidden] { display: none !important; }
    @media (max-width: 600px) { .browse { padding: 20px 17px 18px; } }
"""

LIST_SCRIPT = """
  (function () {
    var input = document.getElementById('search-input');
    var chips = Array.prototype.slice.call(document.querySelectorAll('.chips .chip'));
    var items = Array.prototype.slice.call(document.querySelectorAll('.item'));
    var note = document.getElementById('empty-note');
    var noteText = document.getElementById('empty-text');
    var countLabel = document.getElementById('result-count');
    var resetButton = document.getElementById('reset-button');
    var category = '';

    function apply() {
      var typed = input.value.trim();
      var word = typed.toLowerCase();
      var shown = 0;
      items.forEach(function (item) {
        var wordOk = word === '' || item.dataset.search.indexOf(word) !== -1;
        var categoryOk = category === '' || item.dataset.category === category;
        var show = wordOk && categoryOk;
        item.hidden = !show;
        if (show) { shown += 1; }
      });
      countLabel.textContent = shown + '\\uAC1C';
      note.hidden = shown !== 0;
      if (shown === 0) {
        if (typed !== '') {
          noteText.textContent = '\\u2018' + typed + '\\u2019\\uC5D0 \\uB9DE\\uB294 \\uBB38\\uC7A5\\uC774 \\uC5C6\\uC2B5\\uB2C8\\uB2E4. \\uB2E4\\uB978 \\uB9D0\\uB85C \\uCC3E\\uC544\\uBCF4\\uC138\\uC694.';
        } else {
          noteText.textContent = '\\u2018' + category + '\\u2019 \\uBD84\\uB958\\uC5D0 \\uD574\\uB2F9\\uD558\\uB294 \\uBB38\\uC7A5\\uC774 \\uC5C6\\uC2B5\\uB2C8\\uB2E4.';
        }
      }
    }

    input.addEventListener('input', apply);
    chips.forEach(function (chip) {
      chip.addEventListener('click', function () {
        category = chip.dataset.category;
        chips.forEach(function (other) { other.classList.toggle('is-on', other === chip); });
        apply();
      });
    });
    resetButton.addEventListener('click', function () {
      input.value = '';
      category = '';
      chips.forEach(function (chip) { chip.classList.toggle('is-on', chip.dataset.category === ''); });
      apply();
      input.focus();
    });
    apply();
  })();
"""


def generate_html(items, target_date, generated_at, is_preview=False, environment=None):
    """시트에서 가져온 값과 메타데이터를 HTML 이스케이프하여 화면을 만듭니다."""
    environment = os.environ if environment is None else environment
    yesterday = target_date - timedelta(days=1)
    today_item = pick_item(items, target_date)
    yesterday_item = pick_item(items, yesterday)
    generated_kst = generated_at.astimezone(KST)
    colors = ["#a78bfa", "#7dd3fc", "#a5b4fc", "#6ee7b7", "#f9a8d4", "#fcd34d", "#fdba74"]
    accent = colors[target_date.toordinal() % len(colors)]
    mode_label = "날짜 미리보기" if is_preview else "한국 날짜 기준"
    previous_label = "선택한 날짜의 전날" if is_preview else "어제의 한 문장"
    run_number = environment.get("GITHUB_RUN_NUMBER", "")
    run_attempt = environment.get("GITHUB_RUN_ATTEMPT", "1")
    commit = environment.get("GITHUB_SHA", "")
    provenance = []
    if run_number:
        provenance.append(f"Actions 실행 #{escape(run_number)} · 시도 {escape(run_attempt)}")
    if commit:
        provenance.append(f"커밋 {escape(commit[:7])}")
    provenance_text = " · ".join(provenance) if provenance else "로컬 생성본"
    preview_note = '<p class="preview-note">선택한 날짜의 문구를 확인하는 화면입니다.</p>' if is_preview else ""
    today_link = link_tag(today_item["link"], "자세히 보기", "card-link")
    filters_html = build_filters(items)
    items_html = build_items(items)
    return f'''<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="날짜에 따라 골라 보는 학습과 협업의 한 문장">
  <title>오늘의 한 문장</title>
  <style>
    * {{ box-sizing: border-box; }}
    :root {{ color-scheme: dark; --accent: {accent}; }}
    body {{ margin: 0; min-height: 100vh; padding: 42px 22px 30px;
      font-family: -apple-system, BlinkMacSystemFont, "Apple SD Gothic Neo", "Malgun Gothic", sans-serif;
      background: linear-gradient(135deg, #0f0c29, #302b63, #182235); color: #f1f5f9;
      display: flex; align-items: center; justify-content: center; }}
    body::before {{ content: ""; position: fixed; inset: 0; pointer-events: none;
      background: radial-gradient(circle at 85% 10%, #ffffff08, transparent 40%); }}
    .container {{ width: 100%; max-width: 760px; text-align: center; position: relative; }}
    .eyebrow {{ font-size: 11px; letter-spacing: 3px; color: var(--accent); margin: 0 0 12px; }}
    h1 {{ font-size: 28px; font-weight: 650; margin: 0 0 23px; letter-spacing: -1px; }}
    .date-badge {{ display: inline-flex; gap: 13px; align-items: center; flex-wrap: wrap; justify-content: center;
      padding: 9px 20px; border: 1px solid #ffffff26; border-radius: 30px; color: #cbd5e1;
      background: #ffffff08; font-size: 13px; margin-bottom: 26px; }}
    .mode {{ color: var(--accent); font-size: 12px; }}
    .preview-note {{ margin: -10px 0 22px; color: #d8b4fe; font-size: 13px; }}
    .quote-card {{ background: #ffffff07; border: 1px solid #ffffff1c; border-radius: 24px;
      padding: 39px 46px 34px; margin-bottom: 20px; box-shadow: 0 18px 45px #00000018; }}
    .quote-mark {{ display: block; font-family: Georgia, serif; font-size: 74px; line-height: .8;
      color: var(--accent); opacity: .6; margin-bottom: 10px; }}
    .quote-text {{ font-family: "AppleMyungjo", "Batang", Georgia, serif; font-size: 29px;
      font-weight: 600; line-height: 1.75; margin: 0 auto 26px; word-break: keep-all; overflow-wrap: anywhere; }}
    .divider {{ background: var(--accent); opacity: .5; width: 50px; height: 2px; margin: 0 auto 20px; }}
    .author {{ font-size: 14px; color: var(--accent); margin: 0 0 7px; overflow-wrap: anywhere; }}
    .topic {{ font-size: 12px; color: #a8b4c8; margin: 0; overflow-wrap: anywhere; }}
    .yesterday {{ background: #ffffff04; border: 1px solid #ffffff12; border-radius: 16px;
      padding: 22px 30px; margin-bottom: 23px; }}
    .yesterday-label {{ font-size: 11px; color: #a8b4c8; margin: 0 0 11px; }}
    .yesterday-quote {{ font-family: "AppleMyungjo", "Batang", Georgia, serif; font-size: 16px;
      color: #cbd5e1; line-height: 1.7; margin: 0; word-break: keep-all; overflow-wrap: anywhere; }}
    .yesterday-author {{ font-size: 11px; color: #a8b4c8; margin: 10px 0 0; overflow-wrap: anywhere; }}
    footer {{ font-size: 11px; line-height: 1.9; color: #a8b4c8; }}
    footer p {{ margin: 3px 0; }}
    .generated {{ color: #d3dbea; }}
    @media (max-width: 600px) {{
      body {{ padding: 30px 17px 24px; }} h1 {{ font-size: 25px; }}
      .quote-card {{ padding: 32px 23px 28px; }} .quote-text {{ font-size: 23px; }}
      .yesterday {{ padding: 20px; }} .yesterday-quote {{ font-size: 15px; }}
    }}
{LIST_STYLE}  </style>
</head>
<body>
  <main class="container">
    <p class="eyebrow">TODAY IN ONE SENTENCE</p>
    <h1>오늘의 한 문장</h1>
    <div class="date-badge"><time id="selected-date" datetime="{target_date.isoformat()}">{target_date.isoformat()}</time><span class="mode">{mode_label}</span></div>
    {preview_note}
    <section class="quote-card" aria-label="선택한 날짜의 문구">
      <p class="card-title">{escape(today_item['title'])}</p>
      <span class="quote-mark" aria-hidden="true">&ldquo;</span>
      <p class="quote-text" id="today-quote">{escape(today_item['body'])}</p>
      <div class="divider" aria-hidden="true"></div>
      <p class="topic">{escape(today_item['category'])}</p>
      {today_link}
    </section>
    <section class="yesterday" aria-label="전날의 문구">
      <p class="yesterday-label">{previous_label} · {yesterday.isoformat()}</p>
      <p class="yesterday-quote" id="yesterday-quote">{escape(yesterday_item['body'])}</p>
      <p class="yesterday-author">{escape(yesterday_item['title'])} · {escape(yesterday_item['category'])}</p>
    </section>
    <section class="browse" aria-label="전체 문장 찾아보기">
      <div class="browse-head">
        <h2 class="browse-title">전체 문장</h2>
        <p class="browse-count">보이는 문장 <span id="result-count">{len(items)}개</span> / 전체 {len(items)}개</p>
      </div>
      <div class="search-box">
        <label class="sr-only" for="search-input">문장 검색</label>
        <input type="search" id="search-input" placeholder="제목·내용·분류로 찾기" autocomplete="off">
      </div>
      <div class="chips" role="group" aria-label="분류 고르기">
        {filters_html}
      </div>
      <ul class="item-list" id="item-list">
        {items_html}
      </ul>
      <p class="empty-note" id="empty-note" hidden>
        <span id="empty-text">찾는 문장이 없습니다.</span>
        <button type="button" class="chip" id="reset-button">검색 지우기</button>
      </p>
    </section>
    <footer>
      <p class="generated">마지막 생성 <time id="generated-at" datetime="{generated_kst.isoformat(timespec='seconds')}">{generated_kst.strftime('%Y.%m.%d %H:%M:%S')} KST</time></p>
      <p id="build-info">{provenance_text}</p>
      <p>하루 한 문장, 배움과 협업을 위한 수업 예제</p>
    </footer>
  </main>
  <script>
{LIST_SCRIPT}  </script>
</body>
</html>
'''


def atomic_write(output, content):
    """같은 폴더에 임시 파일을 완성한 뒤 교체하여 기존 HTML의 손상을 막습니다."""
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=output.parent,
                                         prefix=f".{output.name}.", suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description="시트 CSV로 오늘의 한 문장을 생성합니다.")
    parser.add_argument("--date", type=parse_preview_date, help="날짜 미리보기: YYYY-MM-DD")
    parser.add_argument("--output", default="index.html", type=Path, help="출력 HTML 경로")
    parser.add_argument("--source", default=None,
                        help=f"확인용 CSV 주소나 파일 경로. 생략하면 {URL_ENV_NAME}을 씁니다.")
    args = parser.parse_args(argv)
    skipped = []
    try:
        # 현재 시각은 한 번만 얻고, 날짜와 생성 시각 표시 모두에 사용합니다.
        generated_at = datetime.now(KST)
        target_date = choose_date(args.date, generated_at)
        load_env_file()
        items, skipped = load_items(args.source)
        html = generate_html(items, target_date, generated_at, is_preview=args.date is not None)
        atomic_write(args.output, html)
    except (OSError, ValueError) as error:
        for message in skipped:
            print(f"건너뜀 · {message}", file=sys.stderr)
        print(f"생성 실패: {error}", file=sys.stderr)
        return 1
    for message in skipped:
        print(f"건너뜀 · {message}", file=sys.stderr)
    print(f"공개 문장 {len(items)}개 · 선택 날짜 {target_date} · {'날짜 미리보기' if args.date else '한국 날짜 기준'}")
    print(f"마지막 생성: {generated_at.strftime('%Y.%m.%d %H:%M:%S')} KST")
    print(f"HTML 생성 완료: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
