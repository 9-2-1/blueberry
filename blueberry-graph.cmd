@echo off

echo �������ɽ�30�� Goldie �����仯����ͼ...
python test_graph.py

if %ERRORLEVEL% NEQ 0 (
    echo ͼ������ʧ�ܡ�
    pause
    exit /b 1
)

echo ͼ�����ɳɹ����ѱ���Ϊ goldie_points_trend.png
pause