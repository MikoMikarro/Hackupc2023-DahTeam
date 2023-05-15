# SPDX-License-Identifier: GPL-2.0-or-later

bl_info = {
    "name": "VR Scene Inspection Custom",
    "author": "Julian Eisel (Severin), Sebastian Koenig, Peter Kim (muxed-reality)",
    "version": (0, 11, 1),
    "blender": (3, 2, 0),
    "location": "3D View > Sidebar > VR",
    "description": ("View the viewport with virtual reality glasses "
                    "(head-mounted displays)"),
    "support": "OFFICIAL",
    "warning": "This is an early, limited preview of in development "
               "VR support for Blender.",
    "doc_url": "{BLENDER_MANUAL_URL}/addons/3d_view/vr_scene_inspection.html",
    "category": "3D View",
}


if "bpy" in locals():
    import importlib
    importlib.reload(action_map)
    importlib.reload(gui)
    importlib.reload(operators)
    importlib.reload(properties)
else:
    from . import action_map, gui, operators, properties
    from . operators import execute_M, AssetLoader

import bpy
import gpu
import bmesh
from mathutils import Vector, Matrix
from gpu_extras.batch import batch_for_shader
from mathutils.bvhtree import BVHTree
import time
import math

class CustomOpenGLPanel(bpy.types.Panel):
    bl_idname = "VIEW3D_PT_custom_opengl_panel"
    bl_label = "Custom OpenGL Panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Custom Add-On"

    def draw(self, context):
        layout = self.layout
        row = layout.column()
        row.operator("view3d.highlight_object", text="Highlight Object")
        row = layout.column()
        row.operator("asset.load_assets", text="Load Assets & create base scene")
        row = layout.column()
        row.operator( "view3d.dream_bitch", text="dream ma boi")

''' selectionState
    0- wainting furniture selection
    1- furniture selection done, bring up panels
    2- waiting change selection
    3- change done, bring down pannels
'''

class HighlightObjectOperator(bpy.types.Operator):
    """Operator to highlight the object in the center of the camera"""
    bl_idname = "view3d.highlight_object"
    bl_label = "Highlight Object"
    
    _timer = None

    #bpy.ops.object.duplicate()
    '''   
    # Create a new material for the object
    mat = bpy.data.materials.new(name="Transparent Material")
    mat.use_nodes = True
    mat.node_tree.nodes["Principled BSDF"].inputs["Alpha"].default_value = 0.5
    
    if bar_bg.data.materials:
        bar_bg.data.materials[0] = mat
    else: 
        bar_bg.data.materials.append(mat)
    bar_bg.active_material = bpy.data.materials['Transparent Material']
    '''
    def modal(self, context, event):
        if event.type == 'TIMER':
            # Code to execute on each timer tick
            execute_M()
            print("Timer tick:", time.time())

        return {'PASS_THROUGH'}

    def execute(self, context):
        wm = context.window_manager
        self._timer = wm.event_timer_add(.01, window=context.window)
        wm.modal_handler_add(self)
        
        return {'RUNNING_MODAL'}

    def cancel(self, context):
        wm = context.window_manager
        wm.event_timer_remove(self._timer)
        return {'CANCELLED'}



class ExecuteDreamingOperator(bpy.types.Operator):
    """Operator to highlight the object in the center of the camera"""
    bl_idname = "view3d.dream_bitch"
    bl_label = "Highlight Object"
    
    _timer = None

    #bpy.ops.object.duplicate()
    '''   
    # Create a new material for the object
    mat = bpy.data.materials.new(name="Transparent Material")
    mat.use_nodes = True
    mat.node_tree.nodes["Principled BSDF"].inputs["Alpha"].default_value = 0.5
    
    if bar_bg.data.materials:
        bar_bg.data.materials[0] = mat
    else: 
        bar_bg.data.materials.append(mat)
    bar_bg.active_material = bpy.data.materials['Transparent Material']
    '''

    def execute(self, context):
        bpy.ops.object.editmode_toggle()
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.shade.dream_texture_project()
        bpy.ops.object.editmode_toggle()
        
        return {'FINISHED'}


class MySceneProperties(bpy.types.PropertyGroup):
    elapsedTime: bpy.props.FloatProperty(name="elapsedTime", default=0.0)
    selectedObject: bpy.props.StringProperty(name="selectedObject", default='')
    selectedMesh: bpy.props.StringProperty(name="selectedMesh", default='')
    selectionState: bpy.props.IntProperty(name="selectionState", default=3)
    selectedDull: bpy.props.StringProperty(name="selectedDull", default='')
    currentSceneHDRI: bpy.props.IntProperty(name="currentSceneHDRI", default=0)
    currentSceneChanges: bpy.props.IntProperty(name="currentSceneChanges", default=0)
    currentSceneIsDepth: bpy.props.IntProperty(name="currentSceneIsDepth", default=0)
    currentFalseTexture: bpy.props.IntProperty(name="currentFalseTexture", default=1)

def register():
    if not bpy.app.build_options.xr_openxr:
        bpy.utils.register_class(gui.VIEW3D_PT_vr_info)
        

    action_map.register()
    gui.register()
    operators.register()
    properties.register()

    bpy.utils.register_class(MySceneProperties)
    bpy.utils.register_class(AssetLoader)
    bpy.utils.register_class(CustomOpenGLPanel)
    bpy.utils.register_class(ExecuteDreamingOperator)

    bpy.utils.register_class(HighlightObjectOperator)

    bpy.types.Scene.elapsedTime = bpy.props.FloatProperty(name="elapsedTime", default=0.0)
    bpy.types.Scene.selectedObject =  bpy.props.StringProperty(name="selectedObject", default='')
    bpy.types.Scene.selectedMesh = bpy.props.StringProperty(name="selectedMesh", default='')
    bpy.types.Scene.selectionState = bpy.props.IntProperty(name="selectionState", default=3)
    bpy.types.Scene.selectedDull = bpy.props.StringProperty(name="selectedDull", default='')
    bpy.types.Scene.currentSceneHDRI = bpy.props.IntProperty(name="currentSceneHDRI", default=1)
    bpy.types.Scene.currentSceneChanges = bpy.props.IntProperty(name="currentSceneChanges", default=0)
    bpy.types.Scene.currentSceneIsDepth = bpy.props.IntProperty(name="currentSceneIsDepth", default=0)
    bpy.types.Scene.currentFalseTexture = bpy.props.IntProperty(name="currentFalseTexture", default=1)

def unregister():
    
    if not bpy.app.build_options.xr_openxr:
        bpy.utils.unregister_class(gui.VIEW3D_PT_vr_info)
        

    action_map.unregister()
    gui.unregister()
    operators.unregister()
    properties.unregister()

    bpy.utils.unregister_class(CustomOpenGLPanel)
    bpy.utils.unregister_class(HighlightObjectOperator)
    bpy.utils.unregister_class(MySceneProperties)
    bpy.utils.unregister_class(AssetLoader)
    bpy.utils.unregister_class(ExecuteDreamingOperator)

    del bpy.types.Scene.elapsedTime
    del bpy.types.Scene.selectedObject
    del bpy.types.Scene.selectionState
    del bpy.types.Scene.currentSceneHDRI
    del bpy.types.Scene.currentSceneIsDepth
    del bpy.types.Scene.currentFalseTexture

        