import os
from collections.abc import Sequence
from pathlib import Path
from threading import current_thread

import cv2
import imageio
import matplotlib.pyplot as plt
import vassi.features as asf
from matplotlib.collections import LineCollection
from vassi.data_structures.utils import OutOfInterval
from vassi.utils import hash_dict
from vassi.visualization import adjust_lightness, get_trajectory_range

from .multi_video_capture import MultiVideoCapture
from .render_settings import RenderSettings
from .utils import ImageOverlay, crop_and_scale


def get_roi(trajectories, individuals, interval):
    x_lim = []
    y_lim = []
    for individual in individuals:
        trajectory = trajectories[individual]
        if len(trajectory) == 0:
            continue
        first, last = trajectory.timestamps.min(), trajectory.timestamps.max()
        trajectory = trajectory.slice_window(
            start=max(first, interval[0]),
            stop=min(last, interval[1]),
            interpolate=False,
            copy=False,
        )
        x_lim_, y_lim_ = get_trajectory_range(trajectory)
        x_lim.append(x_lim_)
        y_lim.append(y_lim_)
    if len(x_lim) == 0:
        return None
    x_lim = min([x[0] for x in x_lim]), max([x[1] for x in x_lim])
    y_lim = min([y[0] for y in y_lim]), max([y[1] for y in y_lim])
    roi = (
        max(0, x_lim[0]),
        max(0, y_lim[0]),
        x_lim[1],
        y_lim[1],
    )
    return list(map(lambda v: int(round(v)), roi))


class VideoSnippet:
    def __init__(
        self,
        video_files: Sequence[str | Path],
        *,
        start,
        stop,
        render_settings=None,
        video_server_directory=".",
    ):
        self.output_files = []
        self._cap = None
        self._video_files: Sequence[str | Path] | None = None
        if len(video_files) > 0:
            self.video_files = video_files
        self.render_settings = (
            render_settings if render_settings is not None else RenderSettings()
        )
        self.start = start
        self.stop = stop
        self.trajectories = {}
        self.observation_data = {}
        self.video_server_directory = video_server_directory

    @property
    def video_files(self):
        return self._video_files

    @video_files.setter
    def video_files(self, video_files):
        self._cap = MultiVideoCapture(video_files)
        self._video_files = video_files

    @property
    def cap(self):
        if self._cap is None:
            raise ValueError("not initialized")
        return self._cap

    @property
    def padded_start(self):
        return max(0, self.start - self.render_settings.interval_padding * self.cap.fps)

    @property
    def padded_stop(self):
        return min(
            self.cap.total_frames,
            self.stop + self.render_settings.interval_padding * self.cap.fps,
        )

    @property
    def roi(self):
        if self.trajectories == {} or not self.render_settings.crop_roi:
            return None
        individuals = []
        if "observations" in self.observation_data:
            for observation in self.observation_data["observations"]:
                individuals.append(observation["actor"])
                if "recipient" not in observation:
                    continue
                individuals.append(observation["recipient"])
        return get_roi(
            self.trajectories, set(individuals), (self.padded_start, self.padded_stop)
        )

    @property
    def padded_roi(self):
        if self.roi is None:
            return None
        if not all(map(lambda value: isinstance(value, int), self.roi)):
            raise ValueError("Invalid ROI with non-int values")
        padding = self.render_settings.get_roi_padding()
        return (
            max(0, self.roi[0] - padding),
            max(0, self.roi[1] - padding),
            min(self.video_width - 1, self.roi[2] + padding),
            min(self.video_height - 1, self.roi[3] + padding),
        )

    @property
    def video_width(self):
        return int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))

    @property
    def video_height(self):
        return int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    @property
    def output_file(self):
        if self.video_files is None:
            raise ValueError("specify video_files")
        name, ext = os.path.splitext(os.path.basename(self.video_files[0]))
        identifier = {
            "name": name,
            "ext": ext,
            "video_files": self.video_files,
            "start": int(self.padded_start),
            "stop": int(self.padded_stop),
            "roi": self.padded_roi,
            "trajectories": list(self.trajectories.keys()),
            "observation_data": self.observation_data,
            "render_settings": self.render_settings.config(),
        }
        identifier = hash_dict(identifier)
        file_name = f"{name}_{identifier}{ext}"
        return os.path.join(self.video_server_directory, file_name)

    def cut(
        self,
        *,
        progress_bar=None,
    ):
        if os.path.exists(self.output_file):
            if progress_bar is not None:
                progress_bar.value = 100
            return True
        if not os.path.exists(self.video_server_directory):
            os.makedirs(self.video_server_directory, exist_ok=True)
        num_frames = int(self.padded_stop) - int(self.padded_start)
        padded_roi = self.padded_roi
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, int(self.padded_start))
        count = 0
        writer = imageio.get_writer(
            self.output_file,
            fps=self.cap.get(cv2.CAP_PROP_FPS),
            macro_block_size=self.render_settings.macro_block_size,
        )
        thread = current_thread()
        success = True

        overlay = None
        actor = None
        recipient = None
        if (
            "observations" in self.observation_data
            and len(self.observation_data["observations"]) > 0
        ):
            # maybe warn if they are not all consistent
            actor = self.observation_data["observations"][0]["actor"]
            recipient = self.observation_data["observations"][0]["recipient"]

        while count < num_frames:
            if getattr(thread, "interrupt", False):
                success = False
                break
            ret, frame = self.cap.read()
            if not ret or frame is None:
                success = False
                break
            frame_cropped, frame_scaled = crop_and_scale(
                frame,
                roi=padded_roi,
                max_width=self.render_settings.max_render_width,
                max_height=self.render_settings.max_render_height,
                block_size=self.render_settings.macro_block_size,
            )
            frame_scaled = cv2.cvtColor(frame_scaled, cv2.COLOR_BGR2RGBA)
            if overlay is None:
                overlay = ImageOverlay(
                    original_size=frame.shape[:2][::-1],
                    crop_size=frame_cropped.shape[:2][::-1],
                    render_size=frame_scaled.shape[:2][::-1],
                )

            # overlay plotting
            ax = overlay.get_axes()
            if "observations" in self.observation_data:
                observations = self.observation_data["observations"]
                frame_idx = self.cap.frame - 1  # reading increments to the next
                highlight = (
                    []
                    if "highlight" not in self.observation_data
                    else self.observation_data["highlight"]
                )
                highlight_color = None

                for idx, observation in enumerate(observations):
                    if (
                        frame_idx < observation["start"]
                        or frame_idx > observation["stop"]
                    ):
                        continue
                    highlighted = self.render_settings.highlight and idx in highlight
                    category = observation["category"]
                    if highlighted:
                        try:
                            highlight_color = (
                                self.render_settings.override_highlight_color[category]
                            )
                        except KeyError:
                            highlight_color = self.render_settings.highlight_color
                    if not self.render_settings.draw_label:
                        continue
                    ax.text(
                        0.5,
                        0.1,
                        category,
                        ha="center",
                        va="center",
                        color=(
                            highlight_color
                            if highlighted
                            else self.render_settings.text_color
                        ),
                        fontsize=12,
                        bbox=dict(
                            boxstyle="round",
                            lw=1 if highlighted else 0,
                            ec=(
                                highlight_color
                                if highlighted
                                else self.render_settings.box_color
                            ),
                            fc=(
                                *adjust_lightness(
                                    (
                                        highlight_color
                                        if highlighted
                                        else self.render_settings.box_color
                                    ),
                                    1.5,
                                ),
                                0.5,
                            ),
                        ),
                        zorder=3,
                        transform=ax.transAxes,
                    )

                for individual, trajectory in self.trajectories.items():
                    if not self.render_settings.draw_trajectories:
                        break
                    try:
                        trajectory = trajectory.slice_window(frame_idx, frame_idx)
                    except OutOfInterval:
                        continue
                    try:
                        keypoints = asf.keypoints(
                            trajectory,
                            keypoints=tuple(self.render_settings.keypoints),
                        )
                        segments = asf.posture_segments(
                            trajectory,
                            keypoint_pairs=tuple(self.render_settings.get_segments()),
                        )
                    except IndexError as e:
                        print(e, flush=True)
                        success = False
                        break
                    keypoints = keypoints[0]
                    segments = segments[0]  # only one timestamp

                    if padded_roi is None:
                        # simple case without roi
                        keypoints = keypoints / (self.video_width, self.video_height)
                        segments = segments / (self.video_width, self.video_height)
                    else:
                        keypoints = (keypoints - padded_roi[:2]) / (
                            padded_roi[2] - padded_roi[0],
                            padded_roi[3] - padded_roi[1],
                        )
                        segments = (segments - padded_roi[:2]) / (
                            padded_roi[2] - padded_roi[0],
                            padded_roi[3] - padded_roi[1],
                        )
                    keypoints[..., 1] = 1 - keypoints[..., 1]
                    segments[..., 1] = 1 - segments[..., 1]

                    color = self.render_settings.other_color
                    zorder = 0
                    if individual == actor:
                        if (
                            highlight_color is None
                            or not self.render_settings.apply_highlight_color_to_actor()
                        ):
                            color = self.render_settings.actor_color
                        else:
                            color = highlight_color
                        zorder = 2
                    elif individual == recipient:
                        if (
                            highlight_color is None
                            or not self.render_settings.apply_highlight_color_to_recipient()
                        ):
                            color = self.render_settings.recipient_color
                        else:
                            color = highlight_color
                        zorder = 1

                    ax.add_collection(
                        LineCollection(
                            segments,
                            color=color,
                            lw=overlay.get_pixel_size(
                                self.render_settings.overlay_size / 2
                            ),
                            transform=ax.transAxes,
                            zorder=zorder,
                        )
                    )
                    ax.scatter(
                        *keypoints.T,
                        s=overlay.get_pixel_size(self.render_settings.overlay_size)
                        ** 2,
                        c=color,
                        lw=0,
                        transform=ax.transAxes,
                        zorder=zorder,
                    )
            if not success:
                break
            writer.append_data(overlay.draw_overlay(frame_scaled))
            count += 1
            if progress_bar is not None:
                progress_bar.value = 100 * count / num_frames
        if overlay is not None:
            plt.close(overlay.fig)
        writer.close()
        if not success and os.path.exists(self.output_file):
            os.remove(self.output_file)
        return success
