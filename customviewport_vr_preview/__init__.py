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
        row.operator("custom.button_operator", text="3D GUI")
        row.operator("view3d.highlight_object", text="Highlight Object")

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

        bar_size = 0.5
        bar_ditance = 5.0
        panel_size = 0.25
        panel_th = 0.1
        panels_distance = 5.0
        panels_sep = 3.0
        
        styles = ['style_1','style_2','style_3','style_4']
        textures = ['texture_1','texture_2','texture_3','texture_4']
        
        try:
            cursor = bpy.data.objects['Cursor'] 
            bar = bpy.data.objects['Bar']  
            bar_bg = bpy.data.objects['Bar_bg']  
            back = bpy.data.objects['Back']  
            
            for style_name in styles:
                style = bpy.data.objects[style_name] 
                
            for texture_name in textures:
                texture = bpy.data.objects[texture_name]   
                
        except:
            bpy.ops.mesh.primitive_cylinder_add(radius=0.001, depth=10, enter_editmode=False, align='WORLD', location=(0, 0, 0), scale=(1, 1, 1))
            bpy.context.active_object.name = 'Cursor'
            cursor = bpy.data.objects['Cursor']       
            bpy.context.scene.cursor.location = (0.0, 0.0, 5)
            bpy.ops.object.origin_set(type='ORIGIN_CURSOR', center='MEDIAN')
            #cursor.hide_viewport = True
            
            bpy.ops.mesh.primitive_cylinder_add(radius=bar_size/5.0, depth=bar_size, enter_editmode=False, align='WORLD', location=(0, 0, 0), rotation=(0, math.pi/2, 0),  scale=(1, 1, 1))
            bpy.context.active_object.name = 'Bar'
            bar = bpy.data.objects['Bar']
            
            bpy.context.scene.cursor.location = (-bar_size/2.0, 0.0, 0.0)
            bpy.ops.object.origin_set(type='ORIGIN_CURSOR', center='MEDIAN')
            bpy.ops.mesh.primitive_cylinder_add(radius=bar_size/10.0, depth=bar_size, enter_editmode=False, align='WORLD', location=(0, 0, 0), rotation=(0, math.pi/2, 0),  scale=(1, 1, 1))
            bpy.context.active_object.name = 'Bar_bg'
            bar_bg = bpy.data.objects['Bar_bg']   
            bpy.context.scene.cursor.location = (-bar_size/2.0, 0.0, 0.0)
            bpy.ops.object.origin_set(type='ORIGIN_CURSOR', center='MEDIAN')
            
            #bpy.context.scene.cursor.location = (0.0, 0.0, 0.0)
            #bar_bg.location = Vector((0.0,0.0,2.0))
            #bpy.ops.object.origin_set(type='ORIGIN_CURSOR', center='MEDIAN')
            #bar_bg.parent = bpy.data.objects["Bar"]
            
            bpy.ops.mesh.primitive_plane_add(size=panel_size, enter_editmode=False, align='WORLD', location=(0, 0, 0), rotation=(0, 0, 0), scale=(1, 1, 1))
            bpy.context.active_object.name = 'Back'
            back = bpy.data.objects['Back']   
            
            for i,style_name in enumerate(styles):
                if i >0:
                    bpy.ops.mesh.primitive_plane_add(size=panel_size, enter_editmode=False, align='WORLD', location=(i*(panel_size+panel_th), 0, 0), rotation=(0, 0, 0), scale=(1, 1, 1))
                    bpy.context.active_object.name = style_name
                    bpy.context.active_object.parent = bpy.data.objects[styles[0]]
                else:
                    bpy.ops.mesh.primitive_plane_add(size=panel_size, enter_editmode=False, align='WORLD', location=(panel_th, panels_sep/2.0, 0), rotation=(0, 0, 0), scale=(1, 1, 1))
                    bpy.context.active_object.name = style_name
                    
            for i,texture_name in enumerate(textures):
                if i >0:
                    bpy.ops.mesh.primitive_plane_add(size=panel_size, enter_editmode=False, align='WORLD', location=(i*(panel_size+panel_th), 0, 0), rotation=(0, 0, 0), scale=(1, 1, 1))
                    bpy.context.active_object.name = texture_name
                    bpy.context.active_object.parent = bpy.data.objects[textures[0]]
                else:
                    bpy.ops.mesh.primitive_plane_add(size=panel_size, enter_editmode=False, align='WORLD', location=(panel_th, -panels_sep/2.0, 0), rotation=(0, 0, 0), scale=(1, 1, 1))
                    bpy.context.active_object.name = texture_name
            
        bar.scale = (0.0, 0.0, 0.0)

        max_time_to_select = 10
        
        scene = context.scene
        
        wm = context.window_manager

        loc = wm.xr_session_state.viewer_pose_location
        rot = wm.xr_session_state.viewer_pose_rotation
        camera = context.scene.camera
        cursor.location = loc
        cursor.rotation_euler = rot.to_euler()
        #cursor.rotation_euler = context.scene.camera.rotation_euler
        #cursor.location = context.scene.camera.location 
        
        #loc, rot, _= camera.matrix_world.decompose()
        offset = Vector((-bar_size/2.0, 0, -bar_ditance))  # Change this to adjust the distance from the camera
        position = loc + rot @ offset
        
        
        bar.location = position
        bar_bg.location = position
        
        wm = context.window_manager

        loc = wm.xr_session_state.viewer_pose_location
        rot = wm.xr_session_state.viewer_pose_rotation
        camera = context.scene.camera
        cursor.location = loc
        cursor.rotation_euler = rot.to_euler()
        rot_eu = rot.to_euler()
        bar.rotation_euler = (math.pi/2,rot_eu[1],rot_eu[2]+math.pi/2)
        bar_bg.rotation_euler = (math.pi/2,rot_eu[1],rot_eu[2]+math.pi/2)
        
        if scene.selectionState == 1:
            offset = Vector((-panels_sep/2.0, panel_size*2.0, - panels_distance))  # Change this to adjust the distance from the camera
            position = loc + rot @ offset
            
            rot_eu = rot.to_euler()
            bpy.data.objects[styles[0]].rotation_euler = (0,math.pi/2,rot_eu[2]+math.pi/2)
            bpy.data.objects[styles[0]].location = position
            
            offset = Vector((panels_sep/2.0, panel_size*2.0, - panels_distance))  # Change this to adjust the distance from the camera
            position = loc + rot @ offset
            
            rot_eu = rot.to_euler()
            bpy.data.objects[textures[0]].rotation_euler = (0, math.pi/2,rot_eu[2]+math.pi/2)
            bpy.data.objects[textures[0]].location = position
            
            offset = Vector((0, -panel_size*2.0, - panels_distance))  # Change this to adjust the distance from the camera
            position = loc + rot @ offset
            
            rot_eu = rot.to_euler()
            back.rotation_euler = (0,math.pi/2,rot_eu[2]+math.pi/2)
            back.location = position
            
            scene.selectionState = 2
            
        elif scene.selectionState == 3:
            bpy.data.objects[styles[0]].location = Vector((0.0,0.0,-10))
            bpy.data.objects[textures[0]].location = Vector((0.0,0.0,-10))
            scene.selectionState = 0
            back.location = Vector((0.0,0.0,-10))
        
        # Create bmesh objects for the mesh data
        bm1 = bmesh.new()
        bm1.from_mesh(cursor.data)
        bm1.transform(cursor.matrix_world)
        obj_now_BVHtree = BVHTree.FromBMesh(bm1)
        
        new_selected_obj = ''
        for obj_idx, obj in enumerate(context.scene.objects):
            if obj.type == "MESH" and (not obj.name in ['Cursor','Bar','Bar_bg']):
                bm2 = bmesh.new()
                bm2.from_mesh(obj.data)
                bm2.transform(obj.matrix_world) 
                obj_next_BVHtree = BVHTree.FromBMesh(bm2)           

                #get intersecting pairs
                inter = obj_now_BVHtree.overlap(obj_next_BVHtree)
                if inter:
                    obj.active_material = bpy.data.materials['selected']
                    print('Intersect with: ', obj)
                    new_selected_obj = obj.name
                    break
                    #return (obj_idx,)
                else:
                    obj.active_material = bpy.data.materials['not_selected']
        
        scene.elapsedTime += 1

        if new_selected_obj != '':
            if scene.selectedObject != new_selected_obj:
                scene.selectedObject = new_selected_obj
                scene.elapsedTime = 0
            elif scene.elapsedTime >= max_time_to_select:
                print('Selected: ', scene.selectedObject)
                if scene.selectionState ==2 and scene.selectedObject in textures+styles:
                    scene.selectionState = 3
                elif scene.selectionState == 0:
                    scene.selectionState = 1
                elif scene.selectionState == 2 and scene.selectedObject == 'Back':
                    scene.selectionState = 3
                
                scene.elapsedTime = 0
                    
        else:
            scene.elapsedTime = 0
            
        percentage = min(1.0, scene.elapsedTime / max_time_to_select)
        print(percentage)
        if percentage > 0:
            bar.scale = (1.0, 1.0, percentage)
            
        else:
            bar.scale = (0.0, 0.0, 0.0)

        print(scene.selectionState)
        return {'FINISHED'}
    
class MySceneProperties(bpy.types.PropertyGroup):
    elapsedTime: bpy.props.FloatProperty(name="elapsedTime", default=0.0)
    selectedObject: bpy.props.StringProperty(name="selectedobject", default='')
    selectionState: bpy.props.IntProperty(name="selectionState", default=3)
   

def draw_custom_element(shader,batch):
    batch.draw(shader)


def register():
    if not bpy.app.build_options.xr_openxr:
        bpy.utils.register_class(gui.VIEW3D_PT_vr_info)
        return

    action_map.register()
    gui.register()
    operators.register()
    properties.register()

    bpy.utils.register_class(MySceneProperties)
    bpy.utils.register_class(CustomOpenGLPanel)
    bpy.utils.register_class(HighlightObjectOperator)

    bpy.types.Scene.elapsedTime = bpy.props.FloatProperty(name="elapsedTime", default=0.0)
    bpy.types.Scene.selectedObject =  bpy.props.StringProperty(name="selectedobject", default='')
    bpy.types.Scene.selectionState = bpy.props.IntProperty(name="selectionState", default=3)
   
    


def unregister():
    if not bpy.app.build_options.xr_openxr:
        bpy.utils.unregister_class(gui.VIEW3D_PT_vr_info)
        return

    action_map.unregister()
    gui.unregister()
    operators.unregister()
    properties.unregister()

    bpy.utils.unregister_class(CustomOpenGLPanel)
    bpy.utils.unregister_class(HighlightObjectOperator)
    
    bpy.utils.unregister_class(MySceneProperties)
    del bpy.types.Scene.elapsedTime
    del bpy.types.Scene.selectedObject
    del bpy.types.Scene.selectionState
