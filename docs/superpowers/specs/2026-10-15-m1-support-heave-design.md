# M1 v21 common support heave

用户“直接运行，自己许可”授权inline实施，不重复普通审批；仅隔离教师，不生产训练。承接v20完整失败与冻结敏感度：支撑Z覆盖使command rootZ变化对执行Z响应归零，机身.599→.401m下沉，实际COM余量不足冻结抬轮。此为明确缺失通道，不断言唯一物理原因。

方案选择：不回退整个v20（会重引入任意差分漂移），不增大载荷增益/PD。保留支撑世界Z基准与零和载荷分配，添加三支撑共同的世界Z升降修正，单独检验机身高度负反馈。姿态角通道未在本次恢复，若仍失败须依据实测再定位，不能承诺仅此即成功。

首次LIFT/PASS成功事务捕获 e0=完整反馈command.rootZ-measured.rootZ，h0=0。后续目标h*=clamp(-(command.rootZ-measured.rootZ-e0),-.02,.02)m，每步proposal=old+clamp(h*-old,-.02dt,.02dt)。机身低于目标时三支撑目标共同向下推动；基线误差用于首次无跳变，不补历史。RESTORE令h*=0，同速退至零。

最终支撑执行worldZ=已有support_reference_z+load_offset_j+heave（仅3支撑），活动腿不变、XY不变。一次beta从上一已下发q插值；heave状态old+beta*(proposal-old)提交。paired校验有限/形状/device/dtype/幅度/速率，不改变零和load约束。首次capture只在scratch，最终IK/编码/连续性成功才commit；拒绝保留旧状态，reset/episode/完成清理，RESTORE finish另需abs(heave)<=1e-8。基准Z原v20恢复条件保留。

仅load_feedback模式启用；无新CLI开关。fingerprint v21。诊断记录enabled/captured/error0/old/proposed/selected/committed；context保存旧状态，独立审核从raw measuredroot及command_requested算误差、验证历史链及执行Z，不能只重放同函数。

验证：pure function正负误差/饱和/速率/RESTORE/invalid；4活动索引、倾斜root、不同beta；首次无跳变、失败不提交、单行reset、RESTORE退出；篡改审核。冻结v20帧证明竖直共同通道非零且支撑差分不变，非物理成功。全相关CPU+freshreview后唯一4env/seed101/first10cm，完整视频/轨迹/审核，实际经过及恢复才成功。

不变：30N实测保护、真实无碰撞/穿透/跨越后恢复、.05m/s缓慢滚动、PD/资产/关节限位/分支/步长，禁止训练与删除证据。Git作者未配置保留快照SHA、不伪造commit。自审：接口、单位、符号、baseline与RESTORE明确，范围仅公共升降通道；既有直接执行授权覆盖此单变量教师修正。
