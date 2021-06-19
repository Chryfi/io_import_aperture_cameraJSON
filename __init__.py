bl_info = {
    "name": "Aperture JSON tracking import",
    "author": "Christian F. (known as Chryfi)",
    "version": (1, 1, 1),
    "blender": (2, 80, 0),
    "location": "File > Import",
    "description": "Import tracking data from a json file generated by the Aperture Mod.",
    "warning": "",
    "category": "Import"
}

import bpy
import json
import math
from math import sqrt
import traceback
import sys
import os
import numpy

from mathutils import Euler
from bpy.props import (BoolProperty, StringProperty)
from bpy_extras.io_utils import (ImportHelper, path_reference_mode)

class ImportJSON(bpy.types.Operator, ImportHelper):
    # Panel's information
    bl_idname = "test.open_filbrowser"
    bl_label = 'Import Aperture JSON'
    bl_options = {'PRESET'}

    # Panel's properties
    filename_ext = ".json"
    filter_glob = StringProperty(default="*.json", options={'HIDDEN'})
    use_selection = BoolProperty(name="Selection only", description="Import selected json only", default=False)
    path_mode = path_reference_mode
    check_extension = True

    def execute(self, context):
        file = open(self.properties.filepath,)
        data = json.load(file)
        obj_camera = bpy.context.scene.camera
        frameOffset = 1 #first frame of minema rendered video are not usable.
        ignoreFrame = -1
        coordinateCorrectionX = 0 #seems as if the x coordinate needs to be 0.05 off

        if obj_camera is None:
            self.report({"WARNING"}, "No active camera found in the scene.")
            file.close()
            return {"CANCELLED"}

        try:
            if "information" in data:
                renderInfo = data["information"]
                bpy.context.scene.render.fps = renderInfo["fps"]
                bpy.context.scene.render.resolution_x = renderInfo["resolution"][0]
                bpy.context.scene.render.resolution_y = renderInfo["resolution"][1]
                ignoreFrame = round(renderInfo["motionblur_fps"]) / bpy.context.scene.render.fps 
                
                if renderInfo["held_frames"] > 1:
                    frameOffset = 1
            
            obj_camera.delta_location = (0, coordinateCorrectionX, 0)

            #interpolation data
            #x_points = [ 2.5,  2.81,  3.125,   3.75,   5,   6.25,    7.5,     10,  12.5,  15,    20,   25,    30,  35,    40,     50,    60,    70,     80,   90,  100,  110,    120,  130,  140]
            #y_points = [ 422, 375.5, 337.75, 281.25, 211, 168.75, 140.63, 105.25,  84.1,  70, 52.15, 41.4, 34.25,  29, 25.13, 19.525, 15.63, 12.75, 10.525, 8.68, 7.125, 5.71, 4.535, 3.41, 2.35]

            obj_camera.rotation_mode = 'XYZ'
            obj_camera.data.sensor_fit = 'VERTICAL'

            for frame in range(len(data["camera-tracking"])):
                
                blenderFrame = frame

                if ignoreFrame != -1:
                    if int(frame)%int(ignoreFrame) != 0:
                        continue
                    blenderFrame = int(int(frame) // ignoreFrame)

                frameData = data["camera-tracking"][frame]
            
                obj_camera.location = (frameData["position"][0], -frameData["position"][2], frameData["position"][1])
                obj_camera.delta_rotation_euler  = Euler((math.radians(90-frameData["angle"][3]), 0, math.radians(-frameData["angle"][2]-180)), 'XYZ')
                obj_camera.rotation_euler = Euler((0, 0, -math.radians(frameData["angle"][1])), 'XYZ')

                #NyanLi https://github.com/NyaNLI helped a lot to figure out how to convert Minecraft FOV to Blender's FOV
                #fov*1.1 because of specator mode and dynamic fov
                obj_camera.data.lens =  0.5/(math.tan(1.1*math.radians(frameData["angle"][0])/2)) * obj_camera.data.sensor_height

                obj_camera.keyframe_insert(data_path="location", frame=blenderFrame+frameOffset)
                obj_camera.keyframe_insert(data_path="delta_rotation_euler", frame=blenderFrame+frameOffset)
                obj_camera.keyframe_insert(data_path="rotation_euler", frame=blenderFrame+frameOffset)
                obj_camera.data.keyframe_insert(data_path="lens", frame=blenderFrame+frameOffset)

            if "entities" in data:
                entities = data["entities"]
                keyset = entities.keys()

                for entityKey in keyset:
                    entity = entities[entityKey]
                    bpy.ops.object.armature_add()
                    obj = bpy.context.active_object
                
                    obj.name = entityKey

                    for frame in range(len(entity)):

                        blenderFrame = frame

                        if ignoreFrame != -1:
                            if int(frame)%int(ignoreFrame) != 0:
                                continue
                            blenderFrame = int(int(frame) // ignoreFrame)

                        frameData = entity[frame]

                        if "body_rotation" in frameData:
                            obj.delta_rotation_euler  = Euler((math.radians(90-frameData["body_rotation"][2]), 0, math.radians(-frameData["body_rotation"][1])), 'XYZ')
                            obj.keyframe_insert(data_path="delta_rotation_euler", frame=blenderFrame+frameOffset)

                        obj.location = (frameData["position"][0], -frameData["position"][2], frameData["position"][1])
                        obj.keyframe_insert(data_path="location", frame=blenderFrame+frameOffset)

        except:
            traceback.print_exc()
            self.report({"WARNING"}, "An error occured while reading the file.")
            file.close()
            return {"CANCELLED"}
        
        file.close()
        return{'FINISHED'}

# Register and stuff
def menu_func_export(self, context):
    self.layout.operator(ImportJSON.bl_idname, text="JSON cameradata (.json)")

classes = (
    ImportJSON, 
)

def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)

    bpy.types.TOPBAR_MT_file_import.append(menu_func_export)

def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)

    bpy.types.TOPBAR_MT_file_import.remove(menu_func_export)
