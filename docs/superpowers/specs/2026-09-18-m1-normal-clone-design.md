# M1 普通复制路径隔离验证设计

用户在获知 run10 的 `_physx` 静态 Python 列表析构根因及候选代价后，回复“继续”，批准隔离 `replicate_physics=False` 对照。此文件固化已经确认的设计，不扩大范围。

## 方案与范围

在独立 `/home/hexinkun/m1_debug_tools/gdb-jammy/normal_clone_20260918/adapter` 复制 run10 的 cache-off adapter。场景创建前唯一新增配置差异为 `scene.replicate_physics=False`，绕开已确认的错误 attach 回调静态列表初始化。使用受支持的普通 USD 复制与逐对象物理解析，不修改 SDK 二进制。

替代方案是查找并验证兼容 SDK 版本；本轮用户选择先测试更小的复制路径切换，不执行升级。普通复制可能增加启动时间和内存，不预设与快速复制数值行为完全相同。

## 验证契约

1. amp Python、物理 GPU7、8 env × 32 steps；保留占位 PID2795762。正式 adapter 与参考 `/home/hexinkun/m1` 只读。
2. 先 CPU 配置与 USD fixture RED/GREEN，再独立规格/质量审查，然后主代理无 GDB 实测。
3. 原有奖励、控制器、随机化、机器人、容差和退出判定不变；保留 cache-off、fast_shutdown=False 和真实原生退出码。
4. 新增只读实际 collision-group 图、collection 关系与横杆 membership 证据；环境分组与 ground/global 连通图必须符合已安装 Cloner 的 false 路径。
5. 横杆位于 semantic_course 而不在 env/ground 子树；如其未入组，必须如实记录，不伪称已经证明 own-bar 专属碰撞隔离。8m 间距和零 foreign force 不是有接触机会的动态过滤验证。
6. 同时核验原有 17 body/16 joint 浮动 M1、scene geometry、源绑定、32 样本、prepare/IK 次数和 native/wrapper=0。与 run10 比较初始状态、几何和配置差异。
7. 失败保留现场并停止扩大；短 smoke 成功也不能当作 1600 步跨越或 10000 轮训练成功。正式接入不在本次隔离试验范围内。

## 输出与边界

输出目录前缀 `run_logs/m1_reference_validation/20260918_gpu7_8x32_11_normal_clone`，日志和 JSON 保留真实失败结果。没有自动重启、进程信号、SDK 安装、阈值放宽或 checkpoint 续训。本次结论和未验证项写入 T306.6h.5c.2、dashboard、日志索引。

自审：无占位项；与用户已批准的 run10 后续候选一致；只读证据不会修改场景。源码机制参考与实际运行结果分开陈述。
