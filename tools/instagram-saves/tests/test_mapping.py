from instagram_saves_engine.models import ContentIdea, InstagramSave, MediaType
from instagram_saves_engine.notion_client import content_idea_properties, instagram_save_properties


def test_instagram_save_payload_mapping() -> None:
    save = InstagramSave(
        media_id="123",
        shortcode="abc",
        url="https://www.instagram.com/p/abc/",
        author_username="creator",
        caption="caption",
        media_type=MediaType.REEL,
    )
    props = instagram_save_properties(save)
    assert props["Media ID"]["rich_text"][0]["text"]["content"] == "123"
    assert props["Shortcode"]["rich_text"][0]["text"]["content"] == "abc"
    assert props["Type"]["select"]["name"] == "Reel"
    assert props["Content Idea Created"]["checkbox"] is False


def test_content_idea_payload_mapping() -> None:
    idea = ContentIdea(
        title="Maintenance myths",
        pillar="Education",
        platforms=["Instagram", "TikTok", "YouTube Shorts"],
        format="Reel",
        angle="Explain a common maintenance misconception.",
        hook_options=["Hook 1", "Hook 2", "Hook 3"],
        outline="Intro, explanation, practical takeaway.",
        cta="Save this before your next maintenance day.",
        script_draft="Draft script",
        source_media_id="123",
        safety_notes="No claims.",
    )
    props = content_idea_properties(idea)
    assert props["Name"]["title"][0]["text"]["content"] == "Maintenance myths"
    assert props["Platform"]["multi_select"] == [
        {"name": "Instagram"},
        {"name": "TikTok"},
        {"name": "YouTube Shorts"},
    ]
    assert props["Created From Save"]["checkbox"] is True
