from __future__ import annotations


def clamp_position(
    x: int,
    y: int,
    width: int,
    height: int,
    left: int,
    top: int,
    right: int,
    bottom: int,
) -> tuple[int, int]:
    """return a top left position fully inside a screen"""

    # keep fairy on the screen
    max_x = max(left, min(x, right - width))
    max_y = max(top, min(y, bottom - height))

    # if the fairy is larger than the screen, align it to the top-left corner
    if width > right - left:
        max_x = left
    if height > bottom - top:
        max_y = top

    return max_x, max_y


def snap_x(x: int, width: int, left: int, right: int) -> int:
    """return nearest x coordinate edge"""
    if width >= right - left:
        return left

    left_x = left
    right_x = right - width
    left_distance = abs(x - left_x)
    right_distance = abs(x - right_x)

    return left_x if left_distance <= right_distance else right_x
