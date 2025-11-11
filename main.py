import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import logging
from src.data_loader import TimeSeriesLoader
from src.validators import TimeSeriesValidator
from src.cleaners import TimeSeriesCleaner
from src.transformers import TimeSeriesTransformer

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 设置绘图样式
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")


def visualize_cleaning_results(
    df_before: pd.DataFrame,
    df_after: pd.DataFrame,
    target_col: str,
    output_path: str = "output/cleaning_comparison.png"
):
    """可视化清洗前后对比"""
    fig, axes = plt.subplots(2, 1, figsize=(15, 10))
    
    # 清洗前
    axes[0].plot(df_before.index, df_before[target_col], alpha=0.7, label='Original')
    axes[0].set_title('Before Cleaning', fontsize=14, fontweight='bold')
    axes[0].set_xlabel('Time')
    axes[0].set_ylabel(target_col)
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)
    
    # 清洗后
    axes[1].plot(df_after.index, df_after[target_col], alpha=0.7, color='green', label='Cleaned')
    if f'{target_col}_smoothed' in df_after.columns:
        axes[1].plot(
            df_after.index, 
            df_after[f'{target_col}_smoothed'], 
            alpha=0.7, 
            color='red', 
            label='Smoothed'
        )
    axes[1].set_title('After Cleaning', fontsize=14, fontweight='bold')
    axes[1].set_xlabel('Time')
    axes[1].set_ylabel(target_col)
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # 确保输出目录存在
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    logger.info(f"Visualization saved to {output_path}")
    plt.close()


def main():
    """主函数"""
    # 1. 加载数据
    loader = TimeSeriesLoader()
    df_raw = loader.load_csv("某地乳腺检查数据.csv")
    
    # 2. 解析时间戳
    df = loader.parse_timestamp(df_raw)
    
    # 3. 数据验证
    validator = TimeSeriesValidator()
    report = validator.generate_report(df, loader.config)
    
    logger.info("\n" + "="*50)
    logger.info("VALIDATION REPORT")
    logger.info("="*50)
    for key, value in report.items():
        logger.info(f"{key}: {value}")
    
    # 保存原始数据用于对比
    df_before = df.copy()
    
    # 4. 数据清洗
    cleaner = TimeSeriesCleaner(loader.config)
    df_cleaned = cleaner.clean(df)
    
    # 5. 特征工程（可选）
    transformer = TimeSeriesTransformer()
    target_col = loader.config['target']['column_name']
    
    df_cleaned = transformer.add_time_features(df_cleaned)
    df_cleaned = transformer.add_lag_features(df_cleaned, target_col, lags=[1, 7, 24])
    df_cleaned = transformer.add_rolling_features(df_cleaned, target_col, windows=[7, 24, 168])
    df_cleaned = transformer.add_diff_features(df_cleaned, target_col, periods=[1, 24])
    
    # 6. 可视化
    visualize_cleaning_results(df_before, df_cleaned, target_col)
    
    # 7. 导出结果
    output_path = "data/output/cleaned_data.csv"
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    df_cleaned.to_csv(output_path)
    logger.info(f"Cleaned data saved to {output_path}")
    
    # 导出清洗报告
    report_path = "data/output/cleaning_report.txt"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("="*50 + "\n")
        f.write("TIME SERIES CLEANING REPORT\n")
        f.write("="*50 + "\n\n")
        f.write(f"Original rows: {len(df_before)}\n")
        f.write(f"Cleaned rows: {len(df_cleaned)}\n")
        f.write(f"Rows removed: {len(df_before) - len(df_cleaned)}\n")
        f.write(f"Columns: {len(df_cleaned.columns)}\n\n")
        f.write("Validation Report:\n")
        for key, value in report.items():
            f.write(f"  {key}: {value}\n")
    
    logger.info(f"Cleaning report saved to {report_path}")
    logger.info("\n🎉 Pipeline completed successfully!")


if __name__ == "__main__":
    main()