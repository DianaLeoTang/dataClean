"""
计算横向展开后的数据按登记号和就诊号合并后的行数
只计算，不实际合并数据
"""
import pandas as pd
from pathlib import Path
import logging
from typing import Dict, Set, Tuple
from collections import defaultdict

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def find_key_columns(df: pd.DataFrame) -> Tuple[str, str]:
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


def analyze_file(file_path: Path) -> Dict:
    """
    分析单个文件，返回关键信息
    
    Args:
        file_path: 文件路径
        
    Returns:
        包含分析结果的字典
    """
    logger.info(f"分析文件: {file_path.name}")
    
    try:
        # 根据文件扩展名选择读取方式
        if file_path.suffix == '.csv':
            df = pd.read_csv(file_path, low_memory=False)
        else:
            df = pd.read_excel(file_path, engine='openpyxl')
        
        logger.info(f"  - 文件行数: {len(df):,}")
        logger.info(f"  - 文件列数: {len(df.columns):,}")
        
        # 查找关键列
        reg_col, visit_col = find_key_columns(df)
        
        if reg_col is None:
            logger.warning(f"  - ⚠️  未找到登记号列，跳过此文件")
            return None
        
        # 检查是否有缺失值
        missing_reg = df[reg_col].isna().sum()
        if missing_reg > 0:
            logger.warning(f"  - ⚠️  登记号有 {missing_reg} 个缺失值")
        
        # 如果只有登记号，没有就诊号
        if visit_col is None:
            logger.info(f"  - 使用关键列: {reg_col} (无就诊号)")
            # 统计每个登记号出现的次数
            reg_counts = df[reg_col].value_counts()
            unique_regs = len(reg_counts)
            duplicate_regs = (reg_counts > 1).sum()
            max_duplicates = reg_counts.max() if len(reg_counts) > 0 else 0
            
            return {
                'file_name': file_path.name,
                'rows': len(df),
                'reg_col': reg_col,
                'visit_col': None,
                'unique_keys': unique_regs,
                'duplicate_keys': duplicate_regs,
                'max_duplicates': max_duplicates,
                'key_counts': reg_counts.to_dict(),
                'has_visit': False
            }
        else:
            logger.info(f"  - 使用关键列: {reg_col}, {visit_col}")
            
            # 检查就诊号缺失值
            missing_visit = df[visit_col].isna().sum()
            if missing_visit > 0:
                logger.warning(f"  - ⚠️  就诊号有 {missing_visit} 个缺失值")
            
            # 创建组合键
            df['_key'] = df[reg_col].astype(str) + '_' + df[visit_col].astype(str)
            
            # 统计每个(登记号, 就诊号)组合出现的次数
            key_counts = df['_key'].value_counts()
            unique_keys = len(key_counts)
            duplicate_keys = (key_counts > 1).sum()
            max_duplicates = key_counts.max() if len(key_counts) > 0 else 0
            
            logger.info(f"  - 唯一(登记号, 就诊号)组合数: {unique_keys:,}")
            if duplicate_keys > 0:
                logger.warning(f"  - ⚠️  有 {duplicate_keys:,} 个重复的(登记号, 就诊号)组合")
                logger.warning(f"  - ⚠️  最多重复次数: {max_duplicates}")
            
            return {
                'file_name': file_path.name,
                'rows': len(df),
                'reg_col': reg_col,
                'visit_col': visit_col,
                'unique_keys': unique_keys,
                'duplicate_keys': duplicate_keys,
                'max_duplicates': max_duplicates,
                'key_counts': key_counts.to_dict(),
                'has_visit': True
            }
            
    except Exception as e:
        logger.error(f"  - ❌ 读取文件失败: {e}")
        return None


def calculate_merge_size(input_dir: str = "横向展开结果"):
    """
    计算按登记号和就诊号合并后的数据量（笛卡尔乘积）
    
    说明：
    1. 如果使用(登记号, 就诊号)作为关联键，当同一个键在多个文件中都有记录时，
       合并会产生笛卡尔乘积。
    2. 例如：文件1（心跳）中登记号A+就诊号1有3条记录，
           文件2（入院记录）中登记号A+就诊号1有2条记录，
           合并后会产生 3 × 2 = 6 条记录。
    3. 本脚本只计算数据量，不实际合并数据。
    
    Args:
        input_dir: 输入目录路径
    """
    logger.info("=" * 80)
    logger.info("计算按(登记号, 就诊号)合并后的数据量（笛卡尔乘积）")
    logger.info("=" * 80)
    
    input_path = Path(input_dir)
    if not input_path.exists():
        logger.error(f"目录不存在: {input_dir}")
        return
    
    # 获取所有文件
    files = list(input_path.glob("*.xlsx")) + list(input_path.glob("*.csv"))
    logger.info(f"找到 {len(files)} 个文件")
    
    if len(files) == 0:
        logger.error("未找到任何文件")
        return
    
    # 分析每个文件
    file_analyses = []
    for file_path in files:
        analysis = analyze_file(file_path)
        if analysis:
            file_analyses.append(analysis)
    
    if len(file_analyses) == 0:
        logger.error("没有成功分析任何文件")
        return
    
    # 首先计算所有文件行数的乘积（完全笛卡尔乘积，不考虑键匹配）
    logger.info("\n" + "=" * 80)
    logger.info("计算1：所有文件行数的乘积（完全笛卡尔乘积）")
    logger.info("=" * 80)
    logger.info("说明：这是最坏情况，假设所有文件的所有行都做笛卡尔乘积合并")
    logger.info("-" * 80)
    
    file_rows = []
    for analysis in file_analyses:
        rows = analysis['rows']
        file_rows.append((analysis['file_name'], rows))
        logger.info(f"  - {analysis['file_name']}: {rows:,} 行")
    
    # 计算乘积
    total_cartesian_product = 1
    for _, rows in file_rows:
        total_cartesian_product *= rows
    
    logger.info(f"\n所有文件行数的乘积: {total_cartesian_product:,}")
    
    # 估算内存占用
    estimated_memory_gb = total_cartesian_product * 1024 / (1024**3)
    logger.info(f"估算内存占用（假设每行1KB）: {estimated_memory_gb:.2f} GB")
    logger.info(f"估算内存占用（假设每行5KB）: {estimated_memory_gb * 5:.2f} GB")
    
    # 检查是否超出合理范围
    if total_cartesian_product > 10**12:  # 1万亿
        logger.error(f"\n❌ 警告：完全笛卡尔乘积超过1万亿行，绝对会超出内存限制！")
        logger.error(f"   这种合并方式不可行，必须使用键匹配的方式合并。")
    elif total_cartesian_product > 10**9:  # 10亿
        logger.error(f"\n❌ 警告：完全笛卡尔乘积超过10亿行，会导致内存溢出！")
        logger.error(f"   强烈建议使用键匹配的方式合并，而不是完全笛卡尔乘积。")
    elif total_cartesian_product > 10**6:  # 100万
        logger.warning(f"\n⚠️  警告：完全笛卡尔乘积超过100万行")
        logger.warning(f"   建议使用键匹配的方式合并，而不是完全笛卡尔乘积。")
    else:
        logger.info(f"\n✅ 完全笛卡尔乘积在可接受范围内")
    
    logger.info("\n" + "=" * 80)
    logger.info("计算2：按(登记号, 就诊号)键匹配合并后的数据量")
    logger.info("=" * 80)
    
    # 检查是否所有文件都有就诊号
    has_visit_files = [a for a in file_analyses if a['has_visit']]
    no_visit_files = [a for a in file_analyses if not a['has_visit']]
    
    if len(has_visit_files) > 0 and len(no_visit_files) > 0:
        logger.warning("⚠️  部分文件有就诊号，部分文件没有就诊号")
        logger.warning(f"  - 有就诊号的文件: {len(has_visit_files)} 个")
        logger.warning(f"  - 无就诊号的文件: {len(no_visit_files)} 个")
        logger.warning("  - 建议：统一使用登记号作为关联键，或为无就诊号的文件补充就诊号")
    
    # 按是否有就诊号分别处理
    if len(has_visit_files) > 0:
        logger.info("\n" + "="*80)
        logger.info("处理有就诊号的文件（按(登记号, 就诊号)合并）...")
        logger.info("="*80)
        calculate_merge_with_visit(has_visit_files)
    
    if len(no_visit_files) > 0:
        logger.info("\n" + "="*80)
        logger.info("处理无就诊号的文件（按登记号合并）...")
        logger.info("="*80)
        calculate_merge_without_visit(no_visit_files)
    
    # 如果两种都有，计算混合情况
    if len(has_visit_files) > 0 and len(no_visit_files) > 0:
        logger.info("\n" + "="*80)
        logger.info("处理混合情况（部分有就诊号，部分无就诊号）...")
        logger.info("="*80)
        calculate_mixed_merge(has_visit_files, no_visit_files)
    
    logger.info("\n" + "="*80)
    logger.info("计算完成！")
    logger.info("="*80)


def calculate_merge_with_visit(file_analyses: list):
    """
    计算有就诊号文件的合并结果（按(登记号, 就诊号)做笛卡尔乘积合并）
    
    说明：如果同一个(登记号, 就诊号)组合在多个文件中都有记录，
    合并时会产生笛卡尔乘积。
    例如：文件1（心跳）中登记号A+就诊号1有3条，文件2（入院记录）中登记号A+就诊号1有2条
    合并后会产生 3 × 2 = 6 条记录
    """
    logger.info("-" * 80)
    logger.info("合并方式：按(登记号, 就诊号)做笛卡尔乘积合并")
    logger.info("说明：如果同一个(登记号, 就诊号)在多个文件中都有记录，会产生笛卡尔乘积")
    logger.info("-" * 80)
    
    # 收集所有唯一的(登记号, 就诊号)组合
    all_keys = set()
    key_to_files = defaultdict(list)  # 记录每个键出现在哪些文件中
    
    for analysis in file_analyses:
        for key in analysis['key_counts'].keys():
            all_keys.add(key)
            key_to_files[key].append(analysis['file_name'])
    
    logger.info(f"\n所有文件中的唯一(登记号, 就诊号)组合数: {len(all_keys):,}")
    logger.info(f"参与合并的文件数: {len(file_analyses)}")
    
    # 显示每个文件的基本信息
    logger.info("\n各文件信息:")
    for analysis in file_analyses:
        logger.info(f"  - {analysis['file_name']}: {analysis['rows']:,} 行, "
                   f"{analysis['unique_keys']:,} 个唯一键")
    
    # 计算每个键在每个文件中的出现次数
    key_counts_per_file = defaultdict(dict)
    for analysis in file_analyses:
        for key, count in analysis['key_counts'].items():
            key_counts_per_file[key][analysis['file_name']] = count
    
    # 计算合并后的行数（笛卡尔乘积）
    total_rows = 0
    cartesian_keys = []  # 记录会产生笛卡尔乘积的键
    single_file_keys = 0  # 只在一个文件中出现的键数量
    
    for key in all_keys:
        # 计算这个键在所有文件中的出现次数的乘积
        counts = []
        file_names = []
        for analysis in file_analyses:
            count = analysis['key_counts'].get(key, 0)
            if count > 0:
                counts.append(count)
                file_names.append(analysis['file_name'])
        
        if len(counts) > 0:
            product = 1
            for c in counts:
                product *= c
            total_rows += product
            
            if len(counts) == 1:
                single_file_keys += 1
            elif product > 1:
                cartesian_keys.append((key, product, counts, file_names))
    
    logger.info(f"\n{'='*80}")
    logger.info(f"合并后的总行数: {total_rows:,}")
    logger.info(f"{'='*80}")
    
    # 估算内存占用（假设每行约1KB，实际可能更大）
    estimated_memory_gb = total_rows * 1024 / (1024**3)
    logger.info(f"估算内存占用（假设每行1KB）: {estimated_memory_gb:.2f} GB")
    logger.info(f"估算内存占用（假设每行5KB）: {estimated_memory_gb * 5:.2f} GB")
    
    # 检查是否会超出常见内存限制
    if estimated_memory_gb > 16:
        logger.error(f"\n❌ 警告：估算内存占用超过16GB，可能导致内存溢出！")
    elif estimated_memory_gb > 8:
        logger.warning(f"\n⚠️  警告：估算内存占用超过8GB，请确保有足够内存")
    
    # 分析笛卡尔乘积情况
    if len(cartesian_keys) > 0:
        logger.warning(f"\n⚠️  发现 {len(cartesian_keys)} 个(登记号, 就诊号)组合会产生笛卡尔乘积")
        logger.info(f"   - 只在一个文件中出现的键: {single_file_keys:,} 个（不会产生笛卡尔乘积）")
        
        # 找出最大的笛卡尔乘积
        cartesian_keys.sort(key=lambda x: x[1], reverse=True)
        top_10 = cartesian_keys[:10]
        
        logger.warning("\n前10个最大的笛卡尔乘积:")
        for idx, (key, product, counts, file_names) in enumerate(top_10, 1):
            logger.warning(f"\n  {idx}. 键: {key}")
            logger.warning(f"     合并后行数: {product:,}")
            logger.warning(f"     涉及文件数: {len(file_names)}")
            for fname, cnt in zip(file_names, counts):
                logger.warning(f"       - {fname}: {cnt} 条记录")
        
        # 统计
        total_cartesian_rows = sum(p for _, p, _, _ in cartesian_keys)
        non_cartesian_rows = total_rows - total_cartesian_rows + len(cartesian_keys)
        
        logger.warning(f"\n笛卡尔乘积统计:")
        logger.warning(f"  - 笛卡尔乘积产生的行数: {total_cartesian_rows:,}")
        logger.warning(f"  - 非笛卡尔乘积的行数: {non_cartesian_rows:,}")
        logger.warning(f"  - 笛卡尔乘积占比: {total_cartesian_rows / total_rows * 100:.2f}%")
        
        # 分析哪些文件组合产生最多的笛卡尔乘积
        file_pair_cartesian = defaultdict(int)
        for _, product, _, file_names in cartesian_keys:
            if len(file_names) >= 2:
                # 记录所有文件对
                for i in range(len(file_names)):
                    for j in range(i+1, len(file_names)):
                        pair = tuple(sorted([file_names[i], file_names[j]]))
                        file_pair_cartesian[pair] += product
        
        if file_pair_cartesian:
            logger.warning(f"\n产生笛卡尔乘积最多的文件对（前5）:")
            sorted_pairs = sorted(file_pair_cartesian.items(), key=lambda x: x[1], reverse=True)
            for (f1, f2), total in sorted_pairs[:5]:
                logger.warning(f"  - {f1} × {f2}: {total:,} 行")
    else:
        logger.info("\n✅ 没有发现笛卡尔乘积问题，每个(登记号, 就诊号)组合在每个文件中最多出现1次")
    
    # 计算理想情况（如果每个键在每个文件中只出现1次）
    ideal_rows = len(all_keys)
    logger.info(f"\n理想情况（无重复）的行数: {ideal_rows:,}")
    logger.info(f"实际行数: {total_rows:,}")
    if ideal_rows > 0:
        growth_factor = total_rows / ideal_rows
        logger.info(f"增长倍数: {growth_factor:.2f}x")
        if growth_factor > 10:
            logger.warning(f"⚠️  数据量增长了 {growth_factor:.1f} 倍，可能存在严重的笛卡尔乘积问题！")


def calculate_merge_without_visit(file_analyses: list):
    """
    计算无就诊号文件的合并结果（只按登记号做笛卡尔乘积合并）
    """
    logger.info("-" * 80)
    logger.info("合并方式：按登记号做笛卡尔乘积合并")
    logger.info("说明：如果同一个登记号在多个文件中都有记录，会产生笛卡尔乘积")
    logger.info("-" * 80)
    
    # 收集所有唯一的登记号
    all_regs = set()
    reg_to_files = defaultdict(list)
    
    for analysis in file_analyses:
        for reg in analysis['key_counts'].keys():
            all_regs.add(reg)
            reg_to_files[reg].append(analysis['file_name'])
    
    logger.info(f"\n所有文件中的唯一登记号数: {len(all_regs):,}")
    logger.info(f"参与合并的文件数: {len(file_analyses)}")
    
    # 显示每个文件的基本信息
    logger.info("\n各文件信息:")
    for analysis in file_analyses:
        logger.info(f"  - {analysis['file_name']}: {analysis['rows']:,} 行, "
                   f"{analysis['unique_keys']:,} 个唯一登记号")
    
    # 计算合并后的行数
    total_rows = 0
    cartesian_regs = []
    single_file_regs = 0
    
    for reg in all_regs:
        counts = []
        file_names = []
        for analysis in file_analyses:
            count = analysis['key_counts'].get(reg, 0)
            if count > 0:
                counts.append(count)
                file_names.append(analysis['file_name'])
        
        if len(counts) > 0:
            product = 1
            for c in counts:
                product *= c
            total_rows += product
            
            if len(counts) == 1:
                single_file_regs += 1
            elif product > 1:
                cartesian_regs.append((reg, product, counts, file_names))
    
    logger.info(f"\n{'='*80}")
    logger.info(f"合并后的总行数: {total_rows:,}")
    logger.info(f"{'='*80}")
    
    # 估算内存占用
    estimated_memory_gb = total_rows * 1024 / (1024**3)
    logger.info(f"估算内存占用（假设每行1KB）: {estimated_memory_gb:.2f} GB")
    logger.info(f"估算内存占用（假设每行5KB）: {estimated_memory_gb * 5:.2f} GB")
    
    if estimated_memory_gb > 16:
        logger.error(f"\n❌ 警告：估算内存占用超过16GB，可能导致内存溢出！")
    elif estimated_memory_gb > 8:
        logger.warning(f"\n⚠️  警告：估算内存占用超过8GB，请确保有足够内存")
    
    if len(cartesian_regs) > 0:
        logger.warning(f"\n⚠️  发现 {len(cartesian_regs)} 个登记号会产生笛卡尔乘积")
        logger.info(f"   - 只在一个文件中出现的登记号: {single_file_regs:,} 个（不会产生笛卡尔乘积）")
        
        cartesian_regs.sort(key=lambda x: x[1], reverse=True)
        top_10 = cartesian_regs[:10]
        
        logger.warning("\n前10个最大的笛卡尔乘积:")
        for idx, (reg, product, counts, file_names) in enumerate(top_10, 1):
            logger.warning(f"\n  {idx}. 登记号: {reg}")
            logger.warning(f"     合并后行数: {product:,}")
            logger.warning(f"     涉及文件数: {len(file_names)}")
            for fname, cnt in zip(file_names, counts):
                logger.warning(f"       - {fname}: {cnt} 条记录")
    else:
        logger.info("\n✅ 没有发现笛卡尔乘积问题")
    
    ideal_rows = len(all_regs)
    logger.info(f"\n理想情况（无重复）的行数: {ideal_rows:,}")
    logger.info(f"实际行数: {total_rows:,}")
    if ideal_rows > 0:
        growth_factor = total_rows / ideal_rows
        logger.info(f"增长倍数: {growth_factor:.2f}x")
        if growth_factor > 10:
            logger.warning(f"⚠️  数据量增长了 {growth_factor:.1f} 倍，可能存在严重的笛卡尔乘积问题！")


def calculate_mixed_merge(has_visit_files: list, no_visit_files: list):
    """
    计算混合情况的合并结果
    """
    logger.info("-" * 80)
    logger.warning("⚠️  混合情况：部分文件有就诊号，部分文件无就诊号")
    logger.warning("这种情况下的合并逻辑需要明确：")
    logger.warning("  1. 如果统一按登记号合并，有就诊号的文件中的就诊号信息会丢失")
    logger.warning("  2. 如果按(登记号, 就诊号)合并，无就诊号的文件无法匹配")
    logger.warning("\n建议：统一数据格式后再合并")


def main():
    """主函数"""
    input_dir = "横向展开结果"
    calculate_merge_size(input_dir)


if __name__ == "__main__":
    main()

