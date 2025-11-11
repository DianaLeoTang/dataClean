'''
Author: Diana Tang
Date: 2025-11-10 19:17:14
LastEditors: Diana Tang
Description: some description
FilePath: /dataClean/src/transformers.py
'''
import pandas as pd
import numpy as np
from typing import List
import logging

logger = logging.getLogger(__name__)


class TimeSeriesTransformer:
    """时序特征工程"""
    
    @staticmethod
    def add_time_features(df: pd.DataFrame) -> pd.DataFrame:
        """添加时间特征"""
        logger.info("Adding time features...")
        
        df['hour'] = df.index.hour
        df['day_of_week'] = df.index.dayofweek
        df['day_of_month'] = df.index.day
        df['month'] = df.index.month
        df['quarter'] = df.index.quarter
        df['year'] = df.index.year
        df['is_weekend'] = df.index.dayofweek.isin([5, 6]).astype(int)
        df['is_month_start'] = df.index.is_month_start.astype(int)
        df['is_month_end'] = df.index.is_month_end.astype(int)
        
        return df
    
    @staticmethod
    def add_lag_features(
        df: pd.DataFrame,
        column: str,
        lags: List[int]
    ) -> pd.DataFrame:
        """添加滞后特征"""
        logger.info(f"Adding lag features for {column}...")
        
        for lag in lags:
            df[f'{column}_lag_{lag}'] = df[column].shift(lag)
        
        return df
    
    @staticmethod
    def add_rolling_features(
        df: pd.DataFrame,
        column: str,
        windows: List[int]
    ) -> pd.DataFrame:
        """添加滚动窗口特征"""
        logger.info(f"Adding rolling features for {column}...")
        
        for window in windows:
            df[f'{column}_rolling_mean_{window}'] = df[column].rolling(
                window=window
            ).mean()
            df[f'{column}_rolling_std_{window}'] = df[column].rolling(
                window=window
            ).std()
            df[f'{column}_rolling_min_{window}'] = df[column].rolling(
                window=window
            ).min()
            df[f'{column}_rolling_max_{window}'] = df[column].rolling(
                window=window
            ).max()
        
        return df
    
    @staticmethod
    def add_diff_features(
        df: pd.DataFrame,
        column: str,
        periods: List[int]
    ) -> pd.DataFrame:
        """添加差分特征"""
        logger.info(f"Adding diff features for {column}...")
        
        for period in periods:
            df[f'{column}_diff_{period}'] = df[column].diff(period)
        
        return df