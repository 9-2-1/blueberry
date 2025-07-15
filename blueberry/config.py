from datetime import timedelta
from zoneinfo import ZoneInfo

# 提供的时间的时区
CTZ = ZoneInfo("Asia/Shanghai")

# 8小时(时长) * 80%(工作-休息比) ≈ 6.5小时
推荐用时 = timedelta(hours=6.5)
