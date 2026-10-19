# Gold 최종 수용 검증 — 2026-10-15

## 판정과 범위

제공 Silver 기반 신규 Gold 2테이블의 계산 → Delta → MySQL 저장·전량 대사와 CSV 기반 실제 API → 브라우저 검증을 완료했다. 기준 origin/integration `db98102ece2e6d3baab02d259e453b3cf35ed32f`, 기존 C HEAD `9361ad34e4906092c9adc548a48ba53893286bf1`을 정상 merge한 feature/c-gold-final-acceptance에서 수행했다. 기존 이력·75파일 원본 보존, 충돌 없음.

이는 신규 Gold 수용 완료다. 전체 Bronze 재현·기존 B 58테이블 복원·운영 배포·main 승격까지 완료됐다는 뜻은 아니다. 실제 API/브라우저 검사는 CSV 백엔드이며, 신규 C MySQL 테이블을 API가 직접 읽는 동작은 이번에 검증하지 않았다.

## 실제 결과

- c-gold-0.1.0 재무 320행 / 일별 17,440행 재생성, 기존 제출 두 CSV SHA-256 일치.
- B의 기존 pack_c_analysis/import_analysis 재사용. 실제 Delta version 0 로그·Parquet 저장 및 재조회.
- 별도 MySQL 9.5.0 loopback 13316 서버, 새 DB에 17,760행 적재. B의 canonical digest로 전체 행·전체 컬럼 일치.
- C 독립 SQL 검사 222개 PASS: 모든 컬럼 NULL 건수, 숫자 컬럼 합계, 공시일 경계, 매출 성장률. [기계 판독 증빙](../../analysis/evidence/gold-storage-validation.json).
- C 단위 49 PASS / B API 49 PASS·2 SKIP / B 저장 안전성 모의검사 6 PASS.
- A 단위 17 PASS / Vite build PASS / Chromium 18 PASS(실제 B API 연결 검사 포함, 다른 테스트의 fixture·오류 주입과 구분).
- 독립 API: 일별 17,440행·재무 320행·20종목 비교 및 CSV 양방향 값 검사 PASS, 값 차이 0. 숫자 소수 표기 차이는 기록하며 byte 동일을 주장하지 않음.
- 고정 인계본 75파일 무결성 PASS. B 기존 실행 카탈로그가 필요한 2검사는 SKIP 유지.

## 발견한 SQL 검사의 문제와 수정

MySQL 기본 div_precision_increment=4로 나누면 C의 HALF_UP 소수8자리 비율을 재현하지 못해 적격 매출 성장률 259건이 불일치했다. 저장 전량 digest는 일치했다. SQL 세션 div_precision_increment=30을 지정하자 재계산 불일치 0건. 계산·원본 값을 바꾸지 않고 analysis/sql/reconcile.sql과 독립 검사 도구에 세션 정밀도를 명시했다.

## 재실행

B 잠금 환경의 Python을 사용한다. C 산출물을 pack_c_analysis.py로 검증·패키징하고 import_analysis.py로 **새** Delta run을 만든 뒤:

```bash
python -m analysis.verify_storage --run <새-Delta-run-경로> --host 127.0.0.1 --port 3306 --user root
```

암호는 숨김 입력한다. 기존 DB가 있으면 B 적재 도구가 거부하며 초기화하지 않는다. --local-empty-password는 별도 생성한 폐기 가능한 loopback 검사 서버에만 사용한다. 비밀번호·원본·DB덤프·Delta 실파일은 커밋하지 않는다.

CI에 MySQL 8.4 별도 서비스를 추가해 같은 적재·전량·SQL 대사를 실행한다. 로컬 MySQL 9.5 결과와 원격 CI 결과를 구분한다.

## 남는 데이터 제약과 전체 프로젝트 범위

기간 미검증 61보고서, PIT 재무 미연결 1,607행, 수급 격리 1키, 연속성 REVIEW는 그대로 보존한다. 데이터 제약을 임의 보정하거나 완료로 바꾸지 않는다. B 원본 기반 58테이블/덤프/전체 Bronze 증빙과 main 승격은 기존 PR #11의 별도 검토 범위다.
