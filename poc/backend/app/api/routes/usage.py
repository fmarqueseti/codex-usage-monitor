from fastapi import APIRouter, HTTPException, Request

router = APIRouter()


@router.get("/api/usage", tags=["usage"])
def usage(request: Request) -> dict:
    try:
        return request.app.state.usage_service.get_usage().to_dict()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
