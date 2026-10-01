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
// HTML 특수문자 escape (XSS 방지 + 깨짐 방지)
function escapeHtml(value) {
    return String(value === null || value === undefined ? "" : value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}


// =============================================================================
// [요구사항 #3] 상태 기반 Badge 스타일
// =============================================================================
// 상태 값(value)에 따라 적절한 CSS 클래스를 반환한다.
// 적용 위치: 구독 상태, 가전 상태, 전원 상태(Power), 건강 상태(Health)
// 대소문자 구분 없이 매핑되며, 매핑되지 않는 값은 기본 "badge" 스타일.
//
function badgeClass(value) {
    const v = (value || "").toLowerCase();

    // Active, Online, Normal   → "badge status-active"   (초록)
    if (v === "active" || v === "online" || v === "normal") {
        return "badge status-active";
    }
    // Paused, Standby          → "badge status-paused"   (파랑)
    if (v === "paused" || v === "standby") {
        return "badge status-paused";
    }
    // Expired, Error, Warning  → "badge status-expired"  (빨강)
    if (v === "expired" || v === "error" || v === "warning") {
        return "badge status-expired";
    }
    // Offline                  → "badge status-offline"  (회색)
    if (v === "offline") {
        return "badge status-offline";
    }
    // On, Cleaning             → "badge status-on"       (노랑)
    if (v === "on" || v === "cleaning") {
        return "badge status-on";
    }
    // Off                      → "badge status-off"      (연회색)
    if (v === "off") {
        return "badge status-off";
    }
    // 그 외
    return "badge";
}

// 상태 값을 badge <span> HTML로 변환
function badgeHtml(value) {
    return `<span class="${badgeClass(value)}">${escapeHtml(value)}</span>`;
}


// =============================================================================
// [요구사항 #1] 구독 사용자 조회 + 검색/필터
// =============================================================================

// [요구사항 #1-A] GET /api/subscribers 호출
//
async function fetchSubscribers() {
    try {
        // 1. GET /api/subscribers 호출
        const res = await fetch("/api/subscribers");
        if (!res.ok) {
            throw new Error(`HTTP ${res.status}`);
        }

        // 2. 응답을 subscribers 변수에 저장
        subscribers = await res.json();
    } catch (err) {
        console.error("Failed to fetch subscribers:", err);
        subscribers = [];
    }

    // 3. renderSubscribers() 호출
    renderSubscribers();
}

// [요구사항 #1-B] subscribers 배열을 테이블에 렌더링
//
function renderSubscribers() {
    const tbody = document.getElementById("subscriber-body");
    const search = document.getElementById("subscriber-search").value.toLowerCase();
    const statusFilter = document.getElementById("subscriber-status-filter").value;

    // 1~2. 검색어 + 상태 필터로 subscribers 배열 필터링
    const filtered = subscribers.filter((user) => {
        const matchesSearch =
            (user.name || "").toLowerCase().includes(search) ||
            (user.plan || "").toLowerCase().includes(search) ||
            (user.status || "").toLowerCase().includes(search) ||
            (user.userId || "").toLowerCase().includes(search);

        const matchesStatus = !statusFilter || user.status === statusFilter;

        return matchesSearch && matchesStatus;
    });

    // 3. <tbody>에 <tr> 렌더링
    if (filtered.length === 0) {
        tbody.innerHTML =
            '<tr><td colspan="5" class="empty-msg">No subscribers matched.</td></tr>';
        return;
    }

    tbody.innerHTML = filtered
        .map((user) => {
            const selected = user.userId === selectedUserId ? " selected" : "";
            return `
                <tr class="clickable${selected}" data-user-id="${escapeHtml(user.userId)}">
                    <td>${escapeHtml(user.userId)}</td>
                    <td>${escapeHtml(user.name)}</td>
                    <td>${escapeHtml(user.plan)}</td>
                    <td>${badgeHtml(user.status)}</td>
                    <td>${escapeHtml(user.deviceCount)}</td>
                </tr>`;
        })
        .join("");

    // 각 행 클릭 시 selectSubscriber(userId) 호출
    tbody.querySelectorAll("tr[data-user-id]").forEach((row) => {
        row.addEventListener("click", () => selectSubscriber(row.dataset.userId));
    });
}


// =============================================================================
// [요구사항 #2] 사용자별 가전 목록 + 사용 현황 + 차트
// =============================================================================

// [요구사항 #2-A] 사용자 클릭 시 해당 사용자의 가전 목록 조회
//
async function selectSubscriber(userId) {
    // 1. selectedUserId 업데이트, selectedDeviceId 초기화
    selectedUserId = userId;
    selectedDeviceId = null;

    // 2. 선택 상태 반영
    renderSubscribers();

    // 3. 이전 사용 현황 초기화
    resetUsageDetail();

    // 4. GET /api/subscribers/{userId}/devices 호출
    try {
        const res = await fetch(`/api/subscribers/${encodeURIComponent(userId)}/devices`);
        if (!res.ok) {
            throw new Error(`HTTP ${res.status}`);
        }

        // 5. currentDevices에 저장
        currentDevices = await res.json();
    } catch (err) {
        console.error("Failed to fetch devices:", err);
        currentDevices = [];
    }

    // 6. 가전 Table 렌더링
    renderDevices();
}

// 사용 현황 영역 초기화
function resetUsageDetail() {
    document.getElementById("usage-empty").classList.remove("hidden");
    document.getElementById("usage-detail").classList.add("hidden");
    document.getElementById("usage-info").innerHTML = "";

    if (usageChart) {
        usageChart.destroy();
        usageChart = null;
    }
}

// [요구사항 #2-B] currentDevices 배열을 테이블에 렌더링
//
function renderDevices() {
    const emptyEl = document.getElementById("device-empty");
    const tableEl = document.getElementById("device-table");
    const tbody = document.getElementById("device-body");
    const search = document.getElementById("device-search").value.toLowerCase();
    const statusFilter = document.getElementById("device-status-filter").value;

    // 아직 구독자를 선택하지 않은 경우
    if (!selectedUserId) {
        emptyEl.textContent = "Select a subscriber to view devices.";
        emptyEl.classList.remove("hidden");
        tableEl.classList.add("hidden");
        tbody.innerHTML = "";
        return;
    }

    // 등록된 가전 자체가 없는 경우
    if (currentDevices.length === 0) {
        emptyEl.textContent = "No registered devices.";
        emptyEl.classList.remove("hidden");
        tableEl.classList.add("hidden");
        tbody.innerHTML = "";
        return;
    }

    // 1~2. 검색어 + 상태 필터로 currentDevices 배열 필터링
    const filtered = currentDevices.filter((device) => {
        const matchesSearch =
            (device.type || "").toLowerCase().includes(search) ||
            (device.model || "").toLowerCase().includes(search) ||
            (device.status || "").toLowerCase().includes(search) ||
            (device.deviceId || "").toLowerCase().includes(search) ||
            (device.location || "").toLowerCase().includes(search);

        const matchesStatus = !statusFilter || device.status === statusFilter;

        return matchesSearch && matchesStatus;
    });

    // 3. 필터 결과가 없는 경우
    if (filtered.length === 0) {
        emptyEl.textContent = "No devices matched.";
        emptyEl.classList.remove("hidden");
        tableEl.classList.add("hidden");
        tbody.innerHTML = "";
        return;
    }

    // 결과가 있으면 Table 표시
    emptyEl.classList.add("hidden");
    tableEl.classList.remove("hidden");

    // 4. <tbody> 렌더링
    tbody.innerHTML = filtered
        .map((device) => {
            const selected = device.deviceId === selectedDeviceId ? " selected" : "";
            return `
                <tr class="clickable${selected}" data-device-id="${escapeHtml(device.deviceId)}">
                    <td>${escapeHtml(device.deviceId)}</td>
                    <td>${escapeHtml(device.type)}</td>
                    <td>${escapeHtml(device.model)}</td>
                    <td>${escapeHtml(device.location)}</td>
                    <td>${badgeHtml(device.status)}</td>
                </tr>`;
        })
        .join("");

    // 5. 각 행 클릭 시 selectDevice(deviceId) 호출
    tbody.querySelectorAll("tr[data-device-id]").forEach((row) => {
        row.addEventListener("click", () => selectDevice(row.dataset.deviceId));
    });
}

// [요구사항 #2-C] 가전 클릭 시 상세 사용 현황 조회
//
async function selectDevice(deviceId) {
    // 1. selectedDeviceId 업데이트
    selectedDeviceId = deviceId;

    // 2. 선택 상태 반영
    renderDevices();

    // 3. GET /api/devices/{deviceId}/usage 호출
    let data;
    try {
        const res = await fetch(`/api/devices/${encodeURIComponent(deviceId)}/usage`);
        if (!res.ok) {
            throw new Error(`HTTP ${res.status}`);
        }
        data = await res.json();
    } catch (err) {
        console.error("Failed to fetch usage:", err);
        resetUsageDetail();
        document.getElementById("usage-empty").textContent =
            "Failed to load usage detail.";
        return;
    }

    // 4. usage-empty 숨기기, usage-detail 표시
    document.getElementById("usage-empty").classList.add("hidden");
    document.getElementById("usage-detail").classList.remove("hidden");

    // 5. usage-info에 상세 정보 렌더링
    const rows = [
        ["Device ID", escapeHtml(data.deviceId)],
        ["Device Name", escapeHtml(data.deviceName)],
        ["Power Status", badgeHtml(data.powerStatus)],
        ["Last Used", escapeHtml(data.lastUsedAt)],
        ["Total Usage", `${escapeHtml(data.totalUsageHours)} hrs`],
        ["Weekly Count", escapeHtml(data.weeklyUsageCount)],
        ["Health Status", badgeHtml(data.healthStatus)],
        ["Remark", escapeHtml(data.remark)],
    ];

    document.getElementById("usage-info").innerHTML = rows
        .map(
            ([label, value]) =>
                `<div class="label">${label}</div><div class="value">${value}</div>`
        )
        .join("");

    // 6. 주간 사용량 Bar Chart 렌더링
    renderUsageChart(data.weeklyUsageTrend);
}

// [요구사항 #2-D] Chart.js 주간 사용량 Bar Chart
//
function renderUsageChart(trend) {
    const ctx = document.getElementById("usageChart");

    // 1. 기존 차트가 있으면 destroy()
    if (usageChart) {
        usageChart.destroy();
        usageChart = null;
    }

    // 2. 새 차트 생성
    usageChart = new Chart(ctx, {
        type: "bar",
        data: {
            labels: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            datasets: [
                {
                    label: "Weekly Usage Trend",
                    data: trend || [],
                    backgroundColor: "#93c5fd",
                    borderColor: "#1f3c88",
                    borderWidth: 1,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
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

// [요구사항 #1] 대시보드 진입 시 구독자 목록 자동 조회
fetchSubscribers();