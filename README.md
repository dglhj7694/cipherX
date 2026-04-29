# $SIGN (Signal)

`$SIGN (Signal)`은 Streamlit 기반의 주식 분석, 스캐너, 시장 브리핑, Telegram 알림 자동화 애플리케이션입니다. 개별 종목의 기술적 지표와 전략 신호를 분석하고, 섹터/ETF 기반 유니버스 스캔과 GitHub Actions 배치 실행을 통해 Telegram digest와 CSV/JSON 산출물을 생성합니다.

## 주요 기능

- **개별 종목 분석**
  - 미국 주식 티커와 한국 6자리 종목코드 입력을 지원합니다.
  - `AnalysisWorkflow`, `AnalysisRequest`, `AnalysisService` 경계를 통해 가격 데이터, 지표, 시그널, 차트 메타데이터를 생성합니다.
  - Plotly 차트, 판단 라벨, 신뢰도, ensemble score, 전략 요약, audit payload를 Streamlit UI에 표시합니다.

- **차트/지표/시그널 엔진**
  - `yfinance` 가격 데이터를 기반으로 이동평균, WaveTrend, RSI, MFI, MACD, Bollinger, volume, market proxy 관련 지표를 계산합니다.
  - trend, momentum, money, structure, leading/lagging, reversal 계층 점수와 최종 판단을 조합합니다.
  - 전략 엔진은 breakout, trend, reversal, flow, level 기반 setup을 평가합니다.

- **AI Signal-Assisted 판단**
  - `ai_agent.py`의 prompt builder와 `services.ai_signal_service`를 통해 Gemini 기반 2차 판단을 생성할 수 있습니다.
  - 엔진 판단과 AI 판단의 alignment, confidence, driver, risk flag를 함께 보여줍니다.

- **스캐너**
  - 섹터 그룹과 ETF 구성 종목 기반 유니버스를 스캔합니다.
  - pullback, breakout, HMA/EMA, UTBot, Hull turn, pocket pivot, 5-day strength 등 여러 조건의 후보를 추출합니다.
  - shard 실행과 merge 흐름을 지원해 대량 유니버스를 나누어 처리할 수 있습니다.

- **시장 브리핑**
  - 미국 시장 daily mover, breadth, leadership, 주요 섹션 후보를 Streamlit 브리핑 화면에 표시합니다.
  - GitHub-hosted latest digest를 불러와 홈 화면의 Telegram digest 후보로 연결합니다.

- **Telegram 알림 자동화**
  - scheduled script가 scan/briefing 결과를 Telegram message와 CSV document로 발송합니다.
  - `telegram_pipeline/`은 digest contract, section selector, formatter, publisher, sender를 담당합니다.

- **배치 산출물**
  - 스캔 결과와 메타데이터를 `artifacts/` 하위에 CSV, JSON, TXT 형태로 저장합니다.
  - GitHub Actions artifact 업로드와 digest branch publish 흐름을 지원합니다.

## 기술 스택

### Frontend

- **Streamlit**: 메인 웹 애플리케이션 프레임워크
- **Plotly**: 차트 렌더링
- **Custom CSS/theme**: `theme.py`, `branding.py`, `ui_localized.py`
- **Page modules**: `app_ui/pages/`의 홈, 브리핑, 분석, 시장 daily 화면

### Backend / Core

- **Python**
- **pandas / numpy / scipy**: 데이터 처리와 지표 계산
- **yfinance**: 가격 데이터 수집
- **requests / cloudscraper / BeautifulSoup**: 외부 데이터 요청과 parsing
- **unittest**: 테스트 프레임워크

### AI / External APIs

- **google-generativeai**: Gemini AI Signal-Assisted 판단
- **Google API client/auth libraries**: Google API 연동 기반 패키지
- **Telegram Bot API**: scan/briefing message와 CSV document 발송
- **GitHub Actions**: scheduled scan, shard, merge, artifact upload 자동화

## 프로그램 구조

```text
cipherX/
├─ app.py                         # Streamlit 메인 entrypoint
├─ config.py                      # 판단 기준, bias mode, signal/scan registry 설정
├─ utils.py                       # 데이터 fetch, ticker validation, cache helper
├─ indicators.py                  # 기술 지표 계산
├─ engine.py                      # 핵심 신호 감지 엔진
├─ engine_layers.py               # 계층별 점수/시그널 계산
├─ engine_committee.py            # committee 기반 판단 보조
├─ engine_objective.py            # 객관 점수/판단 보조
├─ chart.py                       # Plotly 차트와 metadata 생성
├─ ai_agent.py                    # AI prompt와 AI 응답 parser
├─ scanner_filters.py             # scanner preset/filter 로직
├─ scanner_csv.py                 # scanner CSV export contract
├─ sectors.py                     # 섹터별 티커 그룹
├─ app_ui/                        # Streamlit 화면 모듈
├─ bootstrap/                     # session/default dependency 초기화
├─ domain/                        # request/response/view model dataclass
├─ services/                      # analysis, AI signal service boundary
├─ workflows/                     # AnalysisWorkflow, ScannerWorkflow
├─ engine_runtime/                # final decision, objective/committee pipeline
├─ strategy/                      # 전략 모델, registry, evaluator, summary
├─ infrastructure/etf/            # ETF holdings provider abstraction
├─ telegram_pipeline/             # Telegram digest 생성/발송/publish pipeline
├─ scripts/                       # CLI 배치 scan/briefing/notify scripts
├─ .github/workflows/             # GitHub Actions scheduled workflows
├─ tests/                         # unittest 기반 테스트
├─ legacy/                        # 이전 앱 버전 보관
└─ tools/                         # refactor/maintenance utility
```

## 주요 모듈 역할

### Streamlit 앱

- `app.py`
  - 앱 mode, sidebar, session state, 홈/브리핑/분석/스캐너 화면 routing을 담당합니다.
  - 개별 종목 분석은 `AnalysisWorkflow.run(AnalysisRequest(...), prompt_builder=build_prompt_text)` 경로를 사용합니다.

- `app_ui/pages/`
  - `home_page.py`: latest Telegram digest 후보와 quick analysis 진입점
  - `briefing_page.py`: 시장 브리핑 화면
  - `market_daily_page.py`: daily market dashboard payload
  - `analysis_page.py`: 분석 메시지 rendering wrapper

### 분석 엔진

- `indicators.py`, `engine.py`, `engine_layers.py`
  - 가격 데이터에서 기술 지표와 core signal을 계산합니다.

- `engine_runtime/`
  - objective score, committee score, final decision pipeline을 분리합니다.

- `strategy/`
  - breakout, trend, reversal, flow, level evaluator를 통해 setup 후보와 top strategy를 구성합니다.

- `chart.py`
  - chart figure, metadata, 분석 view payload를 생성합니다.

### Workflow / Service Boundary

- `domain/models/analysis_models.py`
  - `AnalysisRequest`, `AnalysisResponse`, `AnalysisViewModel`, scanner row model을 정의합니다.

- `services/analysis_service.py`
  - 데이터 계산, metadata, prompt, chart JSON, audit payload 생성을 담당합니다.

- `workflows/analysis_workflow.py`
  - Streamlit UI와 scanner가 공유하는 개별 분석 workflow입니다.

- `workflows/scanner_workflow.py`
  - 여러 티커를 병렬 분석해 scanner row로 변환하는 workflow입니다.

### Telegram / Digest

- `telegram_pipeline/contracts.py`
  - Telegram digest, section, candidate dataclass contract입니다.

- `telegram_pipeline/selectors.py`
  - post-close board/core section 후보를 선택합니다.

- `telegram_pipeline/formatters.py`
  - Telegram message text를 구성합니다.

- `telegram_pipeline/sender.py`
  - Telegram `sendMessage`, `sendDocument` 호출과 message chunking을 담당합니다.

- `telegram_pipeline/publisher.py`
  - digest artifact를 로컬에 쓰거나 GitHub branch로 publish합니다.

### 자동화 스크립트

- `scripts/daily_scan_and_notify.py`
  - 장마감/프리마켓/장초반 scan, shard merge, Telegram notify, CSV/JSON artifact 생성을 담당합니다.

- `scripts/realtime_premarket_scan.py`
  - 프리마켓/실시간 성격의 scan과 Telegram 알림을 담당합니다.

- `scripts/market_daily_briefing_notify.py`
  - 시장 daily briefing text artifact와 Telegram briefing 발송을 담당합니다.

## 실행 방법

### 1. 의존성 설치

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Streamlit 앱 실행

```powershell
streamlit run app.py
```

### 3. 주요 배치 실행 예시

장마감 scan:

```powershell
python -m scripts.daily_scan_and_notify --scan-mode post_close --out-dir artifacts/daily_scan
```

프리마켓 scan:

```powershell
python -m scripts.daily_scan_and_notify --scan-mode pre_market --out-dir artifacts/pre_market
```

시장 daily briefing:

```powershell
python -m scripts.market_daily_briefing_notify --out-dir artifacts/daily_scan/market_briefing
```

Telegram 전송 없이 artifact만 만들기:

```powershell
python -m scripts.daily_scan_and_notify --dry-run --skip-telegram
```

## 환경변수 / Secrets

Streamlit Cloud, GitHub Actions, 로컬 실행 환경에서 아래 값을 설정합니다.

```text
GEMINI_API_KEY 또는 GOOGLE_API_KEY
TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID
```

GitHub-hosted digest를 홈 화면에서 불러오는 경우:

```text
GITHUB_DIGEST_REPO
GITHUB_DIGEST_BRANCH
GITHUB_DIGEST_PATH
GITHUB_DIGEST_TOKEN
```

Telegram 관련 값이 없으면 scheduled script의 Telegram 발송은 실패하거나 skip 옵션을 사용해야 합니다. Gemini key가 없으면 AI Signal-Assisted 판단은 사용할 수 없습니다.

## GitHub Actions 자동화

`.github/workflows/`에는 scheduled scan workflow가 정의되어 있습니다.

- `daily_scan_notify.yml`
  - 장마감 briefing, post-close scan, extended scan, merge, Telegram notify를 실행합니다.
  - cron은 UTC 기준입니다.
  - 현재 설정은 EDT 기간의 US/Eastern 16:05에 맞춘 `5 20 * * 1-5`입니다.

- `pre_market_scan.yml`
  - 프리마켓 scan shard/merge 흐름을 실행합니다.

- `pre_market_1800_scan.yml`
  - 더 이른 프리마켓 scan 흐름을 실행합니다.

- `early_session_scan.yml`
  - 장초반 scan 흐름을 실행합니다.

GitHub Actions scheduled workflow는 지연 실행될 수 있으므로 workflow 내부 schedule guard가 실제 US/Eastern 실행 창을 다시 확인합니다.

## 테스트

전체 테스트:

```powershell
python -m unittest discover tests
```

주요 테스트 예시:

```powershell
python -m unittest tests.test_strategy_mvp
python -m unittest tests.test_daily_scan_notify
python -m unittest tests.test_daily_scan_resilience
python -m unittest tests.test_telegram_pipeline
python -m unittest tests.test_market_daily_briefing_notify
```

수동 signal flip 점검:

```powershell
python tests/manual/test_signal_flip.py
```

## 운영 메모

- GitHub Actions cron은 UTC 기준입니다.
- 장마감 daily scan은 현재 EDT 기준 `20:05 UTC`에 맞춰져 있습니다.
- 미국 표준시간(EST) 기간에는 장마감 16:05 ET가 `21:05 UTC`이므로 cron 조정이 필요할 수 있습니다.
- Telegram 전송은 현재 scheduled script와 `telegram_pipeline.sender` 중심입니다.
- Streamlit 앱은 사용자 분석 UI와 digest 확인 UI를 제공하고, scheduled 배치는 GitHub Actions가 담당합니다.
- `artifacts/` 하위 산출물은 scan/briefing 실행 결과이며, 필요 시 GitHub Actions artifact로 업로드됩니다.
