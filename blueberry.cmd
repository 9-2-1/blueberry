@chcp 65001 > nul
@title "请稍候，正在更新Blueberry报告……"
@echo "请稍候，正在更新Blueberry报告……"
@call conda run --no-capture-output -n blueberry python -m blueberry -o blueberry.txt %*
@if errorlevel 1 pause & goto :eof
@start "" gvim.exe -c "colorscheme evening | set nowrap | AnsiEsc" blueberry.txt
@clip < blueberry.txt
