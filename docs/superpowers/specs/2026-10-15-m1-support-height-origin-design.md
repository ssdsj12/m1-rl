# v33 捕获原点相对支撑高度

目的：修正v32冻结数据证明的测量rootZ下降导致支撑body目标同步缩短。真实跨越仍须隔离10cm及恢复证据，不以CPU验证替代。用户直接执行授权代替重复审批，无生产训练。

比较：加大heave速度改变反馈且掩盖测量跟随；恢复完整姿态变换会重新引入已记录XY姿态耦合；采用捕获rootZ相对的支撑高度参考，保持现有XY/载荷/heave和事务保护。

进入LIFT/PASS第一次成功执行事务时捕获 measured root Z 为origin[B]，与support_execution_z同寿命、同提交/回滚/结束清理。执行时三支撑有效世界Z为 stored_height + measured_root_z - origin；活动轮不加此项。height stored表示原捕获坐标高度，不是后续真实世界轮高。捕获当帧delta0，无跳变；故障/encode拒绝不提交。缺完整配对历史必须拒绝，不能把不完整旧状态伪装新capture。

LIFT/PASS stored_height不变，原±.02m/.02m/s公共heave、±.015m载荷项保持。RESTORE仍保留origin，先把旧几何worldZ减去当前delta转换到同一存储坐标，再以原.01m/s趋近；执行时再加delta，不重复施加。恢复确认比较同一坐标的stored与geometry，heave/载荷归零且全部真实恢复条件满足后删除origin。origin只是坐标变换，不作为新增无限幅反馈；真实输出仍原nominal/execution IK、.1mm、.05rad及编码保护。

execution_targets新增可选support_capture_root_z[B]；无参数完全legacy。参数要求finite、同dtype/device/shape并有support_reference_w_z，mode0禁止。pose事务传递同一个origin，不对测量变换额外乘beta；关节目标由原backtracking约束。教师fingerprint v33；显式diagnostic与context记录origin及capture/commit，独立几何审计自行重建delta，动态历史逐帧绑定，伪造/缺失失败。

测试：全4active×float32/64和LIFT/RESTORE；初始delta0/不扰活动腿/相同measuredquat下rootZ扰动的支撑body目标不变（固定heave），非法参数，混合行，原legacy；事务拒绝/encode拒绝/首捕获/非首帧/单行reset/RESTORE连续交接；独立证据篡改拒绝及生产器错误注入。实际未证明前不宣称修复跨越。

自审：存储/执行/恢复明确同一坐标；边界保留；独立审计不可调用同一转换helper充当证明。无新PD/轨迹/轮速/门槛改动，不覆盖运行中源码。无Git身份不改配置，保留SHA基线和原始证据。
