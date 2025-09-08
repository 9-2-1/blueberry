@echo off
title blueberry live
chcp 65001 > nul
call conda activate blueberry

:read
for %%A in (记录.xlsx) do set oldtag=%%~tzA
cls
call python -m blueberry -o blueberry.txt -d

set waits=0
:wait
timeout 1 /nobreak >nul
for %%A in (记录.xlsx) do set tag=%%~tzA
set /a waits+=1
if %waits% GEQ 600 goto :read
if "%tag%" == "%oldtag%" goto :wait

goto :read
