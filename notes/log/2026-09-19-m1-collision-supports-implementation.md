# M1 完整碰撞盒逐刚体变换实施

2026-09-19；T306.6h.6a.1a.2c，G0-B2a纯NumPy数学核。基线0196f6f，计划2b67905。此次不是实际query绑定或离开/再次跨越验收。

## 输入、范围和方法

延续`codex/m1-encounter-lifecycle`隔离worktree。仅新增`collision_supports.py`与`tests/test_collision_supports.py`；原adapter/runtime/SDK/资产不动。`make_body_supports`把每个collider-local有限AABB全部8角点用完整column affine转到own-body；`world_support_points`依据明确body名映射与全部body世界矩阵生成(N,C,8,3)，不把root位姿套给腿，不积累时间历史。

计划明确bounds/shape/name/finite/positive determinant/affine末行校验、noalias和计算overflow拒绝。通过此数学核不能证明query来源：后续B2b必须绑定实际stage/path/完整回调/settings/generation和逐body实际pose。B1 authored bounds禁止在现场当作失败query的fallback。

## TDD过程

实现者复用完成的有界代理，fresh spawn受threadlimit；main并行只读SDK接入审计。先2例assert缺模块RED（无collection error）→最小两级变换2 passed0.18s。扩展边界组51 failed/54 passed0.50s，真实RED包括nonaffine/reflected/singular/empty/badbodymapping/overflow漏拒，以及badshape/name错误类型。32组独立逐点oracle、45度双对角点反例、N1/N1024全17body及rear未离开负例通过；正在补严格校验，尚非最终通过。

第一实现提交3a1d25f，105passed0.52s；main独立105passed0.53s。主代理额外实际复现：外部np.errstate(all='raise')时三轴scale1e-200导致det下溢，两入口均抛FloatingPointError而非ValueError。两个用例先RED，再以局部under='ignore'并继续finitepositive检查使det0仍明确ValueError；未改变全局np策略。同时将1024/17body用例增强为逐body不同rotation+translation及独立逐角点oracle。修复提交`c12e0af04e6c74a09985344fb3b322b1d8cf9ae0`，107passed0.53s。

SPEC独立复审107passed0.54s，并补shear、两级affine/映射、degenerate/noalias及8项np.errstate(all='raise')上下溢/奇异/reflection检查，PASS。随后QUALITY独立107passed0.50s，补shear/不同env-body-collider/非本机字节序/非连续只读输入检查，PASS，无未解决Critical/Important/Minor。

主代理最终完整回归 **1020 passed140.58s，exit0、0skip**（506旧+323A1+84B1+107B2a）。因此本包数学核完成；这不关闭整个B2、G0或总体goal。下一实施包是非阻塞query回调完整性/身份collector、薄SDK绑定与geometry/settings失效监测，再用单独具名的8-env初始化诊断核验真实query及不推进physics的等待路径；诊断不抵扣新候选三次8×1600。

focused命令为[计划](../../docs/superpowers/plans/2026-09-19-m1-collision-supports.md)内amp Python、CPU-only、无bytecode/noautoplugin、OMP/OPENBLAS1、现有pxr库路径、TMPDIR=/data；不安装包。全量唯一新basetemp=`/data/hexinkun-m1-acceptance-20260918/encounter-supports-full`，不覆盖旧fixture。

## 主代理实际USD独立数学验证

在amp、CUDA隐藏、已有pxr库环境，通过stdin脚本先执行旧audit_provenance，再打开原m1_floating overlay。B1采集17body/17collider；只在本CPU数学测试中将mesh authored bounds及Cylinder轴/radius/height盒输入B2a。body世界变换直接从各自USD prim的LocalToWorld取，collider→body来自B1，输出(1,17,8,3)/float64共136角点。另逐collider用Gf.BBox3d(localrange,collider LocalToWorld).ComputeAlignedRange独立算range，与新两级变换每轴min/max比较：**17/17通过、max_abs_error=0、exit0**。来源guard、layerdirty前后不变及无torch/omni导入同时PASS。

该记录明确`evidence_status=authored_bounds_math_only`、`physical_geometry_verified=false`；绝不是把source盒升级成实际query证明。B2b尚需每env的静态shape绑定；B2a跨N共享(C,8,3)支持点之前，provider必须证明各env staticgeometry等价，否则逐env调用，不能默认为等价。

bash-n、git diff --check，以及排除六个新增文件/cache后的冻结adapter diff均PASS。最新只读资源：根盘4.1GiB、/data6.5TiB，GPU7唯一占位351307仍原start23:05:13/15744MiB；未清理/迁移缓存或修改设备进程。

## 后续实际pose来源核对

主代理经amp editable finder确认isaaclab来自`/home/hexinkun/IsaacLab45/source/isaaclab/isaaclab`，不是猜测的`IsaacLab`目录。`assets/articulation/articulation_data.py:554–574`从root PhysX view读取get_link_transforms并将xyzw转成wxyz，body_link_pose_w是actor/link frame而非COM；:1027–1034旧body_pos_w/body_quat_w只是对应alias。`omni.physics.tensors/.../impl/api.py:622–643`的prim_paths/link_paths可绑定真实articulation/link路径。B2b必须检验这些实际路径/顺序，不能只凭相同名称假定env绑定；body世界scale与tensor rigid pose的对应也必须核验，不能漏掉或重复计算scale。

GPU7原占位保留，没有新增Isaac/8-env/1024-env训练或验证。完整G0其余组件、三次新8×1600→1024×32→1024×1600、G2实际再遇障以及AME/learned/10000均仍待完成。

关联：[B1完成](2026-09-19-m1-collision-inventory-implementation.md)、[query合同与异步边界](2026-09-19-m1-collision-query-contract.md)、[T306](../todo/T306-m1-ame-long-train-stability.md)。
