from pydantic import ValidationError

from instagram_saves_engine.models import ContentIdea, InstagramSave, MediaType


def test_media_type_normalization() -> None:
    assert InstagramSave(media_id="1", media_type="1").media_type == MediaType.POST
    assert InstagramSave(media_id="2", media_type="2").media_type == MediaType.REEL
    assert InstagramSave(media_id="3", media_type="8").media_type == MediaType.CAROUSEL
    assert InstagramSave(media_id="4", media_type="other").media_type == MediaType.UNKNOWN


def test_content_idea_requires_three_hooks() -> None:
    try:
        ContentIdea(
            title="Idea",
            pillar="Education",
            platforms=["Instagram"],
            format="Reel",
            angle="Angle",
            hook_options=["one", "two"],
            outline="Outline",
            cta="CTA",
            script_draft="Script",
            safety_notes="Safe",
        )
    except ValidationError as exc:
        assert "at least 3 hook options" in str(exc)
    else:
        raise AssertionError("expected validation error")
