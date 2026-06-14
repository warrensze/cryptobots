# Example command to use to load the program and export the output
# pipx run pybricksdev run ble --name "Pybricks Hub" test_datalog.py > training_data.csv

from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor
from pybricks.parameters import Port
from pybricks.robotics import DriveBase
from pybricks.tools import wait, StopWatch

# 1. Initialize SPIKE Prime Hub and Motors
hub = PrimeHub()
left_motor = Motor(Port.A)
right_motor = Motor(Port.B)

# 2. Setup DriveBase (Adjust wheel diameter and axle track for your robot)
robot = DriveBase(left_motor, right_motor, wheel_diameter=56, axle_track=114)

# 3. Initialize the timer and reset tracking metrics
watch = StopWatch()
robot.reset()            # Resets drivebase distance to 0
hub.imu.reset_heading(0) # Resets gyro heading to 0

# 4. Print CSV Headers first
print("Time_ms", "Distance_mm", "Gyro_Heading", sep=", ")

# Give you 3 seconds to get ready after launching the command
hub.speaker.beep(frequency=440, duration=200)
wait(3000)
hub.speaker.beep(frequency=880, duration=500)

try:
    # Records data every 50ms for roughly 10 seconds (200 samples)
    for _ in range(200):
        time = watch.time()
        distance = robot.distance() # Gets composite distance in mm
        heading = hub.imu.heading()  # Gets internal gyro heading
        
        # Stream the 3 columns over Bluetooth to your terminal
        print(time, distance, heading, sep=", ")
        
        wait(50)
        
    hub.speaker.beep(frequency=660, duration=200)
    print("--- RECORDING FINISHED ---")

except KeyboardInterrupt:
    print("--- RECORDING STOPPED MANUALLY ---")
