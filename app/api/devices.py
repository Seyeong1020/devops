from fastapi import APIRouter, HTTPException
from app.data.dummy_data import usage_by_device

router = APIRouter()


# =============================================================================
# [요구사항 #2]: GET /api/devices/{device_id}/usage
# =============================================================================
# 특정 가전의 상세 사용 현황을 반환한다.
# - 디바이스가 존재하지 않는 경우: 404
# =============================================================================
@router.get("/devices/{device_id}/usage")
def get_device_usage(device_id: str):
    # 1. usage_by_device에서 device_id로 조회
    usage = usage_by_device.get(device_id)
    if usage is None:
        # 3. 존재하지 않으면 404
        raise HTTPException(status_code=404, detail=f"Device '{device_id}' not found")

    # 2. 존재하면 사용 현황 데이터 반환
    return usage
