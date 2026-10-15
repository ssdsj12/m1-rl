# 载荷优先的统一支撑调整

## 依据与范围

v23真实10cm失败：活动轮未离地，右后先失载。固定世界Z消掉姿态竖直响应，但独立叠加姿态offset冻结复算又与弱轮补载冲突。用户授权直接修改并隔离实测，目标始终是真实跨越并恢复，不是静态姿态稳定。生产训练不在范围。

选择单一支撑offset状态和单一投影，不添加第二个位置积分器。保留现有预载高度、公共heave、慢速轮驱动、主动轮抬升、IK/连续性/支撑安全与事件成功标准。

## 纯数学合同

输入raw_fz/fractions/wheels/active/previous/dt/valid沿用load feedback。新可选attitude_error_m为[B,4]，活动轮0、三支撑零和、有限；None完全保留旧行为。

姿态几何误差由期望body姿态Rd、实测Rm和目标轮相对期望body向量p计算：(Rm Rd^T p-p).z，再对三支撑去均值。第一次有效事务捕获e0，后续使用e-e0；仅LIFT/PASS启用，RESTORE沿用原offset归零与高度恢复。活动轮不接受支撑修正。

保留已有目标载荷与活动接触力矩计算，目标支撑载荷>=45N。新统一速度偏好：

v_prefer=-.0002*(target_fz-raw_fz)+.5*attitude_error_m。

单位m/s；.5为每秒误差反馈，不是新增积分器。旧限额保持：每轮速度<=.01m/s，offset<=.015m，三支撑offset/速度零和。所有态姿/载荷共用这一限额，不分别饱和后相加。

方向约束：raw_fz<45N或target_fz-raw_fz>15N的轮upper_velocity<=0；其余raw_fz-target_fz>15N的轮lower_velocity>=0。弱载优先，避免矛盾分支。先求纯载荷偏好的有界零和解baseline，再限制weak upper<=baseline、strong lower>=baseline，避免姿态把补载抵消为零。baseline始终是第二次速度投影的可行解。对偏好做原有有界零和投影，再对积分后的offset做包含同一方向约束的投影，防止最后一次投影恢复被禁止方向。无效输入行保持previous，valid=false，不能借此当支持充分。

非有限attitude当前输入行冻结；形状/dtype/device、非零活动项或非零和结构错误显式拒绝。不修改旧None输入路径的有限性或输出语义。

## 事务和审核

实际fraction只缩放一次统一offset增量；拒绝不得捕获e0或提交offset。第二PIpass必须基于相同原历史，不重复累计。episode/reset/恢复完成清e0。probe记录原始姿态、捕获e0、当前误差、统一偏好、方向掩码；独立复算和完整反馈重放绑定这些字段及生命周期。指纹仅在集成完成时升级，纯模块测试不代表部署。

## 验证与非目标

RED/GREEN：弱RR/强相反姿态仍向下；载荷平衡时姿态产生非零零和调整；四活动轮、float32/64、批量无效行、边界饱和、长序列、None兼容；负例篡改e0/误差/方向掩码被审核拒绝。集成后相关回归和独立review，唯一4env真实10cm隔离probe，无训练/native并发，保存视频/完整JSONL/源码SHA。数学通过不能宣布物理成功。

不做力矩/扭矩动作接管、不改PD/安全阈值，不把姿态绝对不倾斜作为目标。原未成功版本和PT全部保留。

自审：捕获误差仅在成功事务提交；restore不二次叠加姿态；方向约束贯穿两次投影；所有正负号有实际失败帧反例。直接执行授权免重复审批，不能免验证。Git身份限制仍保留文件与SHA，不修改全局Git配置。
