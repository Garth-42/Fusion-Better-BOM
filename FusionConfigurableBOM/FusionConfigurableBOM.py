import adsk.core, traceback
from . import app

def run(context):
    try: app.start(adsk.core.Application.get())
    except: adsk.core.Application.get().userInterface.messageBox('Failed to start Configurable BOM:\n' + traceback.format_exc())
def stop(context):
    try: app.stop(adsk.core.Application.get())
    except: adsk.core.Application.get().userInterface.messageBox('Failed to stop Configurable BOM:\n' + traceback.format_exc())
