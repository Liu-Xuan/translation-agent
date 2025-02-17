# 波音737 MAX技术文档翻译过程记录

开始时间：2025-02-16 00:17:50


## 源文档信息

- 文件路径: /Volumes/SSD/LLM/Translation_Agent/testcases/737MAX-FTD-46-19002_Doc_01092023/auto/737MAX-FTD-46-19002_Doc_01092023.md

- 文本长度: 7008 字符

## 术语匹配分析

### 识别到的关键术语
1. **文档标题相关**
   - `Revision Description` → `改版说明`
   - `Final Action` → `最终措施`
   - `Interim Action` → `临时措施`
   - `Parts List` → `部件清单`
   - `FLEET TEAM DIGEST` → `FLEET TEAM DIGEST（FTD）`

2. **技术术语**
   - `serial numbers (S/Ns)` → `序号（S/Ns）`
   - `Present Leg Fault (PLF)` → `当前航段故障（PLF）`
   - `Loadable Software Airplane Part Library (LSAPL)` → `机载软件电子库房（LSAPL）`
   - `Flight Deck` → `驾驶舱`
   - `service bulletins` → `服务通告`

3. **通用术语**
   - `units` → `组件`
   - `Close this FTD` → `关闭此 FTD`
   - `Parts` → `部件`
   - `Dispatch` → `放行`
   - `Fleet` → `机队`

### 术语使用统计
- 总识别术语数：15个
- 高频术语：
  * `units`（出现3次）
  * `Parts`（出现3次）
  * `Fleet`（出现3次）
- 专有名词保留：
  * S/Ns
  * PLF
  * LSAPL
### 初始翻译结果

```
# FLEET TEAM DIGEST（FTD）  

737MAX-FTD-46-19002  

**问题标题**：网络文件服务器 2（NFS-2）硬件相关问题  

![](images/6a5f0a361f745e3854a0f08ea7716af61d5e9f0bada7338e144811c38c102576.jpg)  

# 改版说明  

修订了状态部分、最终措施以及里程碑部分，增加了连接器焊点故障的日期信息。  

# 适用范围  

以下状态部分中提到的具有 NFS 序号（S/Ns）的 737 MAX 飞机。  

# 描述  

737MAX 运营商遇到了网络文件服务器（NFS）问题。目前，NFS 存在两个已知的硬件相关问题：固态硬盘（SSD）和网络扩展设备（NED）子系统处理器（NSP）连接器故障。  

## SSD 故障症状：  

• NFS 前面的故障灯在通电后持续亮起超过 10 分钟。  

## SSD 故障背景：  

• Delkin（SSD 供应商）的故障分析未能确定根本原因。  
• Delkin 尝试通过固件更新解决问题，但未取得积极效果。  
• 主要假设是 SSD 在写入时容易受到电源中断的影响。  

## 连接器焊点故障症状：  

典型故障是 A429 ACARS 输出（输出 #4）的性能下降。但随着故障模式的发展，该输出端口可能会出现持续故障。在极端情况下，其他 A429 和程序引脚也可能受到影响。  

• 当前航段故障（PLF）和实时事件（RTE）报告未通过 ARINC 通信寻址与报告系统（ACARS）数据链下传。  
• CFM LEAP EEC 报告未通过 ACARS 数据链下传到地面。  
• 维护信息 23-23010（CMU 未从 NFS-L 接收到 CABIN TERM #1 的输入）在过去 10 个航段中频繁出现（10 次或更多）。  
• 不受影响：PLF 和故障历史（FH）报告通过无线网络或 Gatelink 下传到机载软件电子库房（LSAPL）。  
• 不受影响：能够通过多功能显示系统（MDS）或维护笔记本电脑访问 PLF、FH 和驾驶舱影响。  

## 连接器焊点故障背景：  

• 已开启服务相关问题 737MAX-SRP-46-0006 以调查 NSP 连接器问题。  
• 初步调查表明，内部电路卡组件（CCA）连接器承受的力超过了设计范围。  
• 焊点故障的根本原因已确定。  

# 状态  

## SSD 状态：  

• Teledyne Controls 选择了另一家固态硬盘（SSD）供应商：ATP Electronics。  
• ATP Electronics 的 SSD 采用更新的技术，具有改进的固件和架构。  
• ATP Electronics 的 SSD 提供了电源保护功能，以确保正常关机。  
• ATP Electronics 的 SSD 内置电源保护功能要求在手动重置期间完全断电重启 NFS。如果使用断路器，请确保在重新通电前至少拔出三秒钟。  
• Teledyne Controls 正在用 ATP Electronics 的 SSD 替换返回的组件中故障的 Delkin SSD。  
• 生产组件（从序号 47B01090 开始）已配备 ATP Electronics 的 SSD。请参阅服务通告以了解适用的序号。  
• 更换 SSD 的现场返回组件正在通过 Mod Dot 和序号进行跟踪。Teledyne Controls 服务通告（SB）SB2247200-46-7 已发布，适用于 NFS P/N 2247200-01，并列出了 NFS 序号的有效性。  
• Teledyne 将在 2021 年第一季度末发布以下服务通告：  
  - Teledyne Controls 服务通告（SB）SB2247200-46-12 适用于 NFS P/N 2247200-01  
  - Teledyne Controls 服务通告（SB）SB2247200-46-15 适用于 NFS P/N 2247200-03  

## 连接器焊点状态：  

维护信息 23-23010（CMU 未从 NFS-L 接收到 CABIN TERM #1 的输入）可用于预测连接器问题的警报。  
Teledyne 进行了故障分析，并修改了设计，以机械方式将网络扩展设备（NED）子系统处理器（NSP）与服务器子系统处理器（SSP）模块组件断开。  
• 根本原因已确定。NSP 连接器：NFS 中的机械公差叠加以及连接器上使用的环氧树脂的不同热膨胀特性导致机械应力，从而在连接器与印刷线路板之间的焊点处产生断裂。  
• Teledyne 将在 2021 年第一季度末发布以下服务通告：  
  - Teledyne SB SB2247200-46-13 取代 SB2247200-46-9，适用于 NFS PN 2247200-01。  
  - Teledyne SB SB2247200-46-14 适用于 NFS PN 2247200-03。  

# 临时措施  

如果 NFS 出现讨论部分中描述的症状，请根据 AMM 任务 46-13-01-000-801（网络文件服务器移除）移除 NFS，并根据 AMM 任务 46-13-01-400-801（网络文件服务器安装）更换 NFS。  

# 最终措施  

波音建议航空公司运营商将故障的 NFS 组件送回 Teledyne Controls 进行维修。  

根本原因已确定。NSP 连接器的机械公差叠加以及连接器上使用的环氧树脂的不同热膨胀特性导致机械应力，从而在连接器与印刷线路板之间的焊点处产生断裂。  

实施 Teledyne SB SB2247200-46-13 适用于 NFS PN 2247200-01，以及 Teledyne SB SB2247200-46-14 适用于 NFS PN 2247200-03。  

关闭此 FTD  

# 里程碑  

**注意**：目标日期基于当前可用状态，未来可能会修订。  

**NFS2 SSD 更换**  
根本原因确定：2019 年 3 月  
解决方案选定：2019 年 3 月  
变更提交：2019 年 3 月  
服务通告可用：  
  - Teledyne Controls 服务通告（SB）SB2247200-46-12 适用于 NFS P/N 2247200-01  
  - Teledyne Controls 服务通告（SB）SB2247200-46-15 适用于 NFS P/N 2247200-03  
部件可用：2021 年 3 月 18 日  
波音服务信函：737-SL-46-039-A（已发布）  

**连接器焊点问题**  
根本原因确定：2020 年 10 月  
解决方案选定：2020 年 12 月  
变更提交：2021 年第一季度  
服务通告可用：2021 年 3 月 19 日  
  - Teledyne SB SB2247200-46-13 将发布，适用于 NFS PN 2247200-01  
  - Teledyne SB SB2247200-46-14 将发布，适用于 NFS PN 2247200-02 和 2247200-03  
部件可用：2021 年 3 月 18 日  
波音服务信函：737-SL-46-043（已发布）  

![](images/1df656d4a64022e20f8cf44c96a72f4afebaf15f85e69b647ec9b3df33b1542e.jpg)  

# 部件清单  

![](images/517814f865aa9fa99d1eb35ead1b1a9dcd69a7479f0610ca918f3ed006b87542.jpg)  

# 相关类别  

• 组件问题 - 在组件维护期间发生或对组件可靠性产生影响的问题  
• 放行可靠性问题 - 导致航班延误和取消的问题  
• 机队团队 IdeaXchange - 机队团队 IdeaXchange 公告板上的讨论主题
```

