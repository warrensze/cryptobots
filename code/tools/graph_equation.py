import numpy as np
import matplotlib.pyplot as plt

coeffs = [7.57, 0.755, 4.26e-03, 5.82e-06, 2.25e-09]

def poly(x):
    return coeffs[0] + coeffs[1]*x + coeffs[2]*x**2 + coeffs[3]*x**3 + coeffs[4]*x**4

x = np.linspace(0, 400, 1000)
y = poly(x)

plt.figure(figsize=(10, 6))
plt.plot(x, y, 'b-', linewidth=2)
plt.axhline(y=180, color='r', linestyle='--', alpha=0.5, label='±180° gyro wrap')
plt.axhline(y=-180, color='r', linestyle='--', alpha=0.5)
plt.axvline(x=182, color='g', linestyle=':', alpha=0.5, label='~182mm (wrap point from context)')
plt.xlabel('Distance (mm)')
plt.ylabel('Target Gyro Angle (degrees)')
plt.title('Polynomial Equation: 7.57 + 0.755x + 4.26E-03x² + 5.82E-06x³ + 2.25E-09x⁴')
plt.grid(True, alpha=0.3)
plt.legend()
plt.tight_layout()
out = 'C:\\Users\\warren\\Desktop\\Earons Projects\\opencode-sandbox\\Lego League\\Autonomous Learning\\cryptobots\\code\\logs\\equation5_graph.png'
plt.savefig(out, dpi=150)
print(f"Graph saved to {out}")
