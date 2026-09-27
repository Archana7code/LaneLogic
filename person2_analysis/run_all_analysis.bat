@echo off

cd /d "%USERPROFILE%\Documents\LaneLogic\person2_analysis"

echo ============================================================
echo LANELOGIC - PERSON 2
echo Phase-wise analysis for all roads
echo ============================================================

echo.
echo [1/6] ROAD_001 - Noida
python main.py --phase-input ..\person1_detection\output\detection_stream_1.jsonl --roi roi_config.json --output analysis1.json --phase-output analysis_stream_1.jsonl --road-id ROAD_001 --road-name "Noida"

echo.
echo [2/6] ROAD_002 - Delhi
python main.py --phase-input ..\person1_detection\output\detection_stream_2.jsonl --roi roi_config.json --output analysis2.json --phase-output analysis_stream_2.jsonl --road-id ROAD_002 --road-name "Delhi"

echo.
echo [3/6] ROAD_003 - Ghaziabad
python main.py --phase-input ..\person1_detection\output\detection_stream_3.jsonl --roi roi_config.json --output analysis3.json --phase-output analysis_stream_3.jsonl --road-id ROAD_003 --road-name "Ghaziabad"

echo.
echo [4/6] ROAD_004 - Faridabad
python main.py --phase-input ..\person1_detection\output\detection_stream_4.jsonl --roi roi_config.json --output analysis4.json --phase-output analysis_stream_4.jsonl --road-id ROAD_004 --road-name "Faridabad"

echo.
echo [5/6] ROAD_005
python main.py --phase-input ..\person1_detection\output\detection_stream_5.jsonl --roi roi_config.json --output analysis5.json --phase-output analysis_stream_5.jsonl --road-id ROAD_005 --road-name "Traffic 5"

echo.
echo [6/6] ROAD_006
python main.py --phase-input ..\person1_detection\output\detection_stream_6.jsonl --roi roi_config.json --output analysis6.json --phase-output analysis_stream_6.jsonl --road-id ROAD_006 --road-name "Traffic 6"

echo.
echo ============================================================
echo ALL 6 ROAD ANALYSES COMPLETED
echo ============================================================

pause