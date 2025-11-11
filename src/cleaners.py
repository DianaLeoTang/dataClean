import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from scipy import signal
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class TimeSeriesCleaner:
    """时序数据清洗器"""
    
    def __init__(self, config: dict):
        self.config = config
    
    def handle_duplicates(self, df: pd.DataFrame) -> pd.DataFrame:
        """处理重复时间戳"""
        logger.info("Handling duplicate timestamps...")
        
        keep_strategy = self.config['duplicates']['keep']
        
        if keep_strategy == 'mean':
            # 对重复时间戳取平均值
            df = df.groupby(df.index).mean()
        else:
            # 保留first或last
            df = df[~df.index.duplicated(keep=keep_strategy)]
        
        logger.info(f"After handling duplicates: {len(df)} rows")
        return df
    
    def resample_to_frequency(self, df: pd.DataFrame) -> pd.DataFrame:
        """重采样到固定频率"""
        expected_freq = self.config['frequency']['expected']
        logger.info(f"Resampling to {expected_freq} frequency...")
        
        # 重采样
        df_resampled = df.resample(expected_freq).mean()
        
        logger.info(f"After resampling: {len(df_resampled)} rows")
        return df_resampled
    
    def handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """处理缺失值"""
        logger.info("Handling missing values...")
        
        strategy = self.config['missing_values']['strategy']
        max_gap = self.config['missing_values'].get('max_gap', 3)
        
        # 标记连续缺失长度
        missing_mask = df.isnull()
        for col in df.columns:
            if missing_mask[col].any():
                # 计算连续缺失长度
                missing_groups = (missing_mask[col] != missing_mask[col].shift()).cumsum()
                missing_lengths = missing_mask[col].groupby(missing_groups).transform('sum')
                
                # 对于超过max_gap的缺失，根据策略处理
                long_gaps = missing_lengths > max_gap
                
                if strategy == 'interpolate':
                    method = self.config['missing_values'].get('interpolation_method', 'time')
                    df[col] = df[col].interpolate(method=method, limit=max_gap)
                    # 超过max_gap的保持NaN或删除
                    if long_gaps.any():
                        logger.warning(
                            f"Column '{col}': {long_gaps.sum()} values exceed max_gap={max_gap}"
                        )
                
                elif strategy == 'ffill':
                    df[col] = df[col].fillna(method='ffill', limit=max_gap)
                
                elif strategy == 'bfill':
                    df[col] = df[col].fillna(method='bfill', limit=max_gap)
                
                elif strategy == 'mean':
                    # 使用滚动窗口均值
                    window = self.config['missing_values'].get('window', 24)
                    rolling_mean = df[col].rolling(window=window, center=True).mean()
                    df[col] = df[col].fillna(rolling_mean)
        
        if strategy == 'drop':
            df = df.dropna()
        
        remaining_missing = df.isnull().sum().sum()
        logger.info(f"Remaining missing values: {remaining_missing}")
        
        return df
    
    def detect_outliers_iqr(
        self, 
        series: pd.Series, 
        threshold: float = 1.5
    ) -> pd.Series:
        """IQR方法检测异常值"""
        Q1 = series.quantile(0.25)
        Q3 = series.quantile(0.75)
        IQR = Q3 - Q1
        
        lower_bound = Q1 - threshold * IQR
        upper_bound = Q3 + threshold * IQR
        
        outliers = (series < lower_bound) | (series > upper_bound)
        return outliers
    
    def detect_outliers_zscore(
        self, 
        series: pd.Series, 
        threshold: float = 3.0
    ) -> pd.Series:
        """Z-score方法检测异常值"""
        z_scores = np.abs((series - series.mean()) / series.std())
        outliers = z_scores > threshold
        return outliers
    
    def detect_outliers_rolling_zscore(
        self,
        series: pd.Series,
        window: int = 24,
        threshold: float = 3.0
    ) -> pd.Series:
        """滚动Z-score方法检测异常值（适合时序数据）"""
        rolling_mean = series.rolling(window=window, center=True).mean()
        rolling_std = series.rolling(window=window, center=True).std()
        
        z_scores = np.abs((series - rolling_mean) / rolling_std)
        outliers = z_scores > threshold
        
        return outliers
    
    def detect_outliers_isolation_forest(
        self,
        series: pd.Series,
        contamination: float = 0.01
    ) -> pd.Series:
        """Isolation Forest方法检测异常值"""
        values = series.values.reshape(-1, 1)
        iso_forest = IsolationForest(
            contamination=contamination,
            random_state=42
        )
        predictions = iso_forest.fit_predict(values)
        outliers = predictions == -1
        
        return pd.Series(outliers, index=series.index)
    
    def handle_outliers(self, df: pd.DataFrame) -> pd.DataFrame:
        """处理异常值"""
        logger.info("Detecting and handling outliers...")
        
        method = self.config['outliers']['method']
        threshold = self.config['outliers']['threshold']
        action = self.config['outliers']['action']
        
        target_col = self.config['target']['column_name']
        
        if target_col not in df.columns:
            logger.warning(f"Target column '{target_col}' not found, skipping outlier detection")
            return df
        
        # 检测异常值
        if method == 'iqr':
            outliers = self.detect_outliers_iqr(df[target_col], threshold)
        elif method == 'zscore':
            outliers = self.detect_outliers_zscore(df[target_col], threshold)
        elif method == 'rolling_zscore':
            window = self.config['outliers'].get('window_size', 24)
            outliers = self.detect_outliers_rolling_zscore(
                df[target_col], window, threshold
            )
        elif method == 'isolation_forest':
            outliers = self.detect_outliers_isolation_forest(
                df[target_col], 
                contamination=threshold
            )
        else:
            logger.warning(f"Unknown outlier detection method: {method}")
            return df
        
        outlier_count = outliers.sum()
        logger.info(f"Detected {outlier_count} outliers ({outlier_count/len(df)*100:.2f}%)")
        
        # 处理异常值
        if action == 'remove':
            df = df[~outliers]
            logger.info(f"Removed outliers, remaining: {len(df)} rows")
        
        elif action == 'clip':
            # 裁剪到合理范围
            Q1 = df[target_col].quantile(0.25)
            Q3 = df[target_col].quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - threshold * IQR
            upper_bound = Q3 + threshold * IQR
            
            df.loc[outliers, target_col] = df.loc[outliers, target_col].clip(
                lower_bound, upper_bound
            )
            logger.info("Clipped outliers to bounds")
        
        elif action == 'interpolate':
            # 将异常值设为NaN后插值
            df.loc[outliers, target_col] = np.nan
            df[target_col] = df[target_col].interpolate(method='time')
            logger.info("Interpolated outliers")
        
        elif action == 'flag':
            # 只标记不处理
            df['is_outlier'] = outliers
            logger.info("Flagged outliers (no removal)")
        
        return df
    
    def apply_smoothing(self, df: pd.DataFrame) -> pd.DataFrame:
        """应用平滑处理"""
        if not self.config['smoothing'].get('enabled', False):
            return df
        
        logger.info("Applying smoothing...")
        
        method = self.config['smoothing']['method']
        window = self.config['smoothing']['window']
        target_col = self.config['target']['column_name']
        
        if method == 'moving_average':
            df[f'{target_col}_smoothed'] = df[target_col].rolling(
                window=window, 
                center=True
            ).mean()
        
        elif method == 'ewm':
            df[f'{target_col}_smoothed'] = df[target_col].ewm(
                span=window
            ).mean()
        
        elif method == 'savgol':
            # Savitzky-Golay滤波
            df[f'{target_col}_smoothed'] = signal.savgol_filter(
                df[target_col], 
                window_length=window,
                polyorder=3
            )
        
        logger.info(f"Applied {method} smoothing")
        return df
    
    def clean(self, df: pd.DataFrame) -> pd.DataFrame:
        """执行完整的清洗流程"""
        logger.info("=" * 50)
        logger.info("Starting time series cleaning pipeline")
        logger.info("=" * 50)
        
        # 1. 处理重复值
        df = self.handle_duplicates(df)
        
        # 2. 重采样到固定频率
        df = self.resample_to_frequency(df)
        
        # 3. 处理缺失值
        df = self.handle_missing_values(df)
        
        # 4. 处理异常值
        df = self.handle_outliers(df)
        
        # 5. 平滑处理（可选）
        df = self.apply_smoothing(df)
        
        logger.info("=" * 50)
        logger.info("Cleaning pipeline completed")
        logger.info("=" * 50)
        
        return df