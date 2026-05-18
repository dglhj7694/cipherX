# $SIGN (Signal)

## 현재 AI / PROMPT TAPE 동작

- 개별 종목 분석을 실행하면 `AnalysisWorkflow.run(..., prompt_builder=build_prompt_text)` 경로에서 최신 OHLCV, 검증된 보조지표, 수급/구조 지표, 시장/상대강도 맥락만 묶은 `PROMPT TAPE`가 생성됩니다.
- `PROMPT TAPE`에는 프로그램 엔진의 판단, 점수, 전략 후보, 시그널 라벨, 엔진 리스크 태그를 포함하지 않습니다. AI는 보조지표 데이터만으로 독립적인 2차 판단을 내립니다.
- `최근 60봉 보조지표 테이프`는 Vol, WaveTrend, MACD, MoneyFlow, StochSlow, SqueezeMom, Reversal/Momentum/Flow Pack, ADX/DMI, BB/VWAP, RSI/StochRSI, CMF/OBV/AD, Ichimoku/Mass, Volatility/Liquidity, RS/Acceleration, Position/Structure, HMA/UTBot, VP/POC/RR, FibStructure, MA/EMA, Trendline/Pattern 그룹을 포함합니다. `Objective_*` 내부 엔진 판단/점수 계열은 출력하지 않습니다.
- 분석 메시지의 `PROMPT TAPE` expander에는 수동 복사용 프롬프트와 `AI분석` 버튼이 함께 표시됩니다.
- `AI분석` 버튼은 `build_ai_prompt()`로 PROMPT TAPE를 Gemini JSON-only 프롬프트에 감싼 뒤 `services.ai_signal_service.generate_ai_signal_assisted()`를 호출합니다.
- AI 결과는 기존 분석 카드 안에 직접 덮어쓰지 않고 별도 `리포트` 메시지로 채팅 피드에 추가됩니다. 리포트는 판단/신뢰도/Bull·Bear 점수, 핵심 근거, 리스크, 상세 근거, 반대 근거, 데이터 한계, 진입·무효화·목표, 전략 플레이북을 카드형 UI로 분리해 표시하며 Markdown 원문과 다운로드도 함께 제공합니다.
- 동시에 원본 분석 메시지의 `meta.ai_signal_assisted`에도 저장되어 세션 내 재렌더와 후속 처리가 가능합니다.
- Gemini 키가 없으면 버튼 근처의 `AI Key Setup`에서 현재 Streamlit 세션에만 키를 저장할 수 있습니다. 키는 메시지, 리포트, PROMPT TAPE, 로그에 출력하지 않습니다.

`$SIGN (Signal)`은 Streamlit 기반의 주식 분석, 스캐너, 시장 브리핑, Telegram 알림 자동화 애플리케이션입니다. 개별 종목의 기술적 지표와 전략 신호를 분석하고, 섹터/ETF 기반 유니버스 스캔과 GitHub Actions 배치 실행을 통해 Telegram digest와 CSV/JSON 산출물을 생성합니다.

## 주요 기능

- **개별 종목 분석**
  - 미국 주식 티커와 한국 6자리 종목코드 입력을 지원합니다.
  - `AnalysisWorkflow`, `AnalysisRequest`, `AnalysisService` 경계를 통해 가격 데이터, 지표, 시그널, 차트 메타데이터를 생성합니다.
  - Plotly 차트, 판단 라벨, 신뢰도, ensemble score, 전략 요약, audit payload를 Streamlit UI에 표시합니다.
  - `Startup9 강세확인` 탭에서 공개 자료 기반 추정형 강세확인 모델의 S9 Confirm n/9, 등급, 충족/부족 축, 리스크 플래그, 요약 근거를 별도 보조 지표로 표시합니다.

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
  - 미국 시장 daily mover, breadth, leadership, 주요 섹션 후보를 Streamlit Dashboard 화면에 표시합니다.
  - Dashboard는 기존 Market Briefing에 Heatmap, Quant Prediction, Action Candidates를 결합해 scanner/Telegram/market mover 흐름을 한 화면에서 비교합니다.
  - Heatmap은 Change, 5D, Vol20, ATR, RS, ADX, Signal 기준으로 섹터/종목별 자금 흐름을 Plotly treemap으로 표시합니다.
  - Quant Prediction은 가격, 거래량, 변동성, 추세, 상대강도, 위험 플래그만 사용해 다음 거래일 `UP / NEUTRAL / DOWN` 확률을 추정하며 LLM/뉴스 판단은 섞지 않습니다.
  - GitHub-hosted latest digest를 불러와 홈 화면의 Telegram digest 후보로 연결합니다.

- **Telegram 알림 자동화**
  - scheduled script가 scan/briefing 결과를 Telegram message와 CSV document로 발송합니다.
  - `telegram_pipeline/`은 digest contract, section selector, formatter, publisher, sender를 담당합니다.
  - Daily Scan Notify는 기본 유니버스와 Russell2000 확장 유니버스를 각각 shard/merge한 뒤, 마지막 combine 단계에서 중복 티커를 제거한 통합 CSV 1개만 Telegram으로 보냅니다.
  - 통합 CSV는 분석 성공 티커뿐 아니라 데이터 없음/계산 실패 티커도 `scan_status=skipped`, `scan_skip_reason`, `scan_skip_detail` 행으로 남겨 최종 중복 제거 후 전체 유니버스 티커를 추적할 수 있게 합니다.
  - iShares 계열 IWB/EUSA/IWM 유니버스는 현재 iShares/BlackRock product-data API의 전체 holdings 배열을 우선 사용하고, 실패 시에만 Yahoo Finance 상위 보유 fallback으로 내려갑니다.
  - 장마감 digest는 `[0] 오늘 의사결정 핵심`, `[1] Startup식 9개 강세확인 Top 20`, `[2] 기술적 매수시그널 클러스터`, `[3] 다음 거래일 공격형 매수 후보 8-PART`, `[4] 매매 유형별 후보 보드`, `[5] 참고 랭킹` 흐름으로 구성합니다.
  - 최종 통합 digest는 `dglhj7694/cipherX` 저장소의 `telegram-digest` 브랜치 `post_close/latest.json`에 publish되며 홈 `Telegram Digest Dashboard`의 오늘 종목판이 이 파일을 기본 source of truth로 읽습니다.
  - Startup식 추정 강세확인은 9개 독립 축 중 6개 이상, 최근 매도전환 없음, 유동성 통과를 기본 Top20 조건으로 사용하며 hard exclusion과 soft risk를 분리해 표시합니다.
  - 기술적 매수시그널 클러스터는 0번대 최종 매수 판단 섹션과 Startup9 섹션 뒤에 있는 후보 발굴 섹션이며, 최근 5봉의 UTBot/Hull/TK/DMI/ADX/MACD/Stoch/수급/스퀴즈/눌림/신고가/캔들 반전 신호를 점수화합니다.
  - 공격형 8-PART는 프로그램 자체 점수 대신 ATR, 거래량, RS, ADX, HMA/EMA, BB, 고점 거리, 포켓피봇/갭 지표를 사용하며, 같은 종목이 여러 PART에 걸리면 모두 보여줍니다.
  - 홈 `Telegram Digest Dashboard`는 텔레그램 메시지 구조와 섹션 순서를 유지하면서 상단 요약, 통합 후보 압축표, 섹션별 상세표로 후보를 비교합니다.
  - 통합 종목판은 공격형 8-PART 후보를 기본 압축표로 보여주며 `Today`, `5D`, ATR, Vol20, RS, ADX, MA20, 고점 거리, 근거/주의를 한 화면에서 비교합니다.

- **배치 산출물**
  - 스캔 결과와 메타데이터를 `artifacts/` 하위에 CSV, JSON, TXT 형태로 저장합니다.
  - 장마감 CSV/JSON에는 `scan_status`, `scan_skip_reason`, `scan_skip_detail`, `technical_buy_score`, `technical_buy_signal_count`, `technical_buy_hits`, `technical_buy_bucket`, `technical_buy_reason`, `technical_buy_risk_flags`와 Startup9 CSV 컬럼 `startup9_confirm_count`, `startup9_confirm_grade`, `startup9_confirm_hits`, `startup9_confirm_missing`, `startup9_confirm_reason`, `startup9_risk_flags`, `startup9_score`가 포함됩니다.
  - 통합 장마감 CSV/JSON에는 `source_universe_profiles`, `source_universe_hit_count`를 추가해 default/Russell2000 중 어느 유니버스에서 나온 종목인지 추적합니다.
  - JSON row artifact에는 CSV 표시 필드 외에도 `startup9_confirm_map`, `startup9_confirm_keys`, `startup9_missing_keys`, `startup9_profile`, `startup9_direction_state`, `startup9_hard_exclusions`, `startup9_soft_risk_flags`를 남겨 Dashboard와 사후 분석에서 같은 공개 자료 기반 추정형 강세확인 결과를 재사용할 수 있습니다.
  - GitHub Actions artifact 업로드와 digest branch publish 흐름을 지원합니다.

## 기술 스택

### Frontend

- **Streamlit**: 메인 웹 애플리케이션 프레임워크
- **Plotly**: 차트 렌더링
- **Custom CSS/theme**: `theme.py`, `branding.py`, `ui_localized.py`
- **Page modules**: `app_ui/pages/`의 홈, Dashboard/Heatmap, 분석, 시장 daily 화면

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
├─ ai_report.py                   # AI분석 리포트 Markdown/payload helper
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
  - 앱 mode, sidebar, session state, 홈/Dashboard/분석/스캐너 화면 routing을 담당합니다.
  - 개별 종목 분석은 `AnalysisWorkflow.run(AnalysisRequest(...), prompt_builder=build_prompt_text)` 경로를 사용합니다.

- `app_ui/pages/`
  - `home_page.py`: latest Telegram digest dashboard, 통합 후보 압축표, quick analysis 진입점
  - `market_dashboard_page.py`: Market Briefing, Heatmap, Action Candidates 통합 화면
  - `briefing_page.py`: 이전 시장 브리핑 wrapper
  - `market_daily_page.py`: daily market dashboard payload
  - `analysis_page.py`: 분석 메시지 rendering wrapper

- `services/market_heatmap_service.py`
  - scanner rows, Telegram digest, market payload를 Heatmap row contract로 정규화합니다.
  - 한글 CSV 헤더의 괄호 key를 표준 key로 복원하고 `SECTOR_GROUPS` 기반 섹터 역매핑을 수행합니다.

- `services/quant_prediction_service.py`
  - scanner rows, Telegram digest, market mover를 Quant Prediction row contract로 정규화합니다.
  - rule-based v1 모델로 다음 거래일 방향 확률과 근거/위험 플래그를 산출하며, Gemini/뉴스 판단과 분리합니다.

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

- `telegram_pipeline/final_buy_ranker.py`
  - QBS 기반의 오늘 매수/추격주의/눌림 대기 후보를 점수화합니다.

- `telegram_pipeline/technical_buy_signal_ranker.py`
  - 개별 종목에서 탐지된 최근 매수 시그널을 `technical_buy_score`, 신호 수, 유형, 리스크 태그로 정리하고 `technical_buy_cluster` 섹션 후보를 선별합니다.

- `telegram_pipeline/startup9_confirm_ranker.py`
  - Startup식 추정 강세확인을 9개 독립 축(`trend_bullish`, `above_gold_zone`, `blue_diamond_entry`, `no_pink_diamond`, `market_structure_bullish`, `support_hold`, `smart_money_flow`, `bullish_reversal`, `hype_wave_momentum`)으로 계산합니다.
  - 방향 전환은 최근 hard buy/sell 신호의 날짜와 timestamp를 시간순으로 해석해 `BULL_ACTIVE`, `BULL_RECLAIMED`, `BEAR_ACTIVE`, `MIXED_SAME_DAY`, `NO_RECENT_TURN`으로 분리합니다.

- `telegram_pipeline/aggressive_next_day_ranker.py`
  - 다음 거래일 공격형 매수 후보를 초기 전환, 강추세 지속, 눌림목 재진입, 초고변동 위성, 포켓피봇/거래량 선행, 압축 후 발사 대기, 갭업 추격, 신고가 근처 돌파 대기 8개 PART로 선별합니다.
  - 각 PART는 Top20까지 독립 표시하며, 같은 종목이 여러 PART에 걸리면 중복 제거하지 않고 모두 보여줍니다.

- `telegram_pipeline/early_reversal_ranker.py`
  - `early_reversal` 섹션의 ERS 점수를 계산해 하락추세/박스권에서 첫 전환이 나타나는 watchlist 후보를 선별합니다.

- `telegram_pipeline/hull_buy_turn_ranker.py`
  - `hull_buy_turn` 섹션의 당일 HULL 매수전환 후보를 선별하고 태그/리스크를 부여합니다.

- `telegram_pipeline/formatters.py`
  - Telegram message text를 구성하며 QBS와 `steady_winner`/`early_reversal`/`hull_buy_turn`을 0번대 의사결정 핵심으로 묶고, `startup9_confirm`, `technical_buy_cluster`, 다음 거래일 공격형 8-PART, 상세 보드, `five_day_top` 순서를 고정합니다.

- `telegram_pipeline/sender.py`
  - Telegram `sendMessage`, `sendDocument` 호출과 message chunking을 담당합니다.

- `telegram_pipeline/publisher.py`
  - digest artifact를 로컬에 쓰거나 GitHub branch로 publish합니다.

### 자동화 스크립트

- `scripts/daily_scan_and_notify.py`
  - 장마감/프리마켓/장초반 scan, shard merge, 통합 장마감 combine, Telegram notify, CSV/JSON artifact 생성을 담당합니다.
  - 장마감 combine 모드는 default/Russell2000 final artifact를 합쳐 중복 티커를 제거하고 통합 digest를 `telegram-digest/post_close/latest.json`에 publish합니다.
  - Daily scan CSV는 skipped 티커를 버리지 않고 상태/사유 컬럼으로 보존하며, digest의 `result_count`는 분석 성공 티커 수, `csv_row_count`는 CSV 전체 행 수로 기록합니다.
  - ETF 유니버스 생성은 iShares product-data API, Wikipedia index table, 운용사 holdings, Yahoo fallback 순서로 구성종목을 수집합니다.

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

AI분석 버튼은 Gemini 키를 `runtime_gemini_api_key` 세션 입력값 → Streamlit secrets → 환경변수 순서로 사용합니다. 세션 입력 키는 현재 Streamlit 세션에만 보관되며 PROMPT TAPE나 리포트에는 기록하지 않습니다.

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
  - 장마감 briefing, default post-close scan, Russell2000 extended scan, 각 merge, 최종 combine-and-notify를 실행합니다.
  - default와 Russell2000 스캔은 각각 12개 shard로 나누어 실행합니다.
  - 중간 merge job은 artifact만 만들고, 마지막 combine job이 통합 CSV Telegram 발송과 `telegram-digest/post_close/latest.json` publish를 담당합니다.
  - cron은 UTC 기준이며 US/Eastern 16:05에 맞춰 DST 기간 `5 20 * 3-11 1-5`, 표준시 기간 `5 21 * 1-3,11-12 1-5` 두 schedule을 schedule guard로 필터링합니다.

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
python -m unittest tests.test_startup9_confirm_ranker
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
