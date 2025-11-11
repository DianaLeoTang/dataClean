'''
Author: Diana Tang
Date: 2025-11-10 19:16:54
LastEditors: Diana Tang
Description: some description
FilePath: /dataClean/src/data_loader.py
'''
import pandas as pd
import yaml
from pathlib import Path
from typing import Dict, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TimeSeriesLoader:
    """时序数据加载器"""
    
    def __init__(self, config_path: str = "config/cleaning_config.yaml"):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
    
    def load_csv(self, file_path: str, **kwargs) -> pd.DataFrame:
        """
        加载CSV文件
        
        Args:
            file_path: CSV文件路径
            **kwargs: pandas read_csv的额外参数
        
        Returns:
            DataFrame
        """
        logger.info(f"Loading data from {file_path}")
        
        # 使用pyarrow引擎加速大文件读取
        df = pd.read_csv(
            file_path,
            engine='pyarrow' if Path(file_path).stat().st_size > 100_000_000 else 'c',
            **kwargs
        )
        
        logger.info(f"Loaded {len(df)} rows, {len(df.columns)} columns")
        return df
    
    def parse_timestamp(self, df: pd.DataFrame) -> pd.DataFrame:
        """解析时间戳列"""
        ts_col = self.config['timestamp']['column_name']
        ts_format = self.config['timestamp'].get('format')
        tz = self.config['timestamp'].get('timezone')
        
        if ts_col not in df.columns:
            raise ValueError(f"Timestamp column '{ts_col}' not found in data")
        
        logger.info(f"Parsing timestamp column: {ts_col}")
        
        # 转换为datetime
        if ts_format:
            df[ts_col] = pd.to_datetime(df[ts_col], format=ts_format)
        else:
            df[ts_col] = pd.to_datetime(df[ts_col], infer_datetime_format=True)
        
        # 设置时区
        if tz:
            df[ts_col] = df[ts_col].dt.tz_localize(tz, ambiguous='infer')
        
        # 设置为索引
        df.set_index(ts_col, inplace=True)
        df.sort_index(inplace=True)
        
        return df