@call conda run --no-capture-output -n blueberry python blueberry.py > blueberry.txt
@start "" gvim.exe blueberry.txt
@clip < blueberry.txt