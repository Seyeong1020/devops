// =============================================================================
// 전역 변수
// =============================================================================
let subscribers = [];
let currentDevices = [];
let selectedUserId = null;
let selectedDeviceId = null;
let usageChart = null;


// =============================================================================
// 공통 유틸
// =============================================================================
// XSS 방지 및 HTML 깨짐 방지를 위한 간단한 이스케이프 처리
function escapeHtml(value) {
    return String(value === null || value === undefined ? "" : value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

// 테이블 본문에 "결과 없음" 한 줄을 표시
function renderEmptyRow(tbody, colspan, message) {
    tbody.innerHTML =
        '<tr><td colspan="' + colspan + '" class="empty-msg">' +
        escapeHtml(message) +
        "</td></tr>";
}

// 검색어가 주어진 필드들 중 하나라도 부분 매칭되는지 확인
function matchesSearch(fields, search) {
    if (!search) return true;
    return fields.some(function (field) {
        return String(field || "").toLowerCase().includes(search);
    });
}


// =============================================================================
// [요구사항 #3] 상태 기반 Badge 스타일
// =============================================================================
function badgeClass(value) {
    const v = (value || "").toLowerCase();

    // 매핑 규칙:
    // Active, Online, Normal   → "badge status-active"   (초록)
    // Paused, Standby          → "badge status-paused"   (파랑)
    // Expired, Error, Warning  → "badge status-expired"  (빨강)
    // Offline                  → "badge status-offline"  (회색)
    // On, Cleaning             → "badge status-on"       (노랑)
    // Off                      → "badge status-off"      (연회색)
    // 그 외                     → "badge"
    if (v === "active" || v === "online" || v === "normal") {
        return "badge status-active";
    }
    if (v === "paused" || v === "standby") {
        return "badge status-paused";
    }
    if (v === "expired" || v === "error" || v === "warning") {
        return "badge status-expired";
    }
    if (v === "offline") {
        return "badge status-offline";
    }
    if (v === "on" || v === "cleaning") {
        return "badge status-on";
    }
    if (v === "off") {
        return "badge status-off";
    }
    return "badge";
}

// 상태 값을 Badge HTML로 변환
function badgeHtml(value) {
    return (
        '<span class="' + badgeClass(value) + '">' + escapeHtml(value) + "</span>"
    );
}


// =============================================================================
// [요구사항 #1] 구독 사용자 조회 + 검색/필터
// =============================================================================

// GET /api/subscribers 호출 → subscribers 저장 → 렌더링
async function fetchSubscribers() {
    const tbody = document.getElementById("subscriber-body");

    try {
        const res = await fetch("/api/subscribers");
        if (!res.ok) {
            throw new Error("HTTP " + res.status);
        }

        const data = await res.json();

        // BE 엔드포인트가 아직 구현되지 않은 단계(pass)에서는 null 이 반환된다
        if (data === null) {
            subscribers = [];
            renderEmptyRow(tbody, 5, "Subscribers API is not ready yet.");
            return;
        }

        subscribers = Array.isArray(data) ? data : [];
        renderSubscribers();
    } catch (err) {
        console.error("Failed to fetch subscribers:", err);
        subscribers = [];
        renderEmptyRow(tbody, 5, "Failed to load subscribers.");
    }
}

// subscribers 배열을 검색/필터 적용하여 테이블에 렌더링
function renderSubscribers() {
    const tbody = document.getElementById("subscriber-body");
    const search = document.getElementById("subscriber-search").value.toLowerCase();
    const statusFilter = document.getElementById("subscriber-status-filter").value;

    // 1. 검색어와 상태 필터 적용
    const filtered = subscribers.filter(function (user) {
        const matchSearch = matchesSearch(
            [user.name, user.plan, user.status, user.userId],
            search
        );
        const matchStatus = !statusFilter || user.status === statusFilter;
        return matchSearch && matchStatus;
    });

    // 2. 결과가 없는 경우 안내 메시지
    if (subscribers.length === 0) {
        renderEmptyRow(tbody, 5, "No subscribers.");
        return;
    }
    if (filtered.length === 0) {
        renderEmptyRow(tbody, 5, "No subscribers matched.");
        return;
    }

    // 3. 행 렌더링 (선택된 행에 selected 클래스)
    tbody.innerHTML = filtered
        .map(function (user) {
            const isSelected = user.userId === selectedUserId;
            return (
                '<tr class="clickable' + (isSelected ? " selected" : "") + '"' +
                ' data-user-id="' + escapeHtml(user.userId) + '">' +
                "<td>" + escapeHtml(user.userId) + "</td>" +
                "<td>" + escapeHtml(user.name) + "</td>" +
                "<td>" + escapeHtml(user.plan) + "</td>" +
                "<td>" + badgeHtml(user.status) + "</td>" +
                "<td>" + escapeHtml(user.deviceCount) + "</td>" +
                "</tr>"
            );
        })
        .join("");

    // 4. 행 클릭 시 해당 사용자 선택
    tbody.querySelectorAll("tr[data-user-id]").forEach(function (row) {
        row.addEventListener("click", function () {
            selectSubscriber(row.dataset.userId);
        });
    });
}


// =============================================================================
// [요구사항 #2] 사용자별 가전 목록 + 사용 현황 + 차트
// =============================================================================

// 사용자 클릭 → 해당 사용자의 가전 목록 조회
async function selectSubscriber(userId) {
    // 1. 선택 상태 갱신
    selectedUserId = userId;
    selectedDeviceId = null;

    // 2. 선택 표시 반영
    renderSubscribers();

    // 3. 이전 사용 현황 초기화
    resetUsageDetail();

    // 4. 가전 목록 조회
    const emptyEl = document.getElementById("device-empty");
    const tableEl = document.getElementById("device-table");

    try {
        const res = await fetch(
            "/api/subscribers/" + encodeURIComponent(userId) + "/devices"
        );
        if (!res.ok) {
            throw new Error("HTTP " + res.status);
        }

        const data = await res.json();

        // 응답을 기다리는 사이 다른 사용자를 클릭했다면 이 응답은 버린다
        if (selectedUserId !== userId) return;

        // BE 엔드포인트가 아직 구현되지 않은 단계(pass)에서는 null 이 반환된다
        if (data === null) {
            currentDevices = [];
            tableEl.classList.add("hidden");
            emptyEl.classList.remove("hidden");
            emptyEl.textContent = "Devices API is not ready yet.";
            return;
        }

        currentDevices = Array.isArray(data) ? data : [];
        renderDevices();
    } catch (err) {
        if (selectedUserId !== userId) return;
        console.error("Failed to fetch devices:", err);
        currentDevices = [];
        tableEl.classList.add("hidden");
        emptyEl.classList.remove("hidden");
        emptyEl.textContent = "Failed to load devices.";
    }
}

// 사용 현황 패널 초기화
function resetUsageDetail() {
    const usageEmpty = document.getElementById("usage-empty");
    const usageDetail = document.getElementById("usage-detail");
    const usageInfo = document.getElementById("usage-info");

    usageEmpty.textContent = "Select a device to view usage details.";
    usageEmpty.classList.remove("hidden");
    usageDetail.classList.add("hidden");
    usageInfo.innerHTML = "";

    if (usageChart) {
        usageChart.destroy();
        usageChart = null;
    }
}

// currentDevices 배열을 검색/필터 적용하여 테이블에 렌더링
function renderDevices() {
    const emptyEl = document.getElementById("device-empty");
    const tableEl = document.getElementById("device-table");
    const tbody = document.getElementById("device-body");
    const search = document.getElementById("device-search").value.toLowerCase();
    const statusFilter = document.getElementById("device-status-filter").value;

    // 사용자를 아직 선택하지 않은 상태
    if (!selectedUserId) {
        tbody.innerHTML = "";
        tableEl.classList.add("hidden");
        emptyEl.classList.remove("hidden");
        emptyEl.textContent = "Select a subscriber to view devices.";
        return;
    }

    // 1. 검색어 + 상태 필터 적용
    const filtered = currentDevices.filter(function (device) {
        const matchSearch = matchesSearch(
            [device.type, device.model, device.status, device.deviceId, device.location],
            search
        );
        const matchStatus = !statusFilter || device.status === statusFilter;
        return matchSearch && matchStatus;
    });

    // 2. 등록 가전이 없는 경우 / 필터 결과가 없는 경우
    if (currentDevices.length === 0) {
        tbody.innerHTML = "";
        tableEl.classList.add("hidden");
        emptyEl.classList.remove("hidden");
        emptyEl.textContent = "No registered devices";
        return;
    }
    if (filtered.length === 0) {
        tbody.innerHTML = "";
        tableEl.classList.add("hidden");
        emptyEl.classList.remove("hidden");
        emptyEl.textContent = "No devices matched";
        return;
    }

    // 3. 결과가 있으면 테이블 표시
    emptyEl.classList.add("hidden");
    tableEl.classList.remove("hidden");

    // 4. 행 렌더링
    tbody.innerHTML = filtered
        .map(function (device) {
            const isSelected = device.deviceId === selectedDeviceId;
            return (
                '<tr class="clickable' + (isSelected ? " selected" : "") + '"' +
                ' data-device-id="' + escapeHtml(device.deviceId) + '">' +
                "<td>" + escapeHtml(device.deviceId) + "</td>" +
                "<td>" + escapeHtml(device.type) + "</td>" +
                "<td>" + escapeHtml(device.model) + "</td>" +
                "<td>" + escapeHtml(device.location) + "</td>" +
                "<td>" + badgeHtml(device.status) + "</td>" +
                "</tr>"
            );
        })
        .join("");

    // 5. 행 클릭 시 해당 가전 선택
    tbody.querySelectorAll("tr[data-device-id]").forEach(function (row) {
        row.addEventListener("click", function () {
            selectDevice(row.dataset.deviceId);
        });
    });
}

// 가전 클릭 → 상세 사용 현황 조회
async function selectDevice(deviceId) {
    // 1. 선택 상태 갱신 + 2. 선택 표시 반영
    selectedDeviceId = deviceId;
    renderDevices();

    const usageEmpty = document.getElementById("usage-empty");
    const usageDetail = document.getElementById("usage-detail");
    const usageInfo = document.getElementById("usage-info");

    try {
        // 3. 사용 현황 조회
        const res = await fetch(
            "/api/devices/" + encodeURIComponent(deviceId) + "/usage"
        );
        if (!res.ok) {
            throw new Error("HTTP " + res.status);
        }

        const data = await res.json();

        // 응답을 기다리는 사이 다른 가전(또는 다른 사용자)을 클릭했다면 이 응답은 버린다
        if (selectedDeviceId !== deviceId) return;

        // BE 엔드포인트가 아직 구현되지 않은 단계(pass)에서는 null 이 반환된다
        if (data === null) {
            usageDetail.classList.add("hidden");
            usageInfo.innerHTML = "";
            usageEmpty.classList.remove("hidden");
            usageEmpty.textContent = "Usage API is not ready yet.";
            return;
        }

        // 4. 빈 메시지 숨기고 상세 영역 표시
        usageEmpty.classList.add("hidden");
        usageDetail.classList.remove("hidden");

        // 5. 상세 정보 렌더링
        const rows = [
            ["Device ID", escapeHtml(data.deviceId)],
            ["Device Name", escapeHtml(data.deviceName)],
            ["Power Status", badgeHtml(data.powerStatus)],
            ["Last Used", escapeHtml(data.lastUsedAt)],
            ["Total Usage", escapeHtml(data.totalUsageHours) + " hrs"],
            ["Weekly Count", escapeHtml(data.weeklyUsageCount)],
            ["Health Status", badgeHtml(data.healthStatus)],
            ["Remark", escapeHtml(data.remark)],
        ];

        usageInfo.innerHTML = rows
            .map(function (row) {
                return (
                    '<div class="label">' + row[0] + "</div>" +
                    '<div class="value">' + row[1] + "</div>"
                );
            })
            .join("");

        // 6. 주간 사용량 차트
        renderUsageChart(data.weeklyUsageTrend);
    } catch (err) {
        if (selectedDeviceId !== deviceId) return;
        console.error("Failed to fetch usage:", err);
        usageDetail.classList.add("hidden");
        usageInfo.innerHTML = "";
        usageEmpty.classList.remove("hidden");
        usageEmpty.textContent = "Failed to load usage details.";
    }
}

// Chart.js 주간 사용량 Bar Chart
function renderUsageChart(trend) {
    const ctx = document.getElementById("usageChart");

    // 1. 기존 차트 제거 (캔버스 재사용 시 중복 렌더링 방지)
    if (usageChart) {
        usageChart.destroy();
        usageChart = null;
    }

    const data = Array.isArray(trend) ? trend : [];

    // 2. 새 차트 생성
    usageChart = new Chart(ctx, {
        type: "bar",
        data: {
            labels: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            datasets: [
                {
                    label: "Weekly Usage Trend",
                    data: data,
                    backgroundColor: "#1f3c88",
                    borderRadius: 6,
                    maxBarThickness: 32,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function (item) {
                            return item.parsed.y + " times";
                        },
                    },
                },
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: { precision: 0 },
                },
            },
        },
    });
}


// =============================================================================
// 이벤트 바인딩 + 초기화
// =============================================================================
function bindEvents() {
    // [요구사항 #1]
    document.getElementById("subscriber-search").addEventListener("input", renderSubscribers);
    document.getElementById("subscriber-status-filter").addEventListener("change", renderSubscribers);

    // [요구사항 #2]
    document.getElementById("device-search").addEventListener("input", renderDevices);
    document.getElementById("device-status-filter").addEventListener("change", renderDevices);
}

bindEvents();

// [요구사항 #1] 초기 로딩
fetchSubscribers();