from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor
from pybricks.parameters import Port
from pybricks.robotics import DriveBase
from pybricks.tools import wait

hub = PrimeHub()
left_motor = Motor(Port.A)
right_motor = Motor(Port.B)
robot = DriveBase(left_motor, right_motor, wheel_diameter=56, axle_track=114)

robot.reset()
hub.imu.reset_heading(0)

base_speed = 150 
proportional_gain = 2.0  

try:
    while robot.distance() < 1000: # Drive for 1000mm (100cm)
        # 1. Convert mm to cm to prevent numbers from blowing up
        x = robot.distance() / 10.0 
        
        # 2. Run your polynomial math safely using small numbers
        # Put the equation here - -0.318 + 0.0213x + -1.28E-05x^2 + -5.39E-08x^3 + 8.66E-11x^4 + -3.54E-14x^5
        target_angle = -0.318 + 0.0213*x + -1.28E-05*x**2 + -5.39E-08*x**3 + 8.66E-11*x**4 + -3.54E-14*x**5
        
        # 3. Calculate steering corrections
        current_angle = hub.imu.heading()
        error = target_angle - current_angle
        
        turn_rate = error * proportional_gain
        robot.drive(base_speed, turn_rate)
        
        wait(10)
        
finally:
    robot.stop()


