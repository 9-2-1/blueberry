@chcp 65001 > nul
@title "请稍候，正在更新Blueberry报告……"
@echo "请稍候，正在更新Blueberry报告……"
@call conda run --no-capture-output -n blueberry python blueberry.py %* > blueberry.txt 2>&1
@start "" gvim.exe blueberry.txt
@clip < blueberry.txt
