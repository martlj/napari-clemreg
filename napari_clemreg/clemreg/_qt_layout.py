"""Shared Qt layout helpers for restructuring magicgui-built widgets to
match how Crick's AI-on-Demand napari plugin (aiod_napari) actually lays
out its own forms -- verified against its real source, not guessed: a
QScrollArea-bounded panel (so the dock panel can never grow past the
screen, no matter how much content it holds) and settings grouped into
independently-collapsible sections (so expanding one group only lays out
that group's own handful of widgets, not the whole form at once) rather
than one flat form with a single all-or-nothing "advanced" checkbox.

These helpers reparent a magicgui FunctionGui's *existing* field widgets
after construction, rather than rebuilding the form from scratch -- so a
widget module keeps using ``@magic_factory`` for parameter declaration,
type-based binding and the call button exactly as before; only the visual
grouping changes.
"""
from __future__ import annotations

from qtpy.QtCore import Qt
from qtpy.QtWidgets import QApplication, QScrollArea, QWidget
from superqt import QCollapsible


def extract_field_widget(gui, field_name: str) -> QWidget:
    """Return the Qt widget to move for one magicgui field: either the
    dedicated (label + control) row magicgui builds for a labeled field,
    or the field's own native widget if it has no separate label row
    (e.g. a CheckBox using inline ``text=`` instead of ``label=``).

    Confirmed directly: for a `layout='vertical'` Container, a labeled
    field's native widget is parented under its own per-field row QWidget
    (containing a QLabel plus the control); an inline-text field's native
    widget is parented directly under the Container's own native widget.
    Moving the row (not just the control) keeps the label attached.
    """
    field = getattr(gui, field_name)
    native = field.native
    parent = native.parent()
    return native if parent is gui.native else parent


def group_into_collapsible(gui, title: str, field_names: list, expanded: bool = False) -> QCollapsible:
    """Move a set of a FunctionGui's fields into one collapsible section.

    Reparents each named field's row widget out of the FunctionGui's own
    flat layout and into a new `QCollapsible`, which is then appended to
    the FunctionGui's layout in their place. The underlying magicgui
    `Widget` objects are untouched (still registered on `gui`, still
    readable via `.value`, still collected into the call button's
    arguments) -- only their visual parent changes.
    """
    section = QCollapsible(title)
    for name in field_names:
        section.addWidget(extract_field_widget(gui, name))
    if expanded:
        section.expand(animate=False)
    else:
        section.collapse(animate=False)
    gui.native.layout().addWidget(section)
    return section


_AUTO_SET_STYLESHEET = 'background-color: #ffe8a3;'


def mark_auto_set(field_widget, value) -> None:
    """Set a layer-typed field's value as the result of running a
    pipeline step (rather than a deliberate user choice), and highlight
    it amber to signal that -- distinct from show_error()'s red, which
    already means "something's wrong" elsewhere in this plugin; this
    just means "review if this isn't what you wanted".

    Explicitly refreshes the field's own choices first: a magicgui
    CategoricalWidget's `.value` setter raises ValueError for a value
    not already in `.choices` (confirmed directly, no fallback), and
    `value` here is typically a layer that was only just added to the
    viewer -- relying on some other, external mechanism to have already
    refreshed choices by this point (e.g. napari's dock-widget-level
    layers.events wiring, whose own timing/ordering relative to this
    call isn't guaranteed) is fragile; reset_choices() here is cheap and
    makes this call self-sufficient regardless.
    """
    field_widget.reset_choices()
    field_widget.value = value
    field_widget.native.setStyleSheet(_AUTO_SET_STYLESHEET)


def clear_highlight_on_user_select(field_widget) -> None:
    """Revert a field's auto-set highlight the moment the user actually
    interacts with it. Connected to the underlying Qt widget's
    `activated` signal, which fires only on genuine user interaction --
    unlike magicgui's own `.changed`, which fires identically for a
    programmatic `.value = ...` assignment (mark_auto_set's own) and
    would immediately undo its own highlight if wired there instead.
    """
    field_widget.native.activated.connect(lambda *_: field_widget.native.setStyleSheet(''))


def wrap_in_scroll_area(widget: QWidget, max_height_fraction: float = 0.85) -> QScrollArea:
    """Wrap `widget` in a QScrollArea so the dock panel this becomes has a
    bounded height regardless of how much content it holds, instead of
    growing past the screen (the prior fix for that -- calling
    `adjustSize()` after every visibility toggle -- only made the panel
    shrink back down correctly; it never stopped it growing past the
    screen in the first place, since nothing bounded its maximum size).
    """
    scroll = QScrollArea()
    scroll.setWidget(widget)
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

    screen = QApplication.primaryScreen()
    if screen is not None:
        available_height = screen.availableGeometry().height()
        scroll.setMaximumHeight(int(available_height * max_height_fraction))

    return scroll
