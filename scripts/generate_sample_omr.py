# generate_sample_omr.py
# Generates a synthetic OMR sheet image (sample_omr.jpg) and an answers.json file.
import cv2
import numpy as np
import json

IMG_W, IMG_H = 1200, 1600
BG = 255
NUM_QUESTIONS = 100
OPTIONS = 4

# Layout parameters
left_margin = 60
top_margin = 120
cell_w = 52    # column spacing
cell_h = 220   # row spacing for question groups (we'll put 20 columns across and 5 rows)
cols = 20      # 20 question columns
rows = 5       # 5 rows => 20*5 = 100 questions
opt_spacing = 28  # vertical spacing between the 4 option circles inside a question cell
bubble_r = 10

img = np.ones((IMG_H, IMG_W), dtype=np.uint8) * BG

# store centers for later evaluation => same layout used by evaluator
centers = []  # list of lists: for each question -> 4 centers (x,y)
answers = {}  # question_no (1-based) -> correct option (1..4)

for q in range(NUM_QUESTIONS):
    col = q % cols
    row = q // cols
    base_x = left_margin + col * cell_w
    base_y = top_margin + row * cell_h
    # draw 4 option circles vertically
    q_centers = []
    for opt in range(OPTIONS):
        cx = int(base_x + 0)  # center column aligned
        cy = int(base_y + opt * opt_spacing)
        cv2.circle(img, (cx, cy), bubble_r, (0,0,0), 2)  # black circle outline
        q_centers.append((cx, cy))
    centers.append(q_centers)
    # random correct choice for this synthetic sheet
    answers[str(q+1)] = int(np.random.randint(1, OPTIONS+1))

# Fill some circles to emulate student marks:
# We'll mark the correct option for about 70% questions, leave others wrong/unfilled
for q in range(NUM_QUESTIONS):
    correct = answers[str(q+1)]
    mark_prob = np.random.rand()
    if mark_prob < 0.85:  # 85% will be filled (to simulate a mostly-complete sheet)
        # 80% of the time mark correct, 20% mark random wrong
        if np.random.rand() < 0.8:
            choice = correct
        else:
            choice = int(np.random.randint(1, OPTIONS+1))
        cx, cy = centers[q][choice-1]
        # fill with darker ellipse (simulate pencil)
        cv2.circle(img, (cx, cy), bubble_r-3, (0,0,0), -1)

# Add simple text header
cv2.putText(img, "SAMPLE OMR SHEET - Demo", (300,40), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0,0,0), 2)

# Save image and answers file
cv2.imwrite("sample_omr.jpg", img)
with open("answers.json", "w") as f:
    json.dump(answers, f)
print("Generated sample_omr.jpg and answers.json in current folder.")
