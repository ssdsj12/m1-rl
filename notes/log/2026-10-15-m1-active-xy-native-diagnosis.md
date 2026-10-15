# v34 实际10cm终态与支撑姿态搜索诊断

## 后续一致性冻结证据（当前最新）

只把dynamic goal替换为choice完整姿态仍不足：旧tracking-gated quaternion interpolation在130继续输出水平姿态。进一步在诊断进程内把选中姿态传递到requested（仍经原feedback/IK/backtrack/encode）后，固定roll=-.1/pitch=+.1/captured yaw候选得到6eligible，最弱预测46.75379N，事务valid、executionfraction1、maxdelta.03165758rad<.05。requested quaternion确实为[.99750191,-.04992082,.04991259,.00258021]而非level。原始输出SHA903ea5e3192ce229c9edbff6f5ceabf6d4f95a8b62136dc818f55217c1c08695，本地已下载。初始临时脚本缩进错误不计有效实验，修正后结果如上。

尚未改candidate/production，不宣称新轨迹或真实通过；不是建议跟随实际倾斜自动改目标。设计选择固定有界姿态集，与位置/IK/两套三轮预测共同筛选，保留原jointstep与安全/恢复标准；详见docs/superpowers/specs/2026-10-15-m1-bounded-crossing-attitude-design.md。当前goalturn为进展：排除候选与执行姿态不一致的假可行，并形成有界正式方案；下一写具体计划/TDD。

## 已核实终态

runner428984/native428986已退出，exit0只是诊断完成。result FAILED_DIAGNOSTIC：4记录、3完整失败、3锁定、0成功、full-denominator=false；env1 frame134 failure_locked，physical_failure=false，errors=[]。不得把未完成env0计为成功。原始目录、log、exit归档 `/tmp/m1-active-xy-v34-original-evidence.tar.gz`，本地 `.superpowers/sdd/2026-10-15-m1-active-horizontal-anchor/` 同名包，双方SHA `ba2001283bbc209910d865bdeef8280685ecef290179ffceb2f6d377ce3168db`。29帧10fps视频0/14/28已检查，未见完成跨越。地面材质MDL警告不是本次已证实物理失败原因。

## 修正有效但目标未达成

env1–3首次LIFT119：post活动轮XY与同帧实际位置一致，请求XY也一致；第119步执行比例.46875，第120步1。第120步活动轮完整执行目标比实测仅X后退.6084mm、Z高.1530mm（旧v33 X后退约39mm）。129目标X后退5.823mm、Z高1.5074mm；实际轮底仍约.00005m，未抬离地面。初始捕获偏差已消除，但不是充分修复。

130开始invalid reason5，134锁定；实际轮载未等同预测三轮可承载能力。不能称已经三轮抬腿成功，不能直接归因为电机饱和。候选所有Z、support动作限速和安全门槛未改。

## 冻结CPU候选过滤证据

脚本 `.superpowers/sdd/2026-10-15-m1-active-horizontal-anchor/candidate_failure.py`，服务器 `/tmp/m1-v34-candidate-failure.py`。只读同一原始pre/input，CPU无物理推进；原始与单变量输出已下载为m1-v34-candidate-original.jsonl、m1-v34-candidate-measured-orientation.jsonl。

原始frame130：126候选IK全部valid，但预测最弱三轮载荷最大29.26377N，0候选满足30N门槛。相同失败帧CPU外事务post_matches=true。119/125/129 CPU post_matches=false，不能称这些帧完整CPU/GPU复现；只报告候选计算，不忽略该限制。

单变量静态实验：仅把搜索的125个level候选四元数替成同帧measured四元数，位置4/6/8cm范围、IK和30N底线不变。frame130得到6个eligible候选，最大最弱预测载荷42.53421N。119/125/129对应最好值38.87424/41.22367/42.98419N。说明强制水平候选限制确实改变当前失败帧的支撑可行域，不是这一帧纯IK无解。

**重要限制：** 此实验未部署。生产动态goal仍沿用旧goal四元数，不能因实验外事务valid=true就称姿态选择与执行一致，更不能称物理跨越；每步追随实测倾斜可能掩盖失稳，不是可直接上线方案。下一工作应审查“支撑姿态候选—预测COM—真实执行请求—跨后恢复”的共同约束，允许用户已授权的适度倾斜但保留原物理安全门槛和独立证据。不要继续堆叠XY或PD修补，也不降低30N门槛。

## 状态与边界

上一goal turn为进展（Task2完成/部署）；本轮为进展（同PID终态、归档视频、候选失效层定位及单变量冻结证据）。目标仍active、未成功。没有生产训练、没有新native、没有删除PT、没有Git提交或上传；候选C保持v34，下一修改先设计与失败反例。
