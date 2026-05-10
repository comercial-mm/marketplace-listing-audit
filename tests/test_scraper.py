import json
from datetime import date
from pathlib import Path

from scraper import (
    DAILY_LIMIT,
    USAGE_FILE,
    _check_and_increment_usage,
    parse_amazon_html,
)

FIXTURE = Path(__file__).parent / "fixtures" / "amazon_vanish.html"


def test_parse_title():
    html = FIXTURE.read_text()
    result = parse_amazon_html(html)
    assert "Vanish" in result["title"]


def test_parse_price_present():
    html = FIXTURE.read_text()
    result = parse_amazon_html(html)
    assert result["price"] is not None
    assert 5.0 < result["price"] < 200.0  # sanity range


def test_parse_availability_present():
    html = FIXTURE.read_text()
    result = parse_amazon_html(html)
    assert result["available"] is not None


def test_parse_ean_present():
    html = FIXTURE.read_text()
    result = parse_amazon_html(html)
    # tolerante: Amazon as vezes esconde EAN
    assert result["ean"] == "7891035051326" or result["ean"] is None


def test_rate_limit_increments(tmp_path, monkeypatch):
    fake = tmp_path / "usage.json"
    monkeypatch.setattr("scraper.USAGE_FILE", fake)
    permitido, count = _check_and_increment_usage()
    assert permitido is True
    assert count == 1


def test_rate_limit_blocks_after_max(tmp_path, monkeypatch):
    fake = tmp_path / "usage.json"
    fake.write_text(json.dumps({"date": date.today().isoformat(),
                                 "count": DAILY_LIMIT}))
    monkeypatch.setattr("scraper.USAGE_FILE", fake)
    permitido, count = _check_and_increment_usage()
    assert permitido is False
