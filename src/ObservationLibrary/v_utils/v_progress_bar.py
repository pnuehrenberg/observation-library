import ipyvuetify as v
import traitlets


class ProgressBar(v.VuetifyTemplate):  # type: ignore
    template_file = (__file__, "templates/ProgressBar.vue")

    value = traitlets.Any().tag(sync=True)
    label = traitlets.Unicode().tag(sync=True)
    class_ = traitlets.Unicode().tag(sync=True)
    style_ = traitlets.Unicode().tag(sync=True)

    def show(self):
        self.class_ = self.class_.replace("d-none", "")

    def hide(self):
        if "d-none" in self.class_:
            return
        self.class_ = f"{self.class_} d-none"
