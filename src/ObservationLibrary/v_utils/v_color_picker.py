import ipyvuetify as v
import traitlets


class ColorPicker(v.VuetifyTemplate):  # type: ignore
    template_file = (__file__, "templates/ColorPicker.vue")

    color = traitlets.Any(default_value="#FFFFFF").tag(sync=True)
    label = traitlets.Unicode().tag(sync=True)
