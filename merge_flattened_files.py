"""
合并横向展开后的文件，按(登记号, 就诊号)将列追加到一起
"""
import pandas as pd
from pathlib import Path
import logging
from typing import Tuple, Optional

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def find_key_columns(df: pd.DataFrame) -> Tuple[Optional[str], Optional[str]]:
    """
    查找关键列：登记号和就诊号
    
    Args:
        df: DataFrame
        
    Returns:
        (登记号列名, 就诊号列名)
    """
    # 可能的登记号列名
    reg_columns = ['登记号', '登记号_', '登记号 ']
    # 可能的就诊号列名
    visit_columns = ['就诊号', '就诊号_', '就诊号 ', '门诊号', '住院号']
    
    reg_col = None
    visit_col = None
    
    for col in reg_columns:
        if col in df.columns:
            reg_col = col
            break
    
    for col in visit_columns:
        if col in df.columns:
            visit_col = col
            break
    
    return reg_col, visit_col


def load_file(file_path: Path) -> Optional[pd.DataFrame]:
    """
    加载文件并返回DataFrame
    
    Args:
        file_path: 文件路径
        
    Returns:
        DataFrame或None
    """
    try:
        if file_path.suffix == '.csv':
            df = pd.read_csv(file_path, low_memory=False)
        else:
            df = pd.read_excel(file_path, engine='openpyxl')
        
        logger.info(f"  - 读取成功: {len(df):,} 行, {len(df.columns):,} 列")
        return df
    except Exception as e:
        logger.error(f"  - ❌ 读取失败: {e}")
        return None


def merge_flattened_files(
    input_dir: str = "横向展开结果",
    output_file: str = "合并后的数据.csv",
    handle_duplicates: str = "first"
):
    """
    合并横向展开后的文件，按(登记号, 就诊号)将列追加到一起
    
    Args:
        input_dir: 输入目录路径
        output_file: 输出文件路径
        handle_duplicates: 处理重复键的方式
            - "first": 取第一条记录（默认）
            - "last": 取最后一条记录
            - "warn": 发出警告但继续处理
    """
    logger.info("=" * 80)
    logger.info("开始合并横向展开后的文件")
    logger.info("=" * 80)
    logger.info(f"输入目录: {input_dir}")
    logger.info(f"输出文件: {output_file}")
    logger.info(f"处理重复键方式: {handle_duplicates}")
    logger.info("=" * 80)
    
    input_path = Path(input_dir)
    if not input_path.exists():
        logger.error(f"目录不存在: {input_dir}")
        return False
    
    # 获取所有文件
    files = sorted(list(input_path.glob("*.xlsx")) + list(input_path.glob("*.csv")))
    logger.info(f"\n找到 {len(files)} 个文件")
    
    if len(files) == 0:
        logger.error("未找到任何文件")
        return False
    
    # 加载所有文件
    file_data = []
    for idx, file_path in enumerate(files, 1):
        logger.info(f"\n[{idx}/{len(files)}] 处理文件: {file_path.name}")
        df = load_file(file_path)
        
        if df is None:
            continue
        
        # 查找关键列
        reg_col, visit_col = find_key_columns(df)
        
        if reg_col is None:
            logger.warning(f"  - ⚠️  未找到登记号列，跳过此文件")
            continue
        
        # 检查是否有重复的键
        if visit_col:
            df['_merge_key'] = df[reg_col].astype(str) + '_' + df[visit_col].astype(str)
            key_cols = [reg_col, visit_col]
        else:
            df['_merge_key'] = df[reg_col].astype(str)
            key_cols = [reg_col]
            logger.warning(f"  - ⚠️  文件没有就诊号列，只使用登记号作为键")
        
        # 检查重复
        duplicate_count = df['_merge_key'].duplicated().sum()
        if duplicate_count > 0:
            logger.warning(f"  - ⚠️  发现 {duplicate_count} 个重复的键")
            
            if handle_duplicates == "first":
                logger.info(f"  - 保留第一条记录，去除重复")
                df = df.drop_duplicates(subset=['_merge_key'], keep='first')
            elif handle_duplicates == "last":
                logger.info(f"  - 保留最后一条记录，去除重复")
                df = df.drop_duplicates(subset=['_merge_key'], keep='last')
            elif handle_duplicates == "warn":
                logger.warning(f"  - 保留所有记录，但会产生笛卡尔乘积")
        
        file_data.append({
            'file_name': file_path.stem,  # 不带扩展名的文件名
            'df': df,
            'reg_col': reg_col,
            'visit_col': visit_col,
            'key_cols': key_cols
        })
    
    if len(file_data) == 0:
        logger.error("没有成功加载任何文件")
        return False
    
    logger.info(f"\n成功加载 {len(file_data)} 个文件")
    
    # 开始合并
    logger.info("\n" + "=" * 80)
    logger.info("开始合并数据")
    logger.info("=" * 80)
    
    merged_df = None
    
    for idx, file_info in enumerate(file_data, 1):
        df = file_info['df']
        file_name = file_info['file_name']
        reg_col = file_info['reg_col']
        visit_col = file_info['visit_col']
        key_cols = file_info['key_cols']
        
        logger.info(f"\n[{idx}/{len(file_data)}] 合并文件: {file_name}")
        logger.info(f"  - 数据行数: {len(df):,}")
        logger.info(f"  - 数据列数: {len(df.columns):,}")
        
        # 准备合并键
        if visit_col:
            merge_on = [reg_col, visit_col]
        else:
            merge_on = [reg_col]
        
        if merged_df is None:
            # 第一个文件，直接使用
            # 确保键列名统一
            if reg_col != '登记号':
                df = df.rename(columns={reg_col: '登记号'})
            if visit_col and visit_col != '就诊号':
                df = df.rename(columns={visit_col: '就诊号'})
            
            merged_df = df.copy()
            logger.info(f"  - 初始数据: {len(merged_df):,} 行, {len(merged_df.columns):,} 列")
        else:
            # 后续文件，进行合并
            before_rows = len(merged_df)
            before_cols = len(merged_df.columns)
            
            # 确保当前文件的键列名与已合并的数据一致
            df_to_merge = df.copy()
            rename_dict = {}
            if reg_col != '登记号':
                rename_dict[reg_col] = '登记号'
            if visit_col:
                if visit_col != '就诊号':
                    rename_dict[visit_col] = '就诊号'
                merge_on = ['登记号', '就诊号']
            else:
                merge_on = ['登记号']
            
            if rename_dict:
                df_to_merge = df_to_merge.rename(columns=rename_dict)
            
            # 获取非键列，如果与已合并数据有冲突，添加文件名前缀
            non_key_cols = [col for col in df_to_merge.columns if col not in merge_on]
            existing_cols = set(merged_df.columns)
            conflict_cols = [col for col in non_key_cols if col in existing_cols]
            
            if conflict_cols:
                logger.info(f"  - 发现 {len(conflict_cols)} 个列名冲突，将添加文件名前缀")
                rename_conflict = {col: f"{col}_{file_name}" for col in conflict_cols}
                df_to_merge = df_to_merge.rename(columns=rename_conflict)
            
            # 使用outer join，保留所有键
            merged_df = pd.merge(
                merged_df,
                df_to_merge,
                on=merge_on,
                how='outer'
            )
            
            after_rows = len(merged_df)
            after_cols = len(merged_df.columns)
            
            logger.info(f"  - 合并前: {before_rows:,} 行, {before_cols} 列")
            logger.info(f"  - 合并后: {after_rows:,} 行, {after_cols} 列")
            logger.info(f"  - 新增行数: {after_rows - before_rows:,}")
            logger.info(f"  - 新增列数: {after_cols - before_cols}")
            
            # 检查是否有异常增长
            if after_rows > before_rows * 2:
                logger.warning(f"  - ⚠️  数据行数异常增长，可能存在笛卡尔乘积问题")
    
    # 清理临时列
    if '_merge_key' in merged_df.columns:
        merged_df = merged_df.drop(columns=['_merge_key'])
    
    # 按登记号和就诊号排序
    if '就诊号' in merged_df.columns:
        merged_df = merged_df.sort_values(by=['登记号', '就诊号']).reset_index(drop=True)
    else:
        merged_df = merged_df.sort_values(by='登记号').reset_index(drop=True)
    
    # 保存结果
    logger.info("\n" + "=" * 80)
    logger.info("保存合并结果")
    logger.info("=" * 80)
    logger.info(f"最终数据: {len(merged_df):,} 行, {len(merged_df.columns):,} 列")
    
    # 确保输出文件是CSV格式
    output_path = Path(output_file)
    if output_path.suffix.lower() not in ['.csv']:
        output_file = str(output_path.with_suffix('.csv'))
        output_path = Path(output_file)
        logger.info(f"输出文件已改为CSV格式: {output_file}")
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 直接保存为CSV格式
    logger.info(f"正在保存为CSV格式: {output_file}")
    
    try:
        merged_df.to_csv(output_file, index=False, encoding='utf-8-sig')
        file_size_mb = output_path.stat().st_size / (1024**2)
        logger.info(f"✅ 成功保存为CSV格式: {output_file}")
        logger.info(f"   文件大小: {file_size_mb:.2f} MB")
        logger.info(f"   行数: {len(merged_df):,}")
        logger.info(f"   列数: {len(merged_df.columns):,}")
        return True
    except Exception as e:
        logger.error(f"❌ 保存CSV文件失败: {e}")
        return False


def main():
    """主函数"""
    input_dir = "横向展开结果"
    output_file = "合并后的数据.csv"  # 直接使用CSV格式
    
    # 处理重复键的方式：
    # "first" - 取第一条记录（推荐，避免笛卡尔乘积）
    # "last" - 取最后一条记录
    # "warn" - 发出警告但保留所有记录（可能产生笛卡尔乘积）
    handle_duplicates = "first"
    
    merge_flattened_files(
        input_dir=input_dir,
        output_file=output_file,
        handle_duplicates=handle_duplicates
    )


if __name__ == "__main__":
    main()

