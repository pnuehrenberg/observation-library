import ipyvuetify as v
import ipywidgets as widgets
import traitlets
from vTableApp.v_bounded_input import BoundedInput

from ..render_settings import RenderSettings
from .v_color_picker import ColorPicker


class RenderSettingsInput(v.VuetifyTemplate, RenderSettings):  # type: ignore
    template_file = (__file__, "templates/RenderSettingsInput.vue")

    tab = traitlets.Int(default_value=0).tag(sync=True)

    interval_padding_input = traitlets.Any().tag(
        sync=True, **widgets.widget_serialization
    )
    roi_padding_input = traitlets.Any().tag(sync=True, **widgets.widget_serialization)
    max_render_width_input = traitlets.Any().tag(
        sync=True, **widgets.widget_serialization
    )
    max_render_height_input = traitlets.Any().tag(
        sync=True, **widgets.widget_serialization
    )

    actor_color_input = traitlets.Any().tag(sync=True, **widgets.widget_serialization)
    recipient_color_input = traitlets.Any().tag(
        sync=True, **widgets.widget_serialization
    )
    other_color_input = traitlets.Any().tag(sync=True, **widgets.widget_serialization)

    text_color_input = traitlets.Any().tag(sync=True, **widgets.widget_serialization)
    box_color_input = traitlets.Any().tag(sync=True, **widgets.widget_serialization)
    highlight_color_input = traitlets.Any().tag(
        sync=True, **widgets.widget_serialization
    )
    override_highlight_color_input = traitlets.Any().tag(
        sync=True, **widgets.widget_serialization
    )
    categories = traitlets.List(default_value=[]).tag(sync=True)
    selected_category = traitlets.Any().tag(sync=True)
    overridden_highlight = traitlets.Bool().tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        RenderSettings.__init__(self)

        self.interval_padding_input = BoundedInput(
            value=self.interval_padding,
            min=0,
            max=60,
            step=0.1,
            label="Interval padding (seconds)",
        )

        self.roi_padding_input = BoundedInput(
            value=self.roi_padding, min=0, max=1000, step=1, label="ROI padding (px)"
        )
        self.max_render_width_input = BoundedInput(
            value=self.max_render_width, min=256, max=5000, step=1, label="Width (px)"
        )
        self.max_render_height_input = BoundedInput(
            value=self.max_render_height, min=256, max=5000, step=1, label="Height (px)"
        )

        self.actor_color_input = ColorPicker(color=self.actor_color, label="Actor")
        self.recipient_color_input = ColorPicker(
            color=self.recipient_color, label="Recipient"
        )
        self.other_color_input = ColorPicker(color=self.other_color, label="Others")

        self.text_color_input = ColorPicker(color=self.text_color, label="Text")
        self.box_color_input = ColorPicker(color=self.box_color, label="Box")
        self.highlight_color_input = ColorPicker(
            color=self.highlight_color, label="Highlight"
        )
        self.override_highlight_color_input = ColorPicker(color=self.highlight_color)

        traitlets.link(
            (self, "interval_padding"),
            ((self.interval_padding_input, "value")),
            transform=(float, float),
        )
        traitlets.link(
            (self, "max_render_width"),
            ((self.max_render_width_input, "value")),
            transform=(int, int),
        )
        traitlets.link(
            (self, "max_render_height"),
            ((self.max_render_height_input, "value")),
            transform=(int, int),
        )
        traitlets.link(
            (self, "roi_padding"),
            ((self.roi_padding_input, "value")),
            transform=(int, int),
        )
        traitlets.link((self, "actor_color"), (self.actor_color_input, "color"))
        traitlets.link((self, "recipient_color"), (self.recipient_color_input, "color"))
        traitlets.link((self, "other_color"), (self.other_color_input, "color"))
        traitlets.link((self, "text_color"), (self.text_color_input, "color"))
        traitlets.link((self, "box_color"), (self.box_color_input, "color"))
        traitlets.link((self, "highlight_color"), (self.highlight_color_input, "color"))

        self.override_highlight_color_input.observe(
            self._on_override_highlight_color_change, "color"
        )

    @traitlets.observe("highlight_color")
    def _on_highlight_color_change(self, change):
        if change["old"] == (color := change["new"]):
            return
        if self.selected_category is not None and not self.overridden_highlight:
            self.override_highlight_color_input.color = color

    @traitlets.observe("selected_category")
    def _on_selected_category_change(self, change):
        if change["old"] == (category := change["new"]):
            return
        if category is None:
            return
        if category not in self.override_highlight_color:
            self.override_highlight_color_input.color = self.highlight_color
            self.overridden_highlight = False
            return
        color = self.override_highlight_color[category]
        self.override_highlight_color_input.color = color
        self.overridden_highlight = color != self.highlight_color

    @traitlets.observe("override_highlight_color")
    def _on_override_highlight_dict_change(self, change):
        if change["new"] == {}:
            self.vue_reset_override_highlight_color()

    def _on_override_highlight_color_change(self, change):
        if change["old"] == change["new"]:
            return
        if self.selected_category is None:
            return
        color = change["new"]
        overridden = color != self.highlight_color
        if overridden:
            self.override_highlight_color[self.selected_category] = color
        elif self.selected_category in self.override_highlight_color:
            self.override_highlight_color.pop(self.selected_category)
        self.overridden_highlight = overridden

    def vue_reset_override_highlight_color(self, *args):
        if self.selected_category is None:
            return
        self.override_highlight_color_input.color = self.highlight_color
