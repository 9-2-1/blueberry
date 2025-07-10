@chcp 65001
@set /p oldt=上一个报告的时间:
@title "请稍候，正在更新Blueberry报告……"
@echo "请稍候，正在更新Blueberry报告……"
@call conda run --no-capture-output -n blueberry python blueberry.py -c -d -s -f "%oldt%" > blueberry.txt 2>&1
@start "" gvim.exe blueberry.txt
@clip < blueberry.txt
