# Modify the target-angle equation to match your equation

from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor
from pybricks.parameters import Port, Direction
from pybricks.robotics import DriveBase
from pybricks.tools import wait

hub = PrimeHub()
left_motor = Motor(Port.B, Direction.COUNTERCLOCKWISE)
right_motor = Motor(Port.F, Direction.CLOCKWISE)

robot = DriveBase(left_motor, right_motor, wheel_diameter=56, axle_track=120)

robot.reset()
hub.imu.reset_heading(0)

base_speed = 140 
proportional_gain = 8.0  

try:
    while robot.distance() < 1732: # Drive for mm
        # 1. Convert mm to cm to prevent numbers from blowing up
        x = robot.distance() / 1.0
        
        # 2. Run polynomial math equation route 
        # Put the equation here - -0.318 + 0.0213x + -1.28E-05x^2 + -5.39E-08x^3 + 8.66E-11x^4 + -3.54E-14x^5
        #target_angle = -4.68 + -0.0871*x + 1.72E-03*x**2 + -4.64E-06*x**3 + 4.23E-09*x**4 + -1.25E-12*x**5
        target_angle = -1 * (-1.16 + 0.0393*x + 6.27E-05*x**2 + -1.58E-06*x**3 + 2.9E-09*x**4 + -1.84E-12*x**5 + 3.94E-16*x**6)  # left then right curve
        fit_R2 = 0.979  # Assuming a perfect fit for simplicity

        # Add this in if you just want to drive straight during these distances
        if x <= 170:
            target_angle = 0.0  # Drive straight at the beginning and end of the path
        else:
            target_angle = target_angle * fit_R2  # Scale the target angle by the R² value to improve accuracy

        # 3. Calculate steering corrections
        current_angle = hub.imu.heading()
        error = target_angle - current_angle
        
        turn_rate = error * proportional_gain

        print(round(x,1), round(target_angle,1), round(current_angle,1), round(error,2), round(turn_rate,2), sep=" |")

        robot.drive(base_speed, turn_rate)
        
        wait(10)
        
finally:
    robot.stop()


