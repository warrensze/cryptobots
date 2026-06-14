from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor
from pybricks.parameters import Port
from pybricks.robotics import DriveBase
from pybricks.tools import wait

hub = PrimeHub()
left_motor = Motor(Port.A)
right_motor = Motor(Port.B)
robot = DriveBase(left_motor, right_motor, wheel_diameter=56, axle_track=114)

left_motor.reset_angle(0)
hub.imu.reset_heading(0)

# Your target driving speed
base_speed = 150 
proportional_gain = 2.0  # Adjust how aggressively it corrects steering errors

try:
    while left_motor.angle() < 2000: # Drive until target distance is reached
        x = left_motor.angle()

        # Put the equation here - -0.318 + 0.0213x + -1.28E-05x^2 + -5.39E-08x^3 + 8.66E-11x^4 + -3.54E-14x^5
        target_angle = -0.318 + 0.0213x + -1.28E-05x^2 + -5.39E-08x^3 + 8.66E-11x^4 + -3.54E-14x^5 
        
        # Calculate the steering error
        current_angle = hub.imu.heading()
        error = target_angle - current_angle
        
        # Use proportional control to steer the robot dynamically
        turn_rate = error * proportional_gain
        robot.drive(base_speed, turn_rate)
        
        wait(10)
        
finally:
    robot.stop()
