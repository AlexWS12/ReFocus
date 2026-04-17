"""Compose a pet pixmap with any equipped accessory layers on top.

Every sprite PNG has some transparent padding around the actual artwork and
different pets/accessories have dramatically different amounts of padding
(e.g. the Crown graphic covers ~28% of its PNG while the CopHat covers
~60%).  Scaling and anchoring based on raw PNG dimensions therefore
produces wildly inconsistent results.

Instead, positioning works in **content space** — the tight bounding box
of each sprite's opaque pixels.  Content rects are computed once per path
and cached.

Semantics used by the catalogs:
    * Pet ``slot_anchors[slot] = (rx, ry)`` is a fractional point on the
      pet's content rect (ry=0 is the top of the visible pet, not the top
      of the PNG).
    * Accessory ``anchor_ratio = (rx, ry)`` is a fractional point on the
      accessory's content rect.  ``(0.5, 1.0)`` is the bottom-center of
      the visible hat and is the default.
    * Accessory ``scale_ratio`` is the accessory content width divided by
      the pet content width (``0.4`` => the visible hat is 40% as wide as
      the visible pet).

The output canvas expands to the union of the pet rect and every
accessory rect, so hats placed above the pet head aren't clipped off.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter, QPixmap

from src.experience.accessory_catalog import ACCESSORY_CATALOG
from src.experience.pet_catalog import (
    DEFAULT_PET,
    DEFAULT_SLOT_ANCHORS,
    PET_CATALOG,
)

# Cache the opaque bounding box of each sprite so we only scan pixels once.
_content_rect_cache: dict[str, tuple[int, int, int, int]] = {}


def _content_rect(path: str, pixmap: QPixmap) -> tuple[int, int, int, int]:
    """Return ``(x_min, y_min, x_max, y_max)`` of ``path``'s opaque pixels.

    Falls back to the full pixmap rectangle when the image has no alpha
    channel or is completely opaque.  Results are cached by path so the
    scan runs at most once per sprite.
    """
    cached = _content_rect_cache.get(path)
    if cached is not None:
        return cached

    image = pixmap.toImage().convertToFormat(QImage.Format_RGBA8888)
    w, h = image.width(), image.height()
    min_x, min_y, max_x, max_y = w, h, -1, -1

    # Walk each scanline as raw RGBA bytes and look at the alpha byte only.
    # `pixelColor` is ~30x slower and blocks the UI thread noticeably on
    # 600x600 sprites.
    alpha_threshold = 16
    for y in range(h):
        raw = bytes(image.constScanLine(y))  # length = w*4 (RGBA)
        alphas = raw[3::4]
        # Find first and last column with non-transparent alpha on this row.
        row_min = -1
        for x in range(w):
            if alphas[x] > alpha_threshold:
                row_min = x
                break
        if row_min == -1:
            continue
        row_max = w - 1
        while row_max > row_min and alphas[row_max] <= alpha_threshold:
            row_max -= 1
        if row_min < min_x:
            min_x = row_min
        if row_max > max_x:
            max_x = row_max
        if y < min_y:
            min_y = y
        if y > max_y:
            max_y = y

    if max_x < 0:
        rect = (0, 0, w, h)
    else:
        rect = (min_x, min_y, max_x + 1, max_y + 1)
    _content_rect_cache[path] = rect
    return rect


def compose_pet_pixmap(
    pet_id: str,
    accessory_ids: list[str] | None = None,
) -> QPixmap:
    """Return a pixmap of ``pet_id`` with ``accessory_ids`` layered on top.

    Unknown accessories, missing sprite files, and accessories that
    specify an incompatible pet are silently skipped so the base pet
    still renders correctly.
    """
    pet_info = PET_CATALOG.get(pet_id, PET_CATALOG[DEFAULT_PET])
    base = QPixmap(pet_info["sprite"])
    if base.isNull():
        return QPixmap()

    slot_anchors = pet_info.get("slot_anchors", DEFAULT_SLOT_ANCHORS)
    pet_cx0, pet_cy0, pet_cx1, pet_cy1 = _content_rect(pet_info["sprite"], base)
    pet_content_w = max(1, pet_cx1 - pet_cx0)
    pet_content_h = max(1, pet_cy1 - pet_cy0)

    placements: list[tuple[int, QPixmap, int, int]] = []
    for accessory_id in accessory_ids or []:
        item = ACCESSORY_CATALOG.get(accessory_id)
        if item is None:
            continue
        compatible = item.get("compatible_pets")
        if compatible is not None and pet_id not in compatible:
            continue

        sprite = QPixmap(item["sprite"])
        if sprite.isNull():
            continue

        slot = item.get("slot", "hat")
        anchor_rx_pet, anchor_ry_pet = slot_anchors.get(
            slot, DEFAULT_SLOT_ANCHORS.get(slot, (0.5, 0.0))
        )
        acc_rx, acc_ry = item.get("anchor_ratio", (0.5, 1.0))
        scale_ratio = float(item.get("scale_ratio", 0.4))

        acc_cx0, acc_cy0, acc_cx1, acc_cy1 = _content_rect(item["sprite"], sprite)
        acc_content_w = max(1, acc_cx1 - acc_cx0)

        # Pick a PNG scale so the accessory's CONTENT width matches the
        # requested fraction of the pet's CONTENT width.
        target_content_w = pet_content_w * scale_ratio
        k = target_content_w / acc_content_w

        scaled_w = max(1, int(round(sprite.width() * k)))
        scaled_h = max(1, int(round(sprite.height() * k)))
        scaled = sprite.scaled(
            scaled_w, scaled_h,
            Qt.IgnoreAspectRatio, Qt.SmoothTransformation,
        )

        # Anchor point on the scaled PNG (inside the accessory's content rect).
        content_anchor_x = (acc_cx0 + (acc_cx1 - acc_cx0) * acc_rx) * k
        content_anchor_y = (acc_cy0 + (acc_cy1 - acc_cy0) * acc_ry) * k

        # Slot anchor on the pet (inside the pet's content rect).
        slot_x = pet_cx0 + pet_content_w * anchor_rx_pet
        slot_y = pet_cy0 + pet_content_h * anchor_ry_pet

        x = int(round(slot_x - content_anchor_x))
        y = int(round(slot_y - content_anchor_y))
        placements.append((int(item.get("z_index", 10)), scaled, x, y))

    # Expand the canvas to cover the pet rect plus every accessory rect so
    # hats placed above the head aren't clipped.
    min_x, min_y = 0, 0
    max_x, max_y = base.width(), base.height()
    for _, scaled, x, y in placements:
        if x < min_x:
            min_x = x
        if y < min_y:
            min_y = y
        if x + scaled.width() > max_x:
            max_x = x + scaled.width()
        if y + scaled.height() > max_y:
            max_y = y + scaled.height()

    offset_x, offset_y = -min_x, -min_y
    canvas = QPixmap(max_x - min_x, max_y - min_y)
    canvas.fill(Qt.transparent)

    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    painter.drawPixmap(offset_x, offset_y, base)
    for _, scaled, x, y in sorted(placements, key=lambda t: t[0]):
        painter.drawPixmap(x + offset_x, y + offset_y, scaled)
    painter.end()
    return canvas
