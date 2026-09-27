@echo off

cd /d "%USERPROFILE%\Documents\LaneLogic\person1_detection"

if not exist output mkdir output

echo ============================================================
echo LANELOGIC - PERSON 1
echo Processing all traffic videos
echo ============================================================

echo.
echo [1/6] Traffic 1 - ROAD_001 - Noida
python main.py --source videos\traffic1.mp4 --model yolov8s.pt --output output\detections1.json --csv output\detections1.csv --show --phase-seconds 5 --phase-output output\detection_stream_1.jsonl --road-id ROAD_001 --road-name "Noida" --source-name "traffic1.mp4" --clear-phase-output

echo.
echo [2/6] Traffic 2 - ROAD_002 - Delhi
python main.py --source videos\traffic2.mp4 --model yolov8s.pt --output output\detections2.json --csv output\detections2.csv --show --phase-seconds 5 --phase-output output\detection_stream_2.jsonl --road-id ROAD_002 --road-name "Delhi" --source-name "traffic2.mp4" --clear-phase-output

echo.
echo [3/6] Traffic 3 - ROAD_003 - Ghaziabad
python main.py --source videos\traffic3.mp4 --model yolov8s.pt --output output\detections3.json --csv output\detections3.csv --show --phase-seconds 5 --phase-output output\detection_stream_3.jsonl --road-id ROAD_003 --road-name "Ghaziabad" --source-name "traffic3.mp4" --clear-phase-output

echo.
echo [4/6] Traffic 4 - ROAD_004 - Faridabad
python main.py --source videos\traffic4.mp4 --model yolov8s.pt --output output\detections4.json --csv output\detections4.csv --show --phase-seconds 5 --phase-output output\detection_stream_4.jsonl --road-id ROAD_004 --road-name "Faridabad" --source-name "traffic4.mp4" --clear-phase-output

echo.
echo [5/6] Traffic 5 - ROAD_005
python main.py --source videos\traffic5.mp4 --model yolov8s.pt --output output\detections5.json --csv output\detections5.csv --show --phase-seconds 5 --phase-output output\detection_stream_5.jsonl --road-id ROAD_005 --road-name "Traffic 5" --source-name "traffic5.mp4" --clear-phase-output

echo.
echo [6/6] Traffic 6 - ROAD_006
python main.py --source videos\traffic6.mp4 --model yolov8s.pt --output output\detections6.json --csv output\detections6.csv --show --phase-seconds 5 --phase-output output\detection_stream_6.jsonl --road-id ROAD_006 --road-name "Traffic 6" --source-name "traffic6.mp4" --clear-phase-output

echo.
echo ============================================================
echo ALL 6 VIDEOS COMPLETED
echo ============================================================

pause