'''
Author: Diana Tang
Date: 2025-11-10 19:17:01
LastEditors: Diana Tang
Description: some description
FilePath: /dataClean/src/validators.py
'''
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)


class TimeSeriesValidator:
    """时序数据验证器"""
    
    @staticmethod
    def check_monotonic(df: pd.DataFrame) -> bool:
        """检查时间序列是否单调递增"""
        is_monotonic = df.index.is_monotonic_increasing
        if not is_monotonic:
            logger.warning("⚠️  Time series is not monotonically increasing")
        return is_monotonic
    
    @staticmethod
    def check_duplicates(df: pd.DataFrame) -> Tuple[bool, int]:
        """检查重复时间戳"""
        duplicates = df.index.duplicated()
        dup_count = duplicates.sum()
        
        if dup_count > 0:
            logger.warning(f"⚠️  Found {dup_count} duplicate timestamps")
            logger.info(f"Duplicate timestamps: {df.index[duplicates].tolist()[:5]}")
        
        return dup_count > 0, dup_count
    
    @staticmethod
    def check_missing_values(df: pd.DataFrame) -> Dict[str, int]:
        """检查缺失值"""
        missing = df.isnull().sum()
        missing_dict = missing[missing > 0].to_dict()
        
        if missing_dict:
            logger.warning(f"⚠️  Missing values found: {missing_dict}")
        
        return missing_dict
    
    @staticmethod
    def check_frequency(df: pd.DataFrame, expected_freq: str) -> Dict:
        """检查采样频率"""
        inferred_freq = pd.infer_freq(df.index)
        time_diffs = df.index.to_series().diff()
        
        freq_info = {
            'expected': expected_freq,
            'inferred': inferred_freq,
            'mode_diff': time_diffs.mode()[0] if len(time_diffs) > 0 else None,
            'min_diff': time_diffs.min(),
            'max_diff': time_diffs.max(),
            'is_regular': inferred_freq == expected_freq
        }
        
        if not freq_info['is_regular']:
            logger.warning(
                f"⚠️  Frequency mismatch: expected {expected_freq}, "
                f"inferred {inferred_freq}"
            )
        
        return freq_info
    
    @staticmethod
    def generate_report(df: pd.DataFrame, config: Dict) -> Dict:
        """生成完整的验证报告"""
        report = {
            'total_rows': len(df),
            'date_range': (df.index.min(), df.index.max()),
            'duration': df.index.max() - df.index.min(),
            'is_monotonic': TimeSeriesValidator.check_monotonic(df),
            'duplicates': TimeSeriesValidator.check_duplicates(df),
            'missing_values': TimeSeriesValidator.check_missing_values(df),
            'frequency': TimeSeriesValidator.check_frequency(
                df, 
                config['frequency']['expected']
            )
        }
        
        return report