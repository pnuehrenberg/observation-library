import ipyvuetify as v
from lazyfilter import lazy_filter
from vTableApp.v_callbacks_button import CallbacksButton
from vTableApp.v_data_table import DataTable
from vTableApp.v_dialog import Dialog

from .v_utils.v_render_settings_dialog import RenderSettingsDialog
from .v_utils.v_video_snippet_display import VideoSnippetDisplay
from .video_snippet import VideoSnippet


class ObservationLibrary(DataTable):
    def __init__(
        self,
        observations,
        *,
        video_lookup,
        trajectory_lookup=None,
        filter_dependencies=None,
        video_snippet_directory="video_snippets",
    ):
        self.observations = observations
        self.render_settings_dialog = RenderSettingsDialog()
        self.render_settings = (
            self.render_settings_dialog.render_settings_input
        )  # shortcut
        self.render_settings.categories = observations[
            "category"
        ].dtype.categories.tolist()
        self.video_snippet = VideoSnippet(
            [],
            start=0,
            stop=0,
            video_server_directory=video_snippet_directory,
            render_settings=self.render_settings,
        )
        self.video_snippet_display = VideoSnippetDisplay(self.video_snippet)
        self.reload_video_snippet = CallbacksButton(
            icon=True,
            children=[v.Icon(children=["mdi-replay"])],
            callbacks=[lambda: self.video_snippet_display.cut()],
        )
        self.video_snippet_dialog = Dialog(
            content=[self.video_snippet_display],
            actions=[
                self.video_snippet_display.video_container.loop_switch,
                v.Spacer(),
                self.reload_video_snippet,
                self.render_settings_dialog,
            ],
            open_button="",
            open_button_icon=True,
            confirm_button="",
            on_close_callbacks=[
                lambda: self.video_snippet_display.interrupt(),
                lambda: self.video_snippet_display.video_container.set_looping(False)
                or True,
            ],
        )
        self.video_snippet_dialog.on_open_callbacks = [
            lambda: self.video_snippet_display.cut(
                video_snippet_dialog=self.video_snippet_dialog
            )
        ]
        self.video_lookup = video_lookup
        self.trajectory_lookup = trajectory_lookup

        super().__init__(
            self.observations,
            filter_dependencies=filter_dependencies,
            show_index=True,
            actions={"mdi-play-circle-outline": self.open_video_snippet_dialog},
            action_dialogs=[self.video_snippet_dialog],
        )

    def set_observation(self, observation):
        if self.trajectory_lookup is not None:
            self.video_snippet.trajectories = self.trajectory_lookup[
                observation["group"]
            ]
        self.video_snippet.video_files = self.video_lookup[observation["group"]]
        self.video_snippet.start = observation["start"]
        self.video_snippet.stop = observation["stop"]

    def open_video_snippet_dialog(self, observation):
        self.set_observation(observation)
        # snippet.observation_data = {
        #     "observations": [observation],
        #     "highlight": [0],
        # }
        observations = lazy_filter(self.observations).update(
            {
                "group": ("selected_values", [observation["group"]]),
                "actor": ("selected_values", ["resident"]),
                "recipient": ("selected_values", ["intruder"]),
            }
        )
        # highlight = []
        # try:
        #     highlight = [observations.index.tolist().index(observation["index"])]
        # except ValueError:
        #     pass
        highlight = [
            idx
            for idx, row in observations.iterrows()
            if row["category"] == observation["category"]
        ]
        self.video_snippet.observation_data = {
            "observations": observations.to_dict(orient="records"),
            "highlight": highlight,
        }
        self.video_snippet_dialog.dialog = True
