#!/usr/bin/env python
import os
import time

import roslib
import rospy
import moveit_commander

import geometry_msgs.msg
from moveit_trajectory_planner.srv import *
from std_srvs.srv import Empty

from world_manager_helpers.extended_planning_scene_interface import ExtendedPlanningSceneInterface
from world_manager_helpers.model_rec_manager import ModelManager, ModelRecManager
from world_manager_helpers.object_filename_dict import file_name_dict

roslib.load_manifest('moveit_trajectory_planner')


class WorldManager:

    def __init__(self):
        moveit_commander.roscpp_initialize(sys.argv)
        self.scene = ExtendedPlanningSceneInterface()
        self.robot = moveit_commander.RobotCommander()
        
        #init the server node
        self.add_box_server = rospy.Service('moveit_trajectory_planner/add_box', BoxInfo, self.handle_add_box)
        self.add_autoscaled_mesh_server = rospy.Service('moveit_trajectory_planner/add_autoscaled_mesh', MeshInfo, self.handle_add_autoscaled_mesh)
        self.remove_object_server = rospy.Service('moveit_trajectory_planner/remove_object', ObjectName, self.handle_remove_object)

        #model_rec_manager for all the objects in the enviornment
        self.model_manager = ModelRecManager()
        #a cache of all of the object names in the enviorment, for use with remove_all_objects
        self.body_name_cache = []

        self.refresh_model_list_server = rospy.Service('model_manager/refresh_model_list', Empty, self.refresh_model_list)
        self.reload_model_list_server = rospy.Service('model_manager/reload_model_list', Empty, self.reload_model_list)

    def handle_add_box(self, req):
        box_dimensions = (req.sizeX, req.sizeY, req.sizeZ);
        self.scene.add_box(req.name, req.pose, box_dimensions)
        return BoxInfoResponse()

    def handle_add_autoscaled_mesh(self, req):
        """
        Adds a mesh, but makes sure that the mesh is scaled to meters if given a mesh that 
        is in millimeters. 
        """
        if(os.path.isfile(req.filename)):
            self.scene.add_mesh_autoscaled(req.name, req.pose, req.filename)
        else:
            rospy.logwarn('File doesn\'t exist - object %s, filename %s'%(req.name, req.filename))

        return MeshInfoResponse()

    def handle_remove_object(self, req):
        self.scene.remove_world_object(req.name)
        return ObjectNameResponse()

    ###########################################################################
    #new stuff - from GraspExecutor()
    def refresh_model_list(self, empty_msg):                
        self.model_manager.refresh()
        self.model_manager()

        #self.remove_object_publisher.publish('ALL') #commented lines for graspit
        #self.publish_table_models()
        self.remove_all_objects_from_planner()
        self.add_all_objects_to_planner()
        #need to return [] for empty response
        return []

    def reload_model_list(self, empty_msg):
        self.model_manager.read()
        self.model_manager()

        #self.remove_object_publisher.publish('ALL') #commented lines for graspit
        #self.publish_table_models()
        self.remove_all_objects_from_planner()
        self.add_all_objects_to_planner()
        return []

    def get_model_list(self, empty_msg):
        self.world_manager.read()

    def remove_all_objects_from_planner(self):
        """
        @brief - Clears all models from moveit enivornment (from name cache)

        FIXME - Add additional obstacles for camera post and computers around robot
        and some way of annotating that they shouldn't be removed.
        """
        for index in range(len(self.body_name_cache)):
            body_name = self.body_name_cache[index]
            self.scene.remove_world_object(body_name)
            #del self.body_name_cache[index]
            #del body_name

    def add_all_objects_to_planner(self):
        """
        @brief - Adds all of the models in the model_rec_manager to moveit enviornment and adds names to cache
        """
        for model in self.model_manager.model_list:
            object_name = model.model_name.strip('/')
            filename = file_name_dict[object_name]
            if(os.path.isfile(filename)):
                stampedModelPose = geometry_msgs.msg.PoseStamped()
                stampedModelPose.header.frame_id = self.robot.get_planning_frame()

                print "============================="
                print "adding:"
                print object_name
                stampedModelPose.pose = model.pose
                self.scene.add_mesh_autoscaled(object_name, stampedModelPose, filename)
                print "============================="
            else:
                rospy.logwarn('File doesn\'t exist - object %s, filename %s'%(object_name, filename))

            self.body_name_cache.append(object_name)


    """
    #Graspit stuff
    def publish_table_models(self):
        ""
        @brief - Publishes only the objects that are in a prism above the table to GraspIt                
        ""

        #Republish all of the object pose TFs
        self.model_manager()

        #get a list of models in that cube above the table
        table_models = [model for model in self.model_manager.model_list
                        if self.point_within_table_cube(model.get_world_pose().position)]

        #Print a list of rejected models to the terminal
        print '\ n'.join(['Model rejected %'s''%(model.object_name)
                        for model in self.model_manager.model_list if model not in table_models])
                
        #For each model in the valid model list, add the model to the object list
        #and publish it to GraspIt!
        #FIXME -- needs to use scene message
        object_list = []
        scene_msg = graspit_msgs.msg.SceneInfo()
        for model in table_models:
            model()
                        
            p = model.get_world_pose()
            print "Model name: %'s'"%(model.object_name)
            print p
            object_list.append(graspit_msgs.msg.ObjectInfo(
                                                  model.object_name, model.model_name, p))
            scene_msg.objects = object_list
            self.graspit_scene_publisher.publish(scene_msg)def publish_table_models(self):
            ""
            @brief - Publishes only the objects that are in a prism above the table to GraspIt                
            ""

            #Republish all of the object pose TFs
            self.model_manager()

            #get a list of models in that cube above the table
            table_models = [model for model in self.model_manager.model_list
                                if self.point_within_table_cube(model.get_world_pose().position)]

            #Print a list of rejected models to the terminal
            print '\ n'.join(['Model rejected %'s''%(model.object_name)
                                for model in self.model_manager.model_list if model not in table_models])
                
            #For each model in the valid model list, add the model to the object list
            #and publish it to GraspIt!
            #FIXME -- needs to use scene message
            object_list = []
            scene_msg = graspit_msgs.msg.SceneInfo()
            for model in table_models:
                model()
                
                p = model.get_world_pose()
                print "Model name: %'s'"%(model.object_name)
                print p
                object_list.append(graspit_msgs.msg.ObjectInfo(
                                                      model.object_name, model.model_name, p))
            scene_msg.objects = object_list
            self.graspit_scene_publisher.publish(scene_msg)

    def point_within_table_cube(self, test_point):
        ""
        @brief - Test whether a point is within a cube defined by its
        lower left and upper right corners. The corners are stored in the table_cube
        member. 

        FIXME - This implementation is likely slow and dumb, but it works for me. 

        @param test_point - The point to test
        ""
        [min_corner_point , max_corner_point ] = self.table_cube 
        keys = ['x', 'y', 'z']
        for k in keys:
            t = getattr(test_point, k)
            min_test = getattr(min_corner_point, k)
            max_test = getattr(max_corner_point, k)
            if t < min_test or t > max_test:
                print 'Failed to be inside table in key %'s' - min - %'f' max - %'f' value %'f''%(k, min_test, max_test, t)
                return False
        return True
    """

def add_table(world_manager):

    time.sleep(1)
    rospy.wait_for_service('moveit_trajectory_planner/add_box')
    frame_id = "/world"
    rospy.loginfo("adding table in planning frame: " + str(frame_id))
    box_pose = geometry_msgs.msg.PoseStamped()
    box_pose.header.frame_id = frame_id
    table_x = -.92
    table_y = 1.22
    table_z = .05
    table_world_x_offset = .24
    table_world_y_offset = -.19
    table_world_z_offset = 0
    box_pose.pose.position.x = table_x/2.0 + table_world_x_offset
    box_pose.pose.position.y = table_y/2.0 + table_world_y_offset
    box_pose.pose.position.z = table_z/2.0 + table_world_z_offset
    box_pose.pose.orientation.x = 0
    box_pose.pose.orientation.y = 0
    box_pose.pose.orientation.z = 0
    box_pose.pose.orientation.w = 0
    box_dimensions = (table_x, table_y, table_z)

    world_manager.scene.add_box("table", box_pose, box_dimensions)
    rospy.loginfo("table added")

if __name__ == '__main__':

    try:
        rospy.init_node('world_manager_node')

        world_manager = WorldManager()
        add_table(world_manager)

        loop = rospy.Rate(10)
        while not rospy.is_shutdown():
            loop.sleep()
    except rospy.ROSInterruptException: pass