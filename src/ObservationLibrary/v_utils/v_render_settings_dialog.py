import ipyvuetify as v
from vTableApp.v_dialog import Dialog

from .v_render_settings_input import RenderSettingsInput


class RenderSettingsDialog(Dialog):
    def __init__(self):
        self._confirmed = False
        self.render_settings_input = RenderSettingsInput()
        undo_button = v.Btn(icon=True, children=[v.Icon(children=["mdi-undo-variant"])])
        undo_button.on_event("click", lambda *args: self.render_settings_input.reset())
        super().__init__(
            title="Render settings",
            content=[self.render_settings_input],
            actions=[undo_button, v.Spacer()],
            open_button="mdi-settings",
            open_button_icon=True,
            on_open_callbacks=[
                lambda: self._set_confirmed(False),
            ],
            on_submit_callbacks=[lambda: self._set_confirmed(True)],
            on_close_callbacks=[lambda: self._update_settings()],
        )

    def _set_confirmed(self, confirmed):
        self._confirmed = confirmed
        return True

    def _update_settings(self):
        if self._confirmed:
            self.render_settings_input.commit()
            return True
        self.render_settings_input.revert()
        return True
