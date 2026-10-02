# M1 修正版 A：每次遇障生命周期规格审阅

2026-09-19；T306.6h.6a.1a.2。阶段：设计与源码合同核验，不是控制代码或物理验收。

## 用户决定与产物

用户指出“以后再次遇到同一障碍怎么办”，随后明确同意：只抑制同一次经过的重复触发；离开后重新接近同物体允许建立新 encounter，连续新障碍独立判断，不靠 episode reset 或计时解锁。此同意取代旧的 reset-only A 草案及 A/B 等待条件。

具体规格已提交 **e25e8052e36cbcb6f3429b095ef54d52f1a2f7bd**，仅一个新 Markdown 文件：[encounter lifecycle 规格](../../docs/superpowers/specs/2026-09-19-m1-encounter-lifecycle-design.md)。SHA256=`23116d335921ba7e6e50cb7a3afd15227795a4eb9cb311249872d1847f0c3d6c`。主代理完成自审，两项独立只读复审均 PASS；这是设计审阅，不代表任何控制或仿真通过。

`brainstorming` 的下一门槛是用户审阅本具体书面规格，再进入 writing-plans/TDD。当前未写实施代码、未启动新仿真或训练。完整目标已由用户续行恢复为 active，未调用 complete；旧阻塞记录是历史。

## 输入、方法和发现

读取 repo notes/AGENTS/.codex/RULES、旧重入与首次几何记录，核对外部 reference wrapper/curriculum、scale adapter 的 sync core/bridge/verifier/metrics。两项并行子审计分别检查 source hook/坐标/缓存和同步owner/独立证据；主代理直接复核关键源码，不仅转述结论。

关键发现：

- 起跨限制必须在 teacher 内 phase启动边界，不是在其输出之后把腿清零；G1保持phase0..10的原计算，禁止global monkeypatch/修改外部参考或SDK。
- 当前语义是类别，不是稳定物体ID；两杆同窗被min/max合并。新增显式注册表、唯一候选/歧义结果与每次encounter身份。
- 当前同步 active 与成功事件仅reset清除。合法新encounter或路线必须在新动作之前显式交回控制权；不以fresh wave或错误本身作为释放理由。
- 现有固定world-X、原IK使用env-origin-y锚点、右轨FAR/RAR，均不等于通用返回控制。G1必须保留旧锚点实现首次前缀；G2另立方向/轮侧合同。
- 重新遇障不能继承旧event、ready、积分或nominal姿态；episode不伪增，原失败证据不清除。

## 审查修订闭环

初审阻断后已在同一规格修正并复审：

1. G1明确保留旧 IK 路径锚点和运算顺序，G2 frame另有版本。
2. 补齐碰撞包络离开、重新接近窗口/运动方向、最近正距离候选与并列歧义规则。
3. DEPARTING可观察下一物体但需旧物体整机CLEAR后才能开始；旧物体历史保留。过近且来不及安全恢复/清空的场景显式不适用，不声称已支持密障碍同时跨越。
4. raw-world sample与采样descriptor不可变；跨encounter重新投影不伪造新物理样本，不把旧资格带入；保留prior-step连续性核验和混frame负例。
5. 冻结晋级顺序：同一新候选三次8×1600 → 1024×32容量 → 1024×1600严格；旧通过次数不抵扣。
6. G2必须有无reset/teleport的真实同障碍再次跨越、连续障碍场景。路线、轮侧、方向、场景和接触归属是其必要实现前置，不以CPU/G1冒充G2。

## 新鲜核验与保留范围

- 外部 curriculum SHA `6e630a8f7be6e31d4fbebeec87d1736ab8ac1e764532fca7026ad0c51ecacb5b`，wrapper `d6c7056d422a83efb028e1053d8ce496879e14b25410d6cf14a789734c82100a`，仍与历史绑定一致。
- `diff -rq` 当前 scale adapter 对 `task3_accepted/adapter`（排除Python/pytest cache）为空，未改冻结候选。
- GPU7在10:42核验只有原占位PID351307、15744MiB；未停止进程，未启动新仿真。
- commit前index为空；spec无TBD/TODO/待定占位；cached whitespace检查通过。提交后的尾部状态命令因stdin末尾格式报usage，未影响提交；随后独立SSH读回退出0，确认HEAD、仅一文件、index为空、spec与HEAD无diff、commit whitespace检查通过及本地/远端SHA一致。
- 未推送远端仓库，未提交其他用户已有修改。现行源码/动作/观测/奖励合同未变，故不将设计写成 human/ai 文档中的已生效能力。

## 后续与未完成项

等待用户审阅具体规格后制作实施计划。18个首次几何负例另修；AME lifecycle、named-target、实际路线与policy-only跨越/绕行、单进程10000更新均未完成。不能绕过原保护、改分母或靠重启拼接。

Baseline Ref：formal646f486 / frozen scale Task3，设计前HEAD5553e84。Candidate Ref：设计e25e805，无新代码候选。Key Files：本规格、wrapper/curriculum、post_cross_sync/sync_bridge/sync_verdict/metrics。dashboard、[T306](../todo/T306-m1-ame-long-train-stability.md) 和log index同步本次状态。
