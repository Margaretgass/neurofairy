import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QEnterEvent, QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from fairy.desktop.floating_fairy import FloatingFairy


@pytest.fixture(scope="module")
def application():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def fairy(application):
    widget = FloatingFairy()
    yield widget
    widget.close()


def mouse_event(
    event_type: QEvent.Type,
    global_x: int,
    *,
    button: Qt.MouseButton,
    buttons: Qt.MouseButton,
) -> QMouseEvent:
    position = QPointF(global_x, 25)
    return QMouseEvent(
        event_type,
        position,
        position,
        position,
        button,
        buttons,
        Qt.KeyboardModifier.NoModifier,
    )


def enter_event() -> QEnterEvent:
    position = QPointF(25, 25)
    return QEnterEvent(position, position, position)


def test_move_without_a_press_is_ignored(fairy):
    starting_position = fairy.pos()
    event = mouse_event(
        QEvent.Type.MouseMove,
        25,
        button=Qt.MouseButton.NoButton,
        buttons=Qt.MouseButton.LeftButton,
    )

    fairy.mouseMoveEvent(event)

    assert fairy.pos() == starting_position


def test_tool_window_remains_visible_when_application_is_inactive(fairy):
    assert fairy.testAttribute(Qt.WidgetAttribute.WA_MacAlwaysShowToolWindow)


def test_hover_peek_starts_hidden_with_sample_content(fairy):
    assert hasattr(fairy, "_hover_peek")
    assert fairy._hover_peek.text() == "Next: one visible task\n25:00 left"
    assert not fairy._hover_peek.isVisible()


def test_hover_peek_appears_only_after_pointer_lingers(fairy):
    fairy.enterEvent(enter_event())

    QTest.qWait(500)
    assert not fairy._hover_peek.isVisible()

    QTest.qWait(250)
    assert fairy._hover_peek.isVisible()


def test_hover_peek_hides_when_pointer_leaves(fairy):
    fairy.enterEvent(enter_event())
    QTest.qWait(700)
    assert fairy._hover_peek.isVisible()

    fairy.leaveEvent(QEvent(QEvent.Type.Leave))

    assert not fairy._hover_peek.isVisible()


def test_leaving_before_delay_cancels_hover_peek(fairy):
    fairy.enterEvent(enter_event())
    fairy.leaveEvent(QEvent(QEvent.Type.Leave))

    QTest.qWait(700)

    assert not fairy._hover_peek.isVisible()


def test_mouse_press_hides_hover_peek(fairy):
    fairy.enterEvent(enter_event())
    QTest.qWait(700)
    assert fairy._hover_peek.isVisible()
    press = mouse_event(
        QEvent.Type.MouseButtonPress,
        25,
        button=Qt.MouseButton.LeftButton,
        buttons=Qt.MouseButton.LeftButton,
    )

    fairy.mousePressEvent(press)

    assert not fairy._hover_peek.isVisible()


@pytest.mark.parametrize("edge", ["left", "right"])
def test_hover_peek_opens_toward_screen_interior(fairy, edge):
    screen = QApplication.primaryScreen()
    assert screen is not None
    bounds = screen.availableGeometry()
    fairy_y = bounds.y() + 100

    if edge == "left":
        fairy_x = bounds.x()
        expected_x = fairy_x + fairy.width() + 8
    else:
        fairy_x = bounds.x() + bounds.width() - fairy.width()
        expected_x = fairy_x - fairy._hover_peek.width() - 8

    fairy.move(fairy_x, fairy_y)
    expected_y = fairy_y + (fairy.height() - fairy._hover_peek.height()) // 2

    fairy.enterEvent(enter_event())
    QTest.qWait(700)

    assert fairy._hover_peek.pos() == QPoint(expected_x, expected_y)


@pytest.mark.parametrize(
    ("distance", "expected_position"),
    [
        (4, QPoint(100, 100)),
        (5, QPoint(105, 100)),
    ],
)
def test_drag_uses_a_five_point_threshold(fairy, distance, expected_position):
    fairy.move(100, 100)
    press = mouse_event(
        QEvent.Type.MouseButtonPress,
        25,
        button=Qt.MouseButton.LeftButton,
        buttons=Qt.MouseButton.LeftButton,
    )
    move = mouse_event(
        QEvent.Type.MouseMove,
        25 + distance,
        button=Qt.MouseButton.NoButton,
        buttons=Qt.MouseButton.LeftButton,
    )

    fairy.mousePressEvent(press)
    fairy.mouseMoveEvent(move)

    assert fairy.pos() == expected_position


def test_release_emits_click_only_after_a_press(fairy):
    clicks = []
    fairy.clicked.connect(lambda: clicks.append(True))
    press = mouse_event(
        QEvent.Type.MouseButtonPress,
        25,
        button=Qt.MouseButton.LeftButton,
        buttons=Qt.MouseButton.LeftButton,
    )
    release = mouse_event(
        QEvent.Type.MouseButtonRelease,
        25,
        button=Qt.MouseButton.LeftButton,
        buttons=Qt.MouseButton.NoButton,
    )

    fairy.mouseReleaseEvent(release)
    assert clicks == []

    fairy.mousePressEvent(press)
    fairy.mouseReleaseEvent(release)

    assert clicks == [True]


def test_move_to_screen_edge_snaps_to_the_nearer_edge(fairy):
    screen = QApplication.primaryScreen()
    assert screen is not None
    bounds = screen.availableGeometry()
    starting_y = bounds.y() + 50
    fairy.move(bounds.x() + 20, starting_y)

    fairy.move_to_screen_edge()

    assert fairy.pos() == QPoint(bounds.x(), starting_y)


def test_drag_release_snaps_without_emitting_a_click(fairy):
    screen = QApplication.primaryScreen()
    assert screen is not None
    bounds = screen.availableGeometry()
    clicks = []
    fairy.clicked.connect(lambda: clicks.append(True))
    fairy.move(bounds.x() + 100, bounds.y() + 100)
    press = mouse_event(
        QEvent.Type.MouseButtonPress,
        25,
        button=Qt.MouseButton.LeftButton,
        buttons=Qt.MouseButton.LeftButton,
    )
    move = mouse_event(
        QEvent.Type.MouseMove,
        35,
        button=Qt.MouseButton.NoButton,
        buttons=Qt.MouseButton.LeftButton,
    )
    release = mouse_event(
        QEvent.Type.MouseButtonRelease,
        35,
        button=Qt.MouseButton.LeftButton,
        buttons=Qt.MouseButton.NoButton,
    )

    fairy.mousePressEvent(press)
    fairy.mouseMoveEvent(move)
    fairy.mouseReleaseEvent(release)

    assert fairy.x() == bounds.x()
    assert clicks == []
