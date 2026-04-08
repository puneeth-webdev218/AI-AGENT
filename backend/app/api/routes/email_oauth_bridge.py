from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse


router = APIRouter(prefix='/auth', tags=['email-auth'])


@router.get('/google/callback')
def google_callback_bridge(request: Request) -> RedirectResponse:
    query_string = request.url.query
    target = 'http://localhost:8001/auth/google/callback'
    if query_string:
        target = f'{target}?{query_string}'
    return RedirectResponse(url=target, status_code=307)
