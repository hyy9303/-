# Garbage Classification with MobileNetV2

## 项目简介

本项目实现了一个基于 **MobileNetV2** 的多类别垃圾图像分类系统，采用**迁移学习**方法，在 **仅使用 CPU 的环境**下完成模型训练、测试、评估及预测结果可视化。

项目重点展示了在**有限计算资源条件下**，如何构建、训练并评估一个实用的图像分类模型。

---

## 1. 项目结构说明

```text
Basic_AI/
├─ processed_data/          # 划分后的数据集
│  ├─ train/
│  ├─ val/
│  └─ test/
│
├─ outputs/                 # 训练与评估输出
│  ├─ best_model.keras      # 验证集准确率最优模型
│  ├─ final_model.keras     # 最终模型
│  ├─ class_names.json      # 类别名称列表
│  ├─ history.json          # 训练过程指标
│  ├─ confusion_matrix.png  # 混淆矩阵图
│  ├─ accuracy_curve.png    # 准确率曲线
│  ├─ loss_curve.png        # 损失曲线
│
├─ 01_split_dataset.py      # 数据集划分脚本
├─ 02_train_cpu_light.py    # 训练脚本
├─ 03_evaluate_cpu_light.py # 测试集评估脚本
├─ 04_plot_results.py       # 结果可视化脚本
├─ 05_predict.py            # 单张 / 批量预测脚本
├─ 05_predict_sample.py     # 抽样预测 + 统计可视化脚本
│
├─ requirements.txt
└─ README.md
```


---

## 2. 环境依赖

推荐使用 Python 3.8 或以上版本。

### 安装依赖
```bash
pip install -r requirements.txt
```

`requirements.txt` 内容示例：
```text
tensorflow==2.10.0
numpy
matplotlib
scikit-learn
pandas
```

---

## 3. 数据集准备

### 3.1 原始数据集结构

原始垃圾数据集应按类别存放，例如：

```text
unified_dataset/
├─ battery
├─ glass
├─ metal
├─ organic_waste
├─ paper_cardboard
├─ plastic
├─ textiles
└─ trash
```

### 3.2 划分训练 / 验证 / 测试集

运行以下命令进行数据集划分（70% / 15% / 15%）：

```bash
python 01_split_dataset.py
```

划分完成后会生成：

```text
processed_data/
├─ train
├─ val
└─ test
```

---

## 4. 模型训练（CPU 友好）

使用 MobileNetV2 + 迁移学习，仅训练分类头，适合 CPU 环境。

```bash
python 02_train_cpu_light.py
```

### 训练参数说明
- 输入尺寸：96 × 96
- Batch Size：8
- Epoch：6
- 主干网络：冻结（ImageNet 预训练）
- 优化器：Adam

训练完成后模型将保存在 `outputs/` 目录中。

---

## 5. 模型评估

### 5.1 测试集评估

生成混淆矩阵和分类报告：

```bash
python 03_evaluate_cpu_light.py
```

### 5.2 结果可视化

绘制训练曲线和混淆矩阵：

```bash
python 04_plot_results.py
```

输出结果包括：
- 准确率曲线
- 损失曲线
- 混淆矩阵图

---

## 6. 模型预测

### 6.1 单张图片预测

```bash
python 05_predict.py --image path/to/image.jpg
```

### 6.2 批量预测并导出 CSV

```bash
python 05_predict.py --folder path/to/folder --out_csv predictions.csv
```

---

## 7. 抽样预测与结果分布可视化

用于从测试集中**指定类别**随机抽取若干图片进行预测，并生成预测分布柱状图。

### 示例：从 plastic 类中抽取 200 张
```bash
python 05_predict_sample.py --class_name plastic --num 200 --plot
```

可选参数：
- `--seed`：随机种子（保证复现）
- `--copy_wrong_to`：将预测错误的图片复制到指定文件夹
- `--topk`：显示 Top-K 预测概率

---

## 8. 结果说明

在仅使用 CPU 的条件下，模型在测试集上取得约 80% 以上的分类准确率。混淆矩阵显示模型在 battery、organic_waste、textiles 等类别上表现良好，而在 glass 与 metal、plastic 与 paper_cardboard 等外观相似类别间存在一定混淆，符合实际垃圾分类场景。

---

## 9. 备注

- 所有路径均为**绝对路径**，复现实验时根据本地环境调整
- 若硬件条件允许，可进一步解冻主干网络进行微调以提升性能

---

## 10. 参考文献

1. Sandler M, Howard A, Zhu M, et al. *MobileNetV2: Inverted Residuals and Linear Bottlenecks*. CVPR, 2018.  
2. TensorFlow Official Documentation.  
3. Scikit-learn Metrics Documentation.

---