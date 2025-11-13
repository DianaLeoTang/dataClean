import pandas as pd
import numpy as np

df = pd.read_csv("./某地乳腺检查数据.csv")

# 缺失统计表
missing_report = df.isnull().sum().to_frame("MissingCount")
missing_report["MissingPercent"] = (missing_report["MissingCount"] / len(df) * 100).round(2)
missing_report = missing_report.sort_values("MissingPercent", ascending=False)

# 重复情况
# 检查ID列的重复
duplicate_ids = df[df.duplicated(subset=["ID"], keep=False)]
# 检查所有列的完全重复
duplicate_rows = df[df.duplicated(keep=False)]

# 基本信息
df.info()
df.describe(include='all')
