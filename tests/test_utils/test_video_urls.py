import pytest

from utils.url_utils import is_video_url, youtube_video_id


@pytest.mark.parametrize(
    "url, video_id",
    [
        ("https://www.youtube.com/watch?v=abc123", "abc123"),
        ("https://youtube.com/watch?v=abc123&t=30s", "abc123"),
        ("https://m.youtube.com/watch?v=abc123", "abc123"),
        ("https://youtu.be/abc123?si=x", "abc123"),
        ("https://www.youtube.com/shorts/abc123", "abc123"),
        ("https://www.youtube.com/embed/abc123", "abc123"),
    ],
)
def test_youtube_video_urls_are_recognized(url, video_id):
    assert youtube_video_id(url) == video_id and is_video_url(url)


@pytest.mark.parametrize(
    "url",
    [
        None, "", "https://www.youtube.com/", "https://www.youtube.com/@kanal", "https://www.youtube.com/playlist?list=PL1",
        "https://vimeo.com/12345", "https://example.org/watch?v=abc", "https://notyoutube.com/watch?v=abc", "file:///a.pdf",
    ],
)
def test_other_urls_are_not_videos_and_other_video_sites_stay_manual(url):
    assert youtube_video_id(url) is None and not is_video_url(url)
