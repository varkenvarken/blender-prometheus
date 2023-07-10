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
    "version": (0, 0, 20230710171842),
    "blender": (3, 6, 0),
    "location": "",
    "description": "Expose metrics with the help of prometheus",
    "warning": "Opens a port on the machine running Blender (http://localhost:8000)",
    "doc_url": "https://github.com/varkenvarken/blender-prometheus",
    "category": "System",
}

# add the prometheus python client submodule to the path so we can import
from sys import path
from pathlib import Path
path.append(str(Path(__file__).parent / "client_python"))

import re
valid_address = re.compile(r"(?P<address>.+):(?P<port>\d+)")

import bpy 
from bpy.app.handlers import persistent
from bpy.props import StringProperty

from prometheus_client import Gauge, Counter, REGISTRY
from .server import start_server, stop_server

@persistent
def render_cancel(scene=None):
    global is_rendering
    is_rendering.set(0.0)

@persistent
def render_complete(scene=None):
    global is_rendering
    is_rendering.set(0.0)

@persistent
def render_init(scene=None):
    global is_rendering
    is_rendering.set(1.0)

@persistent
def render_post(scene=None):
    global frame_count
    frame_count.inc()

class BlenderPrometheusPreferences(bpy.types.AddonPreferences):
    bl_idname = __name__

    address: StringProperty(
        name="Address:port", description="address:port the metrics are exposed on", default="0.0.0.0:8000"
    )

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.prop(self, "address")

def start_serving():
    # TODO sanity check on address:port
    print(bpy.context.preferences.addons[__name__].preferences.address)
    if match := valid_address.match(bpy.context.preferences.addons[__name__].preferences.address):
        start_server(port=int(match.group("port")),addr=match.group("address"))
    else:
        start_server(8000)

classes = (
    BlenderPrometheusPreferences,)

def register():
    """
    Create a Gauge and a Counter, then start a metrics server.
    """
    for c in classes:
        bpy.utils.register_class(c)

    global is_rendering
    is_rendering = Gauge("Blender_Render", "Rendering processes")
    global frame_count
    frame_count = Counter("Frame_Counter", "Number of frames rendered")

    start_serving()

    bpy.app.handlers.render_cancel.append(render_cancel)
    bpy.app.handlers.render_complete.append(render_complete)
    bpy.app.handlers.render_init.append(render_init)
    bpy.app.handlers.render_post.append(render_post)

    # Any Python object can act as the subscription's owner.
    owner = object()
    subscribe_to = bpy.context.preferences.addons[__name__].preferences.path_resolve("address", False)

    def msgbus_callback(*args):
        print(bpy.context.preferences.addons[__name__].preferences.address)
        stop_server()
        start_serving()


    bpy.msgbus.subscribe_rna(
        key=subscribe_to,
        owner=owner,
        args=tuple(),
        notify=msgbus_callback,)

def unregister():
    """
    Unregister the Gauge and Counter, then stop the server.

    This will ensure we can indeed restart the server and create
    a new Gauge when we reenable the add-on.
    """
    global is_rendering
    global frame_count
    bpy.app.handlers.render_cancel.remove(render_cancel)
    bpy.app.handlers.render_complete.remove(render_complete)
    bpy.app.handlers.render_init.remove(render_init)
    bpy.app.handlers.render_post.remove(render_post)
    REGISTRY.unregister(is_rendering)
    REGISTRY.unregister(frame_count)
    stop_server()

    for c in classes:
        bpy.utils.unregister_class(c)

