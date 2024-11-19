from itertools import combinations
from typing import Any, List, Tuple

import traitlets


class RenderSettings(traitlets.HasTraits):
    temp_config = traitlets.Dict().tag(sync=True)

    interval_padding = traitlets.Float(default_value=1.0).tag(
        config=True,
        sync=True,
    )

    crop_roi = traitlets.Bool(default_value=True).tag(config=True, sync=True)
    roi_padding = traitlets.Int(default_value=100, min=0).tag(config=True, sync=True)

    # trajectories related settings
    draw_trajectories = traitlets.Bool(default_value=True).tag(config=True, sync=True)
    available_keypoints = traitlets.List(default_value=[]).tag(config=True, sync=True)
    keypoints = traitlets.List(default_value=[]).tag(config=True, sync=True)
    available_segments = traitlets.List(default_value=[]).tag(config=True, sync=True)
    segments = traitlets.List(default_value=[]).tag(config=True, sync=True)
    segment_separator = traitlets.Unicode(default_value=" - ", read_only=True).tag(
        sync=True
    )
    actor_color = traitlets.Any(default_value="#FF6965").tag(
        config=True, sync=True
    )  # rgb tuple or hex
    recipient_color = traitlets.Any(default_value="#65D4FF").tag(
        config=True, sync=True
    )  # rgb tuple or hex
    other_color = traitlets.Any(default_value="#E6E6E6").tag(
        config=True, sync=True
    )  # rgb tuple or hex
    apply_highlight_color_to = traitlets.List(default_value=[]).tag(
        config=True, sync=True
    )  # 0: "actor", 1: "receiver"
    overlay_size = traitlets.Float(default_value=5).tag(config=True, sync=True)

    # label related settings
    draw_label = traitlets.Bool(default_value=True).tag(config=True, sync=True)
    text_color = traitlets.Any(default_value="#000000").tag(
        config=True, sync=True
    )  # rgb tuple or hex
    box_color = traitlets.Any(default_value="#FFFFFF").tag(
        config=True, sync=True
    )  # rgb tuple or hex

    # category related settings
    highlight = traitlets.Bool(defautl_value=True).tag(config=True, sync=True)
    highlight_color = traitlets.Any(default_value="#FC0000").tag(
        config=True, sync=True
    )  # rgb tuple or hex
    override_highlight_color = traitlets.Dict(default_value={}).tag(
        config=True, sync=True
    )  # mapping: category -> highlight_color

    size_preset_options = traitlets.List(
        default_value=[
            "HD (1280x720)",
            "Full HD (1920x1080)",
            "2.7k (2704x1520)",
            "4k (3840x2160)",
            "customize",
        ],
        read_only=True,
    ).tag(sync=True)
    size_preset = traitlets.Unicode("Full HD (1920x1080)").tag(config=True, sync=True)
    max_render_width = traitlets.Int(default_value=1920, min=256).tag(
        config=True, sync=True
    )
    max_render_height = traitlets.Int(default_value=1080, min=256).tag(
        config=True, sync=True
    )
    macro_block_size = traitlets.Int(default_value=8, read_only=True).tag(sync=True)

    def get_roi_padding(self) -> int:
        return 0 if not self.crop_roi else self.roi_padding

    def apply_highlight_color_to_actor(self) -> bool:
        return 0 in self.apply_highlight_color_to

    def apply_highlight_color_to_recipient(self) -> bool:
        return 1 in self.apply_highlight_color_to

    def get_segments(self) -> tuple[tuple[int, int], ...]:
        def parse_segment(segment) -> tuple[int, int]:
            start, end = segment.split(self.segment_separator)
            return int(start), int(end)

        return tuple(parse_segment(segment) for segment in self.segments)

    @traitlets.validate("size_preset")
    def _size_preset_validation(self, proposal) -> str:
        if (value := proposal["value"]) not in self.size_preset_options:
            raise traitlets.TraitError(f"invalid size preset: {value}")
        return value

    def _parse_preset(self, preset) -> Tuple[None | int, None | int]:
        if preset == "customize":
            return None, None
        width, height = preset.split("(")[-1].split(")")[0].split("x")
        return int(width), int(height)

    def _get_preset(self, width: int | None, height: int | None) -> str:
        for preset in self.size_preset_options:
            if (width, height) == self._parse_preset(preset):
                return preset
        return "customize"

    @traitlets.observe("size_preset")
    def _on_size_preset_change(self, change) -> None:
        if change["old"] == change["new"]:
            return
        value = change["new"]
        width, height = self._parse_preset(value)
        if width is not None:
            self.max_render_width = width
        if height is not None:
            self.max_render_height = height

    @traitlets.observe("max_render_width", "max_render_height")
    def _on_max_size_change(self, change) -> None:
        self.size_preset = self._get_preset(
            self.max_render_width, self.max_render_height
        )

    @traitlets.observe("available_keypoints")
    def _on_available_keypoints_change(self, change) -> None:
        keypoints = []
        for keypoint in self.keypoints:
            if keypoint not in self.available_keypoints:
                continue
            keypoints.append(keypoint)
        if len(keypoints) == 0 and len(self.available_keypoints) > 0:
            # default to all
            keypoints = self.available_keypoints
        self.keypoints = keypoints

    @traitlets.observe("keypoints")
    def _on_keypoints_change(self, change) -> None:
        self.available_segments = [
            f"{start}{self.segment_separator}{end}"
            for start, end in list(combinations(self.keypoints, 2))
        ]
        segments = []
        for segment in self.segments:
            if segment not in self.available_segments:
                continue
            segments.append(segment)
        if len(segments) == 0 and len(self.keypoints) > 1:
            # default to simple segmented line
            segments = [
                f"{start}{self.segment_separator}{end}"
                for start, end in zip(self.keypoints[:-1], self.keypoints[1:])
            ]
        self.segments = segments

    def reset(self) -> None:
        for name in self.config_keys():
            if name in ["keypoints", "segments"]:
                continue
            default_value = self.trait_defaults()[name]  # type: ignore
            setattr(self, name, default_value)

    def config_values(self) -> List:
        return [
            getattr(self, name)
            for name, trait in RenderSettings().traits().items()
            if "config" in trait.metadata
            and name not in ["available_keypoints", "available_segments"]
        ]

    def config_keys(self) -> List[str]:
        return [
            name
            for name, trait in RenderSettings().traits().items()
            if "config" in trait.metadata
            and name not in ["available_keypoints", "available_segments"]
        ]

    def config(self) -> dict[str, Any]:
        return {
            key: value for key, value in zip(self.config_keys(), self.config_values())
        }

    def commit(self) -> None:
        for key, value in self.config().items():
            self.temp_config[key] = value

    def revert(self) -> None:
        if self.temp_config is None:
            self.reset()
            return
        for key, value in self.temp_config.items():
            setattr(self, key, value)
