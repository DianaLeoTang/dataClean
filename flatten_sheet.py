"""
将Excel中指定sheet页的数据横向展开
处理同一登记号和就诊号有多条记录（不同时间）的情况
"""
import pandas as pd
from pathlib import Path
import logging
from typing import Optional

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def find_key_columns(df: pd.DataFrame) -> tuple:
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


def find_time_column(df: pd.DataFrame) -> Optional[str]:
    """
    查找时间列
    
    Args:
        df: DataFrame
        
    Returns:
        时间列名，如果找不到返回None
    """
    # 可能的时间列名
    time_keywords = ['时间', '日期', 'date', 'time', 'datetime', '记录时间', '测量时间']
    
    for col in df.columns:
        col_lower = str(col).lower()
        for keyword in time_keywords:
            if keyword in col_lower:
                return col
    
    return None


def flatten_sheet(
    input_file: str,
    sheet_name: str,
    output_file: str,
    key_columns: Optional[list] = None
) -> bool:
    """
    将sheet页中的数据横向展开
    
    Args:
        input_file: 输入的Excel文件路径
        sheet_name: 要处理的sheet名称
        output_file: 输出的Excel文件路径
        key_columns: 用于分组的列（如['登记号', '就诊号']），如果为None则自动查找
    
    Returns:
        True if successful, False otherwise
    """
    logger.info(f"开始处理文件: {input_file}, Sheet: {sheet_name}")
    
    # 读取sheet
    try:
        df = pd.read_excel(input_file, sheet_name=sheet_name)
        logger.info(f"读取到 {len(df)} 行, {len(df.columns)} 列")
        logger.info(f"列名: {list(df.columns)[:10]}...")  # 显示前10个列名
    except Exception as e:
        logger.error(f"读取Excel文件失败: {e}")
        return False
    
    # 查找关键列
    if key_columns is None:
        reg_col, visit_col = find_key_columns(df)
        if reg_col:
            key_columns = [reg_col]
            if visit_col:
                key_columns.append(visit_col)
        else:
            logger.error("未找到登记号列，请手动指定key_columns参数")
            return False
    
    logger.info(f"使用关键列: {key_columns}")
    
    # 检查关键列是否存在
    for col in key_columns:
        if col not in df.columns:
            logger.error(f"关键列 '{col}' 不存在于数据中")
            return False
    
    # 查找时间列
    time_col = find_time_column(df)
    if time_col:
        logger.info(f"找到时间列: {time_col}")
        # 将时间列转换为datetime类型
        try:
            df[time_col] = pd.to_datetime(df[time_col], errors='coerce')
        except Exception as e:
            logger.warning(f"转换时间列失败: {e}")
    else:
        logger.warning("未找到时间列，将按原始顺序展开")
        time_col = None
    
    # 获取需要展开的列（除了关键列和时间列）
    data_columns = [col for col in df.columns if col not in key_columns and col != time_col]
    logger.info(f"需要展开的数据列共 {len(data_columns)} 个: {data_columns[:5]}...")
    
    # 按关键列分组，对每组内的记录进行横向展开
    logger.info("开始横向展开数据...")
    
    result_rows = []
    
    for (key_values), group_df in df.groupby(key_columns):
        # key_values可能是单个值或元组
        if len(key_columns) == 1:
            key_dict = {key_columns[0]: key_values}
        else:
            key_dict = dict(zip(key_columns, key_values))
        
        # 如果有时间列，按时间排序
        if time_col:
            group_df = group_df.sort_values(by=time_col).reset_index(drop=True)
        
        num_records = len(group_df)
        
        # 如果只有一条记录，直接使用
        if num_records == 1:
            row_dict = key_dict.copy()
            for col in data_columns:
                row_dict[col] = group_df.iloc[0][col]
            if time_col:
                row_dict[time_col] = group_df.iloc[0][time_col]
            result_rows.append(row_dict)
        else:
            # 多条记录，横向展开
            logger.debug(f"登记号 {key_dict.get('登记号', key_dict)} 有 {num_records} 条记录，进行横向展开")
            
            row_dict = key_dict.copy()
            
            # 展开数据列
            for idx, (_, record) in enumerate(group_df.iterrows(), 1):
                for col in data_columns:
                    # 列名格式：原列名_序号
                    new_col_name = f"{col}_{idx}"
                    row_dict[new_col_name] = record[col]
                
                # 如果有时间列，也展开时间
                if time_col:
                    new_time_col = f"{time_col}_{idx}"
                    row_dict[new_time_col] = record[time_col]
            
            result_rows.append(row_dict)
    
    # 转换为DataFrame
    result_df = pd.DataFrame(result_rows)
    
    logger.info(f"展开完成！原始数据 {len(df)} 行，展开后 {len(result_df)} 行")
    logger.info(f"原始列数: {len(df.columns)}, 展开后列数: {len(result_df.columns)}")
    
    # 保存结果
    logger.info(f"保存结果到: {output_file}")
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    
    try:
        result_df.to_excel(output_file, index=False, engine='openpyxl')
        logger.info(f"✅ 成功！数据已保存到: {output_file}")
        logger.info(f"   包含 {len(result_df)} 行, {len(result_df.columns)} 列")
        return True
    except Exception as e:
        logger.error(f"保存文件失败: {e}")
        # 如果openpyxl不可用，尝试保存为CSV
        try:
            csv_file = output_file.replace('.xlsx', '.csv')
            result_df.to_csv(csv_file, index=False, encoding='utf-8-sig')
            logger.info(f"已保存为CSV格式: {csv_file}")
            return True
        except Exception as e2:
            logger.error(f"保存CSV文件也失败: {e2}")
            return False


def flatten_all_sheets(
    input_file: str,
    output_dir: str = "横向展开结果",
    skip_sheets: Optional[list] = None
):
    """
    处理Excel文件中的所有sheet页，为每个sheet生成横向展开的文件
    
    Args:
        input_file: 输入的Excel文件路径
        output_dir: 输出目录
        skip_sheets: 要跳过的sheet名称列表
    """
    logger.info(f"开始处理文件: {input_file}")
    
    # 读取所有sheet名称
    try:
        excel_file = pd.ExcelFile(input_file)
        sheet_names = excel_file.sheet_names
        logger.info(f"找到 {len(sheet_names)} 个sheet: {sheet_names}")
    except Exception as e:
        logger.error(f"读取Excel文件失败: {e}")
        return
    
    if skip_sheets is None:
        skip_sheets = []
    
    # 创建输出目录
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # 处理每个sheet
    success_count = 0
    failed_count = 0
    
    for idx, sheet_name in enumerate(sheet_names, 1):
        if sheet_name in skip_sheets:
            logger.info(f"[{idx}/{len(sheet_names)}] 跳过 Sheet: {sheet_name}")
            continue
        
        logger.info(f"\n{'='*60}")
        logger.info(f"[{idx}/{len(sheet_names)}] 处理 Sheet: {sheet_name}")
        logger.info(f"{'='*60}")
        
        # 生成输出文件名（使用sheet名称）
        # 清理文件名中的特殊字符
        safe_sheet_name = sheet_name.replace('/', '_').replace('\\', '_').replace(':', '_')
        output_file = output_path / f"{safe_sheet_name}_横向展开.xlsx"
        
        try:
            success = flatten_sheet(
                input_file=input_file,
                sheet_name=sheet_name,
                output_file=str(output_file)
            )
            if success:
                success_count += 1
            else:
                failed_count += 1
        except Exception as e:
            logger.error(f"处理 Sheet '{sheet_name}' 时出错: {e}")
            failed_count += 1
            continue
    
    logger.info(f"\n{'='*60}")
    logger.info(f"处理完成！成功: {success_count}, 失败: {failed_count}")
    logger.info(f"输出目录: {output_path.absolute()}")
    logger.info(f"{'='*60}")


def main():
    """主函数"""
    # 配置输入输出文件路径
    input_file = "数据们.xlsx"
    output_dir = "横向展开结果"  # 输出目录
    
    # 可选：指定要跳过的sheet（如果需要）
    skip_sheets = []  # 例如: ["Sheet1", "Sheet2"]
    
    # 处理所有sheet
    flatten_all_sheets(
        input_file=input_file,
        output_dir=output_dir,
        skip_sheets=skip_sheets
    )


if __name__ == "__main__":
    main()

