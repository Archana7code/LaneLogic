# # import cv2
# # from pathlib import Path

# # # ============================================================
# # # LaneLogic Local YOLO Annotation Tool
# # # No account, no website, no separate annotation application.
# # # Requires only Python + OpenCV.
# # # ============================================================

# # CLASSES = [
# #     "car",                  # 0
# #     "motorcycle",           # 1
# #     "bicycle",              # 2
# #     "auto_rickshaw",        # 3
# #     "e_rickshaw",           # 4
# #     "bus",                  # 5
# #     "truck",                # 6
# #     "stall",                # 7
# #     "cart",                 # 8
# #     "garbage",              # 9
# #     "debris",               # 10
# #     "construction_material",# 11
# #     "barrier",              # 12
# # ]

# # IMAGE_DIR = Path("dataset/images/train")
# # LABEL_DIR = Path("dataset/labels/train")

# # IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

# # # Class-selection keys:
# # # 0-9 = classes 0-9
# # # a    = class 10 (debris)
# # # b    = class 11 (construction_material)
# # # c    = class 12 (barrier)
# # #
# # # Other keys:
# # # s = save
# # # r = reset all boxes on current image
# # # n = save + next image
# # # p = save + previous image
# # # q / ESC = quit

# # boxes = []
# # drawing = False
# # start_x = start_y = 0
# # mouse_x = mouse_y = 0
# # pending_box = None


# # def key_to_class(key):
# #     if ord("0") <= key <= ord("9"):
# #         class_id = key - ord("0")
# #         return class_id if class_id < 10 else None

# #     if key == ord("a"):
# #         return 10
# #     if key == ord("b"):
# #         return 11
# #     if key == ord("c"):
# #         return 12

# #     return None


# # def save_labels(image_path):
# #     LABEL_DIR.mkdir(parents=True, exist_ok=True)

# #     label_path = LABEL_DIR / f"{image_path.stem}.txt"
# #     img = cv2.imread(str(image_path))

# #     if img is None:
# #         print(f"Could not read: {image_path}")
# #         return

# #     h, w = img.shape[:2]

# #     with open(label_path, "w", encoding="utf-8") as f:
# #         for x1, y1, x2, y2, class_id in boxes:
# #             left, right = sorted([x1, x2])
# #             top, bottom = sorted([y1, y2])

# #             left = max(0, min(left, w - 1))
# #             right = max(0, min(right, w - 1))
# #             top = max(0, min(top, h - 1))
# #             bottom = max(0, min(bottom, h - 1))

# #             box_w = right - left
# #             box_h = bottom - top

# #             if box_w < 2 or box_h < 2:
# #                 continue

# #             # Convert pixel coordinates to YOLO normalized format.
# #             x_center = ((left + right) / 2) / w
# #             y_center = ((top + bottom) / 2) / h
# #             width = box_w / w
# #             height = box_h / h

# #             f.write(
# #                 f"{class_id} "
# #                 f"{x_center:.6f} "
# #                 f"{y_center:.6f} "
# #                 f"{width:.6f} "
# #                 f"{height:.6f}\n"
# #             )

# #     print(f"Saved -> {label_path}")


# # def mouse_callback(event, x, y, flags, param):
# #     global drawing, start_x, start_y, mouse_x, mouse_y, pending_box

# #     mouse_x, mouse_y = x, y

# #     if event == cv2.EVENT_LBUTTONDOWN:
# #         drawing = True
# #         start_x, start_y = x, y

# #     elif event == cv2.EVENT_MOUSEMOVE:
# #         mouse_x, mouse_y = x, y

# #     elif event == cv2.EVENT_LBUTTONUP and drawing:
# #         drawing = False

# #         x1, x2 = sorted([start_x, x])
# #         y1, y2 = sorted([start_y, y])

# #         if x2 - x1 >= 4 and y2 - y1 >= 4:
# #             pending_box = [x1, y1, x2, y2]
# #             print(
# #                 "\nBox created. Choose its class:\n"
# #                 "0 car | 1 motorcycle | 2 bicycle | 3 auto_rickshaw | "
# #                 "4 e_rickshaw | 5 bus | 6 truck | 7 stall | 8 cart | "
# #                 "9 garbage | a debris | b construction_material | c barrier"
# #             )


# # def load_existing_labels(image_path):
# #     label_path = LABEL_DIR / f"{image_path.stem}.txt"

# #     if not label_path.exists():
# #         return []

# #     img = cv2.imread(str(image_path))
# #     if img is None:
# #         return []

# #     h, w = img.shape[:2]
# #     loaded = []

# #     try:
# #         with open(label_path, "r", encoding="utf-8") as f:
# #             for line in f:
# #                 parts = line.strip().split()

# #                 if len(parts) != 5:
# #                     continue

# #                 class_id = int(parts[0])
# #                 xc, yc, bw, bh = map(float, parts[1:])

# #                 if not 0 <= class_id < len(CLASSES):
# #                     continue

# #                 pixel_bw = bw * w
# #                 pixel_bh = bh * h
# #                 center_x = xc * w
# #                 center_y = yc * h

# #                 x1 = int(center_x - pixel_bw / 2)
# #                 y1 = int(center_y - pixel_bh / 2)
# #                 x2 = int(center_x + pixel_bw / 2)
# #                 y2 = int(center_y + pixel_bh / 2)

# #                 loaded.append([x1, y1, x2, y2, class_id])

# #     except Exception as e:
# #         print(f"Could not load existing labels: {e}")

# #     return loaded


# # def draw_screen(img, image_path, index, total):
# #     display = img.copy()

# #     # Existing boxes.
# #     for x1, y1, x2, y2, class_id in boxes:
# #         cv2.rectangle(display, (x1, y1), (x2, y2), (255, 255, 255), 2)
# #         text = f"{class_id}: {CLASSES[class_id]}"
# #         cv2.putText(
# #             display,
# #             text,
# #             (x1, max(20, y1 - 6)),
# #             cv2.FONT_HERSHEY_SIMPLEX,
# #             0.55,
# #             (255, 255, 255),
# #             2,
# #         )

# #     # Box currently being drawn.
# #     if drawing:
# #         cv2.rectangle(
# #             display,
# #             (start_x, start_y),
# #             (mouse_x, mouse_y),
# #             (255, 255, 255),
# #             2,
# #         )

# #     # Box waiting for a class selection.
# #     if pending_box is not None:
# #         x1, y1, x2, y2 = pending_box
# #         cv2.rectangle(display, (x1, y1), (x2, y2), (255, 255, 255), 2)

# #     # Header.
# #     cv2.rectangle(
# #         display,
# #         (0, 0),
# #         (display.shape[1], 38),
# #         (0, 0, 0),
# #         -1,
# #     )

# #     header = (
# #         "Draw=mouse | 0-9=class | a=debris b=construction c=barrier | "
# #         "S=save N=next P=prev R=reset Q=quit"
# #     )

# #     cv2.putText(
# #         display,
# #         header,
# #         (8, 25),
# #         cv2.FONT_HERSHEY_SIMPLEX,
# #         0.48,
# #         (255, 255, 255),
# #         1,
# #     )

# #     # Footer.
# #     footer = (
# #         f"{index + 1}/{total}  {image_path.name}  "
# #         f"Boxes: {len(boxes)}"
# #     )

# #     cv2.rectangle(
# #         display,
# #         (0, display.shape[0] - 35),
# #         (display.shape[1], display.shape[0]),
# #         (0, 0, 0),
# #         -1,
# #     )

# #     cv2.putText(
# #         display,
# #         footer,
# #         (8, display.shape[0] - 12),
# #         cv2.FONT_HERSHEY_SIMPLEX,
# #         0.55,
# #         (255, 255, 255),
# #         1,
# #     )

# #     return display


# # def main():
# #     global boxes, pending_box

# #     if not IMAGE_DIR.exists():
# #         print("\nImage folder not found:")
# #         print(IMAGE_DIR.resolve())
# #         print("\nCreate it and put your images inside:")
# #         print("dataset/images/train/")
# #         return

# #     LABEL_DIR.mkdir(parents=True, exist_ok=True)

# #     images = sorted(
# #         p
# #         for p in IMAGE_DIR.iterdir()
# #         if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
# #     )

# #     if not images:
# #         print("\nNo images found in:")
# #         print(IMAGE_DIR.resolve())
# #         return

# #     print("\n==========================================")
# #     print("      LaneLogic Local Annotation Tool")
# #     print("==========================================")
# #     print(f"Images found: {len(images)}")
# #     print(f"Images: {IMAGE_DIR.resolve()}")
# #     print(f"Labels: {LABEL_DIR.resolve()}")
# #     print("\nClasses:")

# #     for i, name in enumerate(CLASSES):
# #         key = str(i) if i < 10 else chr(ord("a") + i - 10)
# #         print(f"  {key} -> {i} -> {name}")

# #     print("\nHow to annotate:")
# #     print("1. Drag a box around an object with LEFT MOUSE.")
# #     print("2. Press its class key.")
# #     print("3. Press S to save.")
# #     print("4. Press N for next image.")
# #     print("\n")

# #     cv2.namedWindow("LaneLogic Annotator", cv2.WINDOW_NORMAL)
# #     cv2.setMouseCallback("LaneLogic Annotator", mouse_callback)

# #     index = 0

# #     while True:
# #         image_path = images[index]
# #         img = cv2.imread(str(image_path))

# #         if img is None:
# #             print(f"Skipping unreadable image: {image_path}")
# #             index = (index + 1) % len(images)
# #             continue

# #         # Load existing labels so you can reopen/resume annotation.
# #         boxes = load_existing_labels(image_path)
# #         pending_box = None

# #         while True:
# #             display = draw_screen(img, image_path, index, len(images))
# #             cv2.imshow("LaneLogic Annotator", display)

# #             key = cv2.waitKey(30) & 0xFF

# #             # Quit.
# #             if key in (27, ord("q")):
# #                 cv2.destroyAllWindows()
# #                 print("\nExited.")
# #                 return

# #             # Save.
# #             elif key == ord("s"):
# #                 save_labels(image_path)

# #             # Reset current image.
# #             elif key == ord("r"):
# #                 boxes = []
# #                 pending_box = None
# #                 print("Current image cleared. Press S to save the empty annotation.")

# #             # Delete the most recently created box.
# #             elif key == ord("d"):
# #                 if boxes:
# #                     removed = boxes.pop()
# #                     print(f"Removed: {CLASSES[removed[4]]}")

# #             # Select class for pending box.
# #             else:
# #                 class_id = key_to_class(key)

# #                 if class_id is not None and pending_box is not None:
# #                     x1, y1, x2, y2 = pending_box
# #                     boxes.append([x1, y1, x2, y2, class_id])
# #                     print(f"Added: {CLASSES[class_id]}")
# #                     pending_box = None

# #             # Next image.
# #             if key == ord("n"):
# #                 save_labels(image_path)
# #                 index = (index + 1) % len(images)
# #                 break

# #             # Previous image.
# #             if key == ord("p"):
# #                 save_labels(image_path)
# #                 index = (index - 1) % len(images)
# #                 break

# #     cv2.destroyAllWindows()


# # if __name__ == "__main__":
# #     main()












# import cv2
# from pathlib import Path

# # ============================================================
# # LaneLogic Local YOLO Annotation Tool
# # - No account
# # - No website
# # - No separate annotation application
# # - Image fits inside the window
# # - Mouse coordinates are converted back to original image pixels
# # - Zoom in/out for small objects
# # ============================================================

# CLASSES = [
#     "car",                   # 0
#     "motorcycle",            # 1
#     "bicycle",               # 2
#     "auto_rickshaw",         # 3
#     "e_rickshaw",            # 4
#     "bus",                   # 5
#     "truck",                 # 6
#     "stall",                 # 7
#     "cart",                  # 8
#     "garbage",               # 9
#     "debris",                # 10
#     "construction_material", # 11
#     "barrier",               # 12
# ]

# IMAGE_DIR = Path("dataset/images/train")
# LABEL_DIR = Path("dataset/labels/train")

# IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

# WINDOW_NAME = "LaneLogic Annotator"

# # Display limits. The image is fitted to this size initially.
# MAX_DISPLAY_WIDTH = 1400
# MAX_DISPLAY_HEIGHT = 800

# boxes = []  # [x1, y1, x2, y2, class_id] in ORIGINAL image coordinates

# drawing = False
# start_original = None
# current_original = None
# pending_box = None


# def class_name(class_id):
#     return CLASSES[class_id]


# def key_to_class(key):
#     if ord("0") <= key <= ord("9"):
#         cid = key - ord("0")
#         return cid if cid < 10 else None

#     if key == ord("a"):
#         return 10  # debris
#     if key == ord("b"):
#         return 11  # construction_material
#     if key == ord("c"):
#         return 12  # barrier

#     return None


# def load_existing_labels(image_path):
#     label_path = LABEL_DIR / f"{image_path.stem}.txt"

#     if not label_path.exists():
#         return []

#     img = cv2.imread(str(image_path))
#     if img is None:
#         return []

#     h, w = img.shape[:2]
#     result = []

#     try:
#         with open(label_path, "r", encoding="utf-8") as f:
#             for line in f:
#                 p = line.strip().split()

#                 if len(p) != 5:
#                     continue

#                 cid = int(p[0])
#                 if not 0 <= cid < len(CLASSES):
#                     continue

#                 xc, yc, bw, bh = map(float, p[1:])

#                 x1 = int((xc - bw / 2) * w)
#                 y1 = int((yc - bh / 2) * h)
#                 x2 = int((xc + bw / 2) * w)
#                 y2 = int((yc + bh / 2) * h)

#                 result.append([x1, y1, x2, y2, cid])

#     except Exception as e:
#         print(f"Could not read {label_path}: {e}")

#     return result


# def save_labels(image_path, img):
#     LABEL_DIR.mkdir(parents=True, exist_ok=True)

#     h, w = img.shape[:2]
#     label_path = LABEL_DIR / f"{image_path.stem}.txt"

#     with open(label_path, "w", encoding="utf-8") as f:
#         for x1, y1, x2, y2, cid in boxes:
#             left, right = sorted((x1, x2))
#             top, bottom = sorted((y1, y2))

#             left = max(0, min(left, w - 1))
#             right = max(0, min(right, w - 1))
#             top = max(0, min(top, h - 1))
#             bottom = max(0, min(bottom, h - 1))

#             bw = right - left
#             bh = bottom - top

#             if bw < 2 or bh < 2:
#                 continue

#             # YOLO normalized coordinates.
#             xc = ((left + right) / 2) / w
#             yc = ((top + bottom) / 2) / h
#             nw = bw / w
#             nh = bh / h

#             f.write(f"{cid} {xc:.6f} {yc:.6f} {nw:.6f} {nh:.6f}\n")

#     print(f"Saved: {label_path}")


# def fit_scale(img_w, img_h):
#     return min(
#         MAX_DISPLAY_WIDTH / img_w,
#         MAX_DISPLAY_HEIGHT / img_h,
#         1.0
#     )


# def display_transform(img, scale, offset_x, offset_y):
#     """Resize original image for display."""
#     h, w = img.shape[:2]

#     dw = max(1, int(w * scale))
#     dh = max(1, int(h * scale))

#     resized = cv2.resize(img, (dw, dh), interpolation=cv2.INTER_AREA)

#     canvas = resized
#     return canvas


# def screen_to_original(x, y, scale, offset_x, offset_y, img_shape):
#     """Convert displayed mouse coordinates -> original image pixels."""
#     h, w = img_shape[:2]

#     ox = int((x - offset_x) / scale)
#     oy = int((y - offset_y) / scale)

#     ox = max(0, min(ox, w - 1))
#     oy = max(0, min(oy, h - 1))

#     return ox, oy


# def original_to_display(x, y, scale, offset_x, offset_y):
#     return (
#         int(x * scale + offset_x),
#         int(y * scale + offset_y),
#     )


# def draw_box(display, box, scale, offset_x, offset_y, thickness=2):
#     x1, y1, x2, y2, cid = box

#     a = original_to_display(x1, y1, scale, offset_x, offset_y)
#     b = original_to_display(x2, y2, scale, offset_x, offset_y)

#     cv2.rectangle(display, a, b, (255, 255, 255), thickness)

#     label = f"{cid}: {CLASSES[cid]}"
#     text_y = max(18, a[1] - 5)

#     cv2.putText(
#         display,
#         label,
#         (a[0], text_y),
#         cv2.FONT_HERSHEY_SIMPLEX,
#         0.55,
#         (255, 255, 255),
#         2,
#     )


# def make_display(img, image_path, index, total, scale, offset_x, offset_y):
#     base = display_transform(img, scale, offset_x, offset_y)

#     # Header.
#     header_h = 45
#     footer_h = 38

#     display = cv2.copyMakeBorder(
#         base,
#         header_h,
#         footer_h,
#         0,
#         0,
#         cv2.BORDER_CONSTANT,
#         value=(0, 0, 0),
#     )

#     # Because the image starts below the header, all display coordinates
#     # need the header offset.
#     real_offset_y = offset_y + header_h

#     for box in boxes:
#         draw_box(
#             display,
#             box,
#             scale,
#             offset_x,
#             real_offset_y,
#         )

#     if pending_box is not None:
#         x1, y1, x2, y2 = pending_box
#         temp = [x1, y1, x2, y2, 0]
#         draw_box(
#             display,
#             temp,
#             scale,
#             offset_x,
#             real_offset_y,
#             thickness=2,
#         )

#     if drawing and start_original and current_original:
#         x1, y1 = start_original
#         x2, y2 = current_original

#         a = original_to_display(
#             x1, y1, scale, offset_x, real_offset_y
#         )
#         b = original_to_display(
#             x2, y2, scale, offset_x, real_offset_y
#         )

#         cv2.rectangle(display, a, b, (255, 255, 255), 2)

#     # Header text.
#     cv2.putText(
#         display,
#         "Mouse: draw box | 0-9: class | a=debris b=construction c=barrier",
#         (8, 18),
#         cv2.FONT_HERSHEY_SIMPLEX,
#         0.48,
#         (255, 255, 255),
#         1,
#     )

#     cv2.putText(
#         display,
#         "S save | N next | P previous | R reset | D delete | +/- zoom | Q quit",
#         (8, 38),
#         cv2.FONT_HERSHEY_SIMPLEX,
#         0.48,
#         (255, 255, 255),
#         1,
#     )

#     # Footer.
#     cv2.putText(
#         display,
#         f"{index + 1}/{total}  {image_path.name}  "
#         f"Zoom: {scale:.2f}x  Boxes: {len(boxes)}",
#         (8, display.shape[0] - 12),
#         cv2.FONT_HERSHEY_SIMPLEX,
#         0.52,
#         (255, 255, 255),
#         1,
#     )

#     return display, real_offset_y


# def mouse_callback(event, x, y, flags, param):
#     global drawing, start_original, current_original, pending_box

#     img_shape, scale, offset_x, offset_y = param

#     ox, oy = screen_to_original(
#         x, y, scale, offset_x, offset_y, img_shape
#     )

#     if event == cv2.EVENT_LBUTTONDOWN:
#         drawing = True
#         start_original = (ox, oy)
#         current_original = (ox, oy)

#     elif event == cv2.EVENT_MOUSEMOVE and drawing:
#         current_original = (ox, oy)

#     elif event == cv2.EVENT_LBUTTONUP and drawing:
#         drawing = False
#         current_original = (ox, oy)

#         if start_original is None:
#             return

#         x1, y1 = start_original
#         x2, y2 = current_original

#         left, right = sorted((x1, x2))
#         top, bottom = sorted((y1, y2))

#         if right - left >= 4 and bottom - top >= 4:
#             pending_box = [left, top, right, bottom]
#             print(
#                 "\nBox ready. Press the class key:"
#             )
#             print(
#                 "0 car | 1 motorcycle | 2 bicycle | "
#                 "3 auto_rickshaw | 4 e_rickshaw | 5 bus | "
#                 "6 truck | 7 stall | 8 cart | 9 garbage | "
#                 "a debris | b construction_material | c barrier"
#             )


# def main():
#     global boxes, drawing, start_original, current_original
#     global pending_box

#     if not IMAGE_DIR.exists():
#         print(f"\nFolder not found:\n{IMAGE_DIR.resolve()}")
#         print("\nCreate:")
#         print("dataset/images/train/")
#         return

#     LABEL_DIR.mkdir(parents=True, exist_ok=True)

#     images = sorted(
#         p for p in IMAGE_DIR.iterdir()
#         if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
#     )

#     if not images:
#         print(f"\nNo images found in:\n{IMAGE_DIR.resolve()}")
#         return

#     print("\n==============================================")
#     print("       LaneLogic Local YOLO Annotator")
#     print("==============================================")
#     print(f"Images: {len(images)}")
#     print(f"Image folder: {IMAGE_DIR.resolve()}")
#     print(f"Label folder: {LABEL_DIR.resolve()}")
#     print("\nClasses:")

#     for i, name in enumerate(CLASSES):
#         key = str(i) if i < 10 else chr(ord("a") + i - 10)
#         print(f"  {key} -> {i} -> {name}")

#     cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)

#     index = 0

#     while True:
#         image_path = images[index]
#         img = cv2.imread(str(image_path))

#         if img is None:
#             print(f"Cannot read: {image_path}")
#             index = (index + 1) % len(images)
#             continue

#         boxes = load_existing_labels(image_path)
#         pending_box = None
#         drawing = False
#         start_original = None
#         current_original = None

#         h, w = img.shape[:2]
#         scale = fit_scale(w, h)

#         # Zoom is around the center of the image.
#         min_scale = fit_scale(w, h) * 0.75
#         max_scale = 3.0

#         offset_x = 0
#         offset_y = 0

#         # Mouse callback gets the CURRENT image geometry.
#         callback_data = [img.shape, scale, offset_x, 45]

#         cv2.setMouseCallback(
#             WINDOW_NAME,
#             mouse_callback,
#             callback_data,
#         )

#         while True:
#             callback_data[0] = img.shape
#             callback_data[1] = scale
#             callback_data[2] = offset_x
#             callback_data[3] = 45

#             display, real_offset_y = make_display(
#                 img,
#                 image_path,
#                 index,
#                 len(images),
#                 scale,
#                 offset_x,
#                 offset_y,
#             )

#             cv2.imshow(WINDOW_NAME, display)

#             key = cv2.waitKey(20) & 0xFF

#             if key in (27, ord("q")):
#                 save_labels(image_path, img)
#                 cv2.destroyAllWindows()
#                 print("\nExited.")
#                 return

#             # Class selection for the currently drawn box.
#             cid = key_to_class(key)

#             if cid is not None and pending_box is not None:
#                 x1, y1, x2, y2 = pending_box
#                 boxes.append([x1, y1, x2, y2, cid])
#                 print(f"Added: {cid} -> {CLASSES[cid]}")
#                 pending_box = None

#             elif key == ord("s"):
#                 save_labels(image_path, img)

#             elif key == ord("d"):
#                 if boxes:
#                     removed = boxes.pop()
#                     print(f"Deleted: {CLASSES[removed[4]]}")

#             elif key == ord("r"):
#                 boxes = []
#                 pending_box = None
#                 print("All boxes cleared. Press S to save.")

#             elif key in (ord("+"), ord("=")):
#                 old = scale
#                 scale = min(max_scale, scale * 1.25)
#                 print(f"Zoom: {old:.2f}x -> {scale:.2f}x")

#             elif key in (ord("-"), ord("_")):
#                 old = scale
#                 scale = max(min_scale, scale / 1.25)
#                 print(f"Zoom: {old:.2f}x -> {scale:.2f}x")

#             elif key == ord("n"):
#                 save_labels(image_path, img)
#                 index = (index + 1) % len(images)
#                 break

#             elif key == ord("p"):
#                 save_labels(image_path, img)
#                 index = (index - 1) % len(images)
#                 break

#     cv2.destroyAllWindows()


# if __name__ == "__main__":
#     main()












import cv2
from pathlib import Path

# ============================================================
# LaneLogic Local YOLO Annotation Tool
# - No account
# - No website
# - No separate annotation application
# - Image fits inside the window
# - Mouse coordinates are converted back to original image pixels
# - Zoom in/out for small objects
# ============================================================

CLASSES = [
    "car",                   # 0
    "motorcycle",            # 1
    "bicycle",               # 2
    "auto_rickshaw",         # 3
    "e_rickshaw",            # 4
    "bus",                   # 5
    "truck",                 # 6
    "stall",                 # 7
    "garbage",               # 8
    "scooty",                # 9
]

IMAGE_DIR = Path("dataset/images/val")
LABEL_DIR = Path("dataset/labels/val")

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

WINDOW_NAME = "LaneLogic Annotator"

# Display limits. The image is fitted to this size initially.
MAX_DISPLAY_WIDTH = 1400
MAX_DISPLAY_HEIGHT = 800

boxes = []  # [x1, y1, x2, y2, class_id] in ORIGINAL image coordinates

drawing = False
start_original = None
current_original = None
pending_box = None


def class_name(class_id):
    return CLASSES[class_id]


def key_to_class(key):
    # All 10 classes use the number keys 0-9.
    if ord("0") <= key <= ord("9"):
        cid = key - ord("0")
        return cid if cid < len(CLASSES) else None
    return None


def load_existing_labels(image_path):
    label_path = LABEL_DIR / f"{image_path.stem}.txt"

    if not label_path.exists():
        return []

    img = cv2.imread(str(image_path))
    if img is None:
        return []

    h, w = img.shape[:2]
    result = []

    try:
        with open(label_path, "r", encoding="utf-8") as f:
            for line in f:
                p = line.strip().split()

                if len(p) != 5:
                    continue

                cid = int(p[0])
                if not 0 <= cid < len(CLASSES):
                    continue

                xc, yc, bw, bh = map(float, p[1:])

                x1 = int((xc - bw / 2) * w)
                y1 = int((yc - bh / 2) * h)
                x2 = int((xc + bw / 2) * w)
                y2 = int((yc + bh / 2) * h)

                result.append([x1, y1, x2, y2, cid])

    except Exception as e:
        print(f"Could not read {label_path}: {e}")

    return result


def save_labels(image_path, img):
    LABEL_DIR.mkdir(parents=True, exist_ok=True)

    h, w = img.shape[:2]
    label_path = LABEL_DIR / f"{image_path.stem}.txt"

    with open(label_path, "w", encoding="utf-8") as f:
        for x1, y1, x2, y2, cid in boxes:
            left, right = sorted((x1, x2))
            top, bottom = sorted((y1, y2))

            left = max(0, min(left, w - 1))
            right = max(0, min(right, w - 1))
            top = max(0, min(top, h - 1))
            bottom = max(0, min(bottom, h - 1))

            bw = right - left
            bh = bottom - top

            if bw < 2 or bh < 2:
                continue

            # YOLO normalized coordinates.
            xc = ((left + right) / 2) / w
            yc = ((top + bottom) / 2) / h
            nw = bw / w
            nh = bh / h

            f.write(f"{cid} {xc:.6f} {yc:.6f} {nw:.6f} {nh:.6f}\n")

    print(f"Saved: {label_path}")


def fit_scale(img_w, img_h):
    return min(
        MAX_DISPLAY_WIDTH / img_w,
        MAX_DISPLAY_HEIGHT / img_h,
        1.0
    )


def display_transform(img, scale, offset_x, offset_y):
    """Resize original image for display."""
    h, w = img.shape[:2]

    dw = max(1, int(w * scale))
    dh = max(1, int(h * scale))

    resized = cv2.resize(img, (dw, dh), interpolation=cv2.INTER_AREA)

    canvas = resized
    return canvas


def screen_to_original(x, y, scale, offset_x, offset_y, img_shape):
    """Convert displayed mouse coordinates -> original image pixels."""
    h, w = img_shape[:2]

    ox = int((x - offset_x) / scale)
    oy = int((y - offset_y) / scale)

    ox = max(0, min(ox, w - 1))
    oy = max(0, min(oy, h - 1))

    return ox, oy


def original_to_display(x, y, scale, offset_x, offset_y):
    return (
        int(x * scale + offset_x),
        int(y * scale + offset_y),
    )


def draw_box(display, box, scale, offset_x, offset_y, thickness=2):
    x1, y1, x2, y2, cid = box

    a = original_to_display(x1, y1, scale, offset_x, offset_y)
    b = original_to_display(x2, y2, scale, offset_x, offset_y)

    cv2.rectangle(display, a, b, (255, 255, 255), thickness)

    label = f"{cid}: {CLASSES[cid]}"
    text_y = max(18, a[1] - 5)

    cv2.putText(
        display,
        label,
        (a[0], text_y),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 255, 255),
        2,
    )


def make_display(img, image_path, index, total, scale, offset_x, offset_y):
    base = display_transform(img, scale, offset_x, offset_y)

    # Header.
    header_h = 45
    footer_h = 38

    display = cv2.copyMakeBorder(
        base,
        header_h,
        footer_h,
        0,
        0,
        cv2.BORDER_CONSTANT,
        value=(0, 0, 0),
    )

    # Because the image starts below the header, all display coordinates
    # need the header offset.
    real_offset_y = offset_y + header_h

    for box in boxes:
        draw_box(
            display,
            box,
            scale,
            offset_x,
            real_offset_y,
        )

    if pending_box is not None:
        x1, y1, x2, y2 = pending_box
        temp = [x1, y1, x2, y2, 0]
        draw_box(
            display,
            temp,
            scale,
            offset_x,
            real_offset_y,
            thickness=2,
        )

    if drawing and start_original and current_original:
        x1, y1 = start_original
        x2, y2 = current_original

        a = original_to_display(
            x1, y1, scale, offset_x, real_offset_y
        )
        b = original_to_display(
            x2, y2, scale, offset_x, real_offset_y
        )

        cv2.rectangle(display, a, b, (255, 255, 255), 2)

    # Header text.
    cv2.putText(
        display,
        "Mouse: draw box | 0-9: class | S=save N=next P=prev R=reset D=delete +/- zoom Q=quit",
        (8, 18),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.48,
        (255, 255, 255),
        1,
    )

    cv2.putText(
        display,
        "10 classes: 0-9 | S save | N next | P previous | R reset | D delete | +/- zoom | Q quit",
        (8, 38),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.48,
        (255, 255, 255),
        1,
    )

    # Footer.
    cv2.putText(
        display,
        f"{index + 1}/{total}  {image_path.name}  "
        f"Zoom: {scale:.2f}x  Boxes: {len(boxes)}",
        (8, display.shape[0] - 12),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.52,
        (255, 255, 255),
        1,
    )

    return display, real_offset_y


def mouse_callback(event, x, y, flags, param):
    global drawing, start_original, current_original, pending_box

    img_shape, scale, offset_x, offset_y = param

    ox, oy = screen_to_original(
        x, y, scale, offset_x, offset_y, img_shape
    )

    if event == cv2.EVENT_LBUTTONDOWN:
        drawing = True
        start_original = (ox, oy)
        current_original = (ox, oy)

    elif event == cv2.EVENT_MOUSEMOVE and drawing:
        current_original = (ox, oy)

    elif event == cv2.EVENT_LBUTTONUP and drawing:
        drawing = False
        current_original = (ox, oy)

        if start_original is None:
            return

        x1, y1 = start_original
        x2, y2 = current_original

        left, right = sorted((x1, x2))
        top, bottom = sorted((y1, y2))

        if right - left >= 4 and bottom - top >= 4:
            pending_box = [left, top, right, bottom]
            print(
                "\nBox ready. Press the class key:"
            )
            print(
                "0 car | 1 motorcycle | 2 bicycle | "
                "3 auto_rickshaw | 4 e_rickshaw | 5 bus | "
                "6 truck | 7 stall | 8 garbage | 9 scooty"
            )


def main():
    global boxes, drawing, start_original, current_original
    global pending_box

    if not IMAGE_DIR.exists():
        print(f"\nFolder not found:\n{IMAGE_DIR.resolve()}")
        print("\nCreate:")
        print("dataset/images/train/")
        return

    LABEL_DIR.mkdir(parents=True, exist_ok=True)

    images = sorted(
        p for p in IMAGE_DIR.iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
    )

    if not images:
        print(f"\nNo images found in:\n{IMAGE_DIR.resolve()}")
        return

    print("\n==============================================")
    print("       LaneLogic Local YOLO Annotator")
    print("==============================================")
    print(f"Images: {len(images)}")
    print(f"Image folder: {IMAGE_DIR.resolve()}")
    print(f"Label folder: {LABEL_DIR.resolve()}")
    print("\nClasses:")

    for i, name in enumerate(CLASSES):
        key = str(i) if i < 10 else chr(ord("a") + i - 10)
        print(f"  {key} -> {i} -> {name}")

    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)

    index = 0

    while True:
        image_path = images[index]
        img = cv2.imread(str(image_path))

        if img is None:
            print(f"Cannot read: {image_path}")
            index = (index + 1) % len(images)
            continue

        boxes = load_existing_labels(image_path)
        pending_box = None
        drawing = False
        start_original = None
        current_original = None

        h, w = img.shape[:2]
        scale = fit_scale(w, h)

        # Zoom is around the center of the image.
        min_scale = fit_scale(w, h) * 0.75
        max_scale = 3.0

        offset_x = 0
        offset_y = 0

        # Mouse callback gets the CURRENT image geometry.
        callback_data = [img.shape, scale, offset_x, 45]

        cv2.setMouseCallback(
            WINDOW_NAME,
            mouse_callback,
            callback_data,
        )

        while True:
            callback_data[0] = img.shape
            callback_data[1] = scale
            callback_data[2] = offset_x
            callback_data[3] = 45

            display, real_offset_y = make_display(
                img,
                image_path,
                index,
                len(images),
                scale,
                offset_x,
                offset_y,
            )

            cv2.imshow(WINDOW_NAME, display)

            key = cv2.waitKey(20) & 0xFF

            if key in (27, ord("q")):
                save_labels(image_path, img)
                cv2.destroyAllWindows()
                print("\nExited.")
                return

            # Class selection for the currently drawn box.
            cid = key_to_class(key)

            if cid is not None and pending_box is not None:
                x1, y1, x2, y2 = pending_box
                boxes.append([x1, y1, x2, y2, cid])
                print(f"Added: {cid} -> {CLASSES[cid]}")
                pending_box = None

            elif key == ord("s"):
                save_labels(image_path, img)

            elif key == ord("d"):
                if boxes:
                    removed = boxes.pop()
                    print(f"Deleted: {CLASSES[removed[4]]}")

            elif key == ord("r"):
                boxes = []
                pending_box = None
                print("All boxes cleared. Press S to save.")

            elif key in (ord("+"), ord("=")):
                old = scale
                scale = min(max_scale, scale * 1.25)
                print(f"Zoom: {old:.2f}x -> {scale:.2f}x")

            elif key in (ord("-"), ord("_")):
                old = scale
                scale = max(min_scale, scale / 1.25)
                print(f"Zoom: {old:.2f}x -> {scale:.2f}x")

            elif key == ord("n"):
                save_labels(image_path, img)
                index = (index + 1) % len(images)
                break

            elif key == ord("p"):
                save_labels(image_path, img)
                index = (index - 1) % len(images)
                break

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
