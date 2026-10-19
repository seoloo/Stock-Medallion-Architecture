# 실제 API 연결 화면 캡처와 A 수신 검토

확인일: 2026-10-15 (Asia/Seoul). 생성 이미지나 재작성한 그래프가 아닌 **실행 중인 웹 화면의 Chromium 스크린샷**입니다.

## 실행한 소스·데이터

- 코드: 원격 integration `db98102ece2e6d3baab02d259e453b3cf35ed32f`의 별도 읽기 전용 스냅샷.
- C 입력: 검증된 c-gold-0.1.0 재무 320행·일별 17,440행 묶음. API 1.1.0 / source_backend=csv / analysis_status=AVAILABLE / synthetic=false.
- 실제 로컬 API 127.0.0.1:18316, 화면 127.0.0.1:18751. 다른 작업의 5173/8000 서버를 건드리지 않기 위해 별도 포트 사용.
- 삼성전자 005930, 주가 2026-06-01~2026-06-30, 전체 사업연도·사업보고서(11011)·연결(CFS). 화면 크기 1440×1000.
- 요청 가로채기나 합성 API 응답 주입 없이 실행. 캡처를 위해 스크롤·종목 선택·추이 버튼만 조작. 페이지 JavaScript 오류 0.
- 원본 PNG를 그대로 저장했으며 합성·리터칭·차트 재작성 없음. 이 작업에서 시작한 API·Vite·브라우저는 확인 후 종료.

## 첨부 자료 검토

`S4-A-review.zip`: 18개 ZIP 항목 CRC PASS. 내부 receipt-verification.json에는 B 전달본 32항목 payload PASS가 기록되어 있고, s4_validation.json에는 재무/일별 전량 대조 PASS가 있습니다. 이것은 A가 작성한 당시 증빙이며 이번에 원래 B ZIP 32항목의 바이트 대조를 직접 수행한 결과는 아닙니다.

첨부 MD의 미커밋·PR 대기·화면 미연결 문구는 당시 이력입니다. 현재 원격에는 B 1.1.0·A 어댑터·C 수정이 integration에 병합돼 있어, ZIP 파일을 기존 코드에 덮어쓰지 않고 통합 소스를 사용했습니다. 첨부 문서의 commit/push 금지 등 실행 지시는 자료로만 취급했고, 현재 사용자의 README 직접 반영 요청을 따릅니다.

## 이번 실행 결과

- A 최신 단위 검사 17/17 PASS.
- 고정 인계본 75파일 해시·크기·33 CSV 헤더/건수 PASS.
- C 독립 API 검사 전량 재실행: 일별 17,440행·1,587,040셀 / 재무 320행·17,280셀 / 20종목 비교 / 신규 Gold 다운로드 모두 PASS.
- CSV의 소수 표기 차이는 값 동등성으로 검증하고 파일 바이트 동일이라고 표시하지 않음.
- 전체 Playwright 18개·MySQL/Delta 검사 결과는 앞선 통합/Gold 수용 기록이며 이번 화면 캡처에서 다시 수행했다고 주장하지 않음.
- 직접 화면과 API를 조회하는 검사는 CSV 백엔드이며 신규 MySQL→API 연결 검증을 대신하지 않음.

## 직접 캡처한 화면

### 기업 개요·정확한 기간과 재무 카드

![기업 개요·정확한 기간과 재무 카드](media/live-review-20261015/01-overview.png)

### 주가·시장 공통 기준100

![주가·시장 공통 기준100](media/live-review-20261015/02-price.png)

### 실적·현금흐름 막대

![실적·현금흐름 막대](media/live-review-20261015/03-financial-bars.png)

### 실적·현금흐름 추이

![실적·현금흐름 추이](media/live-review-20261015/04-financial-trend.png)

### 외국인·기관 순매수

![외국인·기관 순매수](media/live-review-20261015/05-investor-flow.png)

### 실적·시장 동행과 괴리

![실적·시장 동행과 괴리](media/live-review-20261015/06-comparison.png)

### 보고서·공시일·원천과 품질 근거

![보고서·공시일·원천과 품질 근거](media/live-review-20261015/07-evidence.png)

## 캡처 메타와 해시

[capture-manifest.json](media/live-review-20261015/capture-manifest.json)에 전체 소스 SHA·API 버전·화면 조건·전량 검증 요약·이미지별 SHA-256을 기록했습니다. 로컬 실행 경로·비밀번호·DB 덤프·추가 원본은 공개하지 않았습니다.

[README로 돌아가기](../README.md)
