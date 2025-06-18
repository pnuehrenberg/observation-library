from typing import Tuple

import cv2
import numpy as np


class MultiVideoCapture:
    """
    A class for managing multiple video captures as a single unified stream.

    Attributes:
        video_captures: A list of OpenCV VideoCapture objects.
        width: The width of the videos.
        height: The height of the videos.
        fps: The frame rate of the videos.
        total_frames: The total number of frames across all videos.
        frames: A list of the number of frames in each video.
        cumulative_frames: A list of the cumulative frame counts for each video.
        frame: The current frame index.
        active_cap_idx: The index of the currently active video capture.

    Methods:
        get(prop_id): Returns the value of the specified property.
        set(prop_id, value): Sets the value of the specified property.
        read(): Reads the next frame from the active video capture.
    """

    def __init__(self, video_paths):
        """
        Initializes the MultiVideoCapture object.

        Args:
            video_paths: A list of paths to the video files.

        Raises:
            ValueError: If a video file cannot be opened or if the videos have different dimensions or frame rates.
        """
        if len(video_paths) == 0:
            raise ValueError("Specify at least one video")

        self.video_captures = []
        self._width, self._height, self._fps = None, None, None
        self.total_frames = 0
        self.frames = []
        self.cumulative_frames = []  # Cumulative frame count for each video

        for path in video_paths:
            cap = cv2.VideoCapture(str(path))
            if not cap.isOpened():
                raise ValueError(f"Error opening video: {path}")

            # Validate dimensions and FPS
            width, height, fps = (
                int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                cap.get(cv2.CAP_PROP_FPS),
            )
            if self._width is None:
                self._width, self._height, self._fps = width, height, fps
            else:
                if width != self.width or height != self.height or fps != self.fps:
                    raise ValueError("All videos must have the same dimensions and FPS")

            self.video_captures.append(cap)
            frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.total_frames += frames
            self.frames.append(frames)
            self.cumulative_frames.append(self.total_frames)

        self.frame = 0
        self.active_cap_idx = 0

    @property
    def width(self) -> int:
        if self._width is None:
            raise ValueError("not initialized")
        return self._width

    @property
    def height(self) -> int:
        if self._height is None:
            raise ValueError("not initialized")
        return self._height

    @property
    def fps(self) -> float:
        if self._fps is None:
            raise ValueError("not initialized")
        return self._fps

    def get(self, prop_id: int) -> int | float:
        """
        Gets the value of the specified property.

        Args:
            prop_id: The ID of the property to get.

        Returns:
            The value of the property.

        Raises:
            ValueError: If the property ID is not supported.
        """
        if prop_id == cv2.CAP_PROP_FRAME_WIDTH:
            return self.width
        elif prop_id == cv2.CAP_PROP_FRAME_HEIGHT:
            return self.height
        elif prop_id == cv2.CAP_PROP_FPS:
            return self.fps
        elif prop_id == cv2.CAP_PROP_FRAME_COUNT:
            return self.total_frames
        elif prop_id == cv2.CAP_PROP_POS_FRAMES:
            return self.frame
        else:
            raise ValueError("Unsupported property ID")

    @property
    def cap(self) -> cv2.VideoCapture:
        """
        Returns the currently active VideoCapture object.
        """
        return self.video_captures[self.active_cap_idx]

    def set(self, prop_id: int, value: int) -> None:
        """
        Sets the value of the specified property.

        Args:
            prop_id: The ID of the property to set.
            value: The value to set.

        Raises:
            ValueError: If the property ID is not cv2.CAP_PROP_POS_FRAMES or the value is out of range.
        """
        if prop_id != cv2.CAP_PROP_POS_FRAMES:
            raise ValueError("Unsupported property ID")
        if value < 0 or value > self.total_frames - 1:
            raise ValueError(f"Frame must be within [0, {self.total_frames - 1}]")
        first_frame = 0
        idx = 0
        for idx, _ in enumerate(self.video_captures):
            first_frame = ([0] + self.cumulative_frames)[idx]
            last_frame = self.cumulative_frames[idx] - 1
            if value >= first_frame and value < last_frame:
                break
        self.frame = value
        self.active_cap_idx = idx
        self.cap.set(prop_id, value - first_frame)

    def read(self) -> Tuple[bool, np.ndarray | None]:
        """
        Reads the next frame from the active video capture.

        Returns:
            A tuple (ret, frame), where ret is a boolean indicating whether the read was successful and frame is the read frame.
        """
        if self.frame >= self.total_frames:
            return False, None
        ret, img = self.cap.read()
        if not ret and self.frame >= self.cumulative_frames[self.active_cap_idx]:
            self.active_cap_idx = min(
                self.active_cap_idx + 1, len(self.video_captures) - 1
            )
            return self.read()
        self.frame = min(self.frame + 1, self.total_frames - 1)
        return ret, img
