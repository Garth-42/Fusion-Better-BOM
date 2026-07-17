import adsk.core
from ..constants import COMMAND_ID, COMMAND_NAME, COMMAND_DESCRIPTION, PALETTE_ID
from ..fusion.event_handlers import retain

class CommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def __init__(self, controller): super().__init__(); self.controller = controller
    def notify(self, args): self.controller.show()

class PaletteIncomingHandler(adsk.core.HTMLEventHandler):
    def __init__(self, controller): super().__init__(); self.controller = controller
    def notify(self, args):
        palette = self.controller.app.userInterface.palettes.itemById(PALETTE_ID)
        if args.action == 'fusionBomMessage':
            self.controller.receive(palette, args.data)

def install(ui, controller):
    command = ui.commandDefinitions.itemById(COMMAND_ID)
    if not command: command = ui.commandDefinitions.addButtonDefinition(COMMAND_ID, COMMAND_NAME, COMMAND_DESCRIPTION)
    handler = CommandCreatedHandler(controller); command.commandCreated.add(handler); retain(handler)
    panel = ui.allToolbarPanels.itemById('SolidScriptsAddinsPanel')
    if panel and not panel.controls.itemById(COMMAND_ID): panel.controls.addCommand(command)
    palette = controller.show()
    incoming = PaletteIncomingHandler(controller); palette.incomingFromHTML.add(incoming); retain(incoming)
    palette.isVisible = False

def uninstall(ui):
    palette = ui.palettes.itemById(PALETTE_ID)
    if palette: palette.deleteMe()
    panel = ui.allToolbarPanels.itemById('SolidScriptsAddinsPanel')
    if panel:
        control = panel.controls.itemById(COMMAND_ID)
        if control: control.deleteMe()
    command = ui.commandDefinitions.itemById(COMMAND_ID)
    if command: command.deleteMe()
