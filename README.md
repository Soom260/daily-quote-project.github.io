# 오늘의 한 문장

**구글 시트에 적은 문구를 CSV로 읽어, 한국 날짜에 맞는 항목을 고르고, 웹페이지를 만들어 GitHub Pages에 배포하는 예제**입니다. Hello Actions에서 확인한 ‘명령 실행’을 ‘웹 생성과 배포’로 확장합니다. Python 표준 라이브러리만 사용하며 설치할 패키지가 없습니다.

문구 목록은 코드가 아니라 **구글 시트**에 있습니다. 시트를 고치고 워크플로를 다시 실행하면 공개 웹이 바뀝니다.

```text
main에 저장 / 버튼으로 실행 / 예약 시각 도달
  → GitHub Actions가 Python 실행
  → SHEET_CSV_URL의 구글 시트 CSV 내려받기
  → 열 약속 검사 · 공개=Y 행만 남기기
  → 날짜에 맞는 문구 선택
  → _site/index.html 생성
  → GitHub Pages에 직접 배포
```

## 파일 역할

| 파일 | 역할 |
|---|---|
| **구글 시트** | 문구 목록. 학생이 바꿀 데이터. 코드 안에 없습니다 |
| `.env` | 내 시트 CSV 주소. **GitHub에 올리지 않습니다** |
| `.env.example` | `.env`를 어떻게 적는지 보여 주는 예시 |
| `main.py` | CSV 읽기·검사, 한국 날짜 선택, 문구 선택, HTML 생성 |
| `index.html` | 복사 직후 열어 볼 수 있는 생성된 웹 저장본 |
| `.github/workflows/daily_quote.yml` | 실행 조건, Python 실행, Pages 배포 |
| `문구이용안내.md` | 제공 문구의 복제·수정·공개·배포 안내 |
| `quotes.json` | 시트로 옮기기 전에 쓰던 옛 목록. 이제 읽지 않습니다 |

생성 결과는 정적 HTML입니다. 웹페이지를 새로고침해도 Python은 실행되지 않습니다. **Actions가 다시 생성하고 배포해야** 공개 웹의 문구와 생성 시각이 갱신됩니다. Actions가 끝나면 실행용 컴퓨터도 작업을 마칩니다.

## 1. 예제 파일 복사

압축을 풀고 **`daily-quote-project` 폴더의 내용 전체**를 새 저장소의 최상위에 넣습니다. 최상위가 다음 구조인지 확인하세요.

```text
daily-quote-project/          ← 이 폴더를 작업 폴더로 열기
├── main.py
├── index.html
├── .env.example
├── README.md
├── 문구이용안내.md
├── .gitignore
└── .github/
    └── workflows/
        └── daily_quote.yml
```

`workflows/daily_quote.yml`만 있거나, 저장소 안에 다시 `daily-quote-project/.github/...`로 중첩되면 인식되지 않습니다. **저장소 루트의 `.github/workflows/daily_quote.yml`**이어야 합니다. macOS Finder에서는 `Command + Shift + .`으로 숨김 폴더를 표시할 수 있습니다. GitHub 웹에서 파일을 직접 만들 때는 파일 이름에 `.github/workflows/daily_quote.yml` 전체 경로를 입력하세요.

이번 예제는 별도 Public 저장소 `daily-quote-project`에 배포하는 것을 권장합니다. 기존 개인 홈페이지 저장소를 사용하면 그 사이트가 이 예제로 바뀔 수 있습니다. 기존 `hello.yml`을 함께 둘 수 있지만, 다른 Pages 배포 워크플로가 동시에 같은 사이트를 배포하지 않도록 확인하세요.

### 브라우저로 파일을 올릴 때

1. GitHub의 **New repository**에서 Public·README 초기화로 새 저장소를 만듭니다. 실제 기본 브랜치가 `main`인지 확인합니다.
2. 저장소 첫 화면의 **Add file → Upload files**에서 `main.py`, `index.html`, `.env.example`, `README.md`, `문구이용안내.md`를 올립니다. **`.env`는 올리지 않습니다.** 폴더째나 ZIP째 올리지 않고 **안의 파일**을 루트에 저장합니다. `.gitignore`는 함께 올리면 좋지만 실행 필수 파일은 아닙니다.
3. 숨김 `.github` 업로드가 빠지지 않도록 **Code 첫 화면 → Add file → Create new file**을 누르고 이름에 **`.github/workflows/daily_quote.yml`** 전체 경로를 입력합니다.
4. 제공 워크플로 파일을 텍스트 편집기로 열어 전체 내용을 복사합니다. GitHub 편집창에는 코드만 붙여 넣고 main에 **Commit changes**합니다.
5. 저장 후 경로가 **저장소 / .github / workflows / daily_quote.yml**인지 확인하고 아래 2단계의 시트 준비와 4단계의 Pages 설정·수동 실행으로 이어갑니다.

## 2. 시트 준비하고 주소 넣기

### 시트 만들기

구글 시트를 하나 만들고 **1행에 아래 다섯 열 이름을 정확히** 적습니다. 이름이 하나라도 다르면 `main.py`가 이유를 알리고 멈춥니다.

| 제목 | 내용 | 분류 | 링크 | 공개 |
|---|---|---|---|---|
| 커밋 메시지는 한 줄 요약부터 | 무엇을 왜 바꿨는지 첫 줄에 적으면 나중에 기록을 찾기 쉽습니다. | Git | https://git-scm.com/docs/git-commit | Y |
| 아직 쓰는 중인 초안 | 이 행은 공개 열이 N이라 웹에 나오지 않습니다. | 데이터 | | N |

- **공개** 열에 `Y`를 적은 행만 웹에 나옵니다. 쓰는 중인 행은 `N`으로 둡니다.
- **링크**는 비워도 됩니다. 비우면 그 항목에 링크가 표시되지 않습니다.
- **분류**는 화면 아래 필터 버튼이 됩니다. 시트에 적은 순서 그대로 버튼이 생깁니다.

### CSV 주소 얻기

시트에서 **파일 → 공유 → 웹에 게시 → 쉼표로 구분된 값(.csv) → 게시**를 누릅니다. 나온 주소 끝이 `output=csv`인지 확인하세요.

### 주소를 .env에 넣기

`.env.example`을 복사해 **`.env`**로 이름을 바꾸고 주소를 넣습니다. `.env`는 `.gitignore`에 들어 있어 GitHub에 올라가지 않습니다. **주소를 `main.py`나 HTML에 직접 적지 마세요.**

```bash
SHEET_CSV_URL=https://docs.google.com/spreadsheets/d/e/.../pub?gid=0&single=true&output=csv
```

## 3. 로컬에서 먼저 확인하기 — 선택

Python 3.9 이상이 있으면 프로젝트 폴더에서 실행합니다. GitHub 실습에서는 로컬 Python 설치 없이 Actions로 바로 실행해도 됩니다.

```bash
python3 main.py
```

성공하면 `공개 문장 11개 · 선택 날짜 …`처럼 몇 개를 읽었는지 알려 줍니다. `.env`를 만들지 않고 잠깐 확인만 할 때는 주소를 직접 넘길 수도 있습니다.

```bash
python3 main.py --source "https://docs.google.com/.../pub?output=csv"
```

### 문제가 있으면 화면을 만들지 않고 멈춥니다

반쯤 망가진 화면이 배포되지 않도록, 아래 경우에는 `index.html`을 건드리지 않고 이유를 출력한 뒤 멈춥니다(종료 코드 1).

| 상황 | 나오는 메시지 |
|---|---|
| 주소가 없음 | `SHEET_CSV_URL이(가) 비어 있습니다. .env 파일이나 GitHub Secrets에 시트 CSV 주소를 넣으세요.` (GitHub에서는 Variable도 됩니다) |
| 열 이름이 빠짐 | `CSV에 필요한 열이 없습니다: 분류, 링크. 시트 1행의 현재 열: 제목, 내용, 공개` |
| 공개=Y 행이 없음 | `공개=Y인 행이 없습니다. 검사한 데이터 행 2~14번 가운데 쓸 수 있는 행이 0개입니다.` |
| 데이터 행이 없음 | `CSV에 데이터 행이 없습니다. 시트 1행에 열 이름만 있습니다.` |

행 하나만 이상할 때는 멈추지 않고 **그 행만 건너뛰며 줄 번호를 알려 줍니다.**

```text
건너뜀 · 5번 행: 공개=Y인데 내용이 비어 있어 건너뜁니다.
건너뜀 · 7번 행: 제목이 비어 있어 '(제목 없음)'으로 표시합니다.
```

줄 번호는 **구글 시트에서 눈에 보이는 번호**입니다. 1행이 열 이름, 2행이 첫 데이터입니다. 메시지에 적힌 번호로 시트에서 바로 찾아 고치면 됩니다.

생성된 `index.html`을 다시 열거나 새로고침합니다. 페이지 하단의 ‘마지막 생성’은 실제 실행 시각이며 한국시간(KST)입니다. 로컬 실행 결과에는 ‘로컬 생성본’이 표시됩니다.

다른 날짜의 결과를 확인할 때는 별도 출력 파일을 사용하세요.

```bash
python3 main.py --date 2026-09-23 --output preview.html
```

`preview.html`에는 **‘날짜 미리보기’**가 표시됩니다. 미리보기 날짜가 실제 오늘과 같아도 이 표시는 유지됩니다. 화면의 ‘선택한 날짜의 전날’은 미리보기 날짜 바로 전날입니다. 이 기능은 시간 여행이나 실제 예약 실행 기록이 아닙니다.

## 4. GitHub Pages에 배포하기

1. Public 저장소 `daily-quote-project`를 만들고, 위 파일을 `main` 브랜치 최상위에 저장합니다.
2. **Settings → Pages → Build and deployment → Source → GitHub Actions**를 선택합니다. 제공된 워크플로를 사용하므로 추천 Jekyll·Static HTML 템플릿을 추가하지 않습니다.
3. **Settings → Secrets and variables → Actions**에서 시트 주소를 등록합니다. 이 단계를 빠뜨리면 `build`가 `SHEET_CSV_URL이(가) 비어 있습니다`로 실패합니다.
   - 이름은 어느 쪽이든 **`SHEET_CSV_URL`** 로 똑같이 적습니다.
   - 값은 `.env`에 넣은 것과 같은 CSV 주소를 **따옴표 없이** 붙여넣습니다.
   - **Variables 탭 → New repository variable** — 이 예제의 주소는 이미 ‘웹에 게시’된 공개 링크라 이쪽으로 충분합니다. 나중에 값을 눈으로 다시 확인할 수 있습니다.
   - **Secrets 탭 → New repository secret** — 값을 가려 두고 싶을 때. 한 번 저장하면 다시 볼 수 없습니다.
   - 워크플로는 `${{ secrets.SHEET_CSV_URL || vars.SHEET_CSV_URL }}`로 **둘 다 지원**합니다. 둘 다 있으면 Secret이 이깁니다.
   - **Environment secrets/variables에 넣으면 안 됩니다.** `build` 작업은 환경에 속해 있지 않아 값을 받지 못합니다. 반드시 **Repository** 쪽에 넣으세요.
4. **Actions → Daily Quote Generator → Run workflow**를 엽니다.
5. 브랜치는 `main`, **`preview_date`는 비워 둔 상태**로 Run workflow를 누릅니다.
6. 실행 항목을 열어 **`build`와 `deploy`가 모두 초록색**인지 확인합니다. `build`의 `Generate daily page` 로그에는 읽은 문구 개수·선택 날짜·생성 시각이 표시됩니다.
7. 실행 결과의 배포 링크 또는 Settings → Pages에 표시된 **실제 공개 URL**을 엽니다.

일반 프로젝트 저장소의 주소 형태는 `https://아이디.github.io/daily-quote-project/`입니다. `아이디.github.io`라는 이름의 개인 홈페이지 저장소만 루트 주소를 사용합니다. 추측한 주소 대신 **배포 결과의 실제 링크**를 사용하세요.

첫 Push 때 Pages 설정이 아직 안 되어 있으면 실행이 실패할 수 있습니다. Source 설정을 마친 뒤 수동으로 다시 실행하세요. 액션 실행이 조직 정책으로 제한된 계정은 해당 안내에 따라 허용 여부를 확인해야 합니다.

**저장소의 `index.html`이 매번 커밋되는 방식이 아닙니다.** Actions는 `_site/index.html`을 생성한 뒤 배포 파일 묶음(artifact)으로 전달합니다. 결과는 Code 탭의 저장본이 아니라 **공개 웹과 Actions 로그**에서 확인합니다. 별도 토큰이나 `contents: write` 권한이 필요하지 않습니다.

## 5. 화면에서 찾아보기

위쪽 **오늘의 한 문장**과 **어제의 한 문장** 카드 아래에 **전체 문장** 영역이 있습니다.

- **검색창** — 제목·내용·분류를 한꺼번에 찾습니다. 영문 대소문자는 구분하지 않습니다.
- **분류 버튼** — 시트의 `분류` 값에서 자동으로 만들어집니다. `전체`가 기본입니다.
- **결과 없음 안내** — 맞는 문장이 하나도 없으면 `‘○○’에 맞는 문장이 없습니다. 다른 말로 찾아보세요.`와 **검색 지우기** 버튼이 나옵니다.
- 오른쪽 위 **보이는 문장 N개 / 전체 M개**로 몇 개가 걸러졌는지 확인합니다.

검색과 필터는 이미 만들어진 페이지 안에서 바로 동작합니다. 서버나 Python이 다시 실행되지 않으므로 **시트를 고쳤다면 워크플로를 다시 실행**해야 목록이 바뀝니다.

## 6. 수업 중 갱신을 확인하는 방법

| 실험 | 예상 결과 | 확인할 증거 |
|---|---|---|
| 같은 날, 입력 없이 다시 실행 | 같은 문구 유지 | 마지막 생성 시각·Actions 실행번호 변화 |
| `preview_date`에 오늘 다음 날 입력 | 다음 날짜의 문구 표시 | 선택 날짜·‘날짜 미리보기’ 배지·문구 |
| 시트의 문구 수정 후 워크플로 재실행 | 수정된 문구로 생성·배포 | 수정한 문구·Actions 성공 |
| 시트에서 어떤 행의 공개를 `N`으로 바꾸고 재실행 | 그 문구가 목록에서 사라짐 | 전체 문장 개수 감소 |
| 시트 1행의 열 이름 하나를 바꾸고 재실행 | 배포 실패, 화면은 이전 그대로 | Actions 로그의 ‘필요한 열이 없습니다’ |
| `preview_date`를 비워 다시 실행 | 실제 한국 날짜 화면으로 복귀 | ‘한국 날짜 기준’ 표시 |

**수동 날짜 미리보기도 공개 사이트에 배포됩니다.** 실험을 마치면 입력을 비워 재실행해 오늘 날짜로 되돌리세요. 같은 실행을 `Re-run jobs`로 재시도하면 실행번호는 같고 시도 번호가 달라질 수 있습니다.

문구 선택은 `(날짜 순번 - 1) % 문구 개수`입니다. 같은 날짜·같은 순서의 목록에서는 같은 항목이 선택되고, 다음 날에는 다음 항목으로 이동합니다. 공개=Y인 문구가 11개면 11일마다 반복됩니다. 시트의 순서나 공개 행 개수가 바뀌면 같은 날짜에도 선택되는 항목이 달라질 수 있습니다.

## 7. 매일 예약 실행하기

기본 배포본은 예약 실행이 꺼져 있습니다. 수동 배포에 성공한 뒤 `.github/workflows/daily_quote.yml`의 예약 두 줄에서 **`#`과 그 바로 뒤 공백 한 칸을 제거**하고 `main`에 저장하세요. `schedule`은 `push`, `workflow_dispatch`와 같은 들여쓰기 수준입니다. 아래 모양과 같으면 됩니다.

```yaml
  schedule:
    - cron: '17 23 * * *'  # UTC 23:17 = 다음 날 한국시간 08:17, 매일
```

예약은 기본 브랜치의 워크플로를 사용합니다. 이 실습에서는 기본 브랜치를 `main`으로 둡니다. 예약 시각은 UTC 기준이며, 생성할 문구의 날짜는 코드에서 한국시간으로 계산합니다.

예약 시각은 정확한 실행 시작을 보장하지 않으며 지연될 수 있습니다. 공개 저장소에서 장기간 활동이 없으면 예약이 비활성화될 수 있습니다. **수업에서는 예약 설정을 확인하고, 다음 날에는 Event가 `schedule`인 실행 기록과 공개 웹의 생성 시각을 확인**하세요. 수동 실행 성공은 예약 실행 성공의 증거가 아닙니다. [GitHub 예약 실행 안내](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)

## 8. 문구 바꾸기와 팀 활동

문구는 코드가 아니라 **구글 시트**에서 고칩니다. 시트에 줄을 추가하거나 고친 뒤 **Actions → Run workflow**를 누르면 공개 웹에 반영됩니다. 커밋이 필요 없습니다.

| 열 | 화면에서 보이는 곳 |
|---|---|
| 제목 | 오늘의 카드 맨 위, 목록 항목의 굵은 줄 |
| 내용 | 오늘의 큰 문장, 목록 항목의 본문 |
| 분류 | 카드 아래 태그, **분류 필터 버튼** |
| 링크 | ‘자세히 보기’ · ‘링크 열기’ (비우면 안 나옴) |
| 공개 | `Y`인 행만 웹에 나옴 |

시트를 고칠 때 지킬 것 세 가지입니다.

- **1행의 열 이름은 바꾸지 않습니다.** 바꾸면 배포가 실패합니다.
- **내용은 비우지 않습니다.** 공개=Y인데 내용이 비면 그 행은 건너뜁니다.
- 링크는 `http` 또는 `https`로 시작해야 합니다. 그 밖의 주소는 안전을 위해 무시됩니다.

제공 문구의 이용 범위는 [문구 이용 안내](문구이용안내.md)를 읽으세요. 추가한 콘텐츠는 직접 작성하거나 공개 사용 조건을 확인합니다.

3인 팀의 공통 미션은 **‘팀이 정한 사용자에게 필요한 정보를 자동으로 갱신해 보여 주는 웹서비스 만들기’**입니다. 데이터와 주제는 자유롭게 정합니다. 오늘의 질문·학습 팁·미니 퀴즈·팀 미션은 선택 가능한 아이디어이며 필수 주제가 아닙니다. 역할을 나누되 전원이 실행 조건, 데이터 처리, 배포 결과를 설명할 수 있어야 합니다.

## 9. Codex 또는 Claude Code에 요청할 때

Codex 앱에서는 이 폴더를 로컬 프로젝트에 연결합니다. CLI를 쓰면 터미널에서 이 폴더로 이동한 뒤 `codex` 또는 `claude`를 실행합니다. 두 도구를 함께 쓸 필요는 없습니다. 도구 이용 가능 여부와 사용 한도는 각 계정·요금제에 따릅니다.

Git·GitHub CLI(`gh`) 설치·로그인 상태를 확인하고 계정 인증은 본인이 진행합니다. 다음 요청은 공개 저장소 생성·배포와 수동 성공 후 예약 활성화를 포함합니다. 도구가 못 한 단계는 GitHub 화면에서 직접 이어갑니다.

```text
현재 폴더의 ‘오늘의 한 문장’ 예제를 GitHub Actions와 Pages로 배포해줘.

1. README, main.py, .env.example, .github/workflows/daily_quote.yml을 읽고
   현재 폴더·Git 상태·브랜치·원격 저장소를 먼저 확인해줘.
   예제 폴더를 한 겹 더 넣지 말고 코드가 저장소 최상위에 오게 해줘.
2. Git과 GitHub CLI 설치·로그인 상태를 확인해줘.
   설치나 인증이 필요하면 내가 직접 진행할 수 있게 안내해줘.
3. 내 계정에 daily-quote-project라는 Public 저장소를 만들고 main에 올려줘.
   같은 이름의 저장소가 있거나 기존 홈페이지를 바꾸게 되면 덮어쓰지 말고 알려줘.
   실습안내·활동기록·인증 파일은 올리지 말고 예제 코드만 커밋·Push해줘.
   .env 는 절대 커밋하지 마. .gitignore 에 들어 있는지 먼저 확인해줘.
4. 내 .env 의 SHEET_CSV_URL 값을 저장소 Variable 또는 Secret(이름은 SHEET_CSV_URL)으로
   등록하는 방법을 알려줘. Environment 가 아니라 Repository 쪽이어야 해.
   값은 화면에 그대로 출력하지 말고, 내가 직접 붙여넣게 안내해줘.
5. Pages Source를 GitHub Actions로 설정해줘. 기존 배포 워크플로를 사용하고
   별도의 Jekyll·Static HTML 배포 템플릿을 추가하지 마.
6. Daily Quote Generator를 main에서 preview_date를 비워 실행해줘.
   build와 deploy의 실제 로그를 확인하고, 실패하면 원인을 수정해줘.
7. 공개 웹의 한국 날짜·문구·실제 생성 시각을 확인해줘.
   검색창과 분류 버튼, 결과 없음 안내도 눌러서 확인해줘.
   같은 날짜·같은 문구 목록이면 같은 문장이 나오는 것은 정상이야.
8. 수동 배포가 성공하면 daily_quote.yml의 예약 주석 두 줄을 활성화하고
   main에 커밋·Push해줘. cron은 17 23 * * *로 유지해줘.
   이 수정 커밋의 build·deploy 성공도 확인해줘.
   한국시간 매일 08:17 예약 설정과 실제 예약 실행 관찰을 구분해줘.
9. 공개 URL·Actions 실행 URL·배포 커밋과 확인한 결과를 알려줘.
   도구나 권한 때문에 못 한 단계는 미완료로 적고, 내가 따라 할 수동 순서를 알려줘.

외부 API·API 키는 추가하지 마. 시트 주소는 .env 와 Secret 에만 두고
코드나 HTML 에 직접 적지 마. 날짜 미리보기로 테스트했다면
preview_date를 비워 다시 실행해 실제 오늘 날짜로 복원해줘.
```

[공식 OpenAI Codex CLI 안내](https://learn.chatgpt.com/docs/codex/cli), [Claude Code 시작 안내](https://code.claude.com/docs/en/quickstart)

## 자주 막히는 지점

| 증상 | 확인할 것 |
|---|---|
| Daily Quote Generator가 안 보임 | `main`에 `.github/workflows/daily_quote.yml`로 저장했는지 |
| Configure Pages에서 실패 | Settings → Pages → Source가 GitHub Actions인지 |
| `SHEET_CSV_URL이(가) 비어 있습니다` | **Repository** variables 또는 secrets에 `SHEET_CSV_URL`이 있는지. Environment 쪽에 넣으면 `build`가 못 받습니다 |
| `CSV 파일을 찾지 못했습니다: "https://…` | 값에 따옴표가 같이 들어갔습니다. 따옴표 빼고 다시 저장 |
| `필요한 열이 없습니다` | 시트 1행이 `제목, 내용, 분류, 링크, 공개`인지. 로그에 현재 열이 함께 나옵니다 |
| `공개=Y인 행이 없습니다` | 공개 열에 `Y`를 적은 행이 하나라도 있는지 |
| `CSV를 내려받지 못했습니다(HTTP …)` | 시트가 ‘웹에 게시’ 상태인지, 주소 끝이 `output=csv`인지 |
| Generate daily page에서 실패 | 위 메시지와 날짜 형식. 로그의 오류 문장을 그대로 읽기 |
| 검색·필터가 안 눌림 | 브라우저에서 자바스크립트가 꺼져 있는지 (목록 자체는 그대로 보입니다) |
| 문구가 그대로임 | 같은 날짜·같은 목록이면 정상. 생성 시각과 실행번호도 비교 |
| 공개 웹이 예전 화면임 | 최신 `deploy` 성공 여부와 실제 배포 URL, 브라우저 새로고침 확인 |
| 미래 날짜가 표시됨 | `preview_date`를 비워 다시 실행 |
| 예약 기록이 아직 없음 | 기본 브랜치에 예약 저장, UTC 환산, 실제 예약 시각 경과 여부 확인 |

열이 빠졌거나, 공개=Y 행이 없거나, 주소가 비었거나, 날짜 형식이 틀리면 새 HTML 생성을 중단합니다. 실패한 빌드는 배포하지 않으므로 이전에 배포된 웹은 그대로 남습니다.

## 공식 참고 자료

- [GitHub Pages 배포 소스 설정](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site)
- [사용자 지정 Actions로 Pages 배포](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)
- [워크플로 수동 실행](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow)
- [공식 Pages artifact Action](https://github.com/actions/upload-pages-artifact)

워크플로의 Action 버전과 공식 안내 확인: 2026-09-22. 이 파일은 실습용 안내이며, 학생 계정의 실제 배포 성공은 각자의 실행 로그와 공개 URL에서 확인합니다.
