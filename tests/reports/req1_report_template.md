# requirement_1 검증 Report (TE 실습)

| 항목 | 내용 |
|------|------|
| **프로젝트** | webOS Subscription Management Dashboard |
| **검증 대상** | requirement_1.md |
| **검증 일시** | 2026-10-01 16:31:41 |
| **작성자** | (여기에 이름을 적으세요) |

**총 16건 중 PASS 16 / FAIL 0 — Pass Rate 100.0%**

| TC ID | 테스트 시나리오 | 기대 결과 | 실제 결과 | 판정 |
|:-----:|----------------|-----------|-----------|:----:|
| DEV-01 | get_subscribers() 함수 직접 호출 | 5명 반환 | 5명 반환 | ✅ PASS |
| API-01 | GET /api/subscribers 호출 | 200 OK | status=200 | ✅ PASS |
| TE-1 | /api/subscribers 호출 | 5명의 사용자 목록 반환 | 5명 | ✅ PASS |
| TE-3 | 검색창에 "Kim" 입력 | Kim Minsoo만 표시 | 1명: ['Kim Minsoo'] | ✅ PASS |
| API-02 | 응답 항목 필드 확인 | userId/name/plan/status/deviceCount 포함 | 누락 0건 | ✅ PASS |
| TE-2 | 대시보드 접속 시 Table 자동 표시 | 5명 목록 표시 | 페이지=OK, 초기 fetchSubscribers() 호출=O, API 호출 코드=O, 데이터 5명 | ✅ PASS |
| TE-4 | 검색창에 "Premium" 입력 | Premium 플랜 사용자만 표시 (2명) | 2명: ['Kim Minsoo', 'Choi Sumin'] | ✅ PASS |
| TE-5 | 상태 필터 "Active" 선택 | Active 사용자만 표시 (3명) | 3명: ['Kim Minsoo', 'Lee Jiyoon', 'Choi Sumin'] | ✅ PASS |
| TE-6 | 상태 필터 "Expired" 선택 | Jung Hyerin만 표시 | 1명: ['Jung Hyerin'] | ✅ PASS |
| TE-7 | 검색 "Basic" + 필터 "Active" 동시 적용 | 두 조건 모두 만족하는 Lee Jiyoon만 표시 | 1명: ['Lee Jiyoon'] | ✅ PASS |
| TE-8 | 검색어 "Kim" 입력 후 삭제 | 전체 목록(5명) 복원 | 검색 시 1명 → 삭제 후 5명 | ✅ PASS |
| TE-9 | 검색창에 ID "U003" 입력 | Park Junho만 표시 | 1명: ['Park Junho'] | ✅ PASS |
| TE-10 | 검색창에 소문자 "paused" 입력 | 대소문자 무관, Park Junho만 표시 | 1명: ['Park Junho'] | ✅ PASS |
| TE-11 | 일치하지 않는 검색어 "zzz" 입력 | 0명 표시 (빈 Table) | 0명 | ✅ PASS |
| FE-1 | 검색/필터 실시간 반영 이벤트 바인딩 | input/change 리스너 활성화 | search=O, filter=O | ✅ PASS |
| FE-2 | renderSubscribers() 구현 점검 | 렌더링/행 클릭/선택 표시/필터 코드 존재 | tbody 렌더링=O, selectSubscriber 연결=O, selected 클래스=O, status 필터=O | ✅ PASS |

## 결함 요약

- 없음 — 모든 시나리오 PASS. PM 커밋/배포 진행 가능.

## 비고

- TE-3~TE-11 검색/필터 판정은 API 응답 데이터에 app.js 와 동일한 규칙(name/plan/status/userId 부분 문자열, 대소문자 무시 + status 일치)을 적용해 계산했습니다.
- 브라우저 화면 확인(행 클릭 시 selected 표시 등)은 http://localhost:8000 에서 수동으로 교차 확인합니다.

> 본 Report 는 `tests/req1_test_template.py` 로 생성되었습니다.
