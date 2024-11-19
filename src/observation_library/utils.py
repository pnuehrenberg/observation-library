import cv2
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_agg import FigureCanvasAgg
from PIL import Image


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


def crop_and_scale(img, *, max_width, max_height, roi=None, block_size=None):
    img_cropped = img
    if roi is not None:
        img_cropped = img[roi[1] : (roi[3] + 1), roi[0] : (roi[2] + 1)]
    crop_height, crop_width = img_cropped.shape[:2]
    scale = (
        np.array([max_width, max_height]) / np.asarray([crop_width, crop_height])
    ).min()
    scaled_size = crop_width * scale, crop_height * scale
    if block_size is not None:
        scaled_size = tuple(closest_divisible(size, block_size) for size in scaled_size)
    else:
        scaled_size = list(map(lambda size: int(round(size)), scaled_size))
    img_scaled = cv2.resize(img_cropped, dsize=scaled_size)
    return img_cropped, img_scaled


class ImageOverlay:
    def __init__(
        self,
        original_size,
        render_size,
        crop_size=None,
    ):
        self.original_size = np.asarray(original_size)
        self.render_size = np.asarray(render_size)
        self.crop_size = np.asarray(
            crop_size if crop_size is not None else original_size
        )
        self.fig = plt.figure(
            figsize=(
                self.render_size[0] / self.dpi,
                self.render_size[1] / self.dpi,
            ),
            dpi=self.dpi,
        )
        self.ax = self.fig.add_axes((0, 0, 1, 1))

    @property
    def dpi(self):
        # scales linearly with render height, full hd -> 300dpi
        return self.render_size[1] * 300 / 1080

    def get_pixel_size(self, num_pixels):
        return (
            (num_pixels * self.crop_scale / self.original_size[1])
            * self.crop_size[1]
            * self.scale
            * 72
            / self.dpi
        )

    @property
    def scale(self):
        return (self.render_size / self.crop_size).min()

    @property
    def crop_scale(self):
        return (self.original_size / self.crop_size).min()

    def get_axes(self, clear=True):
        if clear:
            self.ax.clear()
        return self.ax

    @property
    def _overlay_numpy(self):
        self.fig.patch.set_facecolor((0, 0, 0, 0))
        self.ax.axis("off")
        canvas = FigureCanvasAgg(self.fig)
        canvas.draw()
        *_, width, height = canvas.figure.bbox.bounds
        width, height = int(round(width)), int(round(height))
        if width != self.render_size[0] or height != self.render_size[1]:
            raise ValueError(
                f"image size ({width, height}) does not match render size ({tuple(self.render_size)})"
            )
        buffer = canvas.buffer_rgba()
        overlay_numpy = np.frombuffer(buffer, dtype=np.uint8)
        return overlay_numpy.reshape(height, width, 4)

    def _to_rgb(self, image, background_color=(255, 255, 255)):
        """
        http://stackoverflow.com/a/9459208/284318
        """
        image.load()
        background = Image.new("RGB", image.size, background_color)
        # use alpha channel as mask
        background.paste(image, mask=image.split()[3])
        return background

    def draw_overlay(self, img):
        img_width = img.shape[1]
        img_height = img.shape[0]
        if img_width != self.render_size[0] or img_height != self.render_size[1]:
            raise ValueError(
                f"image size ({img_width, img_height}) does not match render size ({tuple(self.render_size)})"
            )
        image = Image.fromarray(img)
        overlay = Image.fromarray(self._overlay_numpy)
        # use overlay alpha as mask
        image.paste(overlay, (0, 0), overlay)
        image = self._to_rgb(image)
        return np.asarray(image)
