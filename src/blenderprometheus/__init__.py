# ##### BEGIN GPL LICENSE BLOCK #####
#
#  Blender-Prometheus, a Blender addon
#  (c) 2023 Michel J. Anders (varkenvarken)
#
# This program is free software: you can redistribute it and/or modify it under the terms 
# of the GNU General Public License as published by the Free Software Foundation, 
# either version 3 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; 
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. 
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program. 
# If not, see <https://www.gnu.org/licenses/>.
# 
# ##### END GPL LICENSE BLOCK #####

# Note: the client_python subdirectory is part of
# https://github.com/prometheus/client_python/tree/master and covered by its own license.

bl_info = {
    "name": "Blender-Prometheus",
    "author": "Michel Anders (varkenvarken)",
    "version": (0, 0, 20230710105529),
    "blender": (3, 6, 0),
    "location": "",
    "description": "Expose metrics with the help of prometheus",
    "warning": "Opens a port on the machine running Blender (http://localhost:8000)",
    "wiki_url": "https://github.com/varkenvarken/blenderaddons/blob/master/prometheus",
    "tracker_url": "",
    "category": "System",
}

# add the prometheus python client submodule to the path so we can import
from sys import path
from pathlib import Path
path.append(str(Path(__file__).parent / "client_python"))

import bpy 

from prometheus_client import Gauge, REGISTRY
from .server import start_server, stop_server

def every_10_seconds():
    """
    Check if we are running a render job.

    Updates a global Gauge accordingly and returns the number
    of seconds when to run this function again.
    """
    global g
    r = bpy.app.is_job_running("RENDER")
    if r:
        g.set(1.0)
    else:
        g.set(0.0)
    return 10.0

def register():
    """
    Create a Gauge, start a metrics server and add a timer.
    """
    global g
    g = Gauge("Blender_Render", "Rendering processes")
    start_server(8000)
    # We make it persistent so it will survive loading a .blend
    bpy.app.timers.register(every_10_seconds, persistent=True)

def unregister():
    """
    Remove the timer, unregister the Gauge and stop the server.

    This will ensure we can indeed restart the server and create
    a new Gauge when we reenable the add-on.
    """
    global g
    bpy.app.timers.unregister(every_10_seconds)
    REGISTRY.unregister(g)
    stop_server()

