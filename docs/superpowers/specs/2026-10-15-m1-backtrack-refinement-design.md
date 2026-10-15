# 有界执行回溯细化设计

依据：notes/log/2026-10-15-m1-execution-backtrack-diagnosis.md。用户要求直接继续，免重复审批；只隔离教师，禁止生产训练。目标仍真实10cm跨越并恢复，数学改进不是完成。

## 选择

1. 推荐：原8级粗回溯取得安全解后，最多4次二分细化；最坏12次候选，保留已有安全解。
2. 固定100级扫描能更密但昂贵；不选。
3. 提高速率或从实测q直接跳转会改变安全/执行合同；不选。

## 精确行为

仅 execution_mode 1/2 的已接受且 coarse_index>0 行细化。原coarse候选1..1/128及无可行解行为不变。每行lower=原已接受fraction，upper=2*lower（该上界此前被拒绝），四轮mid=(lower+upper)/2；每个候选独立重建物理参考、虚拟反馈、执行目标，完整检查input/nominalIK/executionIK/2.5rad/s/编码/反馈slew。valid则lower=mid并原子替换所有解、目标、output；invalid只upper=mid，绝不覆盖已有安全解。混合批量各行独立。满步/mode0/无解不细化。有限非单调可行区间不保证全局最大，但每个返回点必须确实验证，绝不因假定单调直接接受。

`backtrack_index`保留首次粗级索引供反积分饱和/诊断；它不再代表精确fraction。精确fraction以execution_target.fraction与execution_fraction为准；load/height/heave提交及独立审计必须使用同一fraction。非execution事务继续2**(-index)。已有独立完整重放绑定fraction，篡改fraction必须失败。新指纹v23-backtrack-refinement，旧v22证据/代码归档保持。

不改PD、负载分配、heave、物理地形、速率、恢复与碰撞标准；不裁切关节、不改IK容差、不补不安全奖励。

## 验证

真实IK合成反例需从coarse .5提升到>.5，保持maxdq<=.05；四帧冻结复算验证实际命令高度变化。批量混合满步/拒绝/细化、回调拒绝、无解、浮点32/64、原子提交与单次缩放均覆盖。完整相关回归与一次独立最终审查后，SHA部署隔离candidate，确认GPU无进程，仅唯一4env实际10cm探针；记录所有失败/成功、视频/载荷/净空/落轮恢复，完整归档。无真实完整成功则目标OPEN。

自审：精确fraction消费者全部列出；不把coarse_index当小数步长；不承诺全局最优；12次每PIpass、最多24次每事务；费用增加作为隔离实验可接受。
