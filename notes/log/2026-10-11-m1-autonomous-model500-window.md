# 自主抬落新run：model500完整窗口

2026-10-11 08:57 UTC；Parent [T306](../todo/T306-m1-ame-long-train-stability.md)，
pure-ppo-learning/forward-progress-regression/autonomous-run-window OPEN。

## 方法和输入

现场finalize脚本verify核对PID7960/cwd/参数；读取stdout与TB原始scalar，
torch.load(map_location='cpu')读取15-51-33/bb57e7d/model_500.pt。
这是新run500，不是已删除的旧500。未停训、未改生产、未并发native。

## 结果

- stdout548/TB549，2048env，optimizer1/save100，从指定18-49-19/model300开始。
- 544–548 value loss .1315/.1315/.14/.1361/.1287，surrogate有限。
- 新run保存400和500，各5911019字节；500 iter500/next501，模型tensor全部有限。
- 500课程stage1/streak0/pending0；PT.last完整2048回合pass_rate=0，
  velocity_error=.30008805895776525，strict_attempts=1376，strict_successes=0。
  不是stdout部分窗口sample_count=34.1的推断。
- TB301–549：>=2cm预抬仅321轮1次；stable_landings、strict_successes全0。
  连续抬轮增量156轮为正，合计.0024732593994940544（归一化量，非米）；
  最后非零539轮1.7563888832228258e-6，四位打印0不等于原值0。
- stdout548存在低净空重叠样本min_bottom_clearance=-.0350m。

## 结论和后续

新run完整窗口前进未通过，尚未形成可验收跨越；汇总不能确定停滞/绕行/具体支撑失败。
旧700轨迹不可替代当前策略。用户长训优先保持，不盲改奖励/加轮数/自动停训。
持续问题先当前PT定位；原生追踪不得与22GB训练并发。本次未全量重验optimizer/std，
也没有视频姿态证据。奖励、地形、成功合同未变，GitHub发布状态未改变。

Baseline/HEAD 80818c3；Last Feature/Verified c7ed76f；Current Work codex/m1-ppo-repair-upload。
Key Files：当前run model_500.pt、训练log、TB事件。
