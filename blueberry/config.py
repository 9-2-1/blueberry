from datetime import timedelta
from pytz import timezone

# 提供的时间的时区
CTZ = timezone("Asia/ShangHai")

# 8小时(时长) * 80%(工作-休息比) ≈ 6.5小时
推荐用时 = timedelta(hours=6.5)
