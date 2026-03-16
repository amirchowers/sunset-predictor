"""Registry of webcams for sunset capture.

YouTube live streams serve live-updating thumbnails:
  https://i.ytimg.com/vi/{VIDEO_ID}/sddefault_live.jpg
  (SD resolution, 640x480, updates every ~5 minutes)

maxresdefault_live.jpg returns placeholders for most small streams,
but sddefault_live.jpg works reliably for the Ashdod beach cams.
"""

from dataclasses import dataclass


@dataclass
class Camera:
    name: str
    image_url: str
    direction: str
    description: str
    source: str = "youtube_live_thumb"
    min_size: int = 20_000  # bytes — below this is a placeholder


def yt_live_thumb(video_id: str, res: str = "sddefault") -> str:
    """YouTube live thumbnail URL. Use 'sddefault' for small streams,
    'maxresdefault' for large ones."""
    return f"https://i.ytimg.com/vi/{video_id}/{res}_live.jpg"


CAMERAS = [
    Camera(
        name="ashdod_arches",
        image_url=yt_live_thumb("1sl7o94YvEA"),
        direction="west",
        description="Ashdod Arches Beach — lifeguard station, sea, western sky",
    ),
    Camera(
        name="ashdod_mei_ami",
        image_url=yt_live_thumb("OouVI1yucBg"),
        direction="west",
        description="Ashdod Mei Ami Beach — wide sea view, ships on horizon",
    ),
    Camera(
        name="ashdod_zevulun",
        image_url=yt_live_thumb("hWwLAaO0Vyo"),
        direction="west-northwest",
        description="Ashdod Zevulun Beach — near port, sea and sky",
    ),
    Camera(
        name="ashdod_metzuda",
        image_url=yt_live_thumb("KhEmwNERRZc"),
        direction="west",
        description="Ashdod Metzuda Beach — coastal view",
    ),
    Camera(
        name="ashdod_lido",
        image_url=yt_live_thumb("ywRpnpbowXc"),
        direction="west",
        description="Ashdod Lido Beach — wide beach and sea",
    ),
    Camera(
        name="israel_multicam",
        image_url=yt_live_thumb("4E-iFtUM2kk", "maxresdefault"),
        direction="multiple angles",
        description="Grid: Tel Aviv, Jerusalem, Haifa + others",
        min_size=50_000,
    ),
]


DEFAULT_CAMERA = "ashdod_arches"


def get_cameras() -> list:
    """Return active cameras. Currently limited to ashdod_arches to conserve
    Vision AI credits (4 images/day vs 24)."""
    return [c for c in CAMERAS if c.name == DEFAULT_CAMERA]


def add_camera(name: str, video_id: str, direction: str, description: str,
               res: str = "sddefault") -> Camera:
    cam = Camera(
        name=name,
        image_url=yt_live_thumb(video_id, res),
        direction=direction,
        description=description,
    )
    CAMERAS.append(cam)
    return cam
