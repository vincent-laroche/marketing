from instagram_saves_engine.state import StateManager


def test_duplicate_state_handling(tmp_path) -> None:  # type: ignore[no-untyped-def]
    path = tmp_path / "sync_state.json"
    manager = StateManager(path)
    assert not manager.has_seen("123", "abc")

    manager.mark_seen("123", shortcode="abc", notion_page_id="page-1")
    assert manager.has_seen("123")
    assert manager.has_seen(None, "abc")
    manager.save()

    loaded = StateManager(path)
    assert loaded.has_seen("123")
    assert loaded.state.seen_media["123"].notion_page_id == "page-1"
