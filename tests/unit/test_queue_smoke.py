from app.domain.enums import ContentType, Platform
from app.domain.models import MediaItem, UnifiedPost
from app.domain.policies import Route
from app.utils.serialization import route_from_dict, route_to_dict, unified_post_from_dict, unified_post_to_dict


def test_serialization_roundtrip():
    route = Route(
        id="r1",
        source_platform=Platform.TELEGRAM,
        source_chat_id="src",
        target_platform=Platform.MAX,
        target_chat_id="dst",
        enabled=True,
    )
    post = UnifiedPost(
        source_platform=Platform.TELEGRAM,
        source_chat_id="src",
        source_message_id="42",
        text="hello",
        media=[MediaItem(type=ContentType.IMAGE, url="https://example.com/a.jpg")],
    )

    route2 = route_from_dict(route_to_dict(route))
    post2 = unified_post_from_dict(unified_post_to_dict(post))

    assert route2.target_platform == Platform.MAX
    assert post2.media[0].type == ContentType.IMAGE
    assert post2.text == "hello"
