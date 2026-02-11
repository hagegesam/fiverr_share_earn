"""Business logic for link creation, click recording, and stats retrieval."""
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Link, Click
from app.utils import generate_short_code

EARNINGS_PER_CLICK = 0.05


def create_link(db: Session, target_url: str) -> tuple[Link, bool]:
    """
    Create a new short link or return existing one if URL already exists.

    Returns:
        Tuple of (link, is_new) where is_new indicates if a new link was created.
    """
    existing = db.query(Link).filter(Link.target_url == target_url).first()
    if existing:
        return existing, False

    max_attempts = 10
    for _ in range(max_attempts):
        short_code = generate_short_code()
        link = Link(short_code=short_code, target_url=target_url)
        db.add(link)
        try:
            db.commit()
            db.refresh(link)
            return link, True
        except IntegrityError:
            db.rollback()
            continue

    raise RuntimeError("Failed to generate unique short code after multiple attempts")


def record_click(db: Session, link_id) -> Click:
    """Record a click for a given link."""
    click = Click(link_id=link_id)
    db.add(click)
    db.commit()
    db.refresh(click)
    return click


def get_link_by_short_code(db: Session, short_code: str) -> Link | None:
    """Look up a link by its short code."""
    return db.query(Link).filter(Link.short_code == short_code).first()


def get_stats(db: Session, page: int = 1, limit: int = 20) -> dict:
    """
    Get global analytics with pagination and monthly breakdown.

    Applies defaults: page < 1 → 1, limit > 100 → 100.
    """
    if page < 1:
        page = 1
    if limit > 100:
        limit = 100

    offset = (page - 1) * limit
    total_links = db.query(Link).count()

    links = (
        db.query(Link)
        .order_by(Link.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    links_stats = []
    for link in links:
        total_clicks = db.query(Click).filter(Click.link_id == link.id).count()

        monthly_data = (
            db.query(
                func.to_char(Click.clicked_at, "YYYY-MM").label("month"),
                func.count(Click.id).label("clicks"),
            )
            .filter(Click.link_id == link.id)
            .group_by("month")
            .order_by("month")
            .all()
        )

        links_stats.append({
            "short_code": link.short_code,
            "target_url": link.target_url,
            "total_clicks": total_clicks,
            "total_earnings": round(total_clicks * EARNINGS_PER_CLICK, 2),
            "monthly_breakdown": [
                {"month": month, "clicks": clicks}
                for month, clicks in monthly_data
            ],
        })

    return {
        "page": page,
        "limit": limit,
        "total_links": total_links,
        "links": links_stats,
    }
