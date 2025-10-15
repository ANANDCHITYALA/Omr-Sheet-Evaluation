# hack.py - OMR evaluator (updated to accept answers dict or filename)
import cv2
import numpy as np
import json
import csv
import os

IMG_W, IMG_H = 1200, 1600
NUM_QUESTIONS = 100
OPTIONS = 4

left_margin = 60
top_margin = 120
cell_w = 52
cell_h = 220
opt_spacing = 28
bubble_r = 10

def load_answers(fname_or_dict):
    """
    Accepts either:
    - a dict mapping question numbers (str) to option ints
    - a filename string pointing to a JSON file
    """
    if isinstance(fname_or_dict, dict):
        return fname_or_dict
    if not os.path.exists(fname_or_dict):
        raise FileNotFoundError(f"{fname_or_dict} not found.")
    with open(fname_or_dict, "r") as f:
        return json.load(f)

def get_centers(num_questions=NUM_QUESTIONS):
    centers = []
    cols = 20 if num_questions >= 20 else num_questions
    # For simplicity layout assumes 20 columns; if num_questions changes significantly,
    # you can tweak cols / rows logic or pass bespoke centers.
    for q in range(num_questions):
        col = q % 20
        row = q // 20
        base_x = left_margin + col * cell_w
        base_y = top_margin + row * cell_h
        q_centers = []
        for opt in range(OPTIONS):
            cx = int(base_x + 0)
            cy = int(base_y + opt * opt_spacing)
            q_centers.append((cx, cy))
        centers.append(q_centers)
    return centers

def read_image(fname="sample_omr.jpg"):
    if not os.path.exists(fname):
        raise FileNotFoundError(f"{fname} not found in folder.")
    img = cv2.imread(fname, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise RuntimeError("Failed to read image. Ensure file is a valid image.")
    return img

def evaluate(image_path="sample_omr.jpg", answers_source="answers.json", num_questions=NUM_QUESTIONS):
    """
    image_path: path to OMR image
    answers_source: either a dict (answers) or filename for JSON
    num_questions: number of questions on the sheet
    """
    answers = load_answers(answers_source)
    img = read_image(image_path)
    overlay = cv2.cvtColor(img.copy(), cv2.COLOR_GRAY2BGR)
    centers = get_centers(num_questions)

    results = []
    correct_count = 0

    # threshold: invert so filled marks become white
    _, th = cv2.threshold(img, 200, 255, cv2.THRESH_BINARY_INV)

    for q_idx in range(num_questions):
        q_no = q_idx + 1
        q_centers = centers[q_idx]
        fill_scores = []
        for opt_idx, (cx, cy) in enumerate(q_centers):
            x1 = max(cx - bubble_r - 3, 0)
            y1 = max(cy - bubble_r - 3, 0)
            x2 = min(cx + bubble_r + 3, img.shape[1]-1)
            y2 = min(cy + bubble_r + 3, img.shape[0]-1)
            roi = th[y1:y2, x1:x2]
            non_zero = cv2.countNonZero(roi)
            area = roi.size if roi.size>0 else 1
            score = non_zero / area
            fill_scores.append(score)

        sel_idx = int(np.argmax(fill_scores))
        sel_score = fill_scores[sel_idx]
        marked_threshold = 0.05
        if sel_score < marked_threshold:
            selected = None
        else:
            selected = sel_idx + 1

        correct_option = int(answers.get(str(q_no), 0))
        status = "unanswered"
        if selected is None:
            status = "unanswered"
            color = (255, 0, 0)
        else:
            if selected == correct_option:
                status = "correct"
                correct_count += 1
                color = (0, 255, 0)
            else:
                status = "wrong"
                color = (0, 0, 255)

        for opt_idx, (cx, cy) in enumerate(q_centers):
            x1 = max(cx - bubble_r - 3, 0)
            y1 = max(cy - bubble_r - 3, 0)
            x2 = min(cx + bubble_r + 3, img.shape[1]-1)
            y2 = min(cy + bubble_r + 3, img.shape[0]-1)
            if selected is not None and (opt_idx+1) == selected:
                cv2.rectangle(overlay, (x1,y1), (x2,y2), color, 2)
            else:
                cv2.rectangle(overlay, (x1,y1), (x2,y2), (120,120,120), 1)

        results.append({
            "question": q_no,
            "selected": selected,
            "correct": correct_option,
            "status": status,
            "fill_score": float(np.round(float(sel_score), 4))
        })

    total = correct_count
    subject_scores = {}
    per_subject = 20
    # compute dynamic per-subject segmentation based on num_questions
    num_subjects = max(1, num_questions // per_subject)
    for s in range(num_subjects):
        start = s*per_subject + 1
        end = min((s+1)*per_subject, num_questions)
        sc = sum(1 for r in results if start <= r["question"] <= end and r["status"]=="correct")
        subject_scores[f"subject_{s+1}"] = sc

    # save overlay and csv with a timestamp-safe filename to avoid overwrites in multi-user
    overlay_file = "evaluated.png"
    csv_file = "results.csv"
    cv2.imwrite(overlay_file, overlay)
    keys = ["question", "selected", "correct", "status", "fill_score"]
    with open(csv_file, "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=keys)
        writer.writeheader()
        for row in results:
            writer.writerow(row)
    # --- Save mistakes JSON per student ---
    mistakes = {}
    for r in results:
        if r["status"] != "correct":
            q = r["question"]
            mistakes[q] = {"marked": r["selected"], "correct": r["correct"]}

    # Make sure results directory exists
    os.makedirs("results", exist_ok=True)
    roll_no = os.path.basename(image_path).replace(".jpg", "")
    mistakes_path = os.path.join("results", f"mistakes_{roll_no}.json")
    with open(mistakes_path, "w") as f:
        json.dump(mistakes, f)


    summary = {
        "total_correct": total,
        "total_questions": num_questions,
        "subject_scores": subject_scores,
        "results_file": csv_file,
        "overlay_image": overlay_file,
        "per_question": results
    }
    return summary
