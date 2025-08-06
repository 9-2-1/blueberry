@echo off

echo 正在生成近30天 Goldie 点数变化折线图...
python test_graph.py

if %ERRORLEVEL% NEQ 0 (
    echo 图表生成失败。
    pause
    exit /b 1
)

echo 图表生成成功！已保存为 goldie_points_trend.png
pause