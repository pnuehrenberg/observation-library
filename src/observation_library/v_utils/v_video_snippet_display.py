import os
import signal
import socketserver
from multiprocessing import Process
from threading import Thread

import ipyvuetify as v
import ipywidgets as widgets
import traitlets

from ..video_server import run_server
from .v_progress_bar import ProgressBar
from .v_video_container import VideoContainer


class VideoSnippetDisplay(v.VuetifyTemplate):  # type: ignore
    video_container = traitlets.Any().tag(sync=True, **widgets.widget_serialization)
    progress_bar_container = traitlets.Any().tag(
        sync=True, **widgets.widget_serialization
    )
    active_widget = traitlets.Any().tag(sync=True, **widgets.widget_serialization)

    @traitlets.default("template")
    def _template(self):
        return """
            <v-template>
                <jupyter-widget :widget="active_widget"/>
            <v-template>
            """

    def __init__(self, snippet):
        self.snippet = snippet
        self.thread = None
        with socketserver.TCPServer(("localhost", 0), None) as s:  # type: ignore
            self.port = s.server_address[1]
        self.server_process = Process(
            target=run_server,
            kwargs={
                "video_directory": self.snippet.video_server_directory,
                "port": self.port,
            },
        )
        self.server_process.start()
        self.progress_bar = ProgressBar(label="Preparing video:", style_="height: 25px")
        self.progress_bar_container = v.Layout(
            children=[self.progress_bar],
            class_="ma-4",
            style_="width: 400px; height: 100px",
        )
        try:
            output_file = self.snippet.output_file
        except ValueError:
            output_file = ""
        self.video_container = VideoContainer(
            url=f"http://localhost:{self.port}/{output_file}",
            class_="pa-4",
            style_="width: 100%; height: auto; max-height: 400px",
        )
        self.active_widget = self.progress_bar_container
        super().__init__()

    def interrupt_server_process(self):
        if self.server_process is None or (pid := self.server_process.pid) is None:
            return
        os.kill(pid, signal.SIGINT)
        self.server_process.join()

    def interrupt(self):
        if self.thread is None:
            return
        setattr(self.thread, "interrupt", True)
        self.thread.join()
        self.thread = None
        self.progress_bar.value = 0
        return True

    def cut(self, *, video_snippet_dialog=None):
        def _cut():
            self.active_widget = self.progress_bar_container
            if video_snippet_dialog is not None:
                video_snippet_dialog.show_actions = False
            success = self.snippet.cut(progress_bar=self.progress_bar)
            if video_snippet_dialog is not None:
                video_snippet_dialog.show_actions = True
            if success:
                self.active_widget = self.video_container
                self.video_container.url = (
                    f"http://localhost:{self.port}/{self.snippet.output_file}"
                )
            self.progress_bar.value = 0

        if self.thread is not None:
            self.interrupt()
        if os.path.exists(self.snippet.output_file):
            self.active_widget = self.video_container
            self.video_container.url = (
                f"http://localhost:{self.port}/{self.snippet.output_file}"
            )
            return True
        self.thread = Thread(target=_cut)
        self.thread.start()
        return True
