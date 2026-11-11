from .commands.open_bom import install, uninstall
from .fusion.event_handlers import clear
from .ui.palette_controller import PaletteController

_controller = None


def start(app):
    global _controller
    _controller = PaletteController(app)
    install(app, _controller)


def stop(app):
    global _controller
    uninstall(app)
    clear()
    _controller = None
