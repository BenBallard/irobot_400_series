#!/usr/bin/python
import roslib; roslib.load_manifest('irobot_create_2_1')
import rospy
from time import sleep
from irobot import Roomba
from threading import Thread
from math import sin,cos,pi
from datetime import datetime

from geometry_msgs.msg import Quaternion
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from tf.broadcaster import TransformBroadcaster

from irobot_create_2_1.msg import SensorPacket
from irobot_create_2_1.srv import *

class RoombaDriver:
	def __init__(self):
		port = rospy.get_param('/brown/irobot_create_2_1/port', "/dev/ttyUSB0")
		self.roomba = Roomba(port)
		self.packetPub = rospy.Publisher('sensorPacket', SensorPacket)
		self.odomPub = rospy.Publisher('odom',Odometry)
		self.odomBroadcaster = TransformBroadcaster()
		self.fields = ['wheeldropCaster','wheeldropLeft','wheeldropRight','bumpLeft','bumpRight','wall','cliffLeft','cliffFrontLeft','cliffFrontRight','cliffRight','virtualWall','overCurrentLeft','overCurrentRight','overCurrentMainBrush','overCurrentSideBrush','dirtDetectorLeft','dirtDetectorRight','virtualWall','infraredByte','button','distance','angle','chargingState','voltage','current','batteryTemperature','batteryCharge','batteryCapacity']
		self.then = datetime.now() 
		self.x = 0
		self.y = 0
		self.th = 0
		self.roomba.update = self.sense

	def start(self):
		self.roomba.start()
		self.then = datetime.now() 

	def stop(self):
		self.roomba.stop()

	def sense(self):
		now = datetime.now()
		elapsed = now - self.then
		self.then = now
		elapsed = float(elapsed.seconds) + elapsed.microseconds/1000000.
		d = self.roomba.d_distance / 1000.
		th = self.roomba.d_angle*pi/180
		dx = d / elapsed
		dth = th / elapsed

		if (d != 0):
			x = cos(th)*d
			y = -sin(th)*d
			self.x = self.x + (cos(self.th)*x - sin(self.th)*y)
			self.y = self.y + (sin(self.th)*x + cos(self.th)*y)

		if (th != 0):
			self.th = self.th + th

		quaternion = Quaternion()
		quaternion.x = 0.0 
		quaternion.y = 0.0
		quaternion.z = sin(self.th/2)
		quaternion.w = cos(self.th/2)

		self.odomBroadcaster.sendTransform(
			(self.x, self.y, 0), 
			(quaternion.x, quaternion.y, quaternion.z, quaternion.w),
			rospy.Time.now(),
			"base_link",
			"odom"
			)

		odom = Odometry()
		odom.header.stamp = rospy.Time.now()
		odom.header.frame_id = "odom"
		odom.pose.pose.position.x = self.x
		odom.pose.pose.position.y = self.y
		odom.pose.pose.position.z = 0
		odom.pose.pose.orientation = quaternion

		odom.child_frame_id = "base_link"
		odom.twist.twist.linear.x = dx
		odom.twist.twist.linear.y = 0
		odom.twist.twist.angular.z = dth

		self.odomPub.publish(odom)

		packet = SensorPacket()
		for field in self.fields:
			packet.__setattr__(field,self.roomba.__getattr__(field))
		self.packetPub.publish(packet)

	def brake(self,req):
		if (req.brake):
			self.roomba.brake()
		return BrakeResponse(True)

	def demo(self,req):
		self.roomba.demo(req.demo)
		return DemoResponse(True)

	def leds(self,req):
		self.roomba.leds(req.advance,req.play,req.color,req.intensity)
		return LedsResponse(True)

	def twist(self,req):
		x = req.linear.x*1000
		omega = req.angular.z
		self.roomba.driveTwist(x,omega)


if __name__ == '__main__':
	node = rospy.init_node('create')
	driver = RoombaDriver()
	
	rospy.Service('brake',Brake,driver.brake)
	#rospy.Service('demo',Demo,driver.demo)
	#rospy.Service('leds',Leds,driver.leds)
	#rospy.Service('motors',Motor,driver.motors)
	rospy.Subscriber("cmd_vel", Twist, driver.twist)

	sleep(1)
	driver.start()
	sleep(1)

	rospy.spin()
	driver.stop()
