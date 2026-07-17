from .ui.palette_controller import PaletteController
from .commands.open_bom import install, uninstall
from .fusion.event_handlers import clear
_controller = None

def start(app):
    global _controller
    _controller = PaletteController(app); install(app.userInterface, _controller)
def stop(app):
    uninstall(app.userInterface); clear()
