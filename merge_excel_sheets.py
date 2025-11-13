"""
从Excel文件的所有sheet页签中查找指定列名，按登记号合并数据
"""
import pandas as pd
from pathlib import Path
import logging
from typing import List, Dict

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 需要查找的列名列表
TARGET_COLUMNS = [
    "登记号", "姓名", "骨科诊断", "骨科手术名称", "住院时间", "出院时间", "性别", "就诊年龄", "出生日期",
    "婚姻状态", "职业", "教育程度", "医保类型", "身高(cm)", "体重(kg)", "BMI", "吸烟史", "饮酒史",
    "体温", "呼吸", "心率", "脉搏", "收缩压", "舒张压", "心脏病(有1,无0,下同)", "冠心病", "心律失常",
    "瓣膜病", "心力衰竭", "肺心病", "先心病", "心肌病", "起搏器术后", "新发心梗", "高血压", "糖尿病",
    "高脂血症", "脑血管病", "肾功能不全", "COPD", "肺炎", "RCRI评分", "手术开始时间", "手术结束时间",
    "手术时长", "受伤至受伤时间(仅限骨伤)", "手术医师", "患者体位", "麻醉方式(全麻为1,椎管内麻为2,其他为3)",
    "麻醉开始时间", "麻醉结束时间", "麻醉医师", "ASA分级", "术中失血量", "术中自体血回输量", "术中输悬红量",
    "术中输血浆量", "术中输血小板量", "术中输液量", "术中尿量", "是否变更过麻醉计划", "麻醉恢复是否完全",
    "是否拔除气管插管", "有无动脉穿刺置管", "红细胞(*10^12/L)", "血红蛋白(g/l)", "红细胞压积(%)",
    "血小板(*10^9/L)", "白细胞(*10^9/L)", "中性粒细胞百分比(%)", "白蛋白(Alb)(g/l)",
    "丙氨酸氨基转移酶(ALT)(U/L)", "天门冬氨酸氨基转移酶(AST)(U/L)", "总胆红素(μmol/L)",
    "直接胆红素(μmol/L)", "碱性磷酸酶(ALP)(U/L)", "γ-谷氨酰基转移酶(GGT)(U/L)",
    "总胆汁酸(TBA)(μmol/L)", "腺苷脱氨酶(ADA)(U/L)", "胆碱脂酶(ChE)(kU/L)", "白蛋白比球蛋白",
    "肌酐(Cr)(μmol/L)", "尿素(Urea)(mmol/L)", "尿酸(UA)(μmol/L)", "葡萄糖(Glu)(mmol/L)",
    "eGFR(CKD-EPI 肌酐)", "甘油三酯(TG)(mmol/L)", "总胆固醇(TC)(mmol/L)",
    "高密度脂蛋白胆固醇(HDL-C)(mmol/L)", "低密度脂蛋白胆固醇(LDL-C)(mmol/L)",
    "钙(Ca)(mmol/L)(mmol/L)", "磷(P)(mmol/L)(mmol/L)", "镁(Mg)(mmol/L)(mmol/L)",
    "钠(Na)(mmol/L)", "钾(K)(mmol/L)", "氯(Cl)(mmol/L)", "阴离子间隙", "胱抑素(Cys-C)(mg/L)",
    "新冠状病毒核酸检测(2019-nCoV)", "红细胞沉降率", "快速C-反应蛋白(mg/L)",
    "降钙素原(PCT)(ng/ml)", "白细胞介素-6(IL-6)(pg/ml)", "酸碱度", "二氧化碳分压(mmHg)",
    "氧分压(mmHg)", "乳酸(mmol/L)", "血浆凝血酶原时间(PT)(Sec)", "活化部分凝血活酶时间(APTT)(Sec)",
    "国际标准化比值", "D-二聚体(D-Dimer)(ng/ml)", "肌红蛋白(Mb)(ng/ml)", "肌酸激酶(CK)(U/L)",
    "肌酸激酶-MB同工酶质量(CK-MBmass)(ng/ml)", "肌钙蛋白Ⅰ(hsTnI)(pg/ml)", "肌钙蛋白Ⅰ(TnI)(ng/ml)",
    "B型钠尿肽(BNP)(pg/ml)", "N端-B型钠尿肽前体(NT-ProBNP)(pg/ml)", "尿糖", "酮体",
    "术后血红蛋白(g/l)", "术后红细胞压积(%)", "术后肌钙蛋白Ⅰ(hsTnI)(pg/ml)",
    "术后肌钙蛋白Ⅰ(TnI)(ng/ml)", "术后B型钠尿肽(BNP)(pg/ml)",
    "术后N端-B型钠尿肽前体(NT-ProBNP)(pg/ml)", "冠状动脉CT时间", "左主干钙化积分",
    "左前降支钙化积分", "左回旋支钙化积分", "右支钙化积分", "总钙化积分", "左前降支DVDDR",
    "左旋支DVFFR", "右支DCFFR", "最窄DCFFR（包括非前三种的）", "左前降支狭窄度", "左旋支狭窄度",
    "右支狭窄度", "超声心动检查时间", "超声-左房", "超声-右房", "超声-厚度", "超声-运动幅度",
    "超声-与左室后壁逆向运动", "超声-舒末内径", "超声-收末内径", "超声-后壁厚度", "超声-后壁运动幅度",
    "超声-前后径", "超声-左右径", "超声-流出道", "超声-射血分数", "超声-缩短分数",
    "超声-E波最大流速", "超声-A波最大流速", "超声-主动脉最大流速", "超声-左室流出道流速",
    "超声-肺动脉最大流速", "超声舒张功能减低", "术前下肢深静脉血栓", "术前下肢肌间静脉血栓",
    "硝酸甘油", "去乙酰毛花苷", "胺碘酮", "阿司匹林", "氯吡格雷", "替格瑞洛", "西洛他唑", "替罗非班",
    "那屈肝素", "依诺肝素", "磺达肝癸钠", "利伐沙班", "达比加群", "美托洛尔", "术后MACE",
    "心绞痛或心梗", "心律失常", "心衰", "肺部感染", "深静脉血栓", "切口感染/愈合不良", "死亡",
    "抢救", "入ICU", "住院天数", "生活能力评分-入院", "生活能力评分-出院"
]


def find_columns_in_sheet(df: pd.DataFrame, target_columns: List[str]) -> List[str]:
    """
    在DataFrame中查找目标列名（支持模糊匹配）
    
    Args:
        df: 要搜索的DataFrame
        target_columns: 目标列名列表
    
    Returns:
        找到的列名列表
    """
    found_columns = []
    df_columns = df.columns.tolist()
    
    for target_col in target_columns:
        # 精确匹配
        if target_col in df_columns:
            found_columns.append(target_col)
        else:
            # 模糊匹配：检查是否包含目标列名（去除空格和特殊字符）
            target_clean = target_col.replace(" ", "").replace("(", "").replace(")", "")
            for col in df_columns:
                col_clean = str(col).replace(" ", "").replace("(", "").replace(")", "")
                if target_clean in col_clean or col_clean in target_clean:
                    found_columns.append(col)
                    break
    
    return found_columns


def merge_excel_sheets(
    input_file: str,
    output_file: str,
    target_columns: List[str],
    key_column: str = "登记号"
):
    """
    从Excel文件的所有sheet中查找指定列，按登记号合并
    
    Args:
        input_file: 输入的Excel文件路径
        output_file: 输出的Excel文件路径
        target_columns: 要查找的列名列表
        key_column: 用于合并的关键列（默认：登记号）
    """
    logger.info(f"开始处理文件: {input_file}")
    
    # 读取所有sheet
    try:
        excel_file = pd.ExcelFile(input_file)
        sheet_names = excel_file.sheet_names
        logger.info(f"找到 {len(sheet_names)} 个sheet: {sheet_names}")
    except Exception as e:
        logger.error(f"读取Excel文件失败: {e}")
        return
    
    # 第一步：遍历所有sheet，记录每个列在哪些sheet中出现
    column_usage = {}  # {列名: [sheet名称列表]}
    
    for sheet_name in sheet_names:
        try:
            df = pd.read_excel(input_file, sheet_name=sheet_name, nrows=0)  # 只读列名
            found_columns = find_columns_in_sheet(df, target_columns)
            
            for col in found_columns:
                if col != key_column:
                    if col not in column_usage:
                        column_usage[col] = []
                    column_usage[col].append(sheet_name)
        except Exception as e:
            logger.warning(f"预扫描 Sheet '{sheet_name}' 时出错: {e}")
    
    # 第二步：处理每个sheet，重命名列
    all_data = []
    
    for sheet_idx, sheet_name in enumerate(sheet_names):
        logger.info(f"处理 Sheet {sheet_idx + 1}/{len(sheet_names)}: {sheet_name}")
        
        try:
            df = pd.read_excel(input_file, sheet_name=sheet_name)
            logger.info(f"  - Sheet '{sheet_name}' 有 {len(df)} 行, {len(df.columns)} 列")
            
            # 检查是否有登记号列
            if key_column not in df.columns:
                logger.warning(f"  - Sheet '{sheet_name}' 中没有找到 '{key_column}' 列，跳过")
                continue
            
            # 查找目标列
            found_columns = find_columns_in_sheet(df, target_columns)
            logger.info(f"  - 在 Sheet '{sheet_name}' 中找到 {len(found_columns)} 个目标列")
            
            if not found_columns:
                logger.warning(f"  - Sheet '{sheet_name}' 中没有找到任何目标列")
                continue
            
            # 选择需要的列（包括登记号）
            columns_to_select = [key_column] + [col for col in found_columns if col != key_column]
            df_selected = df[columns_to_select].copy()
            
            # 检查重复的登记号
            duplicate_count = df_selected[key_column].duplicated().sum()
            if duplicate_count > 0:
                logger.warning(f"  - Sheet '{sheet_name}' 中有 {duplicate_count} 个重复的登记号")
                logger.info(f"  - 合并前数据量: {len(df_selected)} 行")
                
                # 对重复的登记号进行聚合：保留最后一个非空值
                # 先按登记号分组，然后对每组取最后一个非空值
                df_selected = df_selected.groupby(key_column, as_index=False).last()
                logger.info(f"  - 去重后数据量: {len(df_selected)} 行")
            
            # 重命名列：如果列在多个sheet中出现，添加sheet名称后缀
            renamed_columns = {}
            for col in df_selected.columns:
                if col == key_column:
                    renamed_columns[col] = col  # 登记号列不重命名
                else:
                    # 如果这个列在多个sheet中出现，添加sheet名称后缀
                    if col in column_usage and len(column_usage[col]) > 1:
                        new_col_name = f"{col}_{sheet_name}"
                        renamed_columns[col] = new_col_name
                    else:
                        # 只在单个sheet中出现，保持原列名
                        renamed_columns[col] = col
            
            df_selected.rename(columns=renamed_columns, inplace=True)
            
            # 存储数据
            all_data.append({
                'sheet_name': sheet_name,
                'data': df_selected,
                'columns': list(df_selected.columns)
            })
            
        except Exception as e:
            logger.error(f"处理 Sheet '{sheet_name}' 时出错: {e}")
            continue
    
    if not all_data:
        logger.error("没有找到任何有效数据")
        return
    
    # 合并所有数据
    logger.info("开始合并数据...")
    merged_df = None
    
    for item in all_data:
        df = item['data']
        sheet_name = item['sheet_name']
        
        if merged_df is None:
            merged_df = df.copy()
            logger.info(f"  初始数据来自 Sheet '{sheet_name}'，包含 {len(merged_df)} 行")
        else:
            # 检查合并前的数据量，避免笛卡尔积爆炸
            before_rows = len(merged_df)
            df_rows = len(df)
            
            # 检查是否有重复的登记号会导致数据量爆炸
            merged_keys = set(merged_df[key_column].unique())
            df_keys = set(df[key_column].unique())
            common_keys = merged_keys & df_keys
            
            if len(common_keys) > 0:
                # 检查合并后可能的数据量
                merged_duplicates = merged_df[key_column].value_counts()
                df_duplicates = df[key_column].value_counts()
                
                # 估算最大可能的行数（如果所有重复都产生笛卡尔积）
                max_possible = 0
                for key in common_keys:
                    count1 = merged_duplicates.get(key, 1)
                    count2 = df_duplicates.get(key, 1)
                    max_possible += count1 * count2
                
                # 加上没有重复的行
                max_possible += (before_rows - merged_duplicates[merged_duplicates > 1].sum()) + \
                               (df_rows - df_duplicates[df_duplicates > 1].sum())
                
                if max_possible > before_rows * 10:  # 如果可能增长超过10倍
                    logger.warning(f"  ⚠️  警告：合并 Sheet '{sheet_name}' 可能导致数据量从 {before_rows} 行增长到约 {max_possible:,} 行")
                    logger.warning(f"  ⚠️  这可能是由于重复的登记号导致的笛卡尔积。建议先检查数据质量。")
            
            # 按登记号合并
            merged_df = pd.merge(
                merged_df,
                df,
                on=key_column,
                how='outer',
                suffixes=('', f'_{sheet_name}')
            )
            after_rows = len(merged_df)
            logger.info(f"  合并 Sheet '{sheet_name}' 后，共 {after_rows:,} 行 (增长 {after_rows - before_rows:,} 行)")
            
            # 如果数据量异常增长，发出警告
            if after_rows > before_rows * 5:
                logger.warning(f"  ⚠️  数据量异常增长！从 {before_rows:,} 行增长到 {after_rows:,} 行")
    
    # 按登记号排序
    merged_df = merged_df.sort_values(by=key_column).reset_index(drop=True)
    
    # 保存结果
    logger.info(f"保存结果到: {output_file}")
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    
    try:
        merged_df.to_excel(output_file, index=False, engine='openpyxl')
        logger.info(f"✅ 成功！合并后的数据包含 {len(merged_df)} 行, {len(merged_df.columns)} 列")
        logger.info(f"   输出文件: {output_file}")
    except Exception as e:
        logger.error(f"保存文件失败: {e}")
        # 如果openpyxl不可用，尝试保存为CSV
        csv_file = output_file.replace('.xlsx', '.csv')
        merged_df.to_csv(csv_file, index=False, encoding='utf-8-sig')
        logger.info(f"已保存为CSV格式: {csv_file}")


def main():
    """主函数"""
    # 配置输入输出文件路径
    input_file = "数据们.xlsx"  # 修改为你的输入文件路径
    output_file = "合并后的数据.xlsx"  # 输出文件路径
    
    # 执行合并
    merge_excel_sheets(
        input_file=input_file,
        output_file=output_file,
        target_columns=TARGET_COLUMNS,
        key_column="登记号"
    )


if __name__ == "__main__":
    main()

