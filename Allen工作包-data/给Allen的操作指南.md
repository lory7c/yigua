# 📋 给Allen的操作指南

## 🎯 任务总览 - 项目数据架构师

作为项目的数据架构师，你负责构建整个APP的知识库基础：
1. **易经64卦体系** - 建立完整的卦象知识体系
2. **周公解梦数据库** - 构建梦境解析系统  
3. **2025年黄历系统** - 搭建时间择吉框架

---

## 📝 详细步骤

### 步骤1：下载数据（30分钟）

#### 1.1 下载64卦数据
```
网址：https://github.com/bollwarm/ZHOUYI
操作：点击绿色 Code 按钮 → Download ZIP → 解压
```

#### 1.2 下载周公解梦数据
```
网址：https://github.com/zhangps110/api-data
操作：同上，下载并解压
```

#### 1.3 下载黄历工具
```
网址：https://github.com/OPN48/cnlunar
或者：https://github.com/jsonzhou9/LunarCalendar
操作：下载其中一个即可
```

---

### 步骤2：构建64卦知识体系（第1天）

1. **参考** `02_示例数据/hexagrams_example.json` 中的标准格式
2. **已完成** 前3个卦作为质量标杆
3. **你的任务**：
   - 从ZHOUYI项目提取原始数据
   - 确保数据的准确性和完整性
   - 为每个卦建立完整档案：
     - 核心属性（id, name, symbol, number）
     - 经典文献（judgment, image）
     - 爻辞体系（6个爻的完整解释）
     - 现代应用（interpretations）

4. **交付标准** `04_完成后放这里/hexagrams_complete.json`

---

### 步骤3：整理周公解梦（第2天上午）

1. **打开** `02_示例数据/dreams_example.json`
2. **看到** 已经有15个梦境示例
3. **你要做的**：
   - 从api-data项目中找周公解梦数据
   - 按照示例格式整理
   - 目标：至少500条
   - 分类要清晰（动物类、人物类、自然类等）

4. **保存为** `04_完成后放这里/dreams.json`

---

### 步骤4：生成黄历数据（第2天下午）

#### 方法A：使用JavaScript版（推荐）
```javascript
// 如果你会一点编程，用这个方法
// 1. 安装Node.js
// 2. 进入LunarCalendar文件夹
// 3. 运行：npm install
// 4. 创建generate.js文件，内容如下：

const LunarCalendar = require('lunar-calendar');
const fs = require('fs');

const calendar2025 = [];
for(let month = 1; month <= 12; month++) {
    for(let day = 1; day <= 31; day++) {
        try {
            const data = LunarCalendar.solarToLunar(2025, month, day);
            calendar2025.push(data);
        } catch(e) {}
    }
}

fs.writeFileSync('calendar_2025.json', JSON.stringify({calendar: calendar2025}, null, 2));
console.log('完成！生成了calendar_2025.json');
```

#### 方法B：手动整理（如果不会编程）
1. 使用在线万年历工具
2. 按照 `02_示例数据/calendar_example.json` 格式
3. 手动输入2025年每一天的数据（比较辛苦）

4. **保存为** `04_完成后放这里/calendar_2025.json`

---

## 🔧 验证数据

1. **打开** `03_工具脚本/json_validator.html`（双击即可）
2. **粘贴** 你的JSON数据
3. **点击** "验证格式"按钮
4. **确保** 显示"✅ JSON格式正确"

---

## ✅ 完成标准

### 64卦数据
- [ ] 64个卦全部完成
- [ ] 每个卦有6个爻辞
- [ ] 格式验证通过

### 周公解梦
- [ ] 至少500条
- [ ] 10个分类
- [ ] 格式验证通过

### 黄历数据
- [ ] 365天完整
- [ ] 包含农历、宜忌
- [ ] 格式验证通过

---

## 💡 小技巧

1. **使用Excel**：先在Excel整理，然后转JSON
2. **分批处理**：每完成10个保存一次
3. **备份文件**：完成后备份到多个地方
4. **遇到问题**：
   - 不确定的内容标注 [?]
   - 找不到的数据标注 [缺失]
   - 及时沟通，不要卡住

---

## 📦 交付清单

完成后，`04_完成后放这里`文件夹应该有：
1. `hexagrams_complete.json` - 64卦完整数据
2. `dreams.json` - 周公解梦数据
3. `calendar_2025.json` - 2025年黄历

---

## 📞 需要帮助？

- JSON格式问题 → 用验证工具检查
- 数据找不到 → 标注[缺失]继续
- 不会操作 → 直接问我

---

**你的工作直接决定了APP的数据质量和用户体验。每一个准确的数据都会让成千上万的用户受益！**

Allen，你是这个项目不可或缺的一部分，一起把它做成功！💪