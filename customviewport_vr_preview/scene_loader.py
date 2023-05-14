import os
import bpy
import pickle
from skimage import measure
import numpy as np
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


def loadPickle(file_path):
    file_path = r'C:\Users\lopez\Desktop\Hackathon\OthersssCode\Hackupc2023-DahTeam\customviewport_vr_preview\assets\hdri_'+str(file_path)+'.pickle'
    result = ""
    with open(file_path,'rb') as data:
        result = pickle.load(data)

    contour_points = []
    for i in result:
        print(str(i))
        mask = result[i]#["segmentation"]
        contours = measure.find_contours(mask, 0.5)
        # Create a simplified shape using only the outer contour
        current_objects = []
        for outer_contour in contours:
            # Plot the simplified shape
            simplified_contour = measure.approximate_polygon(outer_contour, tolerance=.5)

            # Plot the simplified shape
            #plt.plot(simplified_contour[:, 1], simplified_contour[:, 0], 'k')
            normalized_contour = simplified_contour.copy()
            normalized_contour[:, 0] /= mask.shape[0] 
            normalized_contour[:, 1] /= mask.shape[1] 

            lon = np.pi * normalized_contour[:, 0]  + np.pi / 2
            lat = -2* np.pi * normalized_contour[:, 1] 

            # Convert to Cartesian coordinates
            x = 3* np.cos(lat) * np.cos(lon)
            y = 3* np.sin(lat) *  np.cos(lon)
            z = 3* np.sin(lon) + 1.0
            # Create a simplified mesh plot
            #plt.pcolormesh(mask, cmap='binary')
            contour_points = []
            for j in range(len(x)):
                contour_points.append( 
                    (x[j], y[j], z[j]))

            # Create a new mesh object
            mesh_data = bpy.data.meshes.new("CustomMesh")
            mesh_obj = bpy.data.objects.new("CustomMeshObject", mesh_data)

            # Link the object to the scene collection
            scene = bpy.context.scene
            scene.collection.objects.link(mesh_obj)

            # Create the vertices
            vertices = []
            for point in contour_points:
                vertices.append(point)

            # Create the edges and faces
            edges = []
            for j in range(len(vertices)):
                edges.append((j, (j+1) % len(vertices)))

            faces = [tuple(j for j in range(len(vertices)))]

            # Assign the vertices, edges, and faces to the mesh
            mesh_data.from_pydata(vertices, edges, faces)
            mesh_data.update()
            current_objects.append(mesh_obj)
        # merge all the object meshes
        bpy.ops.object.select_all(action='DESELECT')
        for obj in current_objects:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = current_objects[0]
        bpy.ops.object.join()
        bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='MEDIAN')
        bpy.context.object.name = i+"_shade"


        # create four empty materials for the object
        mat = bpy.data.materials.new(name="Transparent Material_"+i)
        mat.use_nodes = True
        mat.node_tree.nodes["Principled BSDF"].inputs["Alpha"].default_value = 0.5
        mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.0, 0.0, 0.0, 1.0)
        mat.node_tree.nodes["Principled BSDF"].inputs["Metallic"].default_value = 0.0
        mat.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.0
        mat.node_tree.nodes["Principled BSDF"].inputs["Specular"].default_value = 0.0
        mat.blend_method = 'BLEND'

        mat2 = bpy.data.materials.new(name="Transparent Material2_"+i)
        mat2.use_nodes = True
        mat2.node_tree.nodes["Principled BSDF"].inputs["Alpha"].default_value = 0.0
        mat2.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.0, 0.0, 0.0, 1.0)
        mat2.node_tree.nodes["Principled BSDF"].inputs["Metallic"].default_value = 0.0
        mat2.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.0
        mat2.node_tree.nodes["Principled BSDF"].inputs["Specular"].default_value = 0.0
        mat2.blend_method = 'BLEND'

        mat3 = bpy.data.materials.new(name="Transparent Material3_"+i)
        mat3.use_nodes = True
        mat3.node_tree.nodes["Principled BSDF"].inputs["Alpha"].default_value = 0.75
        mat3.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.0, 1.0, 0.0, 1.0)
        mat3.node_tree.nodes["Principled BSDF"].inputs["Metallic"].default_value = 0.0
        mat3.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.0
        mat3.node_tree.nodes["Principled BSDF"].inputs["Specular"].default_value = 0.0
        mat3.blend_method = 'BLEND'

        mat4 = bpy.data.materials.new(name="Transparent Material4_"+i)
        mat4.use_nodes = True
        mat4.node_tree.nodes["Principled BSDF"].inputs["Alpha"].default_value = 0.0
        mat4.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.0, 0.0, 0.0, 1.0)
        mat4.node_tree.nodes["Principled BSDF"].inputs["Metallic"].default_value = 0.0
        mat4.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.0
        mat4.node_tree.nodes["Principled BSDF"].inputs["Specular"].default_value = 0.0
        mat4.blend_method = 'BLEND'

        if i == "floor":
            file = r'C:\Users\lopez\Desktop\Hackathon\OthersssCode\Hackupc2023-DahTeam\customviewport_vr_preview\assets\cool_texture_'+str(bpy.context.scene.currentFalseTexture)+'.jpg'
            nodes = mat4.node_tree.nodes
            links = mat4.node_tree.links
            texture_node = nodes.new(type="ShaderNodeTexImage")
            texture_coordinate_node = nodes.new(type="ShaderNodeTexCoord")
            texture_node.image = getCyclesImage(file)
            color_space = guessColorSpaceFromExtension(file)
            texture_node.image.colorspace_settings.name = color_space["name"]
            mapping_node = nodes.new(type="ShaderNodeMapping")
            links.new(texture_node.outputs[0], nodes["Material Output"].inputs[0])
            links.new(texture_coordinate_node.outputs[0], mapping_node.inputs[0])
            links.new(mapping_node.outputs[0], texture_node.inputs[0])
            
        # append all the materials to the active object
        bpy.context.object.data.materials.append(mat)
        bpy.context.object.data.materials.append(mat2)
        bpy.context.object.data.materials.append(mat3)
        bpy.context.object.data.materials.append(mat3)
        # set the active material to the first material
        bpy.context.object.active_material = bpy.data.materials['Transparent Material_'+i]
        
        #bpy.context.object.active_material = bpy.data.materials['Transparent Material']
        
