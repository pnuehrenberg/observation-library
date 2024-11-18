import ipyvuetify as v
import pandas as pd
from typing import Type, Literal
from collections.abc import Callable

from lazyfilter import lazy_filter
from interactive_table import InteractiveTable
from interactive_table.v_callbacks_button import CallbacksButton
from interactive_table.v_dialog import Dialog

from .v_utils.v_render_settings_dialog import RenderSettingsDialog
from .v_utils.v_video_snippet_display import VideoSnippetDisplay
from .video_snippet import VideoSnippet


def is_same_observation(observation, reference):
    return all([observation[key] == reference[key] for key in observation])


def is_same_category(observation, reference):
    return observation["category"] == reference["category"]


class ObservationLibrary(InteractiveTable):
    def __init__(
        self,
        observations,
        *,
        video_lookup,
        trajectory_lookup=None,
        filter_dependencies=None,
        video_snippet_directory="video_snippets",
        selected_observations_mode: Literal["selected", "dyad"] = "dyad",
        highlight_observations_mode: (
            Literal["selected", "category"] | Callable[[dict, dict], bool]
        ) = "selected",
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
        self.reload_video_snippet.callbacks = [
            lambda: self.video_snippet_display.cut(
                video_snippet_dialog=self.video_snippet_dialog
            )
        ]
        self.video_snippet_dialog.on_open_callbacks = (
            self.reload_video_snippet.callbacks
        )
        self.video_lookup = video_lookup
        self.trajectory_lookup = trajectory_lookup
        self.selected_observations_mode: Literal["selected", "dyad"] = (
            selected_observations_mode
        )
        self.highlight_observations_mode: (
            Literal["selected", "category"] | Callable[[dict, dict], bool]
        ) = highlight_observations_mode
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
        if self.selected_observations_mode == "selected":
            observations = [observation]
        else:
            selection: dict[str | Type[pd.Index], tuple] = {
                "group": ("selected_values", (observation["group"],)),
                "actor": ("selected_values", (observation["actor"],)),
            }
            if "recipient" in observation:
                selection["recipient"] = (
                    "selected_values",
                    (observation["recipient"],),
                )
            observations = (
                lazy_filter(self.observations)
                .update(selection)
                .to_dict(orient="records")
            )
        highlight = []
        for idx, selected_observation in enumerate(observations):
            if self.highlight_observations_mode == "selected":
                if not is_same_observation(selected_observation, observation):
                    continue
                highlight.append(idx)
            elif self.highlight_observations_mode == "category":
                if not is_same_category(selected_observation, observation):
                    continue
                highlight.append(idx)
            elif self.highlight_observations_mode(selected_observation, observation):
                highlight.append(idx)
        self.video_snippet.observation_data = {
            "observations": observations,
            "highlight": highlight,
        }
        self.video_snippet_dialog.dialog = True
