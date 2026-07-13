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
  - 분석 결과의 첫 `초보자 가이드` 탭에서 지금 할 일, 판단과 같은 방향의 구현 전략, 진입 조건, 손절·무효화, 1·2차 목표, 손익비, 반대 근거를 5단계 체크리스트로 확인할 수 있습니다.
  - 초보자 가이드는 `context`/`proxy` 전략이나 최종 판단과 반대 방향인 전략을 기본 매매계획으로 선택하지 않습니다. `TRIGGER_WAIT`, `READY`, `INTEREST`, `*_WAIT`, `*_ALIGNED` 상태에서는 현재 종가로 만들어진 손절·목표·손익비를 숨기고 실제 진입 확인 후 재계산하도록 안내합니다.
  - 최종 판단이 `BUY` 이상이고 매수 방향의 활성 진입 전략에 유효한 진입가·손절가·1차 목표가와 최소 1R 손익비가 있으며, 고위험 신호 충돌이나 얇은 거래대금 위험이 없을 때만 `주문 전 가정 티켓`을 표시합니다. 티켓에서 진입가·손절가·1차 목표를 한 세트로 다시 검증하고 손익비와 손실 한도 기반 정수 수량을 함께 재계산합니다. `WATCH_BUY`와 확인 중인 전략은 조건부 가격 시나리오만 보여주며 수량은 계산하지 않고, 중립·혼조 판단에서는 실행 전략 가격을 표시하지 않습니다.
  - `보유 포지션 점검`을 켜면 현물 매수 보유분의 실제 평단·수량, 점검 현재가, 사용자 방어 기준, 선택 계좌금액으로 평가손익·포지션 비중·방어선까지의 반납 가능액·방어선 체결 가정 손익·목표 도달 가정 손익을 계산합니다. 사용자 방어 기준은 엔진 무효화 기준과 분리해 직접 입력하며 엔진 가격을 자동 채우지 않습니다. `SELL` 판단이나 실행 전략이 없는 경우에도 보유분 방어 재검토 근거를 보여주고, 자동 주문이나 자동 매도는 실행하지 않습니다.
  - 최신 분석의 유효한 `주문 전 가정 티켓`과 사용자 방어 기준을 입력한 보유 점검 결과는 `내 매매계획`에 현재 Streamlit 세션 동안만 저장할 수 있습니다. 신규 진입 계획은 계좌 평가금액을 저장하지 않고 수량도 사용자가 따로 동의한 경우에만 포함합니다. 수량을 포함하면 저장 시점의 계좌금액으로 한 번 더 재계산하지만 계좌금액 자체는 남기지 않으므로 이후 실제 주문 전 다시 계산해야 합니다. 보유 방어계획은 저장 전에 평단·수량이 포함된다는 경고를 표시합니다.
  - `내 매매계획`은 최대 20개 계획의 수동 상태, 저장 당시 판단·가격·위험 신호, 현재 분석과의 일치·변경 여부를 보여줍니다. 계획은 브로커 주문이나 체결 상태와 연결되지 않으며, 이전 분석 카드에서는 새 계획을 저장할 수 없습니다.
  - 계획은 엄격한 v1 스키마의 JSON으로 백업·복원할 수 있습니다. 가져오기는 UTF-8, 512KiB, 최대 20개, 중복 키·비정상 숫자·알 수 없는 필드·민감 필드를 원자적으로 검증하고, 통과한 계획도 현재 분석과 다시 대조할 때까지 `재검토 필요` 상태로 둡니다.
  - `내 매매계획`에서 `계좌 전체 위험예산 점검`을 켜면 실제 보유와 미체결 신규 진입을 별도 시나리오로 계산합니다. 신규 진입은 저장 수량을 무시하고 현재 계좌 평가금액으로 수량을 다시 계산하며, 실제 보유는 증권사 최신 평단·수량·가격·사용자 방어선을 재입력하고 별도 대조 확인을 해야만 반영합니다.
  - 통화 코드와 같은 통화 여부, 반영할 계획 범위, 복수 진입계획, 모두 체결된 동시 가정은 각각 명시적으로 확인해야 합니다. 통화·선택·보유값이 바뀌면 관련 확인도 자동으로 해제되며, 동일 종목의 복수 보유계획은 계좌·포지션 구분 정보가 없어 합산하지 않습니다.
  - 사용자가 직접 입력한 계좌 전체 위험·총 노출·한 종목 노출 한도와 비교하며 기본 권고 한도는 제공하지 않습니다. 실제 보유와 예정 진입의 한도는 따로 검사하고, 두 범위의 합산과 종목 집중도는 `모두 체결` 가정을 켠 경우에만 계산합니다. 방어선에 이미 도달한 보유분도 평가 노출에는 포함하지만 방어선 위험과 남은 위험예산은 미확정으로 표시합니다.
  - Plotly 차트, 판단 라벨, 신뢰도, ensemble score, 전략 요약을 표시하고, `성과/검증` 탭에서 walk-forward 요약과 audit payload를 확인할 수 있습니다. 초보자 가이드에는 과거 동일 판단 라벨이 20건 이상일 때만 적중률과 평균 방향수익을 요약합니다.
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
  - Quant Prediction은 가격, 거래량, 변동성, 추세, 상대강도, 위험 플래그만 사용해 다음 거래일 `UP / NEUTRAL / DOWN` 방향 점수와 신호 강도를 산출하며 LLM/뉴스 판단은 섞지 않습니다. 0~100 값은 규칙 점수를 정규화한 지표이며 통계적으로 보정된 확률이 아닙니다.
  - GitHub-hosted latest digest를 불러와 홈 화면의 Telegram digest 후보로 연결합니다.

- **Telegram 알림 자동화**
  - scheduled script가 scan/briefing 결과를 Telegram message와 CSV document로 발송합니다.
  - `telegram_pipeline/`은 digest contract, section selector, formatter, publisher, sender를 담당합니다.
  - Daily Scan Notify는 기본 유니버스와 Russell2000 확장 유니버스를 각각 shard/merge한 뒤, 마지막 combine 단계에서 중복 티커를 제거한 통합 CSV 1개만 Telegram으로 보냅니다.
  - 통합 CSV는 분석 성공 티커뿐 아니라 데이터 없음/계산 실패 티커도 `scan_status=skipped`, `scan_skip_reason`, `scan_skip_detail` 행으로 남겨 최종 중복 제거 후 전체 유니버스 티커를 추적할 수 있게 합니다.
  - iShares 계열 IWB/EUSA/IWM 유니버스는 현재 iShares/BlackRock product-data API의 전체 holdings 배열을 우선 사용하고, 실패 시에만 Yahoo Finance 상위 보유 fallback으로 내려갑니다.
  - 장마감 digest는 `[0] 오늘 의사결정 핵심`, `[0-T] 13탭 구조 분류`, `[1] Startup식 9개 강세확인 Top 20`, `[2] 기술적 매수시그널 클러스터`, `[3] 다음 거래일 공격형 매수 후보 8-PART`, `[4] 매매 유형별 후보 보드`, `[5] 참고 랭킹` 흐름으로 구성합니다.
  - 13탭 구조 분류는 `매수전환`, `상승대기`, `상승지속`, `지금매수`, `눌림목`, `돌파직전`, `돌파확인`, `기관매집`, `재돌파`, `갭앤고`, `초고변동 위성`, `관망`, `제외/위험`을 Top20 독립 섹션으로 보여주며 같은 종목이 여러 탭에 걸리면 중복 표시합니다.
  - 각 종목에는 `STRONG_BUY_NOW`, `BUY_ON_BREAKOUT`, `BUY_ON_PULLBACK`, `WATCH_EXPLOSION`, `TREND_FOLLOW`, `ACCUMULATION`, `RECLAIM_BUY`, `GAP_AND_GO`, `SPECULATIVE_SATELLITE`, `WAIT`, `AVOID` 중 대표 액션 라벨을 붙입니다.
  - 최종 통합 digest는 `dglhj7694/cipherX` 저장소의 `telegram-digest` 브랜치 `post_close/latest.json`에 publish되며 홈 `Telegram Digest Dashboard`의 오늘 종목판이 이 파일을 기본 source of truth로 읽습니다.
  - Startup식 추정 강세확인은 9개 독립 축 중 6개 이상, 최근 매도전환 없음, 유동성 통과를 기본 Top20 조건으로 사용하며 hard exclusion과 soft risk를 분리해 표시합니다.
  - 기술적 매수시그널 클러스터는 0번대 최종 매수 판단 섹션과 Startup9 섹션 뒤에 있는 후보 발굴 섹션이며, 최근 5봉의 UTBot/Hull/TK/DMI/ADX/MACD/Stoch/수급/스퀴즈/눌림/신고가/캔들 반전 신호를 점수화합니다.
  - 공격형 8-PART는 프로그램 자체 점수 대신 ATR, 거래량, RS, ADX, HMA/EMA, BB, 고점 거리, 포켓피봇/갭 지표를 사용하며, 같은 종목이 여러 PART에 걸리면 모두 보여줍니다.
  - 홈 `Telegram Digest Dashboard`는 텔레그램 메시지 구조와 섹션 순서를 유지하면서 상단 요약, 통합 후보 압축표, 13탭 필터, 섹션별 상세표로 후보를 비교합니다.
  - 통합 종목판은 공격형 8-PART 후보를 기본 압축표로 보여주며 `Today`, `5D`, ATR, Vol20, RS, ADX, MA20, 고점 거리, 근거/주의를 한 화면에서 비교합니다.

- **배치 산출물**
  - 스캔 결과와 메타데이터를 `artifacts/` 하위에 CSV, JSON, TXT 형태로 저장합니다.
  - 장마감 CSV/JSON에는 `scan_status`, `scan_skip_reason`, `scan_skip_detail`, `technical_buy_score`, `technical_buy_signal_count`, `technical_buy_hits`, `technical_buy_bucket`, `technical_buy_reason`, `technical_buy_risk_flags`와 Startup9 CSV 컬럼 `startup9_confirm_count`, `startup9_confirm_grade`, `startup9_confirm_hits`, `startup9_confirm_missing`, `startup9_confirm_reason`, `startup9_risk_flags`, `startup9_score`가 포함됩니다.
  - 장마감 CSV/JSON에는 13탭 구조 분류 결과인 `scan_action_label`, `scan_taxonomy_primary`, `scan_taxonomy_primary_title`, `scan_taxonomy_matches`, `scan_taxonomy_reason`, `scan_taxonomy_risk_flags`, `scan_tab_*` 컬럼도 포함됩니다.
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
│  ├─ components/                # 초보자 가이드·보유·세션 매매계획·계좌 위험예산 UI
│  └─ pages/                     # 홈, Dashboard, 분석, 시장 화면
├─ bootstrap/                     # session/default dependency 초기화
├─ domain/                        # request/response/view model dataclass
├─ services/                      # analysis, AI signal, 신규 진입·보유·매매계획·계좌 위험 검증
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

- `app_ui/components/beginner_trade_guide.py`
  - 초보자용 행동 안내, 가격 계획, 보유 포지션 점검, 5단계 체크리스트, 동일 판단 과거 표본, 주문 전 가정 티켓과 투자 안전 문구를 렌더링합니다.

- `app_ui/components/holding_scenario.py`
  - 사용자가 직접 입력한 현물 롱 보유정보로 평가손익과 방어·목표 시나리오를 세션 안에서만 계산해 표시합니다.

- `app_ui/components/trade_plan_workspace.py`
  - 최신 분석에서 저장한 신규 진입·보유 방어계획을 현재 세션에서 최대 20개까지 보여주고, 수동 상태 변경, 현재 분석 재대조, 2단계 삭제, JSON 백업·가져오기와 계좌 위험예산 점검 진입점을 제공합니다.

- `app_ui/components/portfolio_risk_workspace.py`
  - 저장 계획 통화, 현재 계좌금액, 사용자 한도, 실제 보유 최신값과 유효한 예정 진입 범위를 명시적으로 확인받습니다.
  - 확인 대상 값이나 선택 집합이 바뀌면 통화·완전성·동시 체결·보유 최신값 확인을 무효화하고, 계좌·보유 입력을 민감 세션 네임스페이스에서만 관리합니다. 계획 삭제·상태 변경·전체 초기화 시 관련 상태를 지웁니다.

- `services/beginner_trade_guide.py`
  - 최종 판단과 방향이 맞는 독립 구현 전략을 선택하고, 상태별 가격 노출과 수량 계산 가능 여부를 결정합니다.
  - 저장된 손익비를 그대로 신뢰하지 않고 `LONG: stop < entry < target`, `SHORT: target < entry < stop` 순서를 검증한 뒤 1차 목표 손익비를 다시 계산합니다.
  - 주문 전 가정 티켓의 진입·손절·1차 목표를 한 묶음으로 재검증하고, 계좌 평가금액·거래당 손실 한도·종목당 최대 사용 비중으로 정수 주 수량과 계획상 최대손실을 계산합니다.

- `services/holding_scenario.py`
  - 현물 롱 보유분의 평단·수량 기반 평가손익, 포지션 비중, 사용자 방어선 시나리오와 엔진 위험 신호를 계산합니다. 수수료·세금·배당·환율·슬리피지와 실제 체결가는 포함하지 않습니다.

- `services/trade_plan_service.py`
  - 계좌금액과 원본 분석 메타데이터를 제외한 신규 진입·보유 방어 스냅샷을 생성하고, 저장 가격과 시나리오를 다시 계산해 검증합니다.
  - 보유 계획의 엔진 무효화·목표는 사용자 JSON 입력을 신뢰하지 않고 저장된 분석 스냅샷에서만 다시 가져오며, `ANALYSIS_SNAPSHOT` 가격 출처도 당시 분석 가격과 같은지 확인합니다.
  - 계획 fingerprint 중복 제거, 불변 스냅샷 검증, 위험 경고 변경 감지, 최대 20개 세션 목록, 수동 상태 변경, 원자적 JSON 병합을 담당합니다. JSON은 암호화되지 않은 평문이며 최대 512KiB입니다.

- `services/portfolio_risk_service.py`
  - 저장 계획을 다시 검증한 뒤 실제 보유 위험, 현재 계좌로 재산정한 미체결 진입 위험, 사용자가 확인한 동시 체결 합산 시나리오를 계산합니다.
  - 알려진 저장 통화와 계좌 통화 불일치, 다른 통화 그룹 혼합, 중복 계획 ID, 동일 종목 복수 보유, 미확인 복수 진입, 비정상 숫자·불리언·보유 입력을 실패 처리합니다. 한도 판정은 표시용 반올림값이 아니라 원시 계산값을 사용합니다.
  - 방어선 도달 보유는 긴급 재검토로 분리하되 현재 평가 노출과 종목 노출에서 제거하지 않으며, 이미 지난 방어선 기준의 위험금액을 0으로 간주하지 않습니다.

- `services/market_heatmap_service.py`
  - scanner rows, Telegram digest, market payload를 Heatmap row contract로 정규화합니다.
  - 한글 CSV 헤더의 괄호 key를 표준 key로 복원하고 `SECTOR_GROUPS` 기반 섹터 역매핑을 수행합니다.

- `services/quant_prediction_service.py`
  - scanner rows, Telegram digest, market mover를 Quant Prediction row contract로 정규화합니다.
  - rule-based v1 모델로 다음 거래일 방향 점수와 근거/위험 플래그를 산출하며, Gemini/뉴스 판단과 분리합니다. 내부 `*_probability` 필드명은 기존 산출물 호환을 위해 유지하지만 값의 의미는 보정 확률이 아닌 휴리스틱 점수입니다.

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

- `telegram_pipeline/scan_taxonomy.py`
  - 장마감 rows를 13개 스캐너 탭과 대표 액션 라벨로 분류합니다.
  - 외부 뉴스 API 없이 현재 보유한 갭, 거래량, 상승률, 신고가, 스퀴즈/포켓피봇/이평 지지 신호를 조합해 `scan_action_label`과 `scan_tab_*` 컬럼을 생성합니다.

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
  - Telegram message text를 구성하며 QBS, 13탭 구조 분류, `steady_winner`/`early_reversal`/`hull_buy_turn`, `startup9_confirm`, `technical_buy_cluster`, 다음 거래일 공격형 8-PART, 상세 보드, `five_day_top` 순서를 고정합니다.

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

아래 명령은 실제 Git 저장소 루트인 `C:\gitUpload\cipherX`에서 실행합니다. GitHub Actions와 가장 가까운 Python 3.12 사용을 권장합니다.

### 1. 의존성 설치

```powershell
cd C:\gitUpload\cipherX
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 2. Streamlit 앱 실행

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

### 초보자 가이드 사용법

1. 종목 분석 후 첫 `초보자 가이드` 탭에서 `지금 할 일`과 전략 상태를 먼저 확인합니다.
2. `확인 조건 대기`이면 확인선·관심구간만 관찰합니다. 이 단계의 기존 손절·목표는 실제 진입가와 기준이 다를 수 있어 실행값으로 표시하지 않습니다.
3. `조건 확인 후 분할 접근 검토`여도 진입가, 손절·무효화, 1·2차 목표, 반대 근거를 한 세트로 확인합니다.
4. `주문 전 가정 티켓`에서 진입가·손절가·1차 목표를 함께 바꾸면 가격 순서와 최소 1R을 다시 검증한 뒤, 다음 두 값 중 작은 정수 주 수량을 사용합니다.

```text
손실예산 = 계좌 평가금액 × 거래당 손실 한도
손실기준 수량 = floor(손실예산 ÷ abs(진입가 - 손절가))
비중기준 수량 = floor((계좌 평가금액 × 종목당 최대 사용 비중) ÷ 진입가)
계획 수량 = min(손실기준 수량, 비중기준 수량)
```

5. 이미 보유 중이라면 `보유 포지션 점검`을 켜고 실제 평단·수량과 본인이 정한 방어 기준을 입력합니다. 분석 종가는 기본 참고값일 뿐 실시간 가격이 아니므로 증권사의 최신 가격을 확인해 `점검 현재가`를 수정해야 합니다. 계좌금액은 선택 입력이며 입력 시 포지션 비중과 방어선 가정 손익의 계좌 대비 비율을 함께 표시합니다.
6. 가장 최근 분석에서만 유효한 신규 진입 계획이나 보유 방어계획을 저장할 수 있습니다. 신규 계획의 계좌 평가금액·예상 투입금·계획 손실금액은 저장되지 않으며, `계획 수량도 저장`은 기본적으로 꺼져 있습니다. 수량 포함을 켜면 현재 계좌금액으로 계산 결과와 일치하는지 저장 전에 검증하지만 계좌금액은 저장하지 않으므로, 복원한 계획의 수량은 현재 계좌 기준으로 다시 계산해야 합니다. 보유 방어계획에는 사용자가 확인한 평단·수량·점검 가격·방어 기준이 포함됩니다.
7. 분석 화면 상단의 `내 매매계획`에서 저장 당시 값과 현재 분석의 일치 여부를 확인하고, 상태를 직접 변경하거나 2단계 확인 후 삭제합니다. 이 상태는 브로커 주문·체결 상태가 아니라 사용자의 참고 표시입니다.
8. 세션 초기화나 종료 전에 필요한 계획은 `JSON 백업 다운로드`로 보관할 수 있습니다. JSON은 암호화되지 않은 평문이므로 안전한 위치에 보관해야 하며, 가져온 계획은 자동 실행되지 않고 `재검토 필요`로 표시됩니다. 계좌 평가금액·API 키·차트·PROMPT TAPE는 계획 JSON에 저장하지 않습니다.
9. 여러 계획을 함께 볼 때는 `내 매매계획`의 `계좌 전체 위험예산 점검 사용`을 켭니다. 저장 계획 통화 그룹과 실제 3자리 통화 코드를 확인하고, 같은 통화의 현재 계좌 평가금액을 입력합니다. 계좌 전체 위험·총 노출·한 종목 한도는 본인이 정한 값을 입력하며 0이면 해당 한도 판정을 하지 않습니다.
10. 미체결 신규 진입은 저장 기준일·진입가·손절가가 현재도 유효한지 다시 확인한 항목만 선택합니다. 계산 수량은 저장 수량이 아니라 현재 계좌금액, 계획의 거래당 손실 한도와 종목당 최대 사용 비중으로 다시 산출됩니다.
11. 실제 보유는 현재도 보유 중인 계획을 선택한 뒤 증권사에서 확인한 최신 평단·수량·가격과 현재 사용자 방어선을 입력하고 `증권사 최신값과 대조`를 체크합니다. 저장 기본값을 그대로 두어도 이 대조 확인 없이는 합계에 넣지 않으며 값을 바꾸면 확인이 다시 해제됩니다.
12. 실제 보유와 신규 진입은 기본적으로 따로 봅니다. 선택한 신규 진입이 모두 체결되는 상황까지 보려는 경우에만 `모두 계획가에 체결된 동시 가정`을 켜고 반영 범위 확인을 완료합니다. `기준 이내` 표시는 사용자가 입력한 숫자 한도와의 산술 비교일 뿐 안전·매수 가능·수익 보장 판정이 아닙니다.

계좌 위험예산 점검의 핵심 계산은 다음과 같습니다.

```text
실제 보유 노출 = 최신 확인 가격 × 현재 보유 수량
방어선 미도달 보유 위험 = (최신 확인 가격 - 사용자 방어선) × 현재 보유 수량
미체결 진입 노출 = 계획 진입가 × 현재 계좌로 재계산한 수량
미체결 진입 위험 = (계획 진입가 - 계획 손절가) × 현재 계좌로 재계산한 수량
동시 가정 합계 = 실제 보유 + 선택한 모든 미체결 진입 (사용자가 동시 가정을 확인한 경우만)
```

현재 가격이 사용자 방어선 이하이면 방어선 체결 가정은 이미 지난 값이므로 위험을 0으로 계산하지 않습니다. 해당 보유의 평가 노출은 유지하고 위험금액·남은 위험예산은 미확정으로 표시한 뒤 최신 시세와 주문 상태 확인을 우선 안내합니다.

기본값인 거래당 1%, 종목당 20%와 최소 1R 기준은 프로그램의 안전 게이트·계산 예시이며 개인별 권고 비중이나 수익 기준이 아닙니다. 계좌금액과 가격은 같은 통화로 입력해야 하며, 신규 진입 티켓·보유 점검·저장 계획은 수수료·세금·배당·환율·슬리피지·스프레드·갭 변동·거래소별 호가 단위를 반영하지 않습니다. 저장 계획은 주문 지시가 아니며 실제 체결가나 수익을 보장하지 않습니다. 증권사 평단은 세무상 조정 취득원가와 다를 수 있고, 손절 기준가는 실제 체결가를 보장하지 않으므로 급변장에서는 주문 유형과 체결 위험을 별도로 확인해야 합니다. 자세한 일반 원칙은 [FINRA 취득원가 안내](https://www.finra.org/investors/insights/cost-basis-basics), [FINRA 스톱 주문 유의사항](https://www.finra.org/investors/insights/stop-orders-factors-consider-during-volatile-markets), [Investor.gov 스톱 주문 안내](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-15), [위험 감수 수준](https://www.investor.gov/introduction-investing/investing-basics/save-and-invest/gauge-your-risk-tolerance), [자산배분과 분산](https://www.investor.gov/introduction-investing/getting-started/asset-allocation)을 참고하세요.

이 가이드는 프로그램의 기술적 시나리오를 읽기 쉽게 정리한 교육·정보 제공 기능이며 투자 권유, 맞춤형 자문, 수익 보장이 아닙니다.

### 3. 주요 배치 실행 예시

장마감 scan:

```powershell
.\.venv\Scripts\python.exe -m scripts.daily_scan_and_notify --scan-mode post_close --out-dir artifacts/daily_scan
```

프리마켓 scan:

```powershell
.\.venv\Scripts\python.exe -m scripts.daily_scan_and_notify --scan-mode pre_market --out-dir artifacts/pre_market
```

시장 daily briefing:

```powershell
.\.venv\Scripts\python.exe -m scripts.market_daily_briefing_notify --out-dir artifacts/daily_scan/market_briefing
```

Telegram 전송 없이 artifact만 만들기:

```powershell
.\.venv\Scripts\python.exe -m scripts.daily_scan_and_notify --dry-run --skip-telegram
```

## 환경변수 / Secrets

Streamlit Cloud, GitHub Actions, 로컬 실행 환경에서 아래 값을 설정합니다.

```text
GEMINI_API_KEY 또는 GOOGLE_API_KEY
TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID

```

AI분석 버튼은 Gemini 키를 `runtime_gemini_api_key` 세션 입력값 → Streamlit secrets → 환경변수 순서로 사용합니다. 세션 입력 키는 현재 Streamlit 세션에만 보관되며 PROMPT TAPE나 리포트에는 기록하지 않습니다.

API 키, OAuth 토큰, 서비스 계정 JSON은 저장소에 넣지 않습니다. 로컬에서는 환경변수나 `.streamlit/secrets.toml`을 사용하고, 이미 외부에 노출된 자격증명은 즉시 폐기·재발급해야 합니다.

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
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
```

주요 테스트 예시:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_strategy_mvp
.\.venv\Scripts\python.exe -m unittest tests.test_startup9_confirm_ranker
.\.venv\Scripts\python.exe -m unittest tests.test_scan_taxonomy
.\.venv\Scripts\python.exe -m unittest tests.test_beginner_trade_guide tests.test_holding_scenario tests.test_beginner_trade_guide_app
.\.venv\Scripts\python.exe -m unittest tests.test_trade_plan_service tests.test_trade_plan_workspace_app tests.test_session_defaults
.\.venv\Scripts\python.exe -m unittest tests.test_portfolio_risk_service tests.test_portfolio_risk_workspace_app
.\.venv\Scripts\python.exe -m unittest tests.test_daily_scan_notify
.\.venv\Scripts\python.exe -m unittest tests.test_daily_scan_resilience
.\.venv\Scripts\python.exe -m unittest tests.test_telegram_pipeline
.\.venv\Scripts\python.exe -m unittest tests.test_market_daily_briefing_notify
```

수동 signal flip 점검:

```powershell
.\.venv\Scripts\python.exe tests/manual/test_signal_flip.py
```

## 운영 메모

- GitHub Actions cron은 UTC 기준이며, 장마감 workflow는 EDT `20:05 UTC`와 EST `21:05 UTC` schedule을 함께 등록한 뒤 내부 guard로 실제 US/Eastern 16:05 실행만 허용합니다.
- Telegram 전송은 현재 scheduled script와 `telegram_pipeline.sender` 중심입니다.
- Streamlit 앱은 사용자 분석 UI와 digest 확인 UI를 제공하고, scheduled 배치는 GitHub Actions가 담당합니다.
- `artifacts/` 하위 산출물은 scan/briefing 실행 결과이며, 필요 시 GitHub Actions artifact로 업로드됩니다.
