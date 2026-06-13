"""Simulate the corrected autonomous path following to verify the equation alignment."""

import numpy as np
import matplotlib.pyplot as plt

coeffs = [7.57, 0.755, 4.26e-03, 5.82e-06, 2.25e-09]

def raw_target_angle(x):
    return coeffs[0] + coeffs[1]*x + coeffs[2]*x**2 + coeffs[3]*x**3 + coeffs[4]*x**4

offset = raw_target_angle(0)

def target_angle_for_distance(x):
    return raw_target_angle(x) - offset

def angle_error(target, current):
    error = target - current
    while error > 180:
        error -= 360
    while error < -180:
        error += 360
    return error

base_speed = 50
kp = 5
max_correction = 45
max_speed = 100

distance_mm = np.linspace(0, 300, 1000)
target = np.array([target_angle_for_distance(d) for d in distance_mm])

current_angle_sim = [0.0]
dt = 0.005
for i in range(1, len(distance_mm)):
    d_dist = distance_mm[i] - distance_mm[i-1]
    t = target[i]
    c = current_angle_sim[-1]
    err = angle_error(t, c)
    corr = np.clip(err * kp, -max_correction, max_correction)
    left = np.clip(base_speed + corr, -max_speed, max_speed)
    right = np.clip(base_speed - corr, -max_speed, max_speed)
    angular_vel = (right - left) / 100.0
    current_angle_sim.append(c + angular_vel * dt * 100)

current_angle_sim = np.array(current_angle_sim[:len(distance_mm)])

errors = np.array([angle_error(target[i], current_angle_sim[i]) for i in range(len(distance_mm))])
corrections = np.clip(errors * kp, -max_correction, max_correction)

fig, axes = plt.subplots(3, 1, figsize=(12, 10), sharex=True)

ax = axes[0]
ax.plot(distance_mm, target, 'b-', linewidth=2, label='Target angle (unbounded)')
ax.plot(distance_mm, current_angle_sim, 'r--', linewidth=2, label='Simulated actual (wrapped)')
ax.axhline(y=180, color='gray', linestyle=':', alpha=0.5)
ax.axhline(y=-180, color='gray', linestyle=':', alpha=0.5)
ax.set_ylabel('Gyro Angle (deg)')
ax.legend()
ax.grid(True, alpha=0.3)
ax.set_title('Autonomous Path Following (corrected: forward speed + proper steering)')

ax = axes[1]
ax.plot(distance_mm, errors, 'g-', linewidth=2)
ax.axhline(y=0, color='k', linestyle='-', alpha=0.3)
ax.set_ylabel('Error (deg)')
ax.grid(True, alpha=0.3)

ax = axes[2]
ax.plot(distance_mm, corrections, 'm-', linewidth=2, label='Correction')
ax.plot(distance_mm, np.array([base_speed]*len(distance_mm)) + corrections, 'c--', label='Left speed')
ax.plot(distance_mm, np.array([base_speed]*len(distance_mm)) - corrections, 'y--', label='Right speed')
ax.axhline(y=0, color='k', linestyle='-', alpha=0.3)
ax.set_xlabel('Distance (mm)')
ax.set_ylabel('Speed / Correction')
ax.legend()
ax.grid(True, alpha=0.3)

plt.tight_layout()
out = 'C:\\Users\\warren\\Desktop\\Earons Projects\\opencode-sandbox\\Lego League\\Autonomous Learning\\cryptobots\\code\\logs\\autonomous_simulation.png'
plt.savefig(out, dpi=150)
print(f"Simulation saved to {out}")
