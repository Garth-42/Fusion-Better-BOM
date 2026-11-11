import adsk.core

from ..constants import COMMAND_DESCRIPTION, COMMAND_ID, COMMAND_NAME, PALETTE_ID
from ..fusion.event_handlers import retain

PANEL_ID = 'SolidScriptsAddinsPanel'
# Application-level handlers must be removed again on stop; unlike the command
# definition and palette, the Application object outlives the add-in.
_document_handlers = []


class CommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller

    def notify(self, args):
        self.controller.show()


class PaletteIncomingHandler(adsk.core.HTMLEventHandler):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller

    def notify(self, args):
        palette = self.controller.app.userInterface.palettes.itemById(PALETTE_ID)
        if args.action == 'fusionBomMessage':
            self.controller.receive(palette, args.data)


class DocumentActivatedHandler(adsk.core.DocumentEventHandler):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller

    def notify(self, args):
        # Never let a palette hiccup surface as an error while switching tabs.
        try:
            self.controller.document_activated()
        except Exception:
            pass


def install(app, controller):
    ui = app.userInterface
    command = ui.commandDefinitions.itemById(COMMAND_ID)
    if not command:
        command = ui.commandDefinitions.addButtonDefinition(COMMAND_ID, COMMAND_NAME, COMMAND_DESCRIPTION)
    handler = CommandCreatedHandler(controller)
    command.commandCreated.add(handler)
    retain(handler)
    panel = ui.allToolbarPanels.itemById(PANEL_ID)
    if panel and not panel.controls.itemById(COMMAND_ID):
        panel.controls.addCommand(command)

    # Wire the HTML message handler when the palette is actually built -- on the
    # user's first Open, and again after a workspace switch discards it -- rather
    # than creating the palette here at add-in load. On-demand creation is what
    # lets the palette open above the Browser and object tree instead of behind
    # them (see PaletteController.show).
    def attach_incoming(palette):
        incoming = PaletteIncomingHandler(controller)
        palette.incomingFromHTML.add(incoming)
        retain(incoming)

    controller.on_palette_created(attach_incoming)

    # Re-scan when the user switches document tabs so the table never shows (or
    # edits) another design's rows. Optional: the add-in still works without it
    # because the controller refuses edits against a different design.
    try:
        activated = DocumentActivatedHandler(controller)
        app.documentActivated.add(activated)
        retain(activated)
        _document_handlers.append(activated)
    except Exception:
        pass


def uninstall(app):
    ui = app.userInterface
    while _document_handlers:
        try:
            app.documentActivated.remove(_document_handlers.pop())
        except Exception:
            pass
    palette = ui.palettes.itemById(PALETTE_ID)
    if palette:
        palette.deleteMe()
    panel = ui.allToolbarPanels.itemById(PANEL_ID)
    if panel:
        control = panel.controls.itemById(COMMAND_ID)
        if control:
            control.deleteMe()
    command = ui.commandDefinitions.itemById(COMMAND_ID)
    if command:
        command.deleteMe()
