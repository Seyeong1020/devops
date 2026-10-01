"""
requirement_2.md 검증 스크립트  (TE)

검증 대상
--------
요구사항 #2: 가전 목록 조회 + 사용 현황 + 차트
  - GET /api/subscribers/{userId}/devices
  - GET /api/devices/{deviceId}/usage
  - app.js : selectSubscriber / renderDevices / selectDevice / renderUsageChart

실행 방법
--------
    # 프로젝트 루트에서
    python tests/req2_test_template.py

결과
----
    tests/reports/req2_report_template.md   (검증 Report)

필요 패키지: fastapi, uvicorn (requirements.txt 에 이미 포함)
             그 외에는 파이썬 표준 라이브러리만 사용합니다.

────────────────────────────────────────────────────────────────────────
검증 흐름 3단계 (requirement_2.md 기준)
  1) 개발자 테스트  : API 함수를 직접 호출했을 때 값/404 가 올바른가?
  2) API 테스트     : 서버를 켜고 두 API 가 실제로 동작하는가?
  3) TE 시나리오    : 가전 검색/필터, 사용 현황, 차트가 "기대 결과"대로 동작하는가?
────────────────────────────────────────────────────────────────────────
"""

import os
import re
import sys
import time
import json
import socket
import subprocess
import urllib.request
import urllib.error
from datetime import datetime

# Windows 콘솔(cp949)에서도 한글/기호가 깨지지 않도록 출력 인코딩을 UTF-8 로 설정
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# =============================================================================
# 경로 설정
# =============================================================================
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(THIS_DIR)
REPORT_DIR = os.path.join(THIS_DIR, "reports")
REPORT_PATH = os.path.join(REPORT_DIR, "req2_report_template.md")

os.chdir(PROJECT_ROOT)          # 상대경로(app/static 등)를 위해 루트로 이동
BASE_URL = None                 # 서버 기동 후 채워짐

# 검증 결과를 담는 리스트. 각 항목: (TC ID, 시나리오, 기대결과, 실제결과, 통과여부)
results = []


def check(tc_id, scenario, expected, actual, passed):
    """검증 결과 1건을 기록한다."""
    results.append((tc_id, scenario, expected, actual, bool(passed)))
    tag = "PASS" if passed else "FAIL"
    print(f"  [{tag}] {tc_id}  {scenario}")


# =============================================================================
# HTTP 유틸
# =============================================================================
def http_get(path, timeout=5):
    """(status_code, json_data) 반환. 실패 시 (None, None)."""
    try:
        with urllib.request.urlopen(BASE_URL + path, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            try:
                return resp.status, json.loads(body)
            except json.JSONDecodeError:
                return resp.status, None
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception:
        return None, None


# 가전 검색/필터 로직 (app.js renderDevices 와 동일한 규칙을 파이썬으로 재현)
def filter_devices(devices, search="", status=""):
    s = (search or "").lower()
    out = []
    for d in devices:
        matches_search = any(
            s in str(d.get(k, "")).lower()
            for k in ("type", "model", "status", "deviceId", "location")
        )
        matches_status = (not status) or d.get("status") == status
        if matches_search and matches_status:
            out.append(d)
    return out


def ids(items, key="deviceId"):
    return [x.get(key) for x in items if isinstance(x, dict)]


def call_api_func(func, *args):
    """API 함수를 직접 호출. (결과, 예외로 발생한 HTTP status 또는 None)"""
    try:
        return func(*args), None
    except Exception as e:
        return None, getattr(e, "status_code", repr(e))


# =============================================================================
# FE 정적 점검 유틸 (app.js 를 텍스트로 읽어서 확인)
# =============================================================================
def read_file(*parts):
    try:
        with open(os.path.join(*parts), encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def has_active_line(js, snippet):
    """주석(//)이 아닌 줄에 snippet 이 있는지 확인."""
    for line in js.splitlines():
        code = line.split("//", 1)[0]
        if snippet in code.replace("'", '"'):
            return True
    return False


def js_function_body(js, name):
    """function name(...) { ... } 본문을 주석을 제외하고 반환 (중괄호 짝 맞추기)."""
    start = js.find(f"function {name}(")
    if start < 0:
        return ""
    i = js.find("{", start)
    depth, j = 0, i
    while j < len(js):
        if js[j] == "{":
            depth += 1
        elif js[j] == "}":
            depth -= 1
            if depth == 0:
                break
        j += 1
    lines = [l.split("//", 1)[0] for l in js[i:j + 1].splitlines()]
    return "\n".join(lines).replace("'", '"')


def js_function_code(js, name, depth=2):
    """함수 본문 + 본문에서 호출하는 app.js 내부 헬퍼 함수 본문까지 합쳐서 반환.
    (예: selectSubscriber 가 resetUsageDetail() 로 초기화를 분리한 경우도 인식)"""
    body = js_function_body(js, name)
    if depth <= 0:
        return body
    helpers = set(re.findall(r"function\s+(\w+)\s*\(", js)) - {name}
    called = [h for h in helpers if re.search(rf"\b{h}\s*\(", body)]
    return body + "".join("\n" + js_function_code(js, h, depth - 1) for h in sorted(called))


def code_items(body, items):
    """{표시이름: 찾을 문자열 또는 문자열 튜플(하나라도 있으면 O)} → (요약, 전부통과)"""
    found = {}
    for label, needle in items.items():
        needles = needle if isinstance(needle, tuple) else (needle,)
        found[label] = any(n in body for n in needles)
    summary = ", ".join(f"{k}={'O' if v else 'X'}" for k, v in found.items())
    return summary, all(found.values())


# =============================================================================
# 서버 기동 유틸
# =============================================================================
def find_free_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def start_server(port):
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app",
         "--host", "127.0.0.1", "--port", str(port)],
        cwd=PROJECT_ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    for _ in range(40):
        if proc.poll() is not None:
            return proc, False
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=1) as r:
                if r.status == 200:
                    return proc, True
        except Exception:
            time.sleep(0.5)
    return proc, False


def stop_server(proc):
    if proc and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


# =============================================================================
# 검증 실행부
# =============================================================================
def run_tests():
    # =========================================================================
    # 1) 개발자 테스트 : 서버 없이 API 함수를 직접 호출
    # =========================================================================
    try:
        from app.api.subscribers import get_devices_by_user
        from app.api.devices import get_device_usage
    except Exception as e:
        get_devices_by_user = get_device_usage = None
        print(f"  [경고] API 함수 import 실패: {e}")

    if get_devices_by_user:
        data, err = call_api_func(get_devices_by_user, "U001")
        passed = isinstance(data, list) and len(data) == 2
        actual = f"{len(data)}개 반환" if isinstance(data, list) else f"list 아님 ({data!r}, err={err})"
    else:
        passed, actual = False, "import 실패"
    check("DEV-01", 'get_devices_by_user("U001") 직접 호출', "2개 반환", actual, passed)

    if get_devices_by_user:
        data, err = call_api_func(get_devices_by_user, "U999")
        passed = err == 404
        actual = f"HTTPException {err}" if err else f"예외 없음 (반환값 {data!r})"
    else:
        passed, actual = False, "import 실패"
    check("DEV-02", 'get_devices_by_user("U999") 직접 호출', "HTTPException(404)", actual, passed)

    if get_device_usage:
        data, err = call_api_func(get_device_usage, "D001")
        passed = isinstance(data, dict) and data.get("deviceId") == "D001"
        actual = f'deviceId={data.get("deviceId")}' if isinstance(data, dict) else f"dict 아님 ({data!r}, err={err})"
    else:
        passed, actual = False, "import 실패"
    check("DEV-03", 'get_device_usage("D001") 직접 호출', "D001 사용 현황 dict 반환", actual, passed)

    if get_device_usage:
        data, err = call_api_func(get_device_usage, "D999")
        passed = err == 404
        actual = f"HTTPException {err}" if err else f"예외 없음 (반환값 {data!r})"
    else:
        passed, actual = False, "import 실패"
    check("DEV-04", 'get_device_usage("D999") 직접 호출', "HTTPException(404)", actual, passed)

    # =========================================================================
    # 2) API 테스트 + TE 시나리오 : 가전 목록 (4.3 + 4.4)
    # =========================================================================
    devices = {}
    for uid in ("U001", "U002", "U003", "U004", "U005"):
        st, body = http_get(f"/api/subscribers/{uid}/devices")
        devices[uid] = body if st == 200 and isinstance(body, list) else []

    # TE 시나리오 #1 : U001 → 2개 가전
    st, body = http_get("/api/subscribers/U001/devices")
    passed = st == 200 and isinstance(body, list) and ids(body) == ["D001", "D002"]
    check("TE-1", "/api/subscribers/U001/devices 호출", "200 + 2개 가전 JSON (D001, D002)",
          f"status={st}, {ids(body) if isinstance(body, list) else body!r}", passed)

    # TE 시나리오 #2 : U005 → 빈 배열
    st, body = http_get("/api/subscribers/U005/devices")
    passed = st == 200 and body == []
    check("TE-2", "/api/subscribers/U005/devices 호출", "200 + 빈 배열 []",
          f"status={st}, body={body!r}", passed)

    # TE 시나리오 #3 : U999 → 404
    st, _ = http_get("/api/subscribers/U999/devices")
    check("TE-3", "/api/subscribers/U999/devices 호출", "404 에러",
          f"status={st}", st == 404)

    # 응답 형식 : 가전 Table 표시 컬럼
    required = {"deviceId", "type", "model", "location", "status"}
    all_devs = [d for uid in devices for d in devices[uid]]
    missing = [d.get("deviceId", "?") for d in all_devs
               if not isinstance(d, dict) or not required <= set(d)]
    check("API-01", "가전 항목 필드 확인 (전체 사용자)",
          "deviceId/type/model/location/status 포함, 총 8개",
          f"{len(all_devs)}개, 누락 {len(missing)}건",
          len(all_devs) == 8 and not missing)

    js = read_file("app", "static", "app.js")

    # TE 시나리오 #4 : U001 클릭 시 가전 Table 표시
    body = js_function_code(js, "selectSubscriber")
    summary, code_ok = code_items(body, {
        "devices API 호출": "/devices",
        "currentDevices 저장": "currentDevices =",
        "renderDevices 호출": "renderDevices(",
    })
    render = js_function_code(js, "renderDevices")
    row_click = "selectDevice" in render
    passed = code_ok and row_click and ids(devices["U001"]) == ["D001", "D002"]
    check("TE-4", "U001 클릭 시 가전 Table 표시", "D001, D002 표시",
          f"데이터={ids(devices['U001'])}, {summary}, 행 클릭→selectDevice={'O' if row_click else 'X'}",
          passed)

    # TE 시나리오 #5 : U005 클릭 시 안내 메시지
    has_msg = "No registered devices" in render
    passed = devices["U005"] == [] and has_msg and "device-empty" in render
    check("TE-5", "U005 클릭 시 안내 메시지", '"No registered devices" 표시',
          f"데이터 {len(devices['U005'])}개, 메시지 코드={'O' if has_msg else 'X'}", passed)

    # TE 시나리오 #6 : 가전 검색 "TV" (U001 선택 상태)
    r = filter_devices(devices["U001"], search="TV")
    passed = ids(r) == ["D001"] and all(d["type"] == "TV" for d in r)
    check("TE-6", 'U001 선택 후 가전 검색 "TV" 입력', "TV 타입(D001)만 표시",
          f"{ids(r)}", passed)

    # TE 시나리오 #7 : 상태 필터 "Online" (U003 선택 상태: Online 2 / Error 1)
    r = filter_devices(devices["U003"], status="Online")
    passed = ids(r) == ["D004", "D005"]
    check("TE-7", 'U003 선택 후 상태 필터 "Online" 선택', "Online 가전(D004, D005)만 표시",
          f"{ids(r)}", passed)

    # 추가 시나리오 : 모델명 / 위치 / 나머지 상태 필터 / 검색+필터 / 결과 없음
    r = filter_devices(devices["U001"], search="washtower")
    check("TE-7a", 'U001 선택 후 모델명 "washtower" 검색 (소문자)', "D002만 표시",
          f"{ids(r)}", ids(r) == ["D002"])

    r = filter_devices(devices["U004"], search="Living")
    check("TE-7b", 'U004 선택 후 위치 "Living" 검색', "D008만 표시",
          f"{ids(r)}", ids(r) == ["D008"])

    r = filter_devices(devices["U001"], status="Offline")
    check("TE-7c", 'U001 선택 후 상태 필터 "Offline"', "D002만 표시",
          f"{ids(r)}", ids(r) == ["D002"])

    r = filter_devices(devices["U004"], status="Standby")
    check("TE-7d", 'U004 선택 후 상태 필터 "Standby"', "D008만 표시",
          f"{ids(r)}", ids(r) == ["D008"])

    r = filter_devices(devices["U003"], status="Error")
    check("TE-7e", 'U003 선택 후 상태 필터 "Error"', "D006만 표시",
          f"{ids(r)}", ids(r) == ["D006"])

    r = filter_devices(devices["U003"], search="LG", status="Online")
    check("TE-7f", 'U003 선택 후 검색 "LG" + 필터 "Online"', "D004, D005만 표시",
          f"{ids(r)}", ids(r) == ["D004", "D005"])

    r = filter_devices(devices["U001"], search="zzz")
    has_msg = "No devices matched" in render
    check("TE-7g", 'U001 선택 후 일치하지 않는 검색어 "zzz"', '0개 + "No devices matched" 표시',
          f"{len(r)}개, 메시지 코드={'O' if has_msg else 'X'}",
          bool(devices["U001"]) and not r and has_msg)

    # =========================================================================
    # 3) API 테스트 + TE 시나리오 : 사용 현황 + 차트 (4.5 + 4.6)
    # =========================================================================
    usage_fields = {"deviceId", "deviceName", "powerStatus", "lastUsedAt", "totalUsageHours",
                    "weeklyUsageCount", "healthStatus", "remark", "weeklyUsageTrend"}

    # TE 시나리오 #8 : D001 사용 현황
    st, body = http_get("/api/devices/D001/usage")
    ok = st == 200 and isinstance(body, dict)
    passed = ok and usage_fields <= set(body) and body["deviceId"] == "D001" \
        and body["totalUsageHours"] == 152 and body["powerStatus"] == "On"
    actual = (f"status={st}, deviceName={body.get('deviceName')}, "
              f"totalUsageHours={body.get('totalUsageHours')}, 누락 필드 {sorted(usage_fields - set(body))}"
              if ok else f"status={st}, body={body!r}")
    check("TE-8", "/api/devices/D001/usage 호출", "200 + 사용 현황 JSON (On, 152시간)", actual, passed)

    # TE 시나리오 #9 : D999 → 404
    st, _ = http_get("/api/devices/D999/usage")
    check("TE-9", "/api/devices/D999/usage 호출", "404 에러", f"status={st}", st == 404)

    # 응답 형식 : 등록된 모든 가전의 주간 사용량이 요일 7개 숫자인지
    bad = []
    for did in ids(all_devs) or [f"D00{i}" for i in range(1, 9)]:
        st, body = http_get(f"/api/devices/{did}/usage")
        trend = body.get("weeklyUsageTrend") if isinstance(body, dict) else None
        if st != 200 or not (isinstance(trend, list) and len(trend) == 7
                             and all(isinstance(v, (int, float)) for v in trend)):
            bad.append(did)
    check("API-02", "등록 가전 8개 사용 현황 일괄 조회", "모두 200 + weeklyUsageTrend 7개 숫자",
          f"문제 {len(bad)}건 {bad}" if bad else "8개 모두 정상", not bad)

    # TE 시나리오 #10 : D001 클릭 시 사용 현황 표시
    body = js_function_code(js, "selectDevice")
    summary, passed = code_items(body, {
        "usage API 호출": "/usage",
        "usage-empty 숨김": "usage-empty",
        "usage-detail 표시": "usage-detail",
        "usage-info 렌더링": "usage-info",
        "전원상태": "powerStatus",
        "누적시간": "totalUsageHours",
        "주간횟수": "weeklyUsageCount",
        "건강상태": "healthStatus",
        "마지막사용": "lastUsedAt",
        "비고": "remark",
        "badge 적용": "badgeClass(",
    })
    check("TE-10", "D001 클릭 시 사용 현황 표시", "전원상태, 누적시간 등 표시", summary, passed)

    # TE 시나리오 #11 : D001 클릭 시 Bar Chart 표시
    chart = js_function_code(js, "renderUsageChart")
    html = ""
    try:
        with urllib.request.urlopen(BASE_URL + "/", timeout=5) as resp:
            html = resp.read().decode("utf-8")
    except Exception:
        pass
    summary, code_ok = code_items(chart, {
        "new Chart": "new Chart(",
        "type bar": '"bar"',
        "요일 라벨": '"Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"',
        "beginAtZero": "beginAtZero",
    })
    calls_chart = "renderUsageChart(" in body and "weeklyUsageTrend" in body
    page_ok = 'id="usageChart"' in html and "chart.js" in html
    check("TE-11", "D001 클릭 시 Bar Chart 표시", "요일별(Mon~Sun) 사용량 Bar Chart",
          f"{summary}, selectDevice→renderUsageChart={'O' if calls_chart else 'X'}, "
          f"canvas/Chart.js={'O' if page_ok else 'X'}",
          code_ok and calls_chart and page_ok)

    # TE 시나리오 #12 : 다른 가전 클릭 시 차트 갱신
    _, u1 = http_get("/api/devices/D001/usage")
    _, u2 = http_get("/api/devices/D002/usage")
    t1 = u1.get("weeklyUsageTrend") if isinstance(u1, dict) else None
    t2 = u2.get("weeklyUsageTrend") if isinstance(u2, dict) else None
    destroys = "destroy()" in chart
    assigns = "usageChart = new Chart(" in chart
    passed = destroys and assigns and t1 is not None and t2 is not None and t1 != t2
    check("TE-12", "D001 → D002 클릭 시 차트 갱신", "이전 차트 destroy 후 새 데이터로 차트 표시",
          f"destroy()={'O' if destroys else 'X'}, usageChart 재할당={'O' if assigns else 'X'}, "
          f"D001 {t1} → D002 {t2}", passed)

    # =========================================================================
    # 4) FE 코드 점검 : 이벤트 바인딩 + 사용자 전환 시 초기화
    # =========================================================================
    search_bound = has_active_line(
        js, 'getElementById("device-search").addEventListener("input", renderDevices)')
    filter_bound = has_active_line(
        js, 'getElementById("device-status-filter").addEventListener("change", renderDevices)')
    check("FE-1", "가전 검색/필터 실시간 반영 이벤트 바인딩", "input/change 리스너 활성화",
          f"search={'O' if search_bound else 'X'}, filter={'O' if filter_bound else 'X'}",
          search_bound and filter_bound)

    body = js_function_code(js, "selectSubscriber")
    summary, passed = code_items(body, {
        "selectedUserId 갱신": "selectedUserId = userId",
        "selectedDeviceId 초기화": "selectedDeviceId = null",
        "구독자 선택 표시": "renderSubscribers(",
        "usage-empty 표시": "usage-empty",
        "usage-detail 숨김": "usage-detail",
        "usage-info 비우기": "usage-info",
    })
    check("FE-2", "다른 구독자 선택 시 이전 사용 현황 초기화", "선택 상태 갱신 + 사용 현황 패널 초기화",
          summary, passed)


# =============================================================================
# Markdown Report 생성
# =============================================================================
def render_report():
    total = len(results)
    passed = sum(1 for *_, p in results if p)
    failed = total - passed
    rate = (passed / total * 100) if total else 0.0

    lines = []
    lines.append("# requirement_2 검증 Report (TE 실습)")
    lines.append("")
    lines.append("| 항목 | 내용 |")
    lines.append("|------|------|")
    lines.append("| **프로젝트** | webOS Subscription Management Dashboard |")
    lines.append("| **검증 대상** | requirement_2.md (가전 목록 조회 + 사용 현황 + 차트) |")
    lines.append(f"| **검증 일시** | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} |")
    lines.append("| **작성자** | (여기에 이름을 적으세요) |")
    lines.append("")
    lines.append(f"**총 {total}건 중 PASS {passed} / FAIL {failed} — Pass Rate {rate:.1f}%**")
    lines.append("")
    lines.append("| TC ID | 테스트 시나리오 | 기대 결과 | 실제 결과 | 판정 |")
    lines.append("|:-----:|----------------|-----------|-----------|:----:|")
    for tc_id, scenario, expected, actual, passed_ in results:
        mark = "✅ PASS" if passed_ else "❌ FAIL"
        actual = str(actual).replace("|", "\\|")
        lines.append(f"| {tc_id} | {scenario} | {expected} | {actual} | {mark} |")
    lines.append("")
    lines.append("## 결함 요약")
    lines.append("")
    fails = [r for r in results if not r[4]]
    if fails:
        for tc_id, scenario, expected, actual, _ in fails:
            lines.append(f"- **{tc_id}** {scenario}: 기대 `{expected}` / 실제 `{actual}`")
    else:
        lines.append("- 없음 — 모든 시나리오 PASS. PM 은 PR(feature/devices-api → main) Merge 진행 가능.")
    lines.append("")
    lines.append("## 비고")
    lines.append("")
    lines.append("- TE-6 ~ TE-7g 검색/필터 판정은 API 응답 데이터에 app.js 와 동일한 규칙"
                 "(type/model/status/deviceId/location 부분 문자열, 대소문자 무시 + status 일치)을 적용해 계산했습니다.")
    lines.append("- TE-4, 5, 10~12 와 FE 항목은 app.js 코드 정적 점검 + API 데이터로 판정했습니다. "
                 "실제 화면(Table 표시, 상세 정보, Bar Chart 갱신)은 http://localhost:8000 에서 수동으로 교차 확인합니다.")
    lines.append("")
    lines.append("> 본 Report 는 `tests/req2_test_template.py` 로 생성되었습니다.")

    os.makedirs(REPORT_DIR, exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return passed, failed, total, rate


# =============================================================================
# main
# =============================================================================
def main():
    global BASE_URL
    print("=" * 60)
    print(" requirement_2 검증")
    print("=" * 60)

    if PROJECT_ROOT not in sys.path:
        sys.path.insert(0, PROJECT_ROOT)

    port = find_free_port()
    print(f"[서버 기동] 127.0.0.1:{port} ...")
    proc, ok = start_server(port)
    if not ok:
        print("[오류] 서버 기동 실패. requirements 설치 및 app/main.py 를 확인하세요.")
        stop_server(proc)
        sys.exit(1)

    BASE_URL = f"http://127.0.0.1:{port}"
    print("[서버 기동] 성공\n")

    try:
        run_tests()
    finally:
        stop_server(proc)

    passed, failed, total, rate = render_report()
    print("\n" + "=" * 60)
    print(f" 결과: PASS {passed} / FAIL {failed} (총 {total}) - {rate:.1f}%")
    print(f" Report 저장: {os.path.relpath(REPORT_PATH, PROJECT_ROOT)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
