import hashlib
import json
import os
from threading import current_thread

import cv2
import imageio
import matplotlib.pyplot as plt
import numpy as np
import pyTrajectory.features as ptf
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.collections import LineCollection
from PIL import Image
from pyTrajectory.data_structures.utils import OutOfInterval
from pyTrajectory.visualization import get_trajectory_range

from .multi_video_capture import MultiVideoCapture
from .render_settings import RenderSettings


def hash_dict(dictionary):
    return hashlib.sha1(
        json.dumps(dictionary, sort_keys=True).encode("utf-8")
    ).hexdigest()


def figure_to_numpy(fig):
    fig.patch.set_facecolor((0, 0, 0, 0))
    for ax in fig.get_axes():
        ax.axis("off")

    canvas = FigureCanvasAgg(fig)
    canvas.draw()

    *_, width, height = canvas.figure.bbox.bounds
    width, height = int(width), int(height)

    buffer = canvas.buffer_rgba()
    img = np.frombuffer(buffer, dtype=np.uint8)
    return img.reshape(height, width, 4)


def to_rgb(image, color=(255, 255, 255)):
    """
    http://stackoverflow.com/a/9459208/284318
    """
    image.load()
    background = Image.new("RGB", image.size, color)
    background.paste(image, mask=image.split()[3])
    return background


def adjust_lightness(color, amount):
    import colorsys

    import matplotlib.colors as mc

    try:
        c = mc.cnames[color]
    except KeyError:
        c = color
    c = colorsys.rgb_to_hls(*mc.to_rgb(c))
    return colorsys.hls_to_rgb(c[0], max(0, min(1, amount * c[1])), c[2])


def closest_divisible(number: float, divisor: int) -> int:
    remainder = number % divisor
    closest_smaller_number = number - remainder
    closest_greater_number = (number + divisor) - remainder
    if (number - closest_smaller_number) > (closest_greater_number - number):
        return int(closest_greater_number)
    return int(closest_smaller_number)


def get_roi(trajectories, individuals, interval):
    x_lim = []
    y_lim = []
    for individual in individuals:
        trajectory = trajectories[individual].slice_window(
            start=interval[0], stop=interval[1]
        )
        if len(trajectory) == 0:
            continue
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
        video_files,
        *,
        start,
        stop,
        render_settings=None,
        video_server_directory=".",
    ):
        self.output_files = []
        self._cap = None
        self._video_files = None
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
    def frame_width(self):
        width = self.video_width
        if (padded_roi := self.padded_roi) is None:
            return width
        x1, x2 = padded_roi[0], padded_roi[2]
        if x1 < 0:
            raise ValueError("invalid ROI")
        if x2 > width - 1:
            raise ValueError("invalid ROI")
        return x2 - x1 + 1

    @property
    def frame_height(self):
        height = self.video_height
        if (padded_roi := self.padded_roi) is None:
            return height
        y1, y2 = padded_roi[1], padded_roi[3]
        if y1 < 0:
            raise ValueError("invalid ROI")
        if y2 > height - 1:
            raise ValueError("invalid ROI")
        return y2 - y1 + 1

    @property
    def _scale(self):
        return min(
            self.render_settings.max_render_height / self.frame_height,
            self.render_settings.max_render_width / self.frame_width,
        )

    @property
    def scaled_width(self):
        return closest_divisible(
            self.frame_width * self._scale, self.render_settings.macro_block_size
        )

    @property
    def scaled_height(self):
        return closest_divisible(
            self.frame_height * self._scale, self.render_settings.macro_block_size
        )

    @property
    def scale(self):
        return (
            self.scaled_width / self.frame_width,
            self.scaled_height / self.frame_height,
        )

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
        dsize = (self.scaled_width, self.scaled_height)

        padded_roi = self.padded_roi
        overlay_scale = 1
        if padded_roi is not None:
            overlay_scale = self.video_height / (padded_roi[3] - padded_roi[1])

        self.cap.set(cv2.CAP_PROP_POS_FRAMES, int(self.padded_start))
        count = 0
        writer = imageio.get_writer(
            self.output_file,
            fps=self.cap.get(cv2.CAP_PROP_FPS),
            macro_block_size=self.render_settings.macro_block_size,
        )
        thread = current_thread()
        success = True

        # dpi = dsize[1] * 150 / self.video_height
        # dpi_factor = self.video_height / dsize[1]
        fig = plt.figure(figsize=(dsize[0] / 300, dsize[1] / 300), dpi=300)
        ax = fig.add_axes((0, 0, 1, 1))

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
            if padded_roi is not None:
                frame = frame[
                    padded_roi[1] : (padded_roi[3] + 1),
                    padded_roi[0] : (padded_roi[2] + 1),
                ]
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)
            frame = cv2.resize(frame, dsize=dsize)

            # overlay plotting
            ax.clear()
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
                        keypoints = ptf.keypoints(
                            trajectory,
                            keypoints=tuple(self.render_settings.keypoints),
                        )
                        segments = ptf.posture_segments(
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
                            lw=2.5 * overlay_scale,
                            transform=ax.transAxes,
                            zorder=zorder,
                        )
                    )
                    ax.scatter(
                        *keypoints.T,
                        s=25 * (overlay_scale**2),
                        c=color,
                        lw=0,
                        transform=ax.transAxes,
                        zorder=zorder,
                    )

            if not success:
                break

            overlay = figure_to_numpy(fig)

            overlay = Image.fromarray(overlay)
            frame = Image.fromarray(frame)
            frame.paste(overlay, (0, 0), overlay)
            frame = np.asarray(to_rgb(frame))

            writer.append_data(frame)

            count += 1
            if progress_bar is not None:
                progress_bar.value = 100 * count / num_frames
        plt.close(fig)
        writer.close()
        if not success and os.path.exists(self.output_file):
            os.remove(self.output_file)
        return success
