from pathlib import Path


def test_local_web_build_cache_is_isolated_by_port() -> None:
    root = Path(__file__).parents[4]
    script = (root / "scripts" / "start.sh").read_text()

    assert 'NEXT_DIST_DIR=".next-${WEB_PORT}"' in script
    assert ".next-*/" in (root / ".gitignore").read_text()
