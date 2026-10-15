# v23 有界执行步长细化

## 当前状态

v23最终：唯一10cm实测4×137帧、0成功/3锁停，input131右后16.3886N导致frame132保护，活动轮底最高约0.0501mm未有效抬起。四路审核errors=[]，exit0/GPU1MiB；完整归档双方SHA6d81735b1ee70cf56adfd44593f41870352abb6c2882c2b6dd63ecaa2fe9188b。固定支撑Z对0.001rad roll/pitch指令的竖直响应被冻结CPU复算证实近0，水平响应保留；下一支撑姿态通道结构诊断，不盲增步长/放宽安全。无生产训练，跨越OPEN。

## 最终实测与结构诊断（覆盖下方运行中状态）

- runner343169/python343171正常结束exit0，GPU0回到1MiB。4路各137帧，3完整失败、1诊断中断，计入4路，完整分母未达标；所有student_demonstration_usable=false。env1–3相同轨迹，不能当3次独立成功率试验。
- env1输入131 Fz=[58.2492,162.4297,171.1444,16.3886]N；frame132 failure_locked，非碰撞/穿透。v22在139锁定，本版提前7帧，不能称物理改善。细化帧114–118/130/131确实生效。
- 同帧131预测COM余量.04236m，实际.01418m；预测三轮最小载荷15.39N。公共heave已-5.640mm，右后差分offset约-0.0946mm、目标载荷93.85N，但实际仅16.39N。载荷目标存在不等于真实承载。
- 新纯CPU冻结敏感性：帧118/125/131，command姿态分别增加roll或pitch .001rad，原几何支撑Z变化约.155–.374mm；固定support_reference_w_z后Z响应绝对值<=2.22e-16m，而XY仍约.49–.53mm。证实该转换消掉姿态竖直通道；尚不能仅此断定全部动力学根因或保证修改后跨越。
- 因连续修正未获得物理跨越，下一重审支撑姿态/载荷/抬升耦合架构，而非再增加步长或调大增益。允许途中倾斜但必须保留实际支撑与跨后恢复。生产未动，不启训练。
- 完整归档本地workspace/m1-backtrack-v23-evidence.tar.gz与服务器/tmp同名，SHA如上；含原始JSONL、视频、episode/result、runtime、测试日志和冻结诊断。审核errors=[]仅代表记录一致，不是跨越成功。未观看视频，不据此描述视觉姿态。
- 诊断脚本及JSON：workspace/support_trace.py、support-trace.json、attitude_authority.py、attitude-authority.json、m1-v23-native-summary.json。额外probe_contract取消不计通过。

最新：独立审查C0/I0/M1通过；2026-10-14T19:13:03Z唯一原生runner343169已启动，输出evidence-first-obstacle-backtrack-refined-v1，尚未完成。三runtime再次sha256sum -c全OK，启动前GPU1MiB，无训练/native/pytest。下方审查中/未启动为历史。

额外非计划probe_contract全suite在构造200合成回合时CPU活跃但耗时，准确确认并中止自己的pytest342554，终态ps无PID，保留partial日志，不能称全suite通过；核心669与独立审查已完成。审查Minor为补强非零height/heave+第二PIpass的实际细化fixture，当前代码正确，不阻断隔离实测，暂留后续。

用户直接执行授权有效。已完成隔离candidate实现和669相关CPU测试（107.16s），独立最终审查进行中；尚未启动v23原生物理，未启动生产/BC/PPO。真实10cm跨越目标OPEN。

依据[冻结执行链诊断](2026-10-15-m1-execution-backtrack-diagnosis.md)，原二分回溯因膝关节略超0.05rad把整步减半。现在先保留8级粗搜索找到的安全点，然后对LIFT/PASS/RESTORE已接受非满步行至多细化4次；所有input/两类IK/速率/编码/反馈slew验证完整重做。拒绝候选不能覆盖安全解，批量行独立，mode0/无解/满步不细化。不提高限速、PD或容差。

coarse backtrack_index保留供反积分饱和，实际执行fraction供load/height/heave提交及独立审核。指纹support-ik-transaction-v23-backtrack-refinement。

## 验证

- float32/64反例先RED（.5而不是.9375）再GREEN；精确fraction载荷提交/审计也经历RED/GREEN。
- 新9案例涵盖混合4行、满步、无解、mode0、非单调validator、上限12候选、实际teacher提交。
- 首轮664通过/5旧硬编码.5断言失败，依新规格改成实际fraction单次缩放，原容差保留；二轮669全部通过，exit0。
- 冻结v22帧114/125/130/138在新代码CPU复算beta .2421875/.9375/.96875/.875，maxdq<=.04953rad，载荷提交误差<=1.46e-11m。后三帧最终目标高于实测轮心，114仍低12.75mm，不能据此声称物理问题已解决。
- 三runtime local/candidate SHA一致：pose d77d248d；teacher163ea290；probeb92e642d，完整值在workspace/runtime.sha256。旧v22归档和全部PT保留。

## 材料与下一步

规格 `docs/superpowers/specs/2026-10-15-m1-backtrack-refinement-design.md`；计划 `docs/superpowers/plans/2026-10-15-m1-backtrack-refinement.md`；ledger/testlogs/frozencheck/baseline-v22/launch脚本在 `.superpowers/sdd/2026-10-15-m1-backtrack-refinement/`。

独立审查确认后唯一原生输出预留 `evidence-first-obstacle-backtrack-refined-v1`，4envseed101真实10cm，kernel flock且无训练/native并发。未执行前不把预留目录当进程或结果。成功必须完整物理跨越和跨后恢复证据。
