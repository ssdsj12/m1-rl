# M1 每次遇障生命周期与动作交接设计

状态：用户于 2026-09-19 明确“按规格实施”，已批准本具体书面规格；进入隔离实施与TDD，未启动新仿真。本次仅更新批准状态，正文合同不变。节点：T306.6h.6a.1a.2；关联首次跨越几何 .1、动作接入 .6j、路线能力 .6k。

## 1. 用户认可的行为与不可替代的最终目标

抑制的是**同一次经过中的重复触发**，不是永久屏蔽某个障碍，也不是每回合只能跨一次。

1. 一次接近、抬腿、跨越、恢复构成一个 encounter；未完成恢复时绝不截断首次动作。
2. 跨完但仍在离开时，雷达再次看到同一个物体不得重新启动抬腿序列。
3. 实际离开后再次接近同一个物体，建立新的 encounter，重新判断能否跨越；不要求 episode reset。
4. 下一独立障碍也有独立 encounter，不要求全部 semantic gate 先变为 false。
5. 大障碍、方向/轮侧不适配或几何不确定不能被这个模块强制解释为可跨越。交由明确的路线/绕行责任模块；不得以“已处理”静默忽略。

本规格不能以 CPU 事件序列、固定单杆 oracle 成功或进程正常结束替代真实再次跨越、policy-only 小障碍跨越/大障碍绕行、单进程 10000 更新。后者仍是完整任务的必需验收项。

## 2. 当前源码事实与选型

基线为 formal reference `646f486`，当前 repo HEAD `5553e84`，scale Task3 冻结副本。原始参考目录、SDK、驱动、用户已有修改不动。

- 原 `m1_curriculum.py:166–172,220` 在 phase0..10 保持序列，phase11 可因 raw gate=false 变为 -1，下一次 true 又启动 phase0；没有物体或 encounter 身份。
- run19 完成 samples0..246 后，在 prepare247 因 env523 新 wave/非零腿动作与同步资格冲突报错。它不是本轮新发生的 Isaac 原生崩溃；不能删除保护来使进程继续。
- `PostCrossSync.active` 在 episode 内只增不减；事件、资格与积分仅 reset 清除。旧 verifier 也只允许一次接管。简单增加 `consumed` 仍不能支持再次遇障。
- scanner semantic1 是类别，不是实例身份；原 spatial helper 将同窗所有 semantic1 点合并求 min/max。当前固定 x=.85、world-X 轮位置、右轨 FAR/RAR 和 root x>1.15 不能直接用于第二根杆或反向返回。

方案选择：采用**每次遇障状态机＋显式动作控制权交接**。拒绝永久物体黑名单、只在 reset 清状态、计时解锁，以及只推迟同步接管的替代方案。前两者不能再次跨越；计时/scan 闪断不能证明重新接近；仅推迟接管不消除错误重入。

## 3. 组件边界和身份

从已冻结 scale adapter 建立新的隔离候选 `encounter_lifecycle_v1`；不覆盖 run19、Task3 或正式控制器。组件分工：

- `EncounterGeometryProvider`：提供静态障碍注册表、唯一候选、通过方向和轮侧适用性；本 reference 阶段是明确标记的 controller-oracle，不伪装 learned perception。
- `EncounterCoordinator`：只管理身份、开始/完成/离开/再次接近和合法交接；不调 lift、PI gain、reward、质量或摩擦。
- 隔离 reference hook：在 phase helper 启动前消费协调器的允许位和几何；保留原顺序与 IK。
- encounter-aware sync：原平地同步公式不变，增加独立于 episode reset 的显式释放及新 encounter 初始化。
- 独立 NumPy replay：从物理原始记录重建身份关联和状态转换，不信任运行时自报通过。

标识为 `(env_id, episode_id, obstacle_id, encounter_seq, geometry_generation)`。`obstacle_id` 是注册物体的稳定身份；同物体再次接近时 obstacle_id 不变、encounter_seq 严格增加。episode_id 只因真实环境 reset 增加。序号不可回退、重用或跨环境借用。

注册表保存实例 prim path、env 归属、尺寸/变换、允许的接近面、语义类别、几何 generation 和来源 hash。使用 adapter 已能读取的实际碰撞/场景几何，不拿 semantic class 或数组槽号冒充永久 ID。当前单杆可直接使用已验证 prim path；多杆需单独扩展 own-object 列表与接触归属。

## 4. 每环境状态及转换

| 状态 | 行为 | 合法离开条件 |
| --- | --- | --- |
| `AVAILABLE` | 可识别唯一候选；不借用旧完成事件 | 唯一、适用的接近条件满足，建立新 encounter |
| `CROSSING` | 锁定所选物体、方向与轮侧，原 phase0..10 继续 | 完整有序跨越事件且恢复完成；或保留失败退出 |
| `DEPARTING` | 本次已完成，禁止为它再次启动抬腿；平地同步可按原资格接管 | 几何证明全机器人已离开该障碍作用区 |
| `CLEAR` | 保留已完成记录；不是一进入就重新放开旧 gate | 同物体发生新的合法接近，或下一物体有独立合法接近 |

`FAILED/UNSUPPORTED/AMBIGUOUS` 为显式结果，不是成功状态。失败结果留在本次运行历史中，不因后续成功清除。

### 4.1 完成判据

完成必须来自同一 encounter 的 pre-reset 已完成物理样本：必需轮的 prelift→overbar→passed→touchdown 严格有序、原恢复 phase10 已结束且见 phase11、无本次终止或无效输入。仅 root 越过1.15、phase=-1、gate=false 或等待若干步均不足以完成。

完成后抑制从下一 prepare 生效；不借用当前 action 执行后的未来样本。5 个稳定样本仍用于同步接管，**不作为完成锁存必须等待的额外条件**，否则会复现只收集1–4个样本就重入的问题。未完成首次几何的18个环境不得伪造完成来绕过负例。

### 4.2 离开与再次接近

离开必须由真实几何位姿证明，不以看不见障碍、raw gate=false、phase切换、时间或 scan 闪断代替。使用实际碰撞形状在 ground plane 的投影包络和冻结的 `.005 m` clearance：相对于本次通过轴，整机投影最靠后的点也越过障碍背面＋clearance，才可进入 CLEAR。离开证明记录 pose、包络和障碍几何；不能只看 root 或两只轮。

CLEAR 本身不允许同物体重新启动。再次接近需：

- 同一稳定物体身份；存在之前的几何离开证据；重新确定并冻结本次通过方向与轮侧；
- 整机曾处在该接近面的障碍前方，不与障碍膨胀区域重叠；随后连续运动进入该面的接近区域；
- 对连续有效位姿，沿本次接近轴的距离确实减小，heading 指向该面；当次 selected semantic hit 与物体几何一致；
- 原有起跨位置条件仍满足；新增有效窗口禁止“已在杆后但 gate=true”作为起跨依据。

外侧几何离开区与内侧接近区不重合，形成空间滞回；边界包含/不包含必须由纯函数测试冻结。几何比较只使用已有数值容差，不用增大容差弥补物理失败。连续样本只是证明实际运动方向，不是倒计时解锁。

具体判据用障碍平面中心为原点、单位通过轴 `d`、左轴 `l=(-d_y,d_x)`，定义 `s(p)=dot(p_xy-center_xy,d)`、`q(p)=dot(p_xy-center_xy,l)`；障碍沿通过轴半厚为 `h`，`.005 m` 记为 `c`。离开为全机器人碰撞包络 `min(s)>h+c`（严格大于）；新的接近面前置证据为 `max(s)<-h-c`（严格小于）。再次起跨时前轴两轮相对位置都在 `[front_start_x, -h-wheel_radius]`，当前固定参数为 `[-.45,-.1259] m`；前后连续有效root样本的s严格增加、当前root heading与d点积>0，raw gate必须来自所选物体。所选轨迹的必需轮通过线需落在该物体原横向允许走廊内，否则返回方向/轮侧不适用。边界浮点只允许原 `_ROUNDING_ATOL=1e-12`，不是新增物理余量；如果采样跨过起跨窗口而没有一次合法启动，不补发历史事件。

第一次原单杆的 bootstrap 仍走原 gate/时序，先用离线及真实前缀验证等价，不向其插入重接近等待条件。以上重新接近谓词用于后续 encounter；新物体也必须有本物体前方证据，不用上一物体的离开记录冒充它的接近记录。

遇到新物体，不要求旧物体从雷达完全消失，也不要求先退到旧物体很远处；但上一跨越/恢复、整机几何CLEAR及动作交接必须完成，两个障碍不能同时驱动同一条腿。DEPARTING期间可以观察下一候选，但不能开始它，唯一启动转换是CLEAR→CROSSING（首次为AVAILABLE→CROSSING）。若下一障碍过近，来不及完成恢复、CLEAR与本物体安全接近，返回明确的路径不适用结果，不强制启动或删除失败样本。旧物体的完成和离开证据永久保留在本episode的历史表，不因选中下一物体而清掉。

## 5. 几何、方向与障碍关联合同

新增 encounter 局部坐标固定于所选障碍和本次通过方向，不随每帧机器人 yaw 漂移。将 root、wheel 和障碍投影到同一坐标后，再计算 longitudinal/lateral、passed 和恢复距离；不能把 body-heading 的 obstacle_x 与 world-X 轮坐标相减。

为复用既有单杆几何常量，canonical坐标明确为 `x_c=.85+s(p)`、`y_c=-.2+q(p)`、`z_c=z-ground_z`；descriptor固定d、center及ground_z。root出杆门槛仍为 `x_c>1.15`，轮passed仍为 `x_c>=.9759`，高度/力阈值不变。这些量只用于所选encounter的几何和eligibility，不将旋转后的坐标覆盖原world原始证据或冒称原scene未变。碰撞包络由全部实际碰撞形状的不可变几何与逐步body pose变换重建；离线verifier必须可从同份原始输入独立重建包络，不能信任一个运行时`clear=true`。

G1原单杆模式的几何映射为恒等：bar=(.85,−.2)、通过方向=+X、必需轮=FAR/RAR。但旧wrapper的IK障碍向量实际使用 `env_origin_y-root_y`，并非 `bar_y-root_y`；G1保留这个旧路径锚点与原计算顺序，不能以统一几何之名修改第一次IK输入，也不做多余旋转/减加制造浮点前缀差异。真实杆几何只供G1 lifecycle/identity判定。其第一次接近到恢复完成的 action 与所有非计时状态必须保持前缀一致。

G2的统一frame是另外具名的动作合同版本，必须分别验证，不以G1前缀不变冒称G2控制公式未变。其他方向/轮侧必须有显式 descriptor；不允许默认落回 +X/FAR/RAR。反向返回同一路径时窄杆可能位于机器人左侧，不能将 FAR/RAR 改个标签就认为已适配：必须执行经过验证的轮侧动作映射，或由真实路线先进入适用的右轨接近走廊。

多杆关联仅使用每 env 自己的注册对象。对每个有限 semantic hit，用已验证物体包围几何做唯一归属；重叠、未知或不能唯一分配的点记录为歧义，不合成虚拟杆。原 `2e−5 m` scanner 数值边界仅用于既有世界顶点量化，不是物理余量。活动 CROSSING 中目标锁定，另一个物体出现不能切换正在执行的轨迹。

候选选择规则固定：先按声明的接近面、heading正向和实际前方几何建立候选；已有完成记录但不满足新接近证据的旧物体不得参选。对每个候选以沿其允许轴到前表面的正距离 `delta=-h-s(root)>0` 排序，选最近者；最小值在`1e-12`内并列、同一物体有两个面均有效、未知hit或形状关联歧义均返回AMBIGUOUS，不靠数组顺序打破。最近物体不适用跨越时交给路线判断，不跳过它去选择后方更远的小杆。CROSSING中的身份锁不参与重新排序。原单杆第一次保留原唯一候选/触发语义；新场景启用前，完整注册表、允许面、起跨窗口、frame和轮侧必须写入冻结manifest并由CPU边界用例与独立重放验证。

scene/contact 合同须区分 selected own object、其他合法 own object、foreign env object。多杆不能把第二根 own bar 误报 foreign，也不能把真正邻环境污染放行。物体 identity、frame、需要跨越的轮以及 geometry generation 在整个 encounter 内不可悄悄变化。

本组件只允许已声明的静态障碍几何。物体实际移动/尺寸改变、身份无法保持时明确拒绝当前验证；动态障碍关联不是本次猜测实现的功能。

## 6. Reference 接入与缓存

为避免修改原参考目录或 global monkeypatch，使用可追溯的隔离 vendor wrapper 快照，加实例级 typed hook。记录原文件 SHA、vendor SHA、最小 diff 和 hook 配置；默认 disabled 的快照必须与原代码数值一致，源码来源 guard 对该差异采用新版本显式声明，不伪造原文件绑定。

最小插入点：wrapper 已得到 raw spatial observation，但还未组装 phase helper 输入（当前参考约554–600行）。将原始 raw gate 与 `sequence_start_allowed` 分开：仅 old_phase<0 行向 helper 传 `raw_gate & allowed`；G1既有phase0..10的全部输入/计算不变，所有模式中已经开始的序列不允许中途换frame或动作版本。G2另立frame版本不是删除该冻结要求。不得在原 prepare 完成之后才强行把非零腿清零，也不得把 wheel 的 root-x mask 直接复制到 leg gate。

phase11→-1 可以作为真实 bookkeeping 保留；禁止的是同一已完成 encounter 的非法 -1→0，不伪造 phase11 不变。每个动作仍只执行一次 teacher prepare 和一次实际 IK，诊断没有第二次隐含控制计算。

新 encounter 的行级初始化独立于 episode reset：

- 新序列 phase/steps/drive_allowed 回到初始状态；新事件、phase11、资格及输出诊断 generation 更新；
- nominal wheel position/body height 必须新捕获，不继承上一 encounter 的姿态；第一次 encounter 保持原有捕获时序，以满足前缀 parity；
- 清理当前模式启用的 wheel integral、wave计时、平滑、clearance-release记忆；不用的模式显式拒绝，不能藏未初始化状态；
- joint/body ID 等未变的拓扑缓存保留；不能全batch赋 None 影响其他环境；
- post-reset callback 覆盖显式、局部和 done reset，仍遵守原 pre-reset 先记录、reset通知去重。新 encounter 不调用 `env.reset()` 或同步器旧 `reset()`。

## 7. 动作控制权交接

动作 owner 必须明确为 `REFERENCE`、`POST_CROSS_SYNC` 或已有验证的 `ROUTE`；同一行同一步只能有一个最终轮动作 owner。腿动作仍归原 reference/后续命名动作合同，不能被同步器覆盖。

时序：observe(t)取得完成的物理证据 → coordinator 形成绑定身份的边界 → prepare(t+1)在可能产生新腿动作前验证并交接 → teacher prepare一次 → 按新 owner 决定是否覆盖四轮 → 实际执行 → 同 generation 的 pre-reset observe。

新增 `release_sync/begin_encounter` 接口只处理相应 env 行：清 active、旧 ready/event/phase11、EMA/积分/限速/hold、旧packet资格与activation，保留 episode_id、全局步号、episode_length一致性检查和历史指标。新同步接管必须用本次全新5个稳定样本，首次输出继续 hold 上次真实已执行轮命令。

packet采用不可变raw-world状态加prepare时冻结的descriptor两层记录。sample(t)仍属于实际执行它的旧encounter，不能就地改ID或重投影覆盖；新prepare(t+1)的几何判断可从该raw-world样本重新计算新frame视图，但该视图不是新的物理采样，不能计入新encounter的事件/ready。新observe(t+1)才是新generation的第一个完成样本。位姿连续性/实际动作对照使用raw-world、episode和step；只在descriptor完全相同时比较局部坐标，禁止把旧frame sample与新frame current直接判不等或洗成同一帧。旧样本、旧descriptor与边界凭据全部可独立追溯。

交接凭据必须包含正确 step、原/新 encounter、物体、原因及几何证据。重复、跳号、旧packet、prepare和observe之间改generation一律拒绝。**fresh wave、非零腿动作或报错本身不是交接凭据**：没有合法边界时，旧 applicability guard 仍在覆盖动作前报错。

掉头或进入不再适用“正向直行同步”的路线，必须在路线动作生效前由明确的 ROUTE_REQUEST 交接，且已完成恢复、几何无碰撞、处于安全路线域。不能等 root/heading 变化触发旧保护后再静默取消 active。路线 owner 也须记录实际动作和连续性；此接口不凭空提供已验证的转向能力。无合法路线控制器则返回未支持，而非继续直行并报告返回成功。

旧 PI/EMA/feedforward/限速参数不在此修复中调优；第一跨越高度、横向漂移另属 .1。坐标和合法 owner 的适用域有明确版本，不能为通过新场景删除原固定模式的 root/腿/wave 保护。

## 8. 原始记录与独立验收

保留所有旧 artifacts 和原 `metrics.py`。旧单杆 first-episode collector 不在新 encounter 时 reset；失败/碰撞/termination 不得被后一次成功覆盖。旧 run14/15/16、18、19 用冻结 verifier 得到原结论。

新 sidecar/schema 记录：全部身份、descriptor、raw/effective gate、phase前后、selected rays/hit关联、包络/接近/离开几何、边界理由、owner前后、缓存generation、各次event/ready/activation/release、原/最终/实际processed动作。必须保留可重建关联的 hit与几何输入，不能只保存 `completed/rearmed=true`。

新增独立 NumPy verifier，不导入运行时 coordinator。逐step、全env、每个预期encounter重建选择、转换、动作交接、有序跨越、5样本资格和同步公式；缺失输入或歧义均拒绝。episode与encounter分母在运行前manifest固定，未进入或未完成也计失败；禁止只按已成功encounter统计。

旧单杆 full-first-episode 均速差≤.08、全部接触/姿态/高度/动作阈值和 exact budget 均不改。返回含转弯的新场景另外报告每次跨越与全行程安全，不将转弯窗口伪称旧平地tail800；旧模式的完整严格通过仍为单独必需门槛，不能被新模式结果替代。

## 9. 实施与验收关卡

### G0：CPU 红绿测试和独立审查

- disabled快照与原函数parity；首次phase0..10输入/动作不变；phase10未恢复不得完成；旧root>1.15不能提前禁腿。
- 同物体raw gate/scan闪断、phase11→-1不重建encounter；计时、停留、转头看不见均不解锁。
- 完整离开再接近同物体；不同物体连续可见且无全局gate空隙；活动过程中出现另一物体；错误方向、错误轮侧、重叠/未知候选均有独立用例。
- 4/5或5/5旧ready、新encounter、同步已active三种交接；旧成功不能授予新encounter资格；无合法凭据的新wave仍触发保护。
- 部分env转换不影响其他行；局部/全部reset；重复/跳号/错env/旧generation、pre-reset次序、nominal重捕获、frame旋转/平移一致性。
- 不同原点并旋转方向的合法encounter切换必须通过原始物理连续性核验；混用上一frame的坐标必须拒绝，不能通过删除prior-step检查放行。
- 修改sidecar的身份、完成声明、事件、owner、hold、bias等，独立重放必须拒绝；原始负例不被洗掉。
- 全部既有CPU回归、bash语法、规格与代码质量审查；原正常退出链不变。

### G1：原单杆实际8-env，再1024-env

原配置、随机化、资产、窄杆高度/位置不动。在 amp/物理GPU7 运行全新单进程8×1600，无resume或自动重试。与既有匹配基线比较首次完成之前的非计时前缀、source/scene/randomization与真实动作。原 strict8/8、exact1600、native0/正常关闭、新encounter verifier通过同时成立才允许该候选重复和后续1024门槛。若失败则保留负例，回到原因分析，不连带扫lift/gain。

顺序严格固定为：**同一冻结新候选三次独立8×1600全部通过 → 1024×32容量完整通过 → 1024×1600全量严格行为**。中途改动候选控制/来源则之前通过次数不累计到新版本；旧run14/15/16不能抵扣这三次。容量短测不是行为通过，更不是PPO更新数。

1024仍需全量原严格行为；18首次几何负例不能因修复重入而当作已解决。缺任一环境都不能宣称1024验收。新候选修改了行为来源，旧三次通过不能直接记为新候选重复次数。

### G2：再次遇障的真实物理验证——必需，不以CPU替代

需要独立具名的8-env场景：①同物体连续运动离开后再次接近；②连续两个独立小障碍；③近邻/混合可见、未完全离开或恢复未完成时出现候选的负例。每个正场景每env预期至少两个encounter，在manifest中提前固定，不允许reset、teleport、直接写pose或人工伪造完成。重新抬腿与第二次实际跨越分别计结果。

这些场景的前置子项是统一方向坐标、轮侧选择、多对象接触归属、真实平地路线/掉头控制与足够空间的隔离布局。当前源码不具备完整能力；不得把固定单杆换个ID就宣称该关卡通过。路线/场景作为独立实现包先固定其完整参数和预算并验证，再启动物理试验；本规格不授权临场试增益、缩短预算或重启拼接。

本 encounter 功能的通用验收在 G2 完成前保持未完成。G1通过只证明原场景的误重入修复，不能替代用户要求的再次跨越。后续 AME named-target桥、policy-only跨越/大绕行、单进程10000仍按总目标继续，不因完成此模块而结束任务。

## 10. 资源、来源和设计工作清单

只用 amp 与物理GPU7。原占位仅在确需GPU且重新验证用户/PID/start/script/设备后按既有授权暂停，任务计算结束且GPU7无其他任务时恢复。不得操作其他人的进程，不改SDK/驱动。旧run、模型、随机化和失败证据全部保留；新输出唯一目录优先 `/data/hexinkun-m1-acceptance-20260918`，启动前核容量。

来源：原 `m1_curriculum.py` SHA `6e630a8f7be6e31d4fbebeec87d1736ab8ac1e764532fca7026ad0c51ecacb5b`；wrapper SHA `d6c7056d422a83efb028e1053d8ce496879e14b25410d6cf14a789734c82100a`。新vendor/coordinator/bridge/verifier/场景必须另立版本及hash，不能冒用上述来源未变声明。

- [x] 读取入口、当前代码、负例和首次几何诊断。
- [x] 解释方案差异；用户指出再次遇障边界后，同意修正版A。此问题采用文字说明，不需要视觉伴侣。
- [x] 两项独立只读审计：reference选择/坐标/缓存，sync所有权/独立验收；主代理复核关键源码。
- [x] 写明状态、组件、因果时序、错误处理、保留范围和分阶段但不可替代的完整验收。
- [x] 规格自审与两项独立边界复审通过；已修订G1旧IK锚点、明确几何选择谓词、DEPARTING出口、raw-world/frame分层及三次8-env晋级顺序。这仅是规格审阅，不是代码或物理通过。
- [x] 用户审阅本具体规格并明确“按规格实施”。
- [x] 已使用 writing-plans 创建首个独立几何包计划并开始隔离TDD；后续包/物理门槛仍待完成，本文件不是已运行结果。

相关：[重入根因](../../../notes/log/2026-09-18-m1-scale-wave-reentry-diagnosis.md)、[首次几何](../../../notes/log/2026-09-18-m1-scale-first-cross-geometry.md)、[原同步规格](2026-09-18-m1-post-cross-wheel-sync-design.md)、[T306](../../../notes/todo/T306-m1-ame-long-train-stability.md)。
