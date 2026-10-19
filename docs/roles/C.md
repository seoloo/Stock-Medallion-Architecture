# C 진행 기록 — 김형준 / Pandas 분석·시각화

상태: **기준 반영·점검·분류 완료 / 신규 기능 구현 미착수.** [프롬프트](../../prompts/C_analysis.md) · [체크북](../workbook.md) · [보완 업무](../missing-work.md) · [진행표](../integration-status.md).

단계 책임: S0 분석/차트 계약, S1 진단 근거, S2 규칙 대사, **S3 검사한 Gold 계산을 handoff 브랜치·고정 SHA·실행법으로 B에 전달**, S4 API 수치 확인, S5 전체 대사.

## 1. 기준 반영 기록 (2026-10-15)

| 항목 | 실제 값 |
|---|---|
| 저장소 | `https://github.com/2nd-MLOps-engineer-2/Team-Zero.git` |
| 작업 브랜치 | `feature/c-gold-analysis` (깨끗한 clone의 `main`에서 생성, 기존 C 작업 브랜치 없음) |
| 기존 HEAD | `8af915fba1c40849b4cb80d7d8c2bd1768f674b7` |
| 기준 커밋 포함 여부 | `git fetch origin` 후 `origin/main`·`origin/integration` 모두 `8af915f…`를 포함(두 브랜치 HEAD가 동일) |
| 반영 | `git merge --ff-only origin/main` → Already up to date. `origin/integration`은 `main` 대비 추가 커밋 0개라 별도 반영 대상 없음 |
| 기존 작업 보존 | 기존 미커밋 변경 없음. 미추적 `.DS_Store`(macOS 생성) 1개는 삭제·커밋하지 않고 유지. 강제 reset·stash·삭제 없음 |
| 충돌 | 없음 |
| 로컬 환경 | `.venv/`(gitignore 대상): Python 3.13.15, pandas 3.0.6, numpy 2.5.4, matplotlib 3.11.2 — uv로 생성. 팀 공통 의존성 고정은 B01 범위이며 C 전용 고정 파일은 아직 없음 |

## 2. 실행한 검사

| 명령 | 결과 | 구분 |
|---|---|---|
| `python3 scripts/check_handoff.py` | PASS — 75파일 해시·크기, CSV 33개 헤더·행수. 덤프 1개 미포함 표시 | 파일 무결성(실제 데이터) |
| `python3 -m unittest discover -s scripts/tests -v` | 2 tests OK | 검사 도구 단위 테스트 |
| Pandas 읽기 전용 확인(스크래치, 저장소 출력 없음) | 기존 일별 Gold `dscl_dt >= trd_dt` 0건, 재무 가용 15,833행, 연결 보고서는 모두 `pit_join_elig_yn=Y` | 기존 Gold 재확인(신규 Gold 아님) |
| 〃 | `s_dq_issue` RETAINED 1,795 / EXCLUDED_FROM_PIT 122 / EXPLAINED 41 / OPEN 8 / QUARANTINED 1 | Silver 상태 확인 |
| 〃 | 기간 비교 부적격 61건 = 2022 Q1·반기·Q3 각 20건 + `066570` 2025 사업보고서 1건(`rcept_no 20260706000276`, 데이터 최종일 이후 접수) | M07 범위 특정 |
| 〃 | 지표 충돌 1건: `report_085596476a4ce774dab318fa`(`003490` 대한항공, 2023 사업보고서 CFS, `rcept_no 20240313001650`) | M07 범위 특정 |
| 〃 | 기존 기간 요약 `full_cvrg_yn`×`same_prd_cmpr_elig_yn`: Y·Y 239 / Y·N 1 / N·Y 20 / N·N 60 | Gold 기간 요약 사용 범위 |

미실행: MySQL 복원·203개 검증 재실행·Delta·API·브라우저 검사(환경·구현 없음). 기존 `code/*.py` 파이프라인은 A/B 입력·DB 전제와 출력 덮어쓰기 때문에 실행하지 않음. 신규 Gold 계산·차트는 이번 범위가 아니므로 미구현.

## 3. 담당 업무 분류

분류: **이미 포함** / **증빙 확인 필요** / **문서·계약 미작성** / **미구현** / **입력·합의 필요**. 체크북 체크는 하지 않았다.

| ID | 분류 | 기존 자료·근거 | 부족한 것 → 다음 작업 |
|---|---|---|---|
| C01 원본 진단 | **입력 로컬 확보 / 진단 코드 미작성** | `01_profiling/`(C 통합 전 A/B 인계본 기준) + §3a 수령 자료: 셀 단위 수정 이력(OpenDART 107,846·Toss 37,408), 격리 741행의 오염 입력 행 JSON | 수정 이력의 `before`로 최초 오염본의 결함 유형별 파일·컬럼 수치를 Pandas로 재집계(`analysis/`). 오염 ZIP 원본 자체는 R1 잔여 |
| C02 명세 대조 | **입력 로컬 확보 / 대조 문서 미작성** | 명세서 2종(규칙·건수) + 정화 패키지의 규칙별 복원 건수(OpenDART 15규칙 합 107,846 일치, Toss 35,074행·38,050셀 총계 일치 — 정화 측 보고) | 명세 건수 ↔ 수정 이력 독립 재집계, 정상 결측(CFD 3,720·delistDate 20·leverageFactor 20·거래량 0 11행)과 결함 구분 표 작성 |
| C03 표준 사전 | 이미 포함(검토 필요) | `02_standard_dictionary/` 단어 168·용어 345·도메인 26·코드 133·명명규칙 12, xlsx | 신규 Gold 컬럼(`g_fin_rpt_analysis`·`g_stock_daily_analysis`) 용어·도메인 미등록 → 별도 확장 사전 추가 |
| C04 변환·미해결 정책 | 증빙 확인 필요 | `s_dq_issue` 상태 5종, 원 코드 `run_pipeline.py` | B 실행 코드에 넘길 정책 문서 없음 → `contracts/analysis.md`에 격리·보존·재조회 상태 정의 |
| C05 재무 기간·계정 | 증빙 확인 필요 + 입력 일부 필요 | `cal_prd_stts_cd`·`cf_prd_stts_cd` 259 VERIFIED / 61 미검증, 충돌 1건. 수령 원문 ZIP 752개가 259 보고서를 모두 포함(충돌 보고서 `20240313001650` 포함) | 충돌 1건은 로컬 원문으로 확인 가능. 61건은 원문 미포함 → R2 잔여. 기간·연결구분 검사 코드 추가 |
| C06 주가·수급·시점 | 증빙 확인 필요 | 기존 Gold PIT 위반 0, `pit_select`(공시일 < 거래일), TOP_LEVEL/INST_DETAIL 구분 | 신규 Gold용 독립 PIT·이중합산 검사 미작성 → `analysis/tests` |
| C07 실적 변화 | 문서·계약 미작성 + 미구현 | 설계: `project-plan.md` §4 지표 정의 | 성장률·이익률·영업이익 증감·적자/흑자 전환·분모 0 상태 계산 |
| C08 현금·시장 비교 | 미구현 | 영업CF YTD 320건 존재, 기존 기간 요약의 가격·수급 합 | 영업CF/매출·CF 변화, 시장 대비 성과, TOP_LEVEL 순매수 비율 계산 |
| C09 동반 개선·괴리 | 문서·계약 미작성 + 미구현 | 설계 초안(매출 성장률 × 공시 후 시장 대비 성과 4분류) | 현금·수급 보조 근거, 분석 불가 사유 코드, 임계값·버전 문서화 |
| C10 시각화 | 문서·계약 미작성 + 미구현 | 인계 보고서 ERD·위반 차트(분석 차트 아님) | `contracts/visualization.md` + `analysis/` 샘플 그래프 |
| C11 AI 입력 규격 | 문서·계약 미작성 | 기존 `g_ai_stock_daily`(라벨 없음) | 특징·결측·시간순 분할·라벨 분리 규격. 모델은 후속 범위 |
| C12 Pandas 검증 | 미구현 + 합의 필요 | 기존 203 PASS(과거 기록, 신규 Gold 증거 아님) | B의 SQL 결과가 있어야 대조 가능 → G04 합의 |

| 보완 ID | 분류 | C 담당 범위·다음 작업 |
|---|---|---|
| M01 입력 18개 | 입력·합의 필요(B 주도) | B가 확보하면 `input_manifest.csv` 해시와 대조 확인 |
| M02 최초 오염 원본 증빙 | 입력 로컬 확보 + 문서·코드 미작성 | §3a 계보로 최초 오염본 / 정화 Bronze / A·B 인계본 / C Silver를 분리. 수정 이력 기반 결함 수치 재집계 코드·문서 작성 |
| M03 원문 ZIP·기간 근거 | 입력 로컬 확보(752개) / 61건 잔여 | 로컬 원문으로 259건 대조 가능. B가 저장 경로·해시를 `s_dscl_doc`과 대조(B 주도). 61건은 R2 |
| M05 Bronze Delta | 미구현(B 주도) | B 저장 후 원본↔Delta 건수·값 대사 |
| M06 Silver 저장·대사 | 미구현(B 주도) | B 적재 후 17테이블 371,437행·키·값 Pandas 대사 |
| M07 기간·계정 잔여 | 증빙 확인 필요 + 입력 필요 | 61건·충돌 1건·상세 빈값 2,202행 사용 범위 규칙 작성(0 대체 금지) |
| M08 알려진 부재 | 증빙 확인 필요 | `247540/2026-04-16`(OPEN·QUARANTINED), CFD 2023-08-31 이전 3,721행, 재무 미가용 1,607행 → 영향 지표·상태 표 작성 |
| M09 계약 | 문서·계약 미작성 | `contracts/analysis.md`, `contracts/visualization.md` 작성(제안 상태) |
| M10 신규 Gold | 미구현 | `g_fin_rpt_analysis` 320행, `g_stock_daily_analysis` 17,440행 계산 모듈 |
| M14 AI 규격·대사 | 문서 미작성 | C11 규격 + G04 대사 기록 |

## 3a. 수령한 원천 자료 (2026-10-15, 로컬 전용 — 저장소 미커밋)

사용자가 제공한 자료다. 공개 저장소이고 AGENTS 규칙상 새 원본은 자동 커밋하지 않는다. 특히 `06_sources/OpenDART_corruption_manifest.csv`는 명세서 06에서 **평가자 전용(변경 전·후 정답 포함)**으로 표시되어 있어 저장소·PR·외부 공유에 넣지 않는다. 경로는 향후 환경 변수로 받는다.

| 자료 | 로컬 위치 | SHA-256 | 내용 |
|---|---|---|---|
| 토스증권 최종 오염명세서 | `~/Downloads/토스증권_오염명세서.pdf` | `81022a59…c1d20` | CSV 43개·36,644행, 기존 6유형(WS·CASE·DATE·MISS·REF·MISMATCH)+추가 2유형(종목코드 0 삭제 34,501셀·한글 깨짐 96셀), 원본 대비 35,074행·38,050셀 |
| OpenDART 오염 데이터셋 명세서 | `~/Downloads/OpenDART_오염데이터_명세서.pdf` | `a5e5b2ae…c747e` | CSV 48개·1,089,185행 중 107,846행 변경, 15규칙, 인코딩 혼합(BOM 39·무BOM 3·CP949 6), 원문 ZIP 752개 원본 동일 |
| 정화 패키지 | `~/Downloads/Bronze_Cleanup.zip` → `Bronze_Cleanup_20261014.zip` | `d57ff87d…13a43` / `87de2ab7…a730b` | 정화 Bronze CSV 91개, Toss 전체 행 보존본·격리 741행, 셀 단위 수정 이력, 원문 ZIP 752개, 정화·검증 코드, 명세서 사본 |

`~/Downloads`의 `F1_오염_룰북_하드모드.md`(F1 레이싱 데이터)와 `주식코딩 데이터 수집기`(Windows 실행 파일)는 이 프로젝트 입력이 아니어서 사용하지 않았다.

### 확인한 데이터 계보 (읽기 전용 대조, 스크래치 경로에서 실행)

```text
최초 오염본 (OpenDART dataset_corrupted.zip / Toss 추가오염 ZIP — 실물 미수령)
  └ Bronze_Cleanup_20261014: OpenDART 107,846셀 이력 역복원, Toss 37,303셀 복원 + 741행 격리
      └ A/B 인계본 (src_ver=Bronze_Cleanup_20261014 / B sha256) — B가 격리 행을 Toss API 재조회
          └ C 통합 Silver (본 저장소)
```

| 대조 | 결과 |
|---|---|
| Toss 격리 741행(일봉 443·수급 243·지수 55) ↔ Silver | `s_stock_daily_prc` `API_REQUERY` 443행 = 격리 일봉 443키 전부, `s_idx_daily_prc` 55행, `s_invstr_trd_daily` 2,662행 = 242키×11유형. 남은 1키 `247540/2026-04-16`이 Silver QUARANTINED·OPEN 이슈와 일치 |
| 격리 행 원값 표본(`000660/2022-12-15`) | 오염본 고가·저가·종가·거래량이 재조회 값과 일치, 누락됐던 시가만 재조회로 채움 |
| Silver 일봉 OHLC 범위 | 위반 0, 가격 빈값 0 |
| OpenDART 재무 상세 | 정화 4개 파일 66,729행 = `s_fin_item` 66,729행 |
| 원문 ZIP 752개 ↔ `s_fin_rpt` | 공시 연결 259건 모두 원문 존재, 미연결 61건은 원문 없음 |

의미: 저장소 `01_profiling` AS-IS는 **정화·재조회 이후 인계본** 기준이므로 F01의 "오염 원본 5개 결함 유형 수치"는 수정 이력·격리 파일로 다시 집계해야 한다. Silver의 `API_REQUERY` 3,160행은 정화 이력이 아니라 B 재조회값이므로 출처를 구분해 표시한다.

## 4. 필요한 입력 (한 번에 요청)

실제 Silver·Gold는 저장소에 있으므로 다시 요청하지 않는다. 아래는 해당 작업에만 필요하다.

- **R1 잔여 (C01·F01, 선택):** 명세서·정화 이력은 확보했다. 오염 ZIP 실물(`dataset_corrupted.zip`, 정화 README의 Toss 입력 `drive-download-20261014T012748Z-1-001.zip`)이 있으면 인코딩 혼합 등 파일 수준 결함까지 직접 측정한다. 없으면 수정 이력 기반 집계로 진행하고 그 한계를 표시한다. B 재조회 원시 응답(`raw/*_page*.json`)은 B 인계 범위로 확인 요청.
- **R2 잔여 (C05·M03·M07):** 원문 없는 61건 — ① 2022 사업연도 1분기(11013)·반기(11012)·3분기(11014) 20개 기업 × 3 = 60건, ② `066570` 2025 사업보고서 `rcept_no 20260706000276`(데이터 최종일 이후 접수). `003490` 충돌 보고서 `20240313001650`은 수령 원문에 있어 요청에서 제외.
- **R3 (C12·G04·M05·M06):** B의 Silver/Gold 적재 결과와 대조용 SQL 결과(B 구현 후).

## 5. 단계별 전달 계획 (브랜치·PR은 아직 만들지 않음)

| 단계 | C가 넘기거나 받는 것 | 전달 브랜치 예정명 | 수신자·수신 검사 |
|---|---|---|---|
| S0 계약 | `contracts/analysis.md`(G01)·`contracts/visualization.md`(G03) 제안본 + 정상/NULL/분모0 예제 | `handoff/s0-c-to-ab-v1` | B: 컬럼·타입·단위가 DDL·API와 일치 / A: 축·단위·분석 불가 문구 표시 가능 여부 |
| S1 Bronze | 인계본 AS-IS와 최초 원본 진단 분리 문서·진단 코드(R1 확보 시 실측) | `handoff/s1-c-to-b-v1` | B: 원본 보존·Delta 행과 진단 분모 일치 |
| S2 Silver | 기간·계정·수급 규칙 검사 코드와 Pandas 집계 기대값 | `handoff/s2-c-to-b-v1` | B: 371,437행·키·기간 상태 SQL 결과와 대조(G04) |
| **S3 Gold (C 주 전달)** | `analysis/` 계산 모듈·실행법·320/17,440행 결과·검사(PIT·윈도·분모·이중합산)·차트 샘플 | `handoff/s3-c-to-b-v1` | **B**: `review/s3-b-v1`에서 B HEAD에 C SHA 병합 → 실행·저장·건수·값 일치. **A**: 차트 의미 확인 |
| S4 API→화면 | C는 API 수치·기간·단위 확인(수신 측) | — (B의 `handoff/s4-b-to-a-v1`) | C: 동일 종목·기준일 API 값과 Gold 대조 결과를 S4 기록에 남김 |
| S5 전체 | G05 사례 1건 원본→Gold→DB→API→화면·CSV 대조 | 공동 | A·B·C 공동 |

각 전달 시: 검사한 커밋에서 handoff 브랜치 생성·push → base `integration` PR → `docs/handoffs/S{n}-C-to-B.md`(TEMPLATE 복사)와 진행표에 전체 SHA·실행법·기대값·NULL/오류 검사·원천 버전 기록 → 수신 확인 전에는 `수신 확인 대기`로만 표시.

## 6. 다음 개발에서 바로 시작할 작업

1. `contracts/analysis.md` 초안: 두 신규 Gold의 PK·컬럼·타입·단위(소수 비율·원·주)·계산식·상태 코드(`OK`/`DENOM_ZERO`/`NEG_BASE`/`WINDOW_SHORT`/`PRD_UNVERIFIED`/`NOT_PIT_ELIGIBLE`/`NO_DATA` 등, 제안).
2. `analysis/` 모듈: Silver 읽기(문자열 보존·Decimal) → `g_fin_rpt_analysis` 320행 → `g_stock_daily_analysis` 17,440행(기존 `pit_select` 규칙 재사용, 출처 `code/run_pipeline.py` c-integration-1.0.0 명시) → 출력은 `build/analysis/`.
3. `analysis/tests`: 정상·분모 0·음수 기준·결측·공시 당일 경계·기관 이중합산·행 수 보존 검사(합성 + 실제).
4. `contracts/visualization.md`와 1종목 샘플 차트(가격·지수 기준 100, 실적·CF, 수급, 사분면).
5. C11 AI 입력 규격 문서, B와 G04 대조 방식 합의.
6. C01·C02·M02: 수령한 정화 패키지 경로를 환경 변수(예: `TZ_BRONZE_CLEANUP_DIR`, 제안)로 받아 수정 이력·격리 파일에서 최초 오염본 결함 유형별 파일·컬럼 수치를 재집계하고 명세서 건수와 대조. 결과 표만 `build/`·문서에 남기고 원천·정답 이력은 커밋하지 않음.

| 작업 ID | 변경·증빙 경로 | 실행 명령·결과 | 기준 커밋/데이터 버전 | 남은 의존성 |
|---|---|---|---|---|
| 기준 반영·분류 | `docs/roles/C.md` | 위 §2 | `8af915f` / `03_C_integration_20261014`, pipln `c-integration-1.0.0` | R1·R2·R3 |
| 원천 자료 수령·계보 확인 | `docs/roles/C.md` §3a | 읽기 전용 Pandas 대조(위 표) | 정화 패키지 `87de2ab7…` | R1 잔여(오염 ZIP 실물, 선택)·R2 잔여 61건 |
| C01~C12 | `analysis/`(다른 세션 구현 `gold.py` 기준) — 아래 §7 | 아래 §7 | 미커밋, `05a7b3b` 위 작업 트리 | B 실행·SQL 대조, A 화면 확인 |
| M07 SF04·SF06, C06 SS02 | `analysis/rules.py`, `analysis/tests/test_rules.py`, `contracts/analysis.md` | 아래 §7 | c-gold-0.1.0 | REVIEW 11개 보고서 원문 대조 |

## 7. 구현 정리와 Silver 규칙 검사 (2026-10-15)

같은 작업 트리에서 다른 세션이 C 구현(`analysis/gold.py`·`audit.py`·`standards.py`·`sql/reconcile.sql`·`tests/test_gold.py`·`test_source.py`, `contracts/analysis.md`·`visualization.md`)을 먼저 만들었다. 사용자 결정에 따라 **`gold.py` 구현을 기준**으로 하고 이 세션의 중복 구현은 사용자 승인 후 삭제했다.

| 항목 | 처리 |
|---|---|
| 중복 삭제 | `analysis/common.py`·`fin_report.py`·`stock_daily.py`·`checks.py`·`tests/test_metrics.py`·`tests/__init__.py`, 이 세션 실행 결과(`build/analysis`의 혼합 Gold CSV 등) |
| `analysis/run.py` 복원 | 이 세션이 덮어쓴 원본을 남아 있던 `__pycache__/run.cpython-313.pyc`(원본 7,771 bytes, 10:39:42)로 재구성. 원본 바이트코드와 명령 1,128개·이름·변수 **0건 차이** 확인 후 규칙 호출 3줄만 추가 |
| `analysis/rules.py` 추가 | SS02(통과/실패), SF04·SF06(발견 사항). `run.py`가 `validation.json`의 `silver_rules`와 상세 CSV 2개를 쓴다. 플래그·Gold 값은 변경하지 않음 |
| 문서 | `contracts/analysis.md` 규칙 표·전년동기 기준 정책, `analysis/README.md` 출력 표 |

실행·결과(로컬, 실제 공개 인계본):

| 명령 | 결과 |
|---|---|
| `.venv/bin/python -m unittest discover -s analysis/tests -v` | 14 tests OK (기존 8 + 규칙 6: 합성 4·실제 2) |
| `.venv/bin/python -m analysis.run --cleanup-zip <로컬 안쪽 Bronze_Cleanup_20261014.zip>` | Silver PK/FK·Gold 원천·PIT 검사 PASS, 320/17,440행 |
| 재생성 결과 ↔ 다른 세션 10:39 결과 | Gold CSV 2개 SHA-256·`schema.json`·`samples.json`·`silver-profile.csv`·`analysis-preview.png` 바이트 동일. `validation.json`은 `silver_rules` 추가, `cleanup_aggregate`에 다른 세션이 10:40에 `audit.py`에 넣은 `spec_checks`(6항목 PASS)·`toss_repair_or_quarantine_rows` 키만 추가 |

Silver 규칙 결과(c-gold-0.1.0):

- **SS02:** 기관 합계 = 기관 세부 7유형 합 17,439/17,439 → 투자자 간 합계는 TOP_LEVEL만 사용.
- **SF04 (M07):** 비교 480건 중 MATCH 453, UNIT_ROUNDING 7(±1원·±1,000,000원), REVIEW 20행·보고서 11건(기간 검증 11행, 가정 기간 9행). 예: `00413046` 2022 3분기 매출 −18,972,026,021원. MVP 지표는 YTD 기준이라 Q3M을 쓰지 않음.
- **SF06 (M07):** PRIOR_YTD ≠ 전년 보고서 YTD — 매출 32(8개 기업)·영업이익 38·순이익 13 / 각 240. 성장률은 같은 보고서의 재작성된 비교 기준을 유지.

남은 일: REVIEW 11개 보고서 원문 대조(259건은 로컬 원문 ZIP 있음), `standards.py`의 Gold 용어 제안 생성은 복원된 `run.py`에 연결되어 있지 않음(다른 세션 원본에도 호출 없음, 연결 여부 결정 필요), B의 SQL 실행 대조(G04), 커밋·전달 브랜치·PR 미실행.

## 8. 체크북 마무리 (2026-10-15, C 단독 범위)

기준: `feature/c-gold-analysis`를 origin/main `1971dcb`(B 백엔드·C 문서 PR #1·#2 반영)로 fast-forward. B 코드는 읽기만 하고 변경하지 않음.

| ID | 상태 | 이번 추가·증빙 |
|---|---|---|
| C01 | 미체크 — 측정 완료, 실물 ZIP 대기 | `analysis/asis.py`, [asis-original.md](../../analysis/asis-original.md): 결함 5유형 × 원천별 셀·비율·규칙, 명명 스타일, 이음동의 4쌍. 오염 ZIP 실물 직접 진단(인코딩 등)은 미실시 |
| C02 | **체크** | 정상 결측 6항목(정화 README 수치와 일치)·검출 기준·분모 |
| C03 | 미체크 — 용어 제안 생성 | `standards.py`를 `run.py`에 연결, Gold 용어 145·신규 단어 23 제안(미번역 0). 신규 상태 코드의 코드 그룹·허용값 등록은 남음 |
| C04 | 미체크 | 계약에 상태·격리 정책 기재. B 실행 코드 반영 확인 필요 |
| C05 | 미체크 — 입력 대기 | SF04 REVIEW 11행 원문 일치(보고서 간 재작성). 원문 없는 61건(R2) |
| C06·C07·C09·C11 | **체크** | 기존 구현·테스트·계약·`ai-input.md` |
| C08 | **체크** | 공시 후 반응 + `g_fin_rpt_mkt_smry` 1:1 연결 검사(`c08_report_period_join`) |
| C10 | 미체크 | 시각화 계약·시안 있음, A 확인 필요 |
| C12 | 미체크 | Pandas 측 기대값·`sql/reconcile.sql` 준비, B SQL 결과 필요 |

실행: `.venv/bin/python -m unittest discover -s analysis/tests -v` → 18 OK. `.venv/bin/python -m analysis.run --cleanup-zip <로컬 안쪽 ZIP>` → PASS(320/17,440). 작은 출력 사본 `analysis/evidence/`(개인 경로 없음 확인). 전달 기록 [S3-C-to-B](../handoffs/S3-C-to-B.md). 개발 커밋 `feature/c-gold-analysis` `b5d2028`(main 기준, 미push). 전달: `handoff/s3-c-to-b-v1` 검사 대상 `fb1f802c88e2d5b275c737200aa392deac0e628b`(integration `b9b73a4` 위에 C 커밋만 재적용, 내용 동일) → [PR #4](https://github.com/2nd-MLOps-engineer-2/Team-Zero/pull/4), 상태 수신 확인 대기.


## 9. S4 C 수치 확인 (2026-10-15)

B [PR #6](https://github.com/2nd-MLOps-engineer-2/Team-Zero/pull/6) head `9f78ccc`를 C HEAD `81a5705`에서 만든 `review/s4-c-v1`에 merge해 확인했다. C 테스트 18 OK·Gold 해시 S3와 동일, B 테스트 49 passed·2 skipped, `analysis/verify_api.py`로 API 전량 대조 — 값 차이 0. 원천 통과 컬럼 자릿수 표기·`input_version` 표기 차이는 합의 필요. 상세 [S4-C-check](../handoffs/S4-C-check.md), 증빙 `analysis/evidence/s4_api_check.json`. MySQL·Delta 경로와 C12/G04 SQL 대조는 B 실행 결과 대기. push·PR 코멘트는 미실행.


## 2026-10-15 Gold 최종 수용 보완
C12/G04: 신규 Gold 2테이블 Delta→격리 MySQL 전량 digest 및 독립 SQL 222 PASS. G05: CSV 실제 API·브라우저 18 PASS. 기존 이력·데이터 제약 유지. 상세 [Gold 최종 수용](../handoffs/Gold-final-acceptance.md). main 및 기존 B 58테이블 전체 재현은 별도.
