# SPDX-License-Identifier: GPL-2.0-or-later

if "bpy" in locals():
    import importlib
    importlib.reload(properties)
else:
    from . import properties

import bpy
import gpu
import bmesh
from mathutils import Vector, Matrix
from gpu_extras.batch import batch_for_shader
from mathutils.bvhtree import BVHTree
import time
import math, os, glob
from math import pi
from bpy.app.translations import pgettext_data as data_
from bpy.types import (
    Gizmo,
    GizmoGroup,
    Operator,
)
import math
from math import radians
from mathutils import Euler, Matrix, Quaternion, Vector
from . scene_loader import loadPickle
### Landmarks.
class VIEW3D_OT_vr_landmark_add(Operator):
    bl_idname = "view3d.vr_landmark_add"
    bl_label = "Add VR Landmark"
    bl_description = "Add a new VR landmark to the list and select it"
    bl_options = {'UNDO', 'REGISTER'}

    def execute(self, context):
        scene = context.scene
        landmarks = scene.vr_landmarks

        landmarks.add()

        # select newly created set
        scene.vr_landmarks_selected = len(landmarks) - 1

        return {'FINISHED'}

class VIEW3D_OT_vr_landmark_from_camera(Operator):
    bl_idname = "view3d.vr_landmark_from_camera"
    bl_label = "Add VR Landmark from Camera"
    bl_description = "Add a new VR landmark from the active camera object to the list and select it"
    bl_options = {'UNDO', 'REGISTER'}

    @classmethod
    def poll(cls, context):
        cam_selected = False

        vl_objects = bpy.context.view_layer.objects
        if vl_objects.active and vl_objects.active.type == 'CAMERA':
            cam_selected = True
        return cam_selected

    def execute(self, context):
        scene = context.scene
        landmarks = scene.vr_landmarks
        cam = context.view_layer.objects.active
        lm = landmarks.add()
        lm.type = 'OBJECT'
        lm.base_pose_object = cam
        lm.name = "LM_" + cam.name

        # select newly created set
        scene.vr_landmarks_selected = len(landmarks) - 1

        return {'FINISHED'}


class VIEW3D_OT_vr_landmark_from_session(Operator):
    bl_idname = "view3d.vr_landmark_from_session"
    bl_label = "Add VR Landmark from Session"
    bl_description = "Add VR landmark from the viewer pose of the running VR session to the list and select it"
    bl_options = {'UNDO', 'REGISTER'}

    @classmethod
    def poll(cls, context):
        return bpy.types.XrSessionState.is_running(context)

    def execute(self, context):
        scene = context.scene
        landmarks = scene.vr_landmarks
        wm = context.window_manager

        lm = landmarks.add()
        lm.type = "CUSTOM"
        scene.vr_landmarks_selected = len(landmarks) - 1

        loc = wm.xr_session_state.viewer_pose_location
        rot = wm.xr_session_state.viewer_pose_rotation.to_euler()

        lm.base_pose_location = loc
        lm.base_pose_angle = rot[2]

        return {'FINISHED'}


class VIEW3D_OT_vr_camera_landmark_from_session(Operator):
    bl_idname = "view3d.vr_camera_landmark_from_session"
    bl_label = "Add Camera and VR Landmark from Session"
    bl_description = "Create a new Camera and VR Landmark from the viewer pose of the running VR session and select it"
    bl_options = {'UNDO', 'REGISTER'}

    @classmethod
    def poll(cls, context):
        return bpy.types.XrSessionState.is_running(context)

    def execute(self, context):
        scene = context.scene
        landmarks = scene.vr_landmarks
        wm = context.window_manager

        lm = landmarks.add()
        lm.type = 'OBJECT'
        scene.vr_landmarks_selected = len(landmarks) - 1

        loc = wm.xr_session_state.viewer_pose_location
        rot = wm.xr_session_state.viewer_pose_rotation.to_euler()

        cam = bpy.data.cameras.new(data_("Camera") + "_" + lm.name)
        new_cam = bpy.data.objects.new(data_("Camera") + "_" + lm.name, cam)
        scene.collection.objects.link(new_cam)
        new_cam.location = loc
        new_cam.rotation_euler = rot

        lm.base_pose_object = new_cam

        return {'FINISHED'}


class VIEW3D_OT_update_vr_landmark(Operator):
    bl_idname = "view3d.update_vr_landmark"
    bl_label = "Update Custom VR Landmark"
    bl_description = "Update the selected landmark from the current viewer pose in the VR session"
    bl_options = {'UNDO', 'REGISTER'}

    @classmethod
    def poll(cls, context):
        selected_landmark = properties.VRLandmark.get_selected_landmark(context)
        return bpy.types.XrSessionState.is_running(context) and selected_landmark.type == 'CUSTOM'

    def execute(self, context):
        wm = context.window_manager

        lm = properties.VRLandmark.get_selected_landmark(context)

        loc = wm.xr_session_state.viewer_pose_location
        rot = wm.xr_session_state.viewer_pose_rotation.to_euler()

        lm.base_pose_location = loc
        lm.base_pose_angle = rot

        # Re-activate the landmark to trigger viewer reset and flush landmark settings to the session settings.
        properties.vr_landmark_active_update(None, context)

        return {'FINISHED'}


class VIEW3D_OT_vr_landmark_remove(Operator):
    bl_idname = "view3d.vr_landmark_remove"
    bl_label = "Remove VR Landmark"
    bl_description = "Delete the selected VR landmark from the list"
    bl_options = {'UNDO', 'REGISTER'}

    def execute(self, context):
        scene = context.scene
        landmarks = scene.vr_landmarks

        if len(landmarks) > 1:
            landmark_selected_idx = scene.vr_landmarks_selected
            landmarks.remove(landmark_selected_idx)

            scene.vr_landmarks_selected -= 1

        return {'FINISHED'}


class VIEW3D_OT_cursor_to_vr_landmark(Operator):
    bl_idname = "view3d.cursor_to_vr_landmark"
    bl_label = "Cursor to VR Landmark"
    bl_description = "Move the 3D Cursor to the selected VR Landmark"
    bl_options = {'UNDO', 'REGISTER'}

    @classmethod
    def poll(cls, context):
        lm = properties.VRLandmark.get_selected_landmark(context)
        if lm.type == 'SCENE_CAMERA':
            return context.scene.camera is not None
        elif lm.type == 'OBJECT':
            return lm.base_pose_object is not None

        return True

    def execute(self, context):
        scene = context.scene
        lm = properties.VRLandmark.get_selected_landmark(context)
        if lm.type == 'SCENE_CAMERA':
            lm_pos = scene.camera.location
        elif lm.type == 'OBJECT':
            lm_pos = lm.base_pose_object.location
        else:
            lm_pos = lm.base_pose_location
        scene.cursor.location = lm_pos

        return{'FINISHED'}


class VIEW3D_OT_add_camera_from_vr_landmark(Operator):
    bl_idname = "view3d.add_camera_from_vr_landmark"
    bl_label = "New Camera from VR Landmark"
    bl_description = "Create a new Camera from the selected VR Landmark"
    bl_options = {'UNDO', 'REGISTER'}

    def execute(self, context):
        scene = context.scene
        lm = properties.VRLandmark.get_selected_landmark(context)

        cam = bpy.data.cameras.new(data_("Camera") + "_" + lm.name)
        new_cam = bpy.data.objects.new(data_("Camera") + "_" + lm.name, cam)
        scene.collection.objects.link(new_cam)
        angle = lm.base_pose_angle
        new_cam.location = lm.base_pose_location
        new_cam.rotation_euler = (math.pi / 2, 0, angle)

        return {'FINISHED'}


class VIEW3D_OT_camera_to_vr_landmark(Operator):
    bl_idname = "view3d.camera_to_vr_landmark"
    bl_label = "Scene Camera to VR Landmark"
    bl_description = "Position the scene camera at the selected landmark"
    bl_options = {'UNDO', 'REGISTER'}

    @classmethod
    def poll(cls, context):
        return context.scene.camera is not None

    def execute(self, context):
        scene = context.scene
        lm = properties.VRLandmark.get_selected_landmark(context)

        cam = scene.camera
        angle = lm.base_pose_angle
        cam.location = lm.base_pose_location
        cam.rotation_euler = (math.pi / 2, 0, angle)

        return {'FINISHED'}


class VIEW3D_OT_vr_landmark_activate(Operator):
    bl_idname = "view3d.vr_landmark_activate"
    bl_label = "Activate VR Landmark"
    bl_description = "Change to the selected VR landmark from the list"
    bl_options = {'UNDO', 'REGISTER'}

    index: bpy.props.IntProperty(
        name="Index",
        options={'HIDDEN'},
    )

    def execute(self, context):
        scene = context.scene

        if self.index >= len(scene.vr_landmarks):
            return {'CANCELLED'}

        scene.vr_landmarks_active = (
            self.index if self.properties.is_property_set(
                "index") else scene.vr_landmarks_selected
        )

        return {'FINISHED'}


### Gizmos.
class VIEW3D_GT_vr_camera_cone(Gizmo):
    bl_idname = "VIEW_3D_GT_vr_camera_cone"

    aspect = 1.0, 1.0

    def draw(self, context):
        if not hasattr(self, "frame_shape"):
            aspect = self.aspect

            frame_shape_verts = (
                (-aspect[0], -aspect[1], -1.0),
                (aspect[0], -aspect[1], -1.0),
                (aspect[0], aspect[1], -1.0),
                (-aspect[0], aspect[1], -1.0),
            )
            lines_shape_verts = (
                (0.0, 0.0, 0.0),
                frame_shape_verts[0],
                (0.0, 0.0, 0.0),
                frame_shape_verts[1],
                (0.0, 0.0, 0.0),
                frame_shape_verts[2],
                (0.0, 0.0, 0.0),
                frame_shape_verts[3],
            )

            self.frame_shape = self.new_custom_shape(
                'LINE_LOOP', frame_shape_verts)
            self.lines_shape = self.new_custom_shape(
                'LINES', lines_shape_verts)

        # Ensure correct GL state (otherwise other gizmos might mess that up)
        gpu.state.line_width_set(1.0)
        gpu.state.blend_set('ALPHA')

        self.draw_custom_shape(self.frame_shape)
        self.draw_custom_shape(self.lines_shape)


class VIEW3D_GT_vr_controller_grip(Gizmo):
    bl_idname = "VIEW_3D_GT_vr_controller_grip"

    def draw(self, context):
        gpu.state.line_width_set(1.0)
        gpu.state.blend_set('ALPHA')

        self.color = 0.422, 0.438, 0.446
        self.draw_preset_circle(self.matrix_basis, axis='POS_X')
        self.draw_preset_circle(self.matrix_basis, axis='POS_Y')
        self.draw_preset_circle(self.matrix_basis, axis='POS_Z')


class VIEW3D_GT_vr_controller_aim(Gizmo):
    bl_idname = "VIEW_3D_GT_vr_controller_aim"

    def draw(self, context):
        gpu.state.line_width_set(1.0)
        gpu.state.blend_set('ALPHA')

        self.color = 1.0, 0.2, 0.322
        self.draw_preset_arrow(self.matrix_basis, axis='POS_X')
        self.color = 0.545, 0.863, 0.0
        self.draw_preset_arrow(self.matrix_basis, axis='POS_Y')
        self.color = 0.157, 0.565, 1.0
        self.draw_preset_arrow(self.matrix_basis, axis='POS_Z')


class VIEW3D_GGT_vr_viewer_pose(GizmoGroup):
    bl_idname = "VIEW3D_GGT_vr_viewer_pose"
    bl_label = "VR Viewer Pose Indicator"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options = {'3D', 'PERSISTENT', 'SCALE', 'VR_REDRAWS'}

    @classmethod
    def poll(cls, context):
        view3d = context.space_data
        return (
            view3d.shading.vr_show_virtual_camera and
            bpy.types.XrSessionState.is_running(context) and
            not view3d.mirror_xr_session
        )

    @staticmethod
    def _get_viewer_pose_matrix(context):
        wm = context.window_manager

        loc = wm.xr_session_state.viewer_pose_location
        rot = wm.xr_session_state.viewer_pose_rotation

        rotmat = Matrix.Identity(3)
        rotmat.rotate(rot)
        rotmat.resize_4x4()
        transmat = Matrix.Translation(loc)

        return transmat @ rotmat

    def setup(self, context):
        gizmo = self.gizmos.new(VIEW3D_GT_vr_camera_cone.bl_idname)
        gizmo.aspect = 1 / 3, 1 / 4

        gizmo.color = gizmo.color_highlight = 0.2, 0.6, 1.0
        gizmo.alpha = 1.0

        self.gizmo = gizmo

    def draw_prepare(self, context):
        self.gizmo.matrix_basis = self._get_viewer_pose_matrix(context)


class VIEW3D_GGT_vr_controller_poses(GizmoGroup):
    bl_idname = "VIEW3D_GGT_vr_controller_poses"
    bl_label = "VR Controller Poses Indicator"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options = {'3D', 'PERSISTENT', 'SCALE', 'VR_REDRAWS'}

    @classmethod
    def poll(cls, context):
        view3d = context.space_data
        return (
            view3d.shading.vr_show_controllers and
            bpy.types.XrSessionState.is_running(context) and
            not view3d.mirror_xr_session
        )

    @staticmethod
    def _get_controller_pose_matrix(context, idx, is_grip, scale):
        wm = context.window_manager

        loc = None
        rot = None
        if is_grip:
            loc = wm.xr_session_state.controller_grip_location_get(context, idx)
            rot = wm.xr_session_state.controller_grip_rotation_get(context, idx)
        else:
            loc = wm.xr_session_state.controller_aim_location_get(context, idx)
            rot = wm.xr_session_state.controller_aim_rotation_get(context, idx)

        rotmat = Matrix.Identity(3)
        rotmat.rotate(Quaternion(Vector(rot)))
        rotmat.resize_4x4()
        transmat = Matrix.Translation(loc)
        scalemat = Matrix.Scale(scale, 4)

        return transmat @ rotmat @ scalemat

    def setup(self, context):
        for idx in range(2):
            self.gizmos.new(VIEW3D_GT_vr_controller_grip.bl_idname)
            self.gizmos.new(VIEW3D_GT_vr_controller_aim.bl_idname)

        for gizmo in self.gizmos:
            gizmo.aspect = 1 / 3, 1 / 4
            gizmo.color_highlight = 1.0, 1.0, 1.0
            gizmo.alpha = 1.0

    def draw_prepare(self, context):
        grip_idx = 0
        aim_idx = 0
        idx = 0
        scale = 1.0
        for gizmo in self.gizmos:
            is_grip = (gizmo.bl_idname == VIEW3D_GT_vr_controller_grip.bl_idname)
            if (is_grip):
                idx = grip_idx
                grip_idx += 1
                scale = 0.1
            else:
                idx = aim_idx
                aim_idx += 1
                scale = 0.5
            gizmo.matrix_basis = self._get_controller_pose_matrix(context, idx, is_grip, scale)


class VIEW3D_GGT_vr_landmarks(GizmoGroup):
    bl_idname = "VIEW3D_GGT_vr_landmarks"
    bl_label = "VR Landmark Indicators"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options = {'3D', 'PERSISTENT', 'SCALE'}

    @classmethod
    def poll(cls, context):
        view3d = context.space_data
        return (
            view3d.shading.vr_show_landmarks
        )

    def setup(self, context):
        pass

    def draw_prepare(self, context):
        # first delete the old gizmos
        for g in self.gizmos:
            self.gizmos.remove(g)

        scene = context.scene
        landmarks = scene.vr_landmarks

        for lm in landmarks:
            if ((lm.type == 'SCENE_CAMERA' and not scene.camera) or
                    (lm.type == 'OBJECT' and not lm.base_pose_object)):
                continue

            gizmo = self.gizmos.new(VIEW3D_GT_vr_camera_cone.bl_idname)
            gizmo.aspect = 1 / 3, 1 / 4

            gizmo.color = gizmo.color_highlight = 0.2, 1.0, 0.6
            gizmo.alpha = 1.0

            self.gizmo = gizmo

            if lm.type == 'SCENE_CAMERA':
                cam = scene.camera
                lm_mat = cam.matrix_world if cam else Matrix.Identity(4)
            elif lm.type == 'OBJECT':
                lm_mat = lm.base_pose_object.matrix_world
            else:
                angle = lm.base_pose_angle
                raw_rot = Euler((radians(90.0), 0, angle))

                rotmat = Matrix.Identity(3)
                rotmat.rotate(raw_rot)
                rotmat.resize_4x4()

                transmat = Matrix.Translation(lm.base_pose_location)

                lm_mat = transmat @ rotmat

            self.gizmo.matrix_basis = lm_mat


classes = (
    VIEW3D_OT_vr_landmark_add,
    VIEW3D_OT_vr_landmark_remove,
    VIEW3D_OT_vr_landmark_activate,
    VIEW3D_OT_vr_landmark_from_session,
    VIEW3D_OT_vr_camera_landmark_from_session,
    VIEW3D_OT_add_camera_from_vr_landmark,
    VIEW3D_OT_camera_to_vr_landmark,
    VIEW3D_OT_vr_landmark_from_camera,
    VIEW3D_OT_cursor_to_vr_landmark,
    VIEW3D_OT_update_vr_landmark,

    VIEW3D_GT_vr_camera_cone,
    VIEW3D_GT_vr_controller_grip,
    VIEW3D_GT_vr_controller_aim,
    VIEW3D_GGT_vr_viewer_pose,
    VIEW3D_GGT_vr_controller_poses,
    VIEW3D_GGT_vr_landmarks,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)


def execute_M():

    bar_size = 0.5
    bar_ditance = 1.5
    panel_size = 0.25
    panel_th = 0.1
    panels_distance = 2
    panels_sep = 2.0
    text_size = 0.2
    
    styles = ['style_1','style_2','style_3','style_4']
    textures = ['texture_1','texture_2','texture_3','texture_4']
    
    styles_list = ['style_1','style_2','style_3','style_4']
    textures_list = ['texture_1','texture_2','texture_3','texture_4']
    

    try:
        cursor = bpy.data.objects['Cursor'] 
        bar = bpy.data.objects['Bar']  
        bar_bg = bpy.data.objects['Bar_bg']  
        back = bpy.data.objects['Back']  
        prev = bpy.data.objects['Prev']  
        next = bpy.data.objects['Next'] 
        style = bpy.data.objects['Style']  
        texture = bpy.data.objects['Texture']
        hds = bpy.data.objects['HDS'] 
        
        for style_name in styles:
            style = bpy.data.objects[style_name] 
            
        for texture_name in textures:
            texture = bpy.data.objects[texture_name]   
            
    except:
        bpy.ops.mesh.primitive_cylinder_add(radius=0.0005, depth=10, enter_editmode=False, align='WORLD', location=(0, 0, 0), scale=(1, 1, 1))
        bpy.context.active_object.name = 'Cursor'
        cursor = bpy.data.objects['Cursor']       
        bpy.context.scene.cursor.location = (0.0, 0.0, 5)
        bpy.ops.object.origin_set(type='ORIGIN_CURSOR', center='MEDIAN')
        #cursor.hide_viewport = True
        
        bpy.ops.mesh.primitive_uv_sphere_add(radius=bar_size/5.0, enter_editmode=False, align='WORLD', location=(0, 0, 0), rotation=(0, math.pi/2, 0),  scale=(1, 1, 1))
        bpy.context.active_object.name = 'Bar'
        bar = bpy.data.objects['Bar']
        
        #bpy.context.scene.cursor.location = (-bar_size/2.0, 0.0, 0.0)
        #bpy.ops.object.origin_set(type='ORIGIN_CURSOR', center='MEDIAN')
        bpy.ops.mesh.primitive_uv_sphere_add(radius=bar_size/10.0, enter_editmode=False, align='WORLD', location=(0, 0, 0), rotation=(0, math.pi/2, 0),  scale=(1, 1, 1))
        bpy.context.active_object.name = 'Bar_bg'
        bar_bg = bpy.data.objects['Bar_bg']   
        #bpy.context.scene.cursor.location = (-bar_size/2.0, 0.0, 0.0)
        #bpy.ops.object.origin_set(type='ORIGIN_CURSOR', center='MEDIAN')
        
        #bpy.context.scene.cursor.location = (0.0, 0.0, 0.0)
        #bar_bg.location = Vector((0.0,0.0,2.0))
        #bpy.ops.object.origin_set(type='ORIGIN_CURSOR', center='MEDIAN')
        #bar_bg.parent = bpy.data.objects["Bar"]
        
        bpy.ops.mesh.primitive_plane_add(size=panel_size*2.5, enter_editmode=False, align='WORLD', location=(-panel_size*2, 0.3, 0), rotation=(0, -math.pi, math.pi/2.0), scale=(1, 1, 1))
        bpy.context.active_object.name = 'Back'
        bpy.context.object.scale[0] = 0.5
        back = bpy.data.objects['Back']

        bpy.ops.mesh.primitive_plane_add(size=panel_size*2.5, enter_editmode=False, align='WORLD', location=(0.0, 0.0, 0), rotation=(0, 0, 0), scale=(1, 1, 1))
        bpy.context.active_object.name = 'HDS'
        bpy.context.object.scale[0] = 0.5
        hda = bpy.data.objects['HDS']

        bpy.ops.mesh.primitive_plane_add(size=panel_size*2.5, enter_editmode=False, align='WORLD', location=(0, panel_size*2.5, 0), rotation=(0, 0, 0), scale=(1, 1, 1))
        bpy.context.active_object.name = 'Prev'
        bpy.context.object.scale[0] = 0.6
        prev = bpy.data.objects['Prev'] 

        bpy.ops.mesh.primitive_plane_add(size=panel_size*2.5, enter_editmode=False, align='WORLD', location=(0, -panel_size*2.5, 0), rotation=(0, 0, 0), scale=(1, 1, 1))
        bpy.context.active_object.name = 'Next'
        bpy.context.object.scale[0] = 0.6
        next = bpy.data.objects['Next']    

        font_curve = bpy.data.curves.new(type="FONT", name="Font Curve")
        font_curve.body = "Prev"
        font_obj = bpy.data.objects.new(name="Prev Text", object_data=font_curve)
        bpy.context.scene.collection.objects.link(font_obj)
        font_obj.parent = bpy.data.objects["Prev"]
        font_obj.location = (0.05,-0.22, 0.01)
        font_obj.rotation_euler = (0.0, 0.0, math.pi/2.0)
        font_obj.scale = (text_size, text_size, text_size)
        font_obj.active_material = bpy.data.materials['not_selected']  

        font_curve = bpy.data.curves.new(type="FONT", name="Font Curve")
        font_curve.body = "Next"
        font_obj = bpy.data.objects.new(name="Next Text", object_data=font_curve)
        bpy.context.scene.collection.objects.link(font_obj)
        font_obj.parent = bpy.data.objects["Next"]
        font_obj.location = (0.05, -0.16, 0.01)
        font_obj.rotation_euler = (0.0, 0.0, math.pi/2.0)
        font_obj.scale = (text_size, text_size, text_size)
        font_obj.active_material = bpy.data.materials['not_selected']  

        font_curve = bpy.data.curves.new(type="FONT", name="Font Curve")
        font_curve.body = "HDS"
        font_obj = bpy.data.objects.new(name="HDS Text", object_data=font_curve)
        bpy.context.scene.collection.objects.link(font_obj)
        font_obj.parent = bpy.data.objects["HDS"]
        font_obj.location = (0.05, -0.16, 0.01)
        font_obj.rotation_euler = (0.0, 0.0, math.pi/2.0)
        font_obj.scale = (text_size, text_size, text_size)
        font_obj.active_material = bpy.data.materials['not_selected'] 

        font_curve = bpy.data.curves.new(type="FONT", name="Font Curve")
        font_curve.body = "Return\n back"
        font_obj = bpy.data.objects.new(name="Back Text", object_data=font_curve)
        bpy.context.scene.collection.objects.link(font_obj)
        font_obj.parent = bpy.data.objects["Back"]
        font_obj.location = (-0.05, 0.25, -0.005)
        font_obj.rotation_euler = (0.0, -math.pi, math.pi/2.0)
        font_obj.scale = (text_size, text_size, text_size)
        font_obj.active_material = bpy.data.materials['not_selected']  
    
        for i,style_name in enumerate(styles):
            if i >0:
                bpy.ops.mesh.primitive_plane_add(size=panel_size, enter_editmode=False, align='WORLD', location=(i*(panel_size+panel_th), 0, 0), rotation=(0, 0, 0), scale=(1, 1, 1))
                bpy.context.active_object.name = style_name
                bpy.context.active_object.parent = bpy.data.objects[styles[0]]

                bpy.ops.mesh.primitive_plane_add(size=panel_size, enter_editmode=False, align='WORLD', location=(i*(panel_size+panel_th), panel_size*2, 0), rotation=(0, 0, 0), scale=(1, 1, 1))
                bpy.context.active_object.name = style_name+'_label'
                bpy.context.active_object.parent = bpy.data.objects[styles[0]]

                bpy.context.object.scale[1] = 2.0
                font_curve = bpy.data.curves.new(type="FONT", name="Font Curve")
                font_curve.body = styles_list[i]
                font_obj = bpy.data.objects.new(name=styles_list[i], object_data=font_curve)
                bpy.context.scene.collection.objects.link(font_obj)
                font_obj.parent = bpy.data.objects["style_1"]
                font_obj.location = (i*(panel_size+panel_th), panel_size*2+panel_th, 0)
                font_obj.rotation_euler = (0.0, -math.pi, math.pi/2.0)
                font_obj.scale = (text_size*0.5, text_size*0.5, text_size*0.5)
                font_obj.active_material = bpy.data.materials['selected'] 

            else:
                bpy.ops.mesh.primitive_plane_add(size=panel_size, enter_editmode=False, align='WORLD', location=(panel_th, panels_sep/2.0, 0), rotation=(0, 0, 0), scale=(1, 1, 1))
                bpy.context.active_object.name = style_name

                bpy.ops.mesh.primitive_plane_add(size=panel_size, enter_editmode=False, align='WORLD', location=(0.0, panel_size*2, 0), rotation=(0, 0, 0), scale=(1, 1, 1))
                bpy.context.active_object.name = style_name+'_label'
                bpy.context.active_object.parent = bpy.data.objects[styles[0]]
                bpy.context.object.scale[1] = 2.0
                font_curve = bpy.data.curves.new(type="FONT", name="Font Curve")
                font_curve.body = styles_list[i]
                font_obj = bpy.data.objects.new(name=styles_list[i], object_data=font_curve)
                bpy.context.scene.collection.objects.link(font_obj)
                font_obj.parent = bpy.data.objects["style_1"]
                font_obj.location = (0, panel_size*2+panel_th, 0)
                font_obj.rotation_euler = (0.0, -math.pi, math.pi/2.0)
                font_obj.scale = (text_size*0.5, text_size*0.5, text_size*0.5)
                font_obj.active_material = bpy.data.materials['selected'] 

        font_curve = bpy.data.curves.new(type="FONT", name="Font Curve")
        font_curve.body = "Select\n Style"
        font_obj = bpy.data.objects.new(name="Style Text", object_data=font_curve)
        bpy.context.scene.collection.objects.link(font_obj)
        font_obj.parent = bpy.data.objects["style_1"]
        font_obj.location = (-panel_size*2.5, 0.2, 0.0)
        #font_obj.location = (panel_size*5+panel_th, 0.2, 0.0)
        font_obj.rotation_euler = (0.0, -math.pi, math.pi/2.0)
        font_obj.scale = (text_size, text_size, text_size)
        font_obj.active_material = bpy.data.materials['selected']

        bpy.ops.mesh.primitive_plane_add(size=panel_size*2.5, enter_editmode=False, align='WORLD', location=(-panel_size*2, 0.0, 0), rotation=(0, -math.pi, math.pi/2.0), scale=(1, 1, 1))
        bpy.context.active_object.name = 'Style'
        bpy.context.object.scale[0] = 1.2
        style = bpy.data.objects['Style']
        style.parent = bpy.data.objects["style_1"]

        for i,texture_name in enumerate(textures):
            if i >0:
                bpy.ops.mesh.primitive_plane_add(size=panel_size, enter_editmode=False, align='WORLD', location=(i*(panel_size+panel_th), 0, 0), rotation=(0, 0, 0), scale=(1, 1, 1))
                bpy.context.active_object.name = texture_name
                bpy.context.active_object.parent = bpy.data.objects[textures[0]]

                bpy.ops.mesh.primitive_plane_add(size=panel_size, enter_editmode=False, align='WORLD', location=(i*(panel_size+panel_th), -panel_size*2, 0), rotation=(0, 0, 0), scale=(1, 1, 1))
                bpy.context.active_object.name = texture_name+'_label'
                bpy.context.active_object.parent = bpy.data.objects[textures[0]]
                bpy.context.object.scale[1] = 2.0
                font_curve = bpy.data.curves.new(type="FONT", name="Font Curve")
                font_curve.body = textures_list[i]
                font_obj = bpy.data.objects.new(name=textures_list[i], object_data=font_curve)
                bpy.context.scene.collection.objects.link(font_obj)
                font_obj.parent = bpy.data.objects["texture_1"]
                font_obj.location = (i*(panel_size+panel_th/2.0), -panel_size-panel_th, 0)
                font_obj.rotation_euler = (0.0, -math.pi, math.pi/2.0)
                font_obj.scale = (text_size*0.5, text_size*0.5, text_size*0.5)
                font_obj.active_material = bpy.data.materials['selected'] 

            else:
                bpy.ops.mesh.primitive_plane_add(size=panel_size, enter_editmode=False, align='WORLD', location=(panel_th, -panels_sep/2.0, 0), rotation=(0, 0, 0), scale=(1, 1, 1))
                bpy.context.active_object.name = texture_name
                
                bpy.ops.mesh.primitive_plane_add(size=panel_size, enter_editmode=False, align='WORLD', location=(0, -panel_size*2, 0), rotation=(0, 0, 0), scale=(1, 1, 1))
                bpy.context.active_object.name = texture_name+'_label'
                bpy.context.active_object.parent = bpy.data.objects[textures[0]]
                bpy.context.object.scale[1] = 2.0
                font_curve = bpy.data.curves.new(type="FONT", name="Font Curve")
                font_curve.body = textures_list[i]
                font_obj = bpy.data.objects.new(name=textures_list[i], object_data=font_curve)
                bpy.context.scene.collection.objects.link(font_obj)
                font_obj.parent = bpy.data.objects["texture_1"]
                font_obj.location = (0, -panel_size-panel_th/2.0, 0)
                font_obj.rotation_euler = (0.0, -math.pi, math.pi/2.0)
                font_obj.scale = (text_size*0.5, text_size*0.5, text_size*0.5)
                font_obj.active_material = bpy.data.materials['selected'] 

        font_curve = bpy.data.curves.new(type="FONT", name="Font Curve")
        font_curve.body = "  Select\n Texture"
        font_obj = bpy.data.objects.new(name="Texture Text", object_data=font_curve)
        bpy.context.scene.collection.objects.link(font_obj)
        font_obj.parent = bpy.data.objects["texture_1"]
        font_obj.location = (-panel_size*2.5, 0.39, 0.0)
        font_obj.rotation_euler = (0.0, -math.pi, math.pi/2.0)
        font_obj.scale = (text_size, text_size, text_size)
        font_obj.active_material = bpy.data.materials['selected'] 

        bpy.ops.mesh.primitive_plane_add(size=panel_size*2.5, enter_editmode=False, align='WORLD', location=(-panel_size*2, 0.0, 0.0), rotation=(0, -math.pi, math.pi/2.0), scale=(1, 1, 1))
        bpy.context.active_object.name = 'Texture'
        bpy.context.object.scale[0] = 1.2
        texture = bpy.data.objects['Texture']
        texture.parent = bpy.data.objects["texture_1"]
               

    bar.scale = (0.0, 0.0, 0.0)

    max_time_to_select = 20
    
    scene = bpy.context.scene
    
    wm = bpy.context.window_manager

    loc = wm.xr_session_state.viewer_pose_location
    rot = wm.xr_session_state.viewer_pose_rotation
    camera = bpy.context.scene.camera
    cursor.location = loc
    cursor.rotation_euler = rot.to_euler()
    #cursor.rotation_euler = context.scene.camera.rotation_euler
    #cursor.location = context.scene.camera.location 
    
    #loc, rot, _= camera.matrix_world.decompose()
    offset = Vector((0.0, 0.0, -bar_ditance))  # Change this to adjust the distance from the camera
    position = loc + rot @ offset
    
    bar.location = position
    bar_bg.location = position
    
    wm = bpy.context.window_manager

    loc = wm.xr_session_state.viewer_pose_location
    rot = wm.xr_session_state.viewer_pose_rotation
    camera = bpy.context.scene.camera
    cursor.location = loc
    cursor.rotation_euler = rot.to_euler()
    rot_eu = rot.to_euler()
    bar.rotation_euler = (math.pi/2,rot_eu[1],rot_eu[2]+math.pi/2)
    bar_bg.rotation_euler = (math.pi/2,rot_eu[1],rot_eu[2]+math.pi/2)
    
    print('state:',scene.selectionState)
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
        bpy.data.objects[styles[0]].location = Vector((0.0,0.0,-200))
        bpy.data.objects[textures[0]].location = Vector((0.0,0.0,-200))
        scene.selectionState = 0
        back.location = Vector((0.0,0.0,-200))
    
    # Create bmesh objects for the mesh data
    bm1 = bmesh.new()
    bm1.from_mesh(cursor.data)
    bm1.transform(cursor.matrix_world)
    obj_now_BVHtree = BVHTree.FromBMesh(bm1)
    
    new_selected_obj = ''
    for obj_idx, obj in enumerate(bpy.context.scene.objects):
        if obj.type == "MESH" and (not obj.name in ['Cursor','Bar','Bar_bg','Style','Texture']):
            bm2 = bmesh.new()
            bm2.from_mesh(obj.data)
            bm2.transform(obj.matrix_world) 
            obj_next_BVHtree = BVHTree.FromBMesh(bm2)           

            #get intersecting pairs
            inter = obj_now_BVHtree.overlap(obj_next_BVHtree)
            if inter:
                if len(obj.data.materials) > 2:
                    if obj.name == "floor_shade":
                        pass
                    else:
                        obj.active_material = obj.data.materials[2]
                else:
                    obj.active_material = bpy.data.materials['selected']
                print('Intersect with: ', obj)
                new_selected_obj = obj.name
                if obj.name != scene.selectedDull:
                    break
                #return (obj_idx,)
            else:
                if len(obj.data.materials) > 2:
                    if obj.name == "floor_shade":
                        pass
                    else:
                        obj.active_material = obj.data.materials[1]
                else:
                    obj.active_material = bpy.data.materials['not_selected']
    
    scene.elapsedTime += 1

    if new_selected_obj != '':
        if scene.selectedObject != new_selected_obj:
            scene.selectedObject = new_selected_obj
            scene.elapsedTime = 0
        elif scene.elapsedTime >= max_time_to_select:
            print('Selected: ', scene.selectedObject)
            if scene.selectionState == 2 and scene.selectedObject in textures+styles:
                if scene.currentSceneHDRI == 2:
                    file = r'C:\Users\lopez\Desktop\Hackathon\OthersssCode\Hackupc2023-DahTeam\customviewport_vr_preview\assets\cool_texture_'+str(bpy.context.scene.currentFalseTexture)+'.jpg'
                    scene.currentFalseTexture += 1
                    if scene.currentFalseTexture > 4:
                        scene.currentFalseTexture = 1
                    nodes = bpy.data.materials["Transparent Material4_floor"].node_tree.nodes
                    texture_node = nodes["Image Texture"]
                    texture_node.image = getCyclesImage(file)
                    bpy.data.objects["floor_shade"].active_material = bpy.data.materials["Transparent Material4_floor"]
                else:
                    if '_shade' in scene.selectedMesh:
                        print('Mesh selected: ', scene.selectedMesh)
                        real_name = scene.selectedMesh.split('_')[0]
                        bpy.data.scenes["Scene"].dream_textures_project_prompt.prompt_structure_token_subject = \
                            real_name+" "+scene.selectedObject.split('_')[0]
                        #bpy.ops.mesh.select_all(action='DESELECT')
                        bpy.data.objects[scene.selectedMesh].select_set(state=True)
                        bpy.ops.object.editmode_toggle()
                        bpy.ops.mesh.select_all(action='SELECT')
                        bpy.ops.shade.dream_texture_project()
                        bpy.ops.object.editmode_toggle()
        
                scene.selectionState = 3
                scene.elapsedTime = 0
                scene.selectedDull = ''
            elif scene.selectionState == 0 and (not scene.selectedObject in ['Next','Prev', 'Back','Back Text','Prev Text','Next Text', 'HDS', 'HDS Text']):
                scene.selectionState = 1
                scene.selectedMesh=scene.selectedObject
                scene.elapsedTime = 0
                scene.selectedDull = ''
            elif scene.selectedObject in ['Next','Next Text']:
                scene.selectionState = 3
                scene.elapsedTime = 0
                scene.selectedDull = ''
                scene.currentSceneHDRI += 1
                if scene.currentSceneHDRI > 3:
                    scene.currentSceneHDRI = 1
                loadNewHDRI(scene.currentSceneHDRI)
                # delete all objects containing _shade in the name
                for obj in bpy.data.objects:
                    if "_shade" in obj.name:
                        bpy.data.objects.remove(obj, do_unlink=True)
                loadPickle(scene.currentSceneHDRI)
                
            elif scene.selectedObject in ['Prev','Prev Text']:
                scene.selectionState = 3
                scene.elapsedTime = 0
                scene.selectedDull = ''
                scene.currentSceneHDRI -= 1
                if scene.currentSceneHDRI < 1:
                    scene.currentSceneHDRI = 3
                loadNewHDRI(scene.currentSceneHDRI)
                # delete all objects containing _shade in the name
                for obj in bpy.data.objects:
                    if "_shade" in obj.name:
                        bpy.data.objects.remove(obj, do_unlink=True)
                loadPickle(scene.currentSceneHDRI)

            elif scene.selectedObject in ['HDS','HDS Text']:
                scene.selectionState = 3
                scene.elapsedTime = 0
                scene.selectedDull = ''
                if scene.currentSceneIsDepth:
                    scene.currentSceneIsDepth = False
                else:
                    scene.currentSceneIsDepth = True
                loadNewHDRI(scene.currentSceneHDRI)
            elif scene.selectionState == 2 and scene.selectedObject in ['Back','Back Text']:
                scene.selectionState = 3
                scene.elapsedTime = 0
                scene.selectedDull = ''
            else:
                scene.elapsedTime = max_time_to_select
                scene.selectedDull = scene.selectedObject

                
    else:
        scene.elapsedTime = 0
        
    percentage = min(1.0, scene.elapsedTime / max_time_to_select)
    #print(percentage)
    if percentage > 0:
        bar.scale = (percentage, percentage, percentage)
        
    else:
        bar.scale = (0.0, 0.0, 0.0)

    #print(scene.selectionState)
    return {'FINISHED'}

def getGroundHdriNodeGroup():
    if "GroundHdri" not in bpy.data.node_groups:
        blendfile = r"C:\Users\lopez\Desktop\LilySurfaceScraper\database.blend"
        section   = "\\NodeTree\\"
        object    = "GroundHdri"
        filepath  = blendfile + section + object
        directory = blendfile + section
        filename  = object
        bpy.ops.wm.append(
            filepath=filepath,
            filename=filename,
            directory=directory)
    return bpy.data.node_groups["GroundHdri"]

def guessColorSpaceFromExtension(img):
    """Guess the most appropriate color space from filename extension"""
    img = img.lower()
    if img.endswith(".jpg") or img.endswith(".jpeg") or img.endswith(".png"):
        return {
            "name": "sRGB",
            "old_name": "COLOR", # mostly for backward compatibility
        }
    else:
        return {
            "name": "Linear",
            "old_name": "NONE",
        }

def getCyclesImage(imgpath):
    """Avoid reloading an image that has already been loaded"""
    for img in bpy.data.images:
        if os.path.abspath(img.filepath) == os.path.abspath(imgpath):
            return img
    return bpy.data.images.load(imgpath)

class PrincipledWorldWrapper:
    """This is a wrapper similar in use to PrincipledBSDFWrapper (located in
    bpy_extras.node_shader_utils) but for use with worlds. This is required to
    avoid relying on node names, which depend on Blender's UI language settings
    (see issue #7) """

    def __init__(self, world):
        self.node_background = None
        self.node_out = None
        for n in world.node_tree.nodes:
            if self.node_background is None and n.type == "BACKGROUND":
                self.node_background = n
            elif self.node_out is None and n.type == "OUTPUT_WORLD":
                self.node_out = n


class AssetLoader(Operator):
    bl_idname = "asset.load_assets"
    bl_label = "Load Assets"
    bl_description = "This is the hello world operator"

    
    def execute(
        self, context):
        bpy.data.scenes["Scene"].dream_textures_project_prompt.prompt_structure_token_subject = "sofa, rojo"
        bpy.context.scene.dream_textures_project_prompt.use_size = True
        bpy.context.scene.dream_textures_project_prompt.height = 128
        bpy.context.scene.dream_textures_project_prompt.width = 128
        bpy.context.scene.dream_textures_project_prompt.model = 'models--stabilityai--stable-diffusion-2-depth'
        bpy.context.scene.dream_textures_project_prompt.optimizations_sequential_cpu_offload = True
        bpy.context.scene.dream_textures_project_prompt.optimizations_batch_size = 1
        bpy.context.scene.dream_textures_project_prompt.scheduler = 'Euler Ancestral Discrete'
        bpy.context.scene.currentFalseTexture = 1
        loadHDRIs(context)
        loadPickle(context.scene.currentSceneHDRI)
        return {'FINISHED'}

def loadNewHDRI(id):
    if bpy.context.scene.currentSceneIsDepth:
        new_img = bpy.data.images["hdri_"+str(id)+"_depth.jpg"]
    else:
        new_img = bpy.data.images["hdri_"+str(id)+".jpg"]
    world = bpy.context.scene.world
    nodes = world.node_tree.nodes
    environment_texture_node = nodes["Environment Texture"]
    environment_texture_node.image = new_img

def loadHDRIs(context):

    # INIT VARIABLES DEL IZAN
    context.scene.elapsedTime = 0
    context.scene.selectedObject = ''
    context.scene.selectionState = 3
    context.scene.selectedDull = ''
    # get the files of a folder


    txtfiles = []
    for file in glob.glob(r"C:\Users\lopez\Desktop\Hackathon\OthersssCode\Hackupc2023-DahTeam\customviewport_vr_preview\assets\*.jpg"):
        txtfiles.append(file)
        file_name = file.split("\\")[-1]
        getCyclesImage(file)
        #bpy.ops.image.open(filepath=file, directory="C:\\Users\\lopez\\Desktop\\Hackathon\\blender_final_plugin\\assets\\", files=[{"name":file_name, "name":file_name}], relative_path=True, show_multiview=False)

    file = txtfiles[4]
    #for i in list(context.scene.world.node_tree.nodes):
    #    print(i.name)
    #    context.scene.world.node_tree.nodes.remove(i)
    PrincipledWorldWrapper
    world = context.scene.world
    nodes = world.node_tree.nodes
    links = world.node_tree.links
    principled_world = PrincipledWorldWrapper(world)
    background = principled_world.node_background
    texture_node = nodes.new(type="ShaderNodeTexEnvironment")
    texture_coordinate_node = nodes.new(type="ShaderNodeTexCoord")
    texture_node.image = getCyclesImage(file)
    color_space = guessColorSpaceFromExtension(file)
    texture_node.image.colorspace_settings.name = color_space["name"]
    if hasattr(texture_node, "color_space"):
        texture_node.color_space = color_space["old_name"]
    mapping_node = nodes.new(type="ShaderNodeMapping")
    links.new(texture_node.outputs["Color"], background.inputs["Color"])
    links.new(texture_coordinate_node.outputs["Generated"], mapping_node.inputs["Vector"])
    mapping_node.inputs[1].default_value = (0, 0, 0.0)

    links.new(mapping_node.outputs[0], texture_node.inputs[0])


    camera_data = bpy.data.cameras.new(name='Camera2')
    context.scene.camera = bpy.data.objects.new('Camera2', camera_data)

    bpy.context.scene.render.resolution_x = 1080
    bpy.context.scene.render.resolution_y = 1080
    # Set the output format
    bpy.context.scene.render.image_settings.file_format = "PNG"
    bpy.context.space_data.shading.type = 'RENDERED'
    context.scene.camera.data.lens_unit = 'FOV'
    context.scene.camera.data.angle = 100*pi/180
    context.scene.camera.rotation_euler[0] = 1.5708
    context.scene.camera.rotation_euler[1] = 0
    context.scene.camera.rotation_euler[2] = 0
    context.scene.camera.location[2] = 1.0

    for i in range(4):
        

        # bpy.ops.mesh.primitive_plane_add(size=2, enter_editmode=False, align='WORLD', location=(0, 0, i), scale=(1, 1, 1))
        # bpy.ops.material.new()
        # plane = bpy.data.objects[-1]
        # plane.data.materials.append(bpy.data.materials[-1])
        # material = plane.active_material
        # m_tree = material.node_tree
        # m_nodes = m_tree.nodes
        # m_links = m_tree.links
        # texture_node = m_nodes.new(type="ShaderNodeTexImage")
        # texture_coordinate_node = m_nodes.new(type="ShaderNodeTexCoord")
        # file = r"C:\Users\lopez\Desktop\Hackathon\blender_final_plugin\assets\output"+str(i)+".png"
        # texture_node.image = getCyclesImage(file)
        # color_space = guessColorSpaceFromExtension(file)
        # texture_node.image.colorspace_settings.name = color_space["name"]
        # m_links.new(m_nodes["Material Output"].inputs[0], texture_node.outputs[0])
        # mod = plane.modifiers.new("subsurf", 'SUBSURF')
        # plane.modifiers[0].levels = 7
        # plane.modifiers[0].subdivision_type = 'SIMPLE'
        
        # modifier = plane.modifiers.new(type='DISPLACE', name="disp"+str(i))
        # bpy.ops.texture.new()
        # texture = bpy.data.textures[-1]
        # modifier.texture = texture
        # file = r"C:\Users\lopez\Desktop\Hackathon\blender_final_plugin\assets\output"+str(i)+"_depth.png"
        # texture.image = getCyclesImage(file)
        
        pass


        
        
        # 
        # context.active_object = bpy.data.objects["Plane"]
        # context.active_object.name = "Plane"+str(i)
        # bpy.ops.object.modifier_add(type='SUBSURF')
        # context.object.modifiers["Subdivision"].subdivision_type = 'SIMPLE'
        # context.object.modifiers["Subdivision"].levels = 7
        # bpy.ops.object.modifier_apply(modifier="Subdivision")
        # context.active_object.data.location[2] = i
        # 
