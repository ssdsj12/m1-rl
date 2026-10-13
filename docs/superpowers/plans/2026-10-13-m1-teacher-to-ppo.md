# M1 Teacher-to-PPO Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking. Do not launch parallel GPU jobs.

**Goal:** 在相同M1物理和10cm课程中验收16维教师，训练独立学生，完全撤除教师后接续PPO。

**Architecture:** 独立teacher/模仿入口输出与学生一致的16维动作；生产PPO路径保持无teacher调用。动作、课程、碰撞、学习阶段和检查点使用明确的新合同，旧8维PT与旧训练不恢复。

**Tech Stack:** Python、PyTorch、Isaac Lab/Isaac Sim、AME、仓库rsl_rl、pytest、SSH；只使用当前项目的传感与物理接口。

---

规格：[已确认设计](../specs/2026-10-13-m1-teacher-to-ppo-design.md)。Baseline `f58f1fd`。用户2026-10-13已确认书面规格，包含95/100教师、90/100无教师学生验收线。计划不是部署回执。

## 执行顺序与停止条件

2026-10-13执行状态：Task1–3候选软件/两阶段审查完成，Task4控制与碰撞原生合同通过，但教师A失败并阻断。初始及两次有界修订均未完成跨越；最终253相关CPU通过不能覆盖物理失败。Task5–9未开始，生产/学生训练未部署，GPU已释放。后续需新教师设计审阅，禁止自动再试或降低门槛。逐项证据见[实施账本](../../../notes/log/2026-10-13-m1-teacher-to-ppo-implementation.md)，下方原计划复选框保留为原始执行说明，不代表全部待做或已通过。

三个串行里程碑：A新合同/教师原生验收；B模仿和完全撤除；C critic校准/PPO。A失败不启动B，B失败不启动C。CPU通过不等于原生验收，教师通过不等于学生通过。

现有普通clone镜像 `C:/Users/xk/Documents/project/m1-ppo-recovery`、分支10-12；保留预存dirty notes和两个watcher，不stage整目录。执行前按worktree技能核实隔离偏好，不能把普通clone冒充linked worktree。本轮仅写计划，没有创建工作树或安装依赖。

远端只使用当前host `root@a21495354824192000872439`，生产 `/root/quad/m1-rl/.worktrees/contact-recovery`；Python `/opt/conda/envs/env_issacsim/bin/python`。旧helper可能硬编码旧host，禁止直接执行。开发文件先到显式candidate目录，原生通过前不覆盖生产。

所有测试命令在项目的 `Go2Pvcnn` 目录运行，设置 `PYTHONPATH=$PWD:$PWD/rsl_rl`；纯CPU命令额外设置 `CUDA_VISIBLE_DEVICES=''`。原生入口先AppLauncher后Isaac导入。每次运行保存命令、退出码、日志及候选SHA；缺pxr的全库collection失败不得称全库通过。

## 文件责任图

新增：

- `Go2Pvcnn/ame_baseline/m1_teacher_contract.py`：阶段、16维、来源和交接合同（纯Python/torch）。
- `Go2Pvcnn/ame_baseline/m1_teacher_profile.py`：显式16维/平地→10cm/2分每步配置装配，无teacher控制。
- `Go2Pvcnn/ame_baseline/m1_reference_teacher.py`：纯tensor状态机、支撑参考、阻尼IK及标签有效性。
- `Go2Pvcnn/ame_baseline/m1_teacher_adapter.py`：Isaac状态读取/命名关节映射，不推进物理。
- `Go2Pvcnn/ame_baseline/m1_imitation_data.py`：有界样本、terminal对齐和数据split。
- `Go2Pvcnn/ame_baseline/m1_imitation.py`：监督loss、动作来源选择、撤除阶段。
- `Go2Pvcnn/ame_baseline/m1_student_handoff.py`：评估门槛、阶段转换与critic-only校准。
- `Go2Pvcnn/scripts/probe_m1_teacher.py`：teacher/控制/奖励原生验收。
- `Go2Pvcnn/scripts/train_m1_teacher_student.py`：有界BC/再标注，仅监督优化器。
- `Go2Pvcnn/scripts/evaluate_m1_student.py`：无教师均值/采样评估、视频和完整事件。
- `Go2Pvcnn/scripts/prepare_m1_student_ppo.py`：审计并生成显式PPO初始化PT。

小范围修改现有 `m1_collision_budget.py`、`m1_collision_budget_terms.py`、`m1_learning_curriculum.py`、`ame_runner.py`、`train_m1_cross_large_complex_ame.py`。不复活wrapper里的旧 `get_mpc_teacher_action`，不修改extension planner核心；FK/命名映射仅作为数学工具复用。

每个新增纯逻辑模块配同名 `Go2Pvcnn/tests/test_*.py`。最终记录写入 `notes/log/2026-10-13-m1-teacher-to-ppo-implementation.md`，同步T306/index/todo/log索引；README仅按真实已通过状态更新。

### Task 1：16维学习阶段合同与显式配置

**Files:** 新增 `m1_teacher_contract.py`、`m1_teacher_profile.py`、`tests/test_m1_teacher_contract.py`；修改训练入口和runner的profile/save/load接线。

- [ ] RED：测试以下合同生成与严格不匹配拒绝，包括旧8/12维、旧16维但无新profile、未知phase、teacher来源不一致。

```python
def test_old_sixteen_action_checkpoint_is_not_student():
    from ame_baseline.m1_teacher_contract import student_contract, require_contract
    import pytest
    with pytest.raises(ValueError, match='student contract'):
        require_contract({'ame_num_actions': 16}, student_contract())
```

- [ ] Run `python -m pytest tests/test_m1_teacher_contract.py -q`，先确认缺模块/断言失败，再实现纯合同：

```python
from copy import deepcopy
from extension.parallelism.m1_kinematics import M1_ASSET_JOINT_NAMES

PHASES = ('bc', 'withdrawal', 'critic_calibration', 'ppo')
REFERENCE = '8aeb845f73e39fd1e121758522ef05ee2378150f'

def student_contract():
    return dict(version=1, profile='teacher_student_16_10cm',
                action_dim=16, joint_names=list(M1_ASSET_JOINT_NAMES),
                fixed_abad=False, fixed_wheel_speed_m_s=None,
                stage_sequence=[0, 3], teacher_source=REFERENCE,
                collision_cost_per_step=2., collision_budget=20.)

def require_contract(checkpoint, expected):
    if checkpoint.get('m1_student_contract') != expected:
        raise ValueError('student contract mismatch')
    phase = checkpoint.get('training_phase')
    if phase not in PHASES:
        raise ValueError('student contract has invalid training phase')
    if checkpoint.get('ame_num_actions') != 16:
        raise ValueError('student contract requires sixteen actions')
    return deepcopy(checkpoint['m1_student_contract'])
```

- [ ] 配置入口先创建当前M1 cfg、再显式选择profile；profile强制 `M1AmeActionsCfg()`/action_dim16/fixed_abadFalse/fixed_wheel_speedNone，调用flat-first地形，选择stage_sequence(0,3)。forward command维持(.30,.30)、y/yaw命令0，这是任务目标而不是执行轮速锁。旧fixed环境变量不得静默覆盖profile，冲突时报错。
- [ ] profile更新完整 `m1_training_contract` 的profile、collision和stage字段，保留物理/观测/姿态字段；runner保存和加载 `m1_student_contract` 与 `training_phase`。普通resume仅同phase/同合同；预训练切PPO必须Task8的显式转换。不要改旧profile默认语义。
- [ ] GREEN：16列命名映射、default姿态/leg scale1.50、wheel scale1/r、轮限20rad/s逐项测试；runtime配置测试覆盖继承post-init后不被fixed模式覆盖。日志打印实际action manager维度而非只打印cfg。
- [ ] 明确列出Task1文件提交：`feat: add sixteen-action teacher student contract`。

### Task 2：碰撞2/控制步与平地直进10cm

**Files:** `m1_collision_budget.py`、`m1_collision_budget_terms.py`、`m1_learning_curriculum.py`、profile、`tests/test_m1_student_collision.py`、`tests/test_m1_student_curriculum.py`。

- [ ] RED：保留旧5/s测试不动，新profile测试10个收费步封顶20、不同dt、signal=.001也扣2、多来源去重、间歇保留、reset行局部/terminal旧快照。

```python
import pytest
import torch
from ame_baseline.m1_collision_budget import CollisionBudget

@pytest.mark.parametrize('dt', [.01, .02, .04])
def test_student_budget_is_per_step(dt):
    b = CollisionBudget(2, 'cpu', dt, cost_per_step=2.)
    for step in range(10):
        s = b.update(torch.tensor([.001, 0.]), step)
        assert s['cost'].tolist() == [2., 0.]
        assert s['exhausted'][0].item() == (step == 9)
        assert b.update(torch.ones(2), step) is s
    assert s['total'].tolist() == [20., 0.]
```

- [ ] Run `python -m pytest tests/test_m1_student_collision.py tests/test_m1_student_curriculum.py -q`，保存RED证据。
- [ ] 在CollisionBudget构造增加keyword-only `cost_per_step=None`；校验提供值有限且正。旧requested式保留，新增计算：

```python
requested = (5. * self.dt * clean if self.cost_per_step is None
             else self.cost_per_step * (clean > 0).to(clean.dtype))
```

Manager从cfg的profile费用字段传值；reward继续 `-cost/step_dt`，由RewardManager乘dt一次。禁止既扣cost又在wrapper扣第二次。raw signal仍进入strict和正奖励屏蔽。budget contract标记单位，不复用旧version1的5/s字样。

- [ ] `LearningCurriculumGate`增加 `stage_sequence=(0,1,2,3,4)`，profile传(0,3)。检查非空、从0开始、整数唯一递增、范围0..4。晋级用当前stage在sequence中的下一项，最后一项保持。保存新sequence元数据；新profile拒绝旧课程精确恢复。无profile的旧v1读取保留原序列，不能全局破坏历史诊断。
- [ ] GREEN：三个合格完整窗口从0直接3、3不进4；transition期间旧stage回合不污染新stage；真实row3高度.10/8目标+70填充；last/pending分开。原有stage0..4测试保持。
- [ ] Commit `feat: add per-step collision budget and direct ten-centimeter course`。

### Task 3：教师数学核与动作编码（不调用旧MPC）

**Files:** `m1_reference_teacher.py`、`m1_teacher_adapter.py`、`tests/test_m1_reference_teacher.py`。

- [ ] 固定参考commit来源记录。读取已核实的参考sequential和IK函数，记录许可证/来源；只移植必要数学与状态转换，不导入其整个环境、不依赖旧MLP/PVCNN检查点。
- [ ] RED：测试命名映射和动作逆编码的round-trip、不可达/NaN标签拒绝、按实际load/位置晋级而非计时即成功、单行reset、同控制步幂等、左右镜像/前后镜像、没有env.step调用。
- [ ] 使用纯tensor API：`TeacherState`包含root pose/velocity、12腿角、4轮位置/力、障碍中心/尺寸/有效性、dt和resetmask；`TeacherOutput`包含action[B,16]、valid[B]、phase[B]、active_wheel[B]、reason[B]。显式区分asset joint order与planner order，不能reshape猜腿序。
- [ ] FK复用 `m1_fk`；按同一关节序用中心差分eps=1e-4计算位置Jacobian。阻尼解核心如下，测试独立有限差分和奇异构型：

```python
def damped_step(jacobian, error, damping=.05, max_step=.25):
    import torch
    eye = torch.eye(jacobian.shape[-2], device=jacobian.device,
                    dtype=jacobian.dtype)
    dual = torch.linalg.solve(jacobian @ jacobian.transpose(-1, -2)
                              + damping ** 2 * eye, error.unsqueeze(-1))
    return (jacobian.transpose(-1, -2) @ dual).squeeze(-1).clamp(-max_step, max_step)
```

- [ ] 每个目标遭遇独立保持APPROACH→BALANCE→LIFT→PASS→RESTORE状态；一次只选一轮，按现有必跨目标的实际轮轨/位置选择，不套固定单障碍x=.85或永久right-track-only。BALANCE必须测到其余三轮有效承重才进入；LIFT须真实轮底高于top，PASS须真实到远侧，RESTORE须5帧稳定。任何碰撞/失载记失败并保留tracker原始判据；teacher phase不是成功receipt。
- [ ] 初始调度参数写入不可变配置并进hash：balance30控制步、lift ramp10、pass ramp20、restore20、前后最大lift delta .22/.20m、机身横/纵参考偏移最多.06/.04m、远侧轮包络余量.15m。它们是待原生验证的教师参数，不是新的学生成功净空要求。支撑轮接触参考随实际滚动更新，不把滚轮假定成固定足；没有安全有效解时返回validFalse而非发伪标签。
- [ ] 按当前默认joint_pos将IK目标逆编码为(action_leg=(q-default)/1.50)，wheel action=v_surface/(r*wheel_scale)，再通过现有decoder验证到达同一有界目标。教师可减速、停轮/差速；不得修改执行器。标签超限/未收敛标记无效，不能靠clamp把它伪装成可达解。
- [ ] Adapter只读当前scene命名状态/真实geometry，记录privileged来源，不拼到actor输入；state/action时间戳一致。`reset(done_ids)`只清对应环境。用失败有效性测试覆盖连续无标签路径。
- [ ] Run `python -m pytest tests/test_m1_reference_teacher.py tests/test_m1_ame_action_contract.py -q`，确认RED→GREEN后提交 `feat: add isolated reference crossing teacher`。

### Task 4：原生合同与教师验收（里程碑A）

**Files:** `scripts/probe_m1_teacher.py`、`tests/test_m1_teacher_probe_contract.py`、验收jsonl/summary/video与实施日志。

- [ ] 探针只支持显式candidate源码/Python路径，打印代码SHA、16个关节名、实际dim/obs/PD、课程height/count、collision单位；使用4env小批、每次wrapped.step只推进一次。先验证空地和碰撞budget，再验证教师，不并行启动。
- [ ] 测试probe verifier拒绝伪造阶段成功、缺terminal快照、缺视频、重复episode、超时被计成功；样本输出必须有env_id/episode_id/attempt_id/frame/activewheel/Fz/轮底/obstacle top/碰撞/远侧恢复/receipt。
- [ ] 原生碰撞至少验证：env0连续10收费步2→20只env0reset；env1间歇有累计且不被清；最后帧无额外20；纯timeout0；其他物理失败20。检查最终wrapper reward，不只看manager项。
- [ ] 每个seed(101,102,103,104,105)各20完整回合，teacher-only flat与stage3分开跑。完整10cm课程严格成功>=95/100才输出teacher验收PASS；必须覆盖所有必跨目标，不将单轮成功或前进pass作整段成功。保存成功和失败视频及完整轨迹，不挑选单次最好结果。
- [ ] 教师失败只做同env时序归因，在规定参数范围内有界诊断；不改物理/地形/成功判据。记录每次参数hash与失败环节。首个候选加最多两次有证据修订仍不能通过时，停止并汇报，不启动监督长训。
- [ ] Probe退出、GPU释放证据与结果写日志；提交 `test: verify teacher native feasibility` 仅在真实通过时使用“verify”。

### Task 5：数据收集与行为克隆

**Files:** `m1_imitation_data.py`、`m1_imitation.py`、`scripts/train_m1_teacher_student.py`、对应测试。

- [ ] RED：样本obs必须是动作前，自动reset terminal不跨episode拼接；只接受有限/可达标签；按episode而非随机帧分train/validation；buffer上限固定不无限增长。
- [ ] 数据schema：`obs, teacher_action, executed_action, valid, done, terminal_snapshot, episode_id, attempt_id, seed, teacher_hash, phase`。phase仅教学诊断，不进入actor。初始BC成功teacher轨迹与flat轨迹各占batch一半；数据不进入rsl_rl rollout storage。
- [ ] 实现分组loss，legs/wheels各自平均后等权相加；不对不合法标签求均值：

```python
def imitation_loss(prediction, target, valid, leg_ids, wheel_ids):
    import torch.nn.functional as F
    if not valid.any():
        return prediction.sum() * 0.
    p, t = prediction[valid], target[valid]
    return (F.smooth_l1_loss(p[:, leg_ids], t[:, leg_ids])
            + F.smooth_l1_loss(p[:, wheel_ids], t[:, wheel_ids])) / 2.
```

- [ ] 新建16输出AME，不加载旧PT。只优化map_cnn/mha/actor_state_projection/actor，std和critic不参加监督优化。初始Adam lr2e-5、batch256、grad clip1，最多3000次更新；每100次保存并验证，不自动扩大上限。缺数据/NaN立即中止，不保存成可接续成功PT。
- [ ] 验证监督训练降低固定小数据误差、动作映射正确、critic/std未变；生产obs与数据collector一致且无teacher真值泄漏。Run `python -m pytest tests/test_m1_imitation_data.py tests/test_m1_imitation.py -q`。
- [ ] Commit `feat: add bounded teacher behavior cloning`。

### Task 6：学生状态再标注、撤除与无教师评估（里程碑B）

**Files:** `m1_imitation.py`、`scripts/train_m1_teacher_student.py`、`scripts/evaluate_m1_student.py`、`tests/test_m1_student_withdrawal.py`。

- [ ] RED：teacher比例0时不得实例化teacher；同一个seed动作来源可重放；学生自己状态产生的有效标签被收集，无效标签排除但失败率保留；损失低但无教师任务失败不能进入PPO。
- [ ] 分档teacher比例[1,.75,.5,.25,0]，以完整rollout片段选择teacher或student来源并记录，禁止未记录的action覆盖。再标注对学生真实状态调用teacher且只用valid标签。每档最多1000监督更新、总计不超过额外5000；保留flat replay，不调std。
- [ ] 所有档位都运行独立无teacher评估，10cm完整成功最低晋档线依次20/40/60/80/90（100回合），flat均>=95/100；达不到时在本档有界更新，耗尽即停并诊断。中间线仅控制训练节奏，最终仍是规格的90/100，不当掌握证据。
- [ ] 最终用固定seed集与100回合，mean和sample分别报告，要求两者各>=90严格完整成功；teacher_call_count和action_override_count都0。`sys.modules`或依赖注入给teacher构造/调用设置raise替身，确认player可运行。
- [ ] 保存student SHA、合同、teacher来源、数据split、mean/sample结果、BN running stats及视频；不向PPO传入teacher phase。Run `python -m pytest tests/test_m1_student_withdrawal.py -q`。
- [ ] Commit `feat: gate teacher withdrawal on independent student evaluation`。

### Task 7：critic-only校准，保护actor与BatchNorm

**Files:** `m1_student_handoff.py`、`tests/test_m1_student_handoff.py`。

- [ ] RED：校准前后同一固定obs的actor输出及整个actor依赖state_dict逐项一致；critic参数有实际更新。覆盖BN running_mean/running_var/num_batches_tracked，不能只测试requires_grad。
- [ ] 将整个模型设eval，冻结全部参数，只解冻critic_state_projection与critic，单独Adam lr2e-5；不能解冻共享mha/map_cnn。使用teacher-free最新策略rollout、真实reward/done/timeout构造bootstrap returns，遵循仓库现有timeout bootstrap语义。

```python
def critic_only_parameters(model):
    model.eval()
    for parameter in model.parameters():
        parameter.requires_grad_(False)
    selected = list(model.critic_state_projection.parameters()) + list(model.critic.parameters())
    for parameter in selected:
        parameter.requires_grad_(True)
    return selected
```

- [ ] 校准最多100次更新，finite loss/returns和actor逐项一致；完成后解除正常PPO所需参数freeze，丢弃校准Adam，清空旧rollout。std数值保留不手动修改。Run `python -m pytest tests/test_m1_student_handoff.py -q`。
- [ ] Commit `feat: preserve student policy during critic calibration`。

### Task 8：显式PPO交接与checkpoint隔离

**Files:** `scripts/prepare_m1_student_ppo.py`、`m1_student_handoff.py`、`ame_runner.py`、训练入口、`tests/test_m1_student_checkpoint.py`。

- [ ] RED：拒绝BC未验收、teacher比例非0、旧8维/旧16维、伪造teacher-free、非有限权重、不同动作尺度/碰撞单位/课程；拒绝把监督Adam装入PPO。阶段转换只能走prepare入口。
- [ ] CPU审计全部权重和16个std正有限；结合带source SHA的无teacher评估回执核实来源，保存新的conversion记录。初始化新PPO Adam，拷贝学生/校准后critic/编码器/BN状态与同阶段课程；PPO iter起点使用明确的fresh-PPO计数，不能伪称BC update编号是PPO轮数。
- [ ] Runner保存 `training_phase='ppo'`、`teacher_free=True` 和handoff provenance；load默认严格检查同合同/阶段，后续同PPO run恢复才允许加载其Adam。
- [ ] 不改通用PPO更新公式；断言每条rollout action/log_prob来自当前策略，enable_mpc_teacherFalse/imitation_coef0/无trajectory manager。测试teacher依赖raise时PPO采样、一次更新、保存加载仍成功。
- [ ] Run `python -m pytest tests/test_m1_student_checkpoint.py tests/test_m1_student_handoff.py tests/test_m1_teacher_contract.py -q`；Commit `feat: add explicit teacher-free PPO handoff`。

### Task 9：部署、2048首更新与防退化检查（里程碑C）

**Files:** 新启动脚本 `Go2Pvcnn/scripts/train_m1_student_ppo_headless.sh`、README、实施notes和测试清单。

- [ ] 全部相关CPU回归、Task4原生、Task6独立评估、Task7/8交接证明齐全后才部署；静态审查Task1-8关键变更，任何重要问题先反例RED再修复。若选subagent方式，审查与实现分离；若inline，逐项自查并记录其不是独立审查。
- [ ] 仅新host身份核实后，确认play/探针已退出，保存PT/日志，GPU释放；备份所有待部署runtime及SHA到专用manifest，逐文件核对。不能看到GPU空闲就启动旧run。
- [ ] 新launcher明确teacher-student profile、2048/cuda0/save100/max10000、teacher_free，不继承M1_FIXED_ABAD或M1_FIXED_WHEEL_SPEED_M_S；加载Task8的显式初始化PT不是历史1400。使用kernel flock防重复。首次阶段为验收后的10cm，课程状态来自学生，不重新随机初始化网络。
- [ ] 先有界2048两次PPO更新后保存/退出并CPU验证：实际更新存在、loss/权重/Adam有限、16正std、新合同/teacher_free、实际stage3、没有teacher动作覆盖。此检查通过才能按批准上限继续同run；数值正常不等于能力保持。
- [ ] 每save100边界执行串行无teacher固定集评估；训练与评估通过保存退出/恢复或同进程独立环境安全释放实现，禁止旁路native并发。对比预训练基线下降>=10个百分点保留现场并报告；不删PT、不自动回滚、不增加总轮数。
- [ ] 原暂停automation只在训练真实启动核实后更新新合同/PID/run/teacher_free/碰撞单位/课程与通知条件，禁止旧prompt自动恢复。TensorBoard仅切明确所属服务，不动本地隧道/其他服务。
- [ ] notes/README与实际源码、验证、SHA回执对齐；普通push10-12后独立ref验证才说发布完成。所有本轮PT留存，旧watcher/PT不stage。

## 计划自查

- [x] 16维/相同执行接口/旧合同拒绝：Task1、8。
- [x] 每步2累计20、不重复termination、0→3：Task2、4。
- [x] 教师在真实10cm通过而非参考6cm自证：Task3、4。
- [x] 新网络、观察可用性、标签时间对齐：Task5。
- [x] 学生状态再标注、完全撤除与独立验收：Task6。
- [x] 非PPO教师数据隔离、共享BN冻结、显式optimizer交接：Task5、7、8。
- [x] 2048/串行GPU/防退化/保留旧PT/不改网络：Task9。
- [x] 所有门槛失败均停在对应里程碑，不把后续自动开训当默认fallback。

下一步由用户选择当前会话逐项执行或子代理分工；本计划没有执行任何实现或启动命令。执行时遇到教师可行性失败以物理证据报告，不通过重复要求已确认的16维方向来回避问题。
