"""Read-only native initialization control; source chosen by PYTHONPATH."""
import argparse
import faulthandler
from isaaclab.app import AppLauncher

parser=argparse.ArgumentParser(description=__doc__)
AppLauncher.add_app_launcher_args(parser)
args=parser.parse_args()
launcher=AppLauncher(args)
env=None
try:
    from isaaclab.envs import ManagerBasedRLEnv
    from ame_baseline.m1_ame_env_cfg import M1AmeCrossLargeComplexEnvCfg
    from ame_baseline.m1_mixed_course import configure_flat_first_terrain
    import ame_baseline.m1_ame_env_cfg as source
    print('INIT_SOURCE '+source.__file__,flush=True)
    cfg=M1AmeCrossLargeComplexEnvCfg();configure_flat_first_terrain(cfg)
    cfg.scene.num_envs=4;cfg.sim.device=args.device;cfg.seed=7
    trace=open('/tmp/m1-reference-init-stacks.log','a')
    faulthandler.dump_traceback_later(30,repeat=True,file=trace)
    env=ManagerBasedRLEnv(cfg=cfg)
    print('INIT_CONTROL_COMPLETE',flush=True)
except BaseException:
    import traceback
    traceback.print_exc()
    raise
finally:
    faulthandler.cancel_dump_traceback_later()
    if env is not None:env.close()
    launcher.app.close()
