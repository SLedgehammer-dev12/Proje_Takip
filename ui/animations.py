from PySide6.QtCore import (
    QPropertyAnimation,
    QEasingCurve,
    QPoint,
    QSize,
    QObject,
)

# Property is removed as it is unused
from PySide6.QtWidgets import QGraphicsOpacityEffect, QWidget


class FadeAnimation:
    """Helper class for fade in/out animations"""

    @staticmethod
    def fade_in(widget: QWidget, duration: int = 300):
        """Fade in a widget"""
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)

        animation = QPropertyAnimation(effect, b"opacity")
        animation.setDuration(duration)
        animation.setStartValue(0.0)
        animation.setEndValue(1.0)
        animation.setEasingCurve(QEasingCurve.InOutQuad)
        animation.start()

        # Store reference to prevent garbage collection
        widget._fade_animation = animation
        return animation

    @staticmethod
    def fade_out(widget: QWidget, duration: int = 300):
        """Fade out a widget"""
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)

        animation = QPropertyAnimation(effect, b"opacity")
        animation.setDuration(duration)
        animation.setStartValue(1.0)
        animation.setEndValue(0.0)
        animation.setEasingCurve(QEasingCurve.InOutQuad)
        animation.start()

        widget._fade_animation = animation
        return animation


class SlideAnimation:
    """Helper class for slide animations"""

    @staticmethod
    def slide_in(widget: QWidget, direction: str = "left", duration: int = 300):
        """
        Slide in a widget from specified direction
        direction: 'left', 'right', 'top', 'bottom'
        """
        animation = QPropertyAnimation(widget, b"pos")
        animation.setDuration(duration)
        animation.setEasingCurve(QEasingCurve.OutCubic)

        current_pos = widget.pos()

        if direction == "left":
            start_pos = QPoint(current_pos.x() - 100, current_pos.y())
        elif direction == "right":
            start_pos = QPoint(current_pos.x() + 100, current_pos.y())
        elif direction == "top":
            start_pos = QPoint(current_pos.x(), current_pos.y() - 100)
        else:  # bottom
            start_pos = QPoint(current_pos.x(), current_pos.y() + 100)

        animation.setStartValue(start_pos)
        animation.setEndValue(current_pos)
        animation.start()

        widget._slide_animation = animation
        return animation


class AnimationHelper:
    """General animation helper utilities"""

    @staticmethod
    def smooth_resize(widget: QWidget, target_size: QSize, duration: int = 200):
        """Smoothly resize a widget"""
        animation = QPropertyAnimation(widget, b"size")
        animation.setDuration(duration)
        animation.setStartValue(widget.size())
        animation.setEndValue(target_size)
        animation.setEasingCurve(QEasingCurve.InOutQuad)
        animation.start()

        widget._resize_animation = animation
        return animation

    @staticmethod
    def create_property_animation(
        target: QObject,
        property_name: bytes,
        start_value,
        end_value,
        duration: int = 300,
        easing: QEasingCurve.Type = QEasingCurve.InOutQuad,
    ):
        """Create a generic property animation"""
        animation = QPropertyAnimation(target, property_name)
        animation.setDuration(duration)
        animation.setStartValue(start_value)
        animation.setEndValue(end_value)
        animation.setEasingCurve(easing)
        return animation


# Animation duration constants
class AnimationDuration:
    """Standard animation durations in milliseconds"""

    FAST = 150
    NORMAL = 300
    SLOW = 500
