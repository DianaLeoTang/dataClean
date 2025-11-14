import pandas as pd

# ============ 1. 配置区域：改成你自己的路径/表名/列名 ============

INPUT_EXCEL = "./数据们.xlsx"           # 你的原始 Excel 文件
SHEET_NAME = "编目诊断"                # 要处理的 sheet 名
DIAG_COL = "编目-主要诊断"           # 诊断所在的列名

ORTHO_CSV = "ortho_cases.csv"        # 输出：骨科病例
NON_ORTHO_CSV = "non_ortho_cases.csv"  # 输出：非骨科病例

# ============ 2. 定义关键词规则 ============

# 骨科相关关键词（可按需要增删）
ortho_keywords = [
    # 骨与关节
    "骨折", "骨质疏松", "骨不连", "不连接", "连接不正",
    "股骨", "胫骨", "腓骨", "桡骨", "尺骨", "肱骨", "锁骨", "髌骨",
    "跟骨", "趾", "髋关节", "膝关节", "踝关节", "肩关节", "腕关节",

    # 脊柱/椎管相关
    "颈椎", "胸椎", "腰椎", "椎管狭窄", "椎间盘突出", "椎体",
    "滑脱", "脊柱炎", "脊髓", "脊髓型", "颈部脊髓损伤",

    # 关节病/退行性改变
    "骨关节病", "膝骨关节病", "退行性病变", "继发性关节病",

    # 股骨头坏死
    "股骨头缺血性坏死",

    # 内固定/术后问题
    "取出骨折内固定装置",

    # 肌腱/韧带/软组织（骨科常管的）
    "肩袖", "冈上肌", "肌腱损伤", "髋关节扭伤",

    # 其他你这批数据中典型的骨科描述
    "压缩性骨折", "病理性骨折", "多发性骨折"
]

# 常见内科/非骨科关键词（遇到这些可优先判为非骨科）
non_ortho_keywords = [
    # 心血管
    "心肌梗死", "心绞痛", "冠状动脉粥样硬化性心脏病", "心功能不全",
    "急性心肌梗死", "NSTEMI",

    # 呼吸
    "肺炎", "肺栓塞",

    # 神经
    "脑梗死",

    # 内分泌/代谢
    "糖尿病性足坏疽",

    # 肾脏
    "肾衰竭",

    # 消化
    "上消化道出血", "反流性食管炎",

    # 肿瘤学/支持治疗
    "恶性肿瘤支持治疗",

    # 其他系统性疾病
    "筋膜炎", "脂肪瘤"
]


# ============ 3. 分类函数：返回（骨科/非骨科, 理由） ============

def classify_diagnosis(diagnosis: str):
    if pd.isna(diagnosis):
        return "非骨科", "诊断为空"

    diag = str(diagnosis)

    # 先看显式内科/非骨科关键词
    for kw in non_ortho_keywords:
        if kw in diag:
            return "非骨科", f"命中内科/非骨科关键词：{kw}"

    # 再看骨科关键词
    for kw in ortho_keywords:
        if kw in diag:
            return "骨科", f"命中骨科关键词：{kw}"

    # 兜底规则：含“骨”或“椎”大多为骨科
    for kw in ["骨", "椎", "关节"]:
        if kw in diag:
            return "骨科", f"命中骨科兜底关键词：{kw}"

    # 实在都没有，就暂定非骨科（你以后可以手工复核）
    return "非骨科", "未命中骨科相关关键词，默认非骨科"


# ============ 4. 读取 Excel，分类，并拆分导出 CSV ============

def split_excel_by_ortho():
    # 读取指定 sheet
    df = pd.read_excel(INPUT_EXCEL, sheet_name=SHEET_NAME)

    if DIAG_COL not in df.columns:
        raise ValueError(f"找不到诊断列：{DIAG_COL}，当前列名有：{list(df.columns)}")

    # 对诊断列做分类
    result = df[DIAG_COL].apply(classify_diagnosis)
    df["骨科/非骨科"] = result.apply(lambda x: x[0])
    df["分类理由"] = result.apply(lambda x: x[1])

    # 拆分
    df_ortho = df[df["骨科/非骨科"] == "骨科"].copy()
    df_non_ortho = df[df["骨科/非骨科"] == "非骨科"].copy()

    # 导出为 CSV（保留所有原列 + 新增两列）
    df_ortho.to_csv(ORTHO_CSV, index=False, encoding="utf-8-sig")
    df_non_ortho.to_csv(NON_ORTHO_CSV, index=False, encoding="utf-8-sig")

    print(f"骨科病例：{len(df_ortho)} 条，已保存到 {ORTHO_CSV}")
    print(f"非骨科病例：{len(df_non_ortho)} 条，已保存到 {NON_ORTHO_CSV}")


if __name__ == "__main__":
    split_excel_by_ortho()
