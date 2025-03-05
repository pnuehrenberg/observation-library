import warnings
from collections.abc import Callable, Sequence, Hashable
from typing import Literal, Optional, Type, Any

import ipyvuetify as v
import pandas as pd

from automated_scoring.dataset import AnnotatedDataset
from automated_scoring.dataset.utils import GroupIdentifier, IndividualIdentifier
from automated_scoring.data_structures import Trajectory
from automated_scoring.logging import set_logging_level

from interactive_table import InteractiveTable
from interactive_table.v_dialog import Dialog

from lazyfilter import lazy_filter

from .v_utils.v_render_settings_dialog import RenderSettingsDialog
from .v_utils.v_video_snippet_display import VideoSnippetDisplay
from .video_snippet import VideoSnippet


def is_same_observation(observation: pd.Series | dict[Hashable, Any], reference: pd.Series | dict[Hashable, Any]) -> bool:
    return all([observation[str(key)] == reference[str(key)] for key in observation])


def is_same_category(observation: pd.Series | dict[Hashable, Any], reference: pd.Series | dict[Hashable, Any]) -> bool:
    return observation["category"] == reference["category"]


class ObservationLibrary(InteractiveTable):
    def __init__(
        self,
        observations: pd.DataFrame | AnnotatedDataset,
        *,
        video_lookup: dict[GroupIdentifier, Sequence[str]],
        trajectory_lookup: Optional[dict[GroupIdentifier, dict[IndividualIdentifier, Trajectory]]] = None,
        num_keypoints: Optional[int] = None,
        filter_dependencies: Optional[dict[str, tuple[str, ...]]] = None,
        video_snippet_directory: str = "video_snippets",
        selected_observations_mode: Literal["selected", "dyad"] = "dyad",
        highlight_observations_mode: (
            Literal["selected", "category"] | Callable[[dict, dict], bool]
        ) = "selected",
        observations_transform: Optional[Callable[[pd.DataFrame], pd.DataFrame]] = None,
    ):
        if isinstance(observations, AnnotatedDataset):
            trajectory_lookup = {
                identifier: group.trajectories
                for identifier, group in observations
            }
            observations = observations.observations
        na_rows = observations.isna().any(axis=1)
        invalid_observations_error = ValueError(
            "observations must be a valid pandas DataFrame or Dataset"
        )
        if not isinstance(na_rows, pd.Series):
            raise invalid_observations_error
        if (num_na_rows := na_rows.sum()) > 0:
            set_logging_level().warning(f"Dropping {num_na_rows} rows with NaN values")
            observations_cleaned = observations[~na_rows].reset_index(drop=True)
            if not isinstance(observations_cleaned, pd.DataFrame):
                raise invalid_observations_error
            observations = observations_cleaned
        if observations_transform is not None:
            observations = observations_transform(observations)
        if trajectory_lookup is not None and num_keypoints is None:
            raise ValueError("specify number of trajectory keypoints")
        self.observations = observations
        self.render_settings_dialog = RenderSettingsDialog()
        self.render_settings = (
            self.render_settings_dialog.render_settings_input
        )  # shortcut
        if num_keypoints is not None:
            self.render_settings.available_keypoints = list(range(num_keypoints))
        if not isinstance(observations["category"].dtype, pd.CategoricalDtype):
            raise ValueError("observations must have a categorical 'category' column")
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
        self.video_snippet_dialog = Dialog(
            content=[self.video_snippet_display],
            actions=[
                self.video_snippet_display.video_container.loop_switch,
                v.Spacer(),
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
        self.render_settings_dialog.on_submit_callbacks.append(
            lambda: self.video_snippet_display.cut(
                video_snippet_dialog=self.video_snippet_dialog
            )
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
