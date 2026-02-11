"""FastAPI application with all three endpoints."""
from fastapi import FastAPI, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import engine, Base, get_db
from app.schemas import LinkCreate, LinkResponse, StatsResponse
from app.services import create_link, get_link_by_short_code, record_click, get_stats
from app.utils import simulate_fraud_check

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Fiverr Shareable Links API", version="1.0.0")


@app.post("/links", response_model=LinkResponse, status_code=201)
def post_link(body: LinkCreate, request: Request, db: Session = Depends(get_db)):
    """Generate a short link. Returns existing link if URL already exists."""
    link, is_new = create_link(db, body.target_url)

    base_url = str(request.base_url).rstrip("/")
    response = LinkResponse(
        short_code=link.short_code,
        short_url=f"{base_url}/{link.short_code}",
        target_url=link.target_url,
        created_at=link.created_at,
    )

    if is_new:
        return response

    # Return 200 for existing links instead of default 201
    from fastapi.responses import JSONResponse
    return JSONResponse(content=response.model_dump(mode="json"), status_code=200)


@app.get("/stats", response_model=StatsResponse)
def get_global_stats(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Global analytics with pagination and monthly breakdown."""
    return get_stats(db, page=page, limit=limit)


@app.get("/{short_code}")
async def redirect_short_link(short_code: str, db: Session = Depends(get_db)):
    """Redirect to target URL after fraud check and click recording."""
    link = get_link_by_short_code(db, short_code)
    if not link:
        raise HTTPException(status_code=404, detail="Short link not found")

    is_valid = await simulate_fraud_check()
    if not is_valid:
        raise HTTPException(status_code=403, detail="Click failed fraud validation")

    record_click(db, link.id)
    return RedirectResponse(url=link.target_url, status_code=302)
