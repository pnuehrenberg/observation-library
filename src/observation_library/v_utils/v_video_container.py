import ipyvuetify as v
import traitlets


class VideoContainer(v.VuetifyTemplate):  # type: ignore
    template_file = (__file__, "templates/VideoContainer.vue")

    url = traitlets.Unicode().tag(sync=True)
    loop = traitlets.Bool().tag(sync=True)
    autoplay = traitlets.Bool().tag(sync=True)
    class_ = traitlets.Unicode().tag(sync=True)
    style_ = traitlets.Unicode().tag(sync=True)

    def __init__(
        self, *args, url, loop=False, autoplay=False, class_="", style_="", **kwargs
    ):
        self.url = url
        self.loop = loop
        self.autoplay = autoplay
        self.class_ = class_
        self.style_ = style_
        self.loop_switch = v.Switch(
            v_model=loop,
            label="Looped playback",
            hide_details=True,
            class_="pa-0 pl-2 ma-0",
        )
        traitlets.link((self, "loop"), (self.loop_switch, "v_model"))
        super().__init__(*args, **kwargs)

    def set_looping(self, loop):
        self.loop = loop
