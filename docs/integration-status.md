# 단계별 통합 진행표

**main·integration 정렬 — 2026-10-16:** main에 직접 병합된 PR #16~#20을 integration에 합치고, README를 Bronze→Silver→Gold 결과 중심으로 정리했으며, 수집 원값 파일을 공개 트리에서 제거했다. 이후 PR #11로 main 승격. 팀 확인 항목(이력·DB 릴리스·이용 조건)은 [정렬 기록](handoffs/main-sync-20261016.md).

**A 시각화 후속 병합 완료:** PR #12 → integration (`8a9fce00d8181a95a960c543dbd0da88e23e41be`). 병합 전 GitHub CI 두 종류 PASS, 병합 후 단위 17 / 브라우저 18(제외 없음) / 빌드 / 75파일 무결성 PASS. [병합 결과](handoffs/A-visual-merge.md). main 증빙 대기는 유지한다.

**원격 병합 완료 — 2026-10-15:** PR #10 → integration (`81731cd1fafcc9c8604a95e401538295aa3ce449`). PR #4~#9 병합 완료, GitHub 통합/프론트 CI PASS. main은 미반영. [최종 결과와 남은 범위](handoffs/S5-integration.md). 아래 준비/미반영 기록은 이전 이력이다.

**최신 통합 갱신:** B 1.1 고정 SHA와 C 검증 수정 3건을 A 작업 위에 병합하고 회귀검사를 통과했다. 이전 ZIP·미커밋·SHA 대기 기록은 역사 기록이다. 현재 판정·실행법·제한은 [S5 통합 기록](handoffs/S5-integration.md)을 따른다.


2026-10-15 추가: B의 S4 1.1.0은 **미커밋 로컬 보완**이다. C계산해시 재현/2Delta/C값API대조·기준100차트PASS. 신규C MySQL/A실제API연결/새전달SHA·원격반영은대기. 최신요청별자료는 [S4](handoffs/S4-B-to-A.md) 상단을따른다. 아래기존SHA는v1코드로새확장미포함이다.

**다른 역할의 결과를 받으면 이 문서에서 단계 → 전달 기록 → 고정 SHA → 실행법 → 검사 결과 순으로 확인한다.** [절차·브랜치 규칙](integration-workflow.md) · [전달 양식](handoffs/TEMPLATE.md).

2026-10-15 B 실제 Delta·MySQL·기존 Gold API·덤프 복원 로컬 검증 완료. 고정 구현 전달은 `handoff/s4-b-to-a-v1` / `ba2aaf1008d52dc96d983f61cae40d8a628366a2`. 문서 후속 커밋은 feature/b-pipeline-api의 [Draft PR #6](https://github.com/2nd-MLOps-engineer-2/Team-Zero/pull/6). A·C 수신 검증과 integration/main 병합은 별도다.

| 단계 | 합칠 내용 | 전달 → 확인 | 전달 브랜치·고정 SHA·PR | 수신 확인 브랜치·결과 | 상태·열린 의존성 |
|---|---|---|---|---|---|

| **S0 계약** | B API·환경 계약·샘플 | B → A·C | [API](../contracts/api.md)·[S4](handoffs/S4-B-to-A.md) | 미확인 | B 구현·검증 / C 분석·시각화 합의대기 |
| **S1 Bronze** | 실제오염91CSV/인계18입력/28Delta | B → C | [G04](handoffs/G04-validation.md)·S4고정SHA | C 독립확인대기 | B 저장·복구재현 / 최초원본과정제인계구분 |
| **S2 Silver** | 17Delta/MySQL·371437행 | B → C | [G04](handoffs/G04-validation.md)·S4고정SHA | C 독립확인대기 | B 전량대사PASS / 기간61·수급1검토유지 |
| **S3 Gold** | C 계산과 B 실행·저장, 기존Gold2저장·API / 신규분석 | C → B·A | [S3 전달 기록](handoffs/S3-C-to-B.md) / `handoff/s3-c-to-b-v1` / 검사 `fb1f802c88e2d5b275c737200aa392deac0e628b`(기록 커밋 `6a61b132f54bf6a2553ad323e57e73b1cda09e65`) / [PR #4](https://github.com/2nd-MLOps-engineer-2/Team-Zero/pull/4) | B: 별도스냅샷계산/Delta/API대사PASS(정식 review/s3-b-v1 미등록) · A: review/s3-a-v1 재현 PASS | 수신 확인 대기 / 정식 review merge·신규C MySQL 대사(G04) 대기 |
| **S4 API→화면** | 실제조회·품질·근거·다운로드 | B → A·C | [S4](handoffs/S4-B-to-A.md) / `ba2aaf1008d52dc96d983f61cae40d8a628366a2` / [Draft PR #6](https://github.com/2nd-MLOps-engineer-2/Team-Zero/pull/6) | A미확인 · C: `review/s4-c-v1` 값 일치(표기 2건 합의 필요) [S4-C-check](handoffs/S4-C-check.md) | B45자동·13HTTP·9MySQL API PASS / 수신확인대기 |
| **S5 전체** | 화면·계산·API·재현 공동검수 | A·B·C | 미등록 | 미확인 | 미완료 / C신규분석·A화면·G05필요 |
