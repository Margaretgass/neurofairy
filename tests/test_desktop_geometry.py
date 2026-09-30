from fairy.desktop.geometry import clamp_position, snap_x


def test_clamp_bounds():
    result = clamp_position(
        x=200,
        y=150,
        width=100,
        height=80,
        left=0,
        top=0,
        right=1000,
        bottom=800,
    )
    assert result == (200, 150)


def test_clamp_lefttop():
    result = clamp_position(
        x=-50,
        y=-20,
        width=80,
        height=80,
        left=0,
        top=0,
        right=1000,
        bottom=800,
    )
    assert result == (0, 0)


def test_clamp_rightbottom():
    result = clamp_position(
        x=950,
        y=780,
        width=100,
        height=80,
        left=0,
        top=0,
        right=1000,
        bottom=800,
    )
    assert result == (900, 720)


def test_clamp_position_handles_oversized_saved_coordinate():
    result = clamp_position(
        x=-500,
        y=-500,
        width=120,
        height=120,
        left=0,
        top=0,
        right=700,
        bottom=500,
    )
    assert result == (0, 0)


def test_snap_x_prefers_left_edge():
    result = snap_x(x=120, width=80, left=0, right=500)
    assert result == 0


def test_snap_x_prefers_right_edge():
    result = snap_x(x=420, width=80, left=0, right=500)
    assert result == 420
