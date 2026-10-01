from fastapi import APIRouter, HTTPException
from app.data.dummy_data import subscribers, devices_by_user

router = APIRouter()


# =============================================================================
# [요구사항 #1]: GET /api/subscribers
# =============================================================================
# 전체 구독 사용자 목록을 반환한다.
# =============================================================================
@router.get("/subscribers")
def get_subscribers():
    # subscribers 리스트 전체를 반환
    return subscribers


# =============================================================================
# [요구사항 #2]: GET /api/subscribers/{user_id}/devices
# =============================================================================
# 특정 사용자의 가전 목록을 반환한다.
# - 사용자가 존재하지 않는 경우: 404
# - 가전이 없는 경우: 빈 리스트([])
# =============================================================================
@router.get("/subscribers/{user_id}/devices")
def get_devices_by_user(user_id: str):
    # 1. subscribers 리스트에서 user_id가 존재하는지 확인
    exists = any(subscriber["userId"] == user_id for subscriber in subscribers)
    if not exists:
        # 3. 존재하지 않으면 404
        raise HTTPException(status_code=404, detail=f"Subscriber '{user_id}' not found")

    # 2. 존재하면 해당 사용자의 디바이스 목록 반환 (없으면 빈 리스트)
    return devices_by_user.get(user_id, [])
