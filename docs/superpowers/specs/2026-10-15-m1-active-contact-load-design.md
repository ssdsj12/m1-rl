# M1 v22 活动轮接触过渡载荷

用户“直接运行，自己许可”授权延续隔离教师纠正，不重复设计/执行审批，不覆盖生产训练、删证据、全局配置。上一轮v21是真实失败证据进展，进程已退出/GPU1MiB。

## 根因证据与方案选择

冻结frame114：待抬左前仍承载69.073N；三支撑实测99.379/144.460/87.473N，旧目标151.266/135.045/45N。旧公式把目标三轮重心比例乘当前三支撑力总和，遗漏活动轮仍承重的力矩。加上活动轮后，目标力合成压力中心偏离选中COM +.0627204m/+.0334260m。计入活动轮力矩后，三支撑目标115.655/102.994/112.663N，压力中心误差约1e-14m，未投影触界。frame137同样旧RR45.07、新105.98N。脚本/原始依据在v21计划workspace active_contact_moment.py/json。

另外证实fixed supportZ取消command roll/pitch的竖直执行响应，实际roll由-.0073到-.0876rad；这是已知未恢复通道，不能与载荷错误混成唯一原因。

选择A：仅纠正活动轮仍承重时的力矩分配。方案B恢复姿态支撑可能与载荷反馈竞争，暂不叠加。方案C加大增益或提高45N底线不能修复遗漏力矩，拒绝盲调。数学纠正不保证实际成功。

## 公式与接口

四轮世界坐标p[B,4,3]、rawFz[B,4]、活动索引a[B]、选中COM对三支撑的重心比例λ[B,3]，保持原顺序。S=sum(max(rawFz_support,0))，A=max(rawFz_active,0)，W=S+A。

三支撑XY解活动轮的仿射系数b：sum b=1、sum b*p_supportXY=p_activeXY；b允许负值。未投影目标 desired=normalize(λ)*W-A*b。

它保持sum(desired)=S；未投影时，三支撑目标加活动轮实测A的合成一阶矩等于W*selected_COM。A=0退化为旧空中三支撑公式，不控制活动轮力、不指定卸载动作、不取消实际抬轮。

沿用45N下界/S上界/总和S投影。投影可能破坏精确力矩平衡，记录未投影目标和投影后XY一阶矩残差（N·m），不得保证投影后仍对齐。原-.0002*(target-measured)增益、.01m/s、±.015m零和位移及一次beta不变；v21heave、height基线/安全门槛不改。

propose_load_feedback增加必填keyword wheels_w；拒绝shape/dtype/device错配，有限/非退化几何逐行valid，不允许缺几何默默走旧分支。origin-relative XY矩阵，面积阈值沿用1e-10。raw/fractions/geometry无效或S<135冻结旧offset。负raw沿用旧clamp总量/原始反馈逻辑，A非负。

LoadProposal追加unprojected_fz[B,4]、active_affine[B,3]、moment_residual_xy[B,2]，活动target与unprojected为0（表示不驱动它，不代表其实际力0）；无效行新增诊断为0且validfalse。

审查补强：近共线但面积合法时float32大数相消会破坏总力/力矩。新几何求解、S/A、归一化、desired及目标投影用float64；新增三个诊断tensor保留float64，target/offset/velocity仍输入dtype。残差使用最终cast后的target提升double计算；teacher日志最终float32由独立double审核按原容差核验，不扩大容差。

teacher传同帧真实wheel_pos_w，fingerprint v22。诊断新增未投影4值/活动仿射3值/力矩残差XY2值/活动非负力1值。RESTORE仍旧归零，新诊断为0。probe从preparation_input真实轮位与力独立算仿射和标量投影，不调用controller helper或接受自述几何；控制/审核有效性边界一致，history/terminal/回滚保持。

## 验证与不变项

矩形4活动轮、非对称真实几何、全局XY平移/绕Z旋转、A=0/A>0、投影触界、退化/NaN/错shape/device/dtype、batch单行无效、float32连续状态；目标总和与一阶矩均验证。真实frame114重现旧RR45而正确112.66，验证目标力矩和反馈方向。

teacher/probe同帧轮位绑定；篡改affine/未投影/残差/原始轮位必须失败；IK及最终编码失败不commit；RESTORE/reset回归。全相关CPU、一次fresh最终review后唯一4env seed101 first10cm，完整退出/视频/事件归档。真实跨越+跨后恢复才达成。

不改PD/增益/姿态阈值/关节分支/低速.05m/s/30N保护/碰撞穿透和成功标准；不启动BC/PPO。Git身份缺失保留dirty与SHA，不伪造commit。

自审：量纲明确、仿射允许负而λ非负、投影残差不冒充0；A=0恢复旧力分配但几何仍验证。本次只接触力矩修正，姿态缺口未混入。非视觉UI任务，不开浏览器。
