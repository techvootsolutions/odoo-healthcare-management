# -*- coding: utf-8 -*-
from . import models
from . import controllers
from . import wizard

def post_init_hook(env):
    """Post-installation hook to set default data."""
    pass

def post_load():
    """Hook to run after module load."""
    pass

def uninstall_hook(cr, registry):
    """Hook to clean up on uninstall."""
    pass
