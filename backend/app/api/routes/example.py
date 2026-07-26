from fastapi import APIRouter

router = APIRouter(tags=["Example"])


@router.get("/hello")
async def hello(name: str = "World"):
    """示例接口：返回问候语"""
    return {"message": f"Hello, {name}!"}
