# requirement_2 검증 Report (TE 실습)

| 항목 | 내용 |
|------|------|
| **프로젝트** | webOS Subscription Management Dashboard |
| **검증 대상** | requirement_2.md (가전 목록 조회 + 사용 현황 + 차트) |
| **검증 일시** | 2026-10-01 16:31:39 |
| **작성자** | (여기에 이름을 적으세요) |

**총 27건 중 PASS 27 / FAIL 0 — Pass Rate 100.0%**

| TC ID | 테스트 시나리오 | 기대 결과 | 실제 결과 | 판정 |
|:-----:|----------------|-----------|-----------|:----:|
| DEV-01 | get_devices_by_user("U001") 직접 호출 | 2개 반환 | 2개 반환 | ✅ PASS |
| DEV-02 | get_devices_by_user("U999") 직접 호출 | HTTPException(404) | HTTPException 404 | ✅ PASS |
| DEV-03 | get_device_usage("D001") 직접 호출 | D001 사용 현황 dict 반환 | deviceId=D001 | ✅ PASS |
| DEV-04 | get_device_usage("D999") 직접 호출 | HTTPException(404) | HTTPException 404 | ✅ PASS |
| TE-1 | /api/subscribers/U001/devices 호출 | 200 + 2개 가전 JSON (D001, D002) | status=200, ['D001', 'D002'] | ✅ PASS |
| TE-2 | /api/subscribers/U005/devices 호출 | 200 + 빈 배열 [] | status=200, body=[] | ✅ PASS |
| TE-3 | /api/subscribers/U999/devices 호출 | 404 에러 | status=404 | ✅ PASS |
| API-01 | 가전 항목 필드 확인 (전체 사용자) | deviceId/type/model/location/status 포함, 총 8개 | 8개, 누락 0건 | ✅ PASS |
| TE-4 | U001 클릭 시 가전 Table 표시 | D001, D002 표시 | 데이터=['D001', 'D002'], devices API 호출=O, currentDevices 저장=O, renderDevices 호출=O, 행 클릭→selectDevice=O | ✅ PASS |
| TE-5 | U005 클릭 시 안내 메시지 | "No registered devices" 표시 | 데이터 0개, 메시지 코드=O | ✅ PASS |
| TE-6 | U001 선택 후 가전 검색 "TV" 입력 | TV 타입(D001)만 표시 | ['D001'] | ✅ PASS |
| TE-7 | U003 선택 후 상태 필터 "Online" 선택 | Online 가전(D004, D005)만 표시 | ['D004', 'D005'] | ✅ PASS |
| TE-7a | U001 선택 후 모델명 "washtower" 검색 (소문자) | D002만 표시 | ['D002'] | ✅ PASS |
| TE-7b | U004 선택 후 위치 "Living" 검색 | D008만 표시 | ['D008'] | ✅ PASS |
| TE-7c | U001 선택 후 상태 필터 "Offline" | D002만 표시 | ['D002'] | ✅ PASS |
| TE-7d | U004 선택 후 상태 필터 "Standby" | D008만 표시 | ['D008'] | ✅ PASS |
| TE-7e | U003 선택 후 상태 필터 "Error" | D006만 표시 | ['D006'] | ✅ PASS |
| TE-7f | U003 선택 후 검색 "LG" + 필터 "Online" | D004, D005만 표시 | ['D004', 'D005'] | ✅ PASS |
| TE-7g | U001 선택 후 일치하지 않는 검색어 "zzz" | 0개 + "No devices matched" 표시 | 0개, 메시지 코드=O | ✅ PASS |
| TE-8 | /api/devices/D001/usage 호출 | 200 + 사용 현황 JSON (On, 152시간) | status=200, deviceName=LG OLED evo C4, totalUsageHours=152, 누락 필드 [] | ✅ PASS |
| TE-9 | /api/devices/D999/usage 호출 | 404 에러 | status=404 | ✅ PASS |
| API-02 | 등록 가전 8개 사용 현황 일괄 조회 | 모두 200 + weeklyUsageTrend 7개 숫자 | 8개 모두 정상 | ✅ PASS |
| TE-10 | D001 클릭 시 사용 현황 표시 | 전원상태, 누적시간 등 표시 | usage API 호출=O, usage-empty 숨김=O, usage-detail 표시=O, usage-info 렌더링=O, 전원상태=O, 누적시간=O, 주간횟수=O, 건강상태=O, 마지막사용=O, 비고=O, badge 적용=O | ✅ PASS |
| TE-11 | D001 클릭 시 Bar Chart 표시 | 요일별(Mon~Sun) 사용량 Bar Chart | new Chart=O, type bar=O, 요일 라벨=O, beginAtZero=O, selectDevice→renderUsageChart=O, canvas/Chart.js=O | ✅ PASS |
| TE-12 | D001 → D002 클릭 시 차트 갱신 | 이전 차트 destroy 후 새 데이터로 차트 표시 | destroy()=O, usageChart 재할당=O, D001 [2, 3, 1, 4, 2, 3, 3] → D002 [0, 1, 0, 1, 1, 0, 1] | ✅ PASS |
| FE-1 | 가전 검색/필터 실시간 반영 이벤트 바인딩 | input/change 리스너 활성화 | search=O, filter=O | ✅ PASS |
| FE-2 | 다른 구독자 선택 시 이전 사용 현황 초기화 | 선택 상태 갱신 + 사용 현황 패널 초기화 | selectedUserId 갱신=O, selectedDeviceId 초기화=O, 구독자 선택 표시=O, usage-empty 표시=O, usage-detail 숨김=O, usage-info 비우기=O | ✅ PASS |

## 결함 요약

- 없음 — 모든 시나리오 PASS. PM 은 PR(feature/devices-api → main) Merge 진행 가능.

## 비고

- TE-6 ~ TE-7g 검색/필터 판정은 API 응답 데이터에 app.js 와 동일한 규칙(type/model/status/deviceId/location 부분 문자열, 대소문자 무시 + status 일치)을 적용해 계산했습니다.
- TE-4, 5, 10~12 와 FE 항목은 app.js 코드 정적 점검 + API 데이터로 판정했습니다. 실제 화면(Table 표시, 상세 정보, Bar Chart 갱신)은 http://localhost:8000 에서 수동으로 교차 확인합니다.

> 본 Report 는 `tests/req2_test_template.py` 로 생성되었습니다.
