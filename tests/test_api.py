"""Automated tests for all three endpoints."""


# ──────────────────────────────────────
# POST /links
# ──────────────────────────────────────

class TestPostLinks:
    def test_create_link(self, client):
        resp = client.post("/links", json={"target_url": "https://fiverr.com/john/logo-design"})
        assert resp.status_code == 201
        data = resp.json()
        assert len(data["short_code"]) == 6
        assert data["target_url"] == "https://fiverr.com/john/logo-design"
        assert data["short_url"].endswith(f"/{data['short_code']}")
        assert "created_at" in data

    def test_duplicate_url_returns_200(self, client):
        url = "https://fiverr.com/jane/web-design"
        resp1 = client.post("/links", json={"target_url": url})
        resp2 = client.post("/links", json={"target_url": url})
        assert resp1.status_code == 201
        assert resp2.status_code == 200
        assert resp1.json()["short_code"] == resp2.json()["short_code"]

    def test_different_urls_get_different_codes(self, client):
        resp1 = client.post("/links", json={"target_url": "https://fiverr.com/a/svc1"})
        resp2 = client.post("/links", json={"target_url": "https://fiverr.com/b/svc2"})
        assert resp1.json()["short_code"] != resp2.json()["short_code"]

    def test_missing_target_url(self, client):
        resp = client.post("/links", json={})
        assert resp.status_code == 422

    def test_empty_target_url(self, client):
        resp = client.post("/links", json={"target_url": ""})
        assert resp.status_code == 422

    def test_invalid_url_format(self, client):
        resp = client.post("/links", json={"target_url": "not-a-url"})
        assert resp.status_code == 422


# ──────────────────────────────────────
# GET /{short_code}
# ──────────────────────────────────────

class TestRedirect:
    def test_redirect_302(self, client):
        target = "https://fiverr.com/test/redirect"
        resp = client.post("/links", json={"target_url": target})
        short_code = resp.json()["short_code"]

        resp = client.get(f"/{short_code}", follow_redirects=False)
        assert resp.status_code == 302
        assert resp.headers["location"] == target

    def test_not_found(self, client):
        resp = client.get("/zzzzzz", follow_redirects=False)
        assert resp.status_code == 404

    def test_click_is_recorded(self, client):
        target = "https://fiverr.com/test/click-track"
        resp = client.post("/links", json={"target_url": target})
        short_code = resp.json()["short_code"]

        client.get(f"/{short_code}", follow_redirects=False)

        stats = client.get("/stats").json()
        link = next(l for l in stats["links"] if l["short_code"] == short_code)
        assert link["total_clicks"] == 1
        assert link["total_earnings"] == 0.05

    def test_multiple_clicks(self, client):
        resp = client.post("/links", json={"target_url": "https://fiverr.com/test/multi"})
        short_code = resp.json()["short_code"]

        for _ in range(5):
            client.get(f"/{short_code}", follow_redirects=False)

        stats = client.get("/stats").json()
        link = next(l for l in stats["links"] if l["short_code"] == short_code)
        assert link["total_clicks"] == 5
        assert link["total_earnings"] == 0.25


# ──────────────────────────────────────
# GET /stats
# ──────────────────────────────────────

class TestStats:
    def test_empty_stats(self, client):
        resp = client.get("/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data == {"page": 1, "limit": 20, "total_links": 0, "links": []}

    def test_stats_with_links(self, client):
        for i in range(3):
            client.post("/links", json={"target_url": f"https://fiverr.com/u{i}/svc"})

        data = client.get("/stats").json()
        assert data["total_links"] == 3
        assert len(data["links"]) == 3

    def test_pagination(self, client):
        for i in range(5):
            client.post("/links", json={"target_url": f"https://fiverr.com/p{i}/svc"})

        page1 = client.get("/stats?page=1&limit=2").json()
        assert page1["total_links"] == 5
        assert len(page1["links"]) == 2

        page2 = client.get("/stats?page=2&limit=2").json()
        assert len(page2["links"]) == 2

        page3 = client.get("/stats?page=3&limit=2").json()
        assert len(page3["links"]) == 1

    def test_limit_capped_at_100(self, client):
        resp = client.get("/stats?limit=200")
        # FastAPI Query(le=100) rejects this
        assert resp.status_code == 422

    def test_page_below_1_rejected(self, client):
        resp = client.get("/stats?page=0")
        # FastAPI Query(ge=1) rejects this
        assert resp.status_code == 422

    def test_earnings_calculation(self, client):
        resp = client.post("/links", json={"target_url": "https://fiverr.com/test/earn"})
        sc = resp.json()["short_code"]

        for _ in range(10):
            client.get(f"/{sc}", follow_redirects=False)

        link = next(l for l in client.get("/stats").json()["links"] if l["short_code"] == sc)
        assert link["total_clicks"] == 10
        assert link["total_earnings"] == 0.50

    def test_monthly_breakdown_present(self, client):
        resp = client.post("/links", json={"target_url": "https://fiverr.com/test/monthly"})
        sc = resp.json()["short_code"]
        client.get(f"/{sc}", follow_redirects=False)

        link = next(l for l in client.get("/stats").json()["links"] if l["short_code"] == sc)
        assert isinstance(link["monthly_breakdown"], list)
        assert len(link["monthly_breakdown"]) == 1
        assert link["monthly_breakdown"][0]["clicks"] == 1
        # Month format: YYYY-MM
        assert len(link["monthly_breakdown"][0]["month"]) == 7
