@call conda run --no-capture-output -n blueberry python main.py > blueberry.txt
@type blueberry.txt
@clip < blueberry.txt
pause