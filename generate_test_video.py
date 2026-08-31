import cv2
import numpy as np
import random

random.seed(42)
w, h = 640, 360
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
vid = cv2.VideoWriter('videos/trafik.mp4', fourcc, 15.0, (w, h))

cars = []
for _ in range(5):
    x = random.randint(0, w - 60)
    y = random.randint(40, h - 80)
    vtype = random.choice(['car', 'motorcycle', 'bus', 'truck', 'car'])
    cars.append([x, y, vtype])

color_map = {
    'car': (0, 255, 0),
    'motorcycle': (0, 255, 255),
    'bus': (255, 0, 0),
    'truck': (0, 0, 255),
}
size_map = {
    'car': (50, 30),
    'motorcycle': (25, 18),
    'bus': (70, 35),
    'truck': (70, 40),
}

for i in range(225):
    frame = np.zeros((h, w, 3), dtype=np.uint8)
    frame[:] = (40, 40, 40)
    cv2.rectangle(frame, (0, h // 2 + 20), (w, h), (80, 80, 80), -1)

    for idx, (x, y, vtype) in enumerate(cars):
        speed = random.randint(3, 8) if vtype != 'motorcycle' else random.randint(6, 10)
        x = (x + speed) % w
        cars[idx][0] = x
        color = color_map[vtype]
        sw, sh = size_map[vtype]
        cv2.rectangle(frame, (x, y), (x + sw, y + sh), color, -1)
        cv2.putText(frame, vtype, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

    vid.write(frame)

vid.release()
print("Test video created: videos/trafik.mp4")
