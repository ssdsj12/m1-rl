"""Isaac manager lifecycle adapter; raw collision remains a success veto."""
from isaaclab.managers import ManagerTermBase
from .m1_collision_budget import CollisionBudget, EPISODE_BUDGET, combine_collision_signals
from .m1_obstacle_rewards import m1_obstacle_collision_penalty, m1_non_support_obstacle_contact


class CollisionBudgetTermination(ManagerTermBase):
    def __init__(self, cfg, env):
        super().__init__(cfg, env)
        env_cfg = getattr(env, 'cfg', None)
        declared_budget = getattr(env_cfg, 'm1_collision_budget', EPISODE_BUDGET)
        if (isinstance(declared_budget, bool) or not isinstance(declared_budget, (int, float))
                or declared_budget != EPISODE_BUDGET):
            raise ValueError('m1_collision_budget must be 20')
        self.budget=CollisionBudget(env.num_envs,env.device,env.step_dt,
            cost_per_step=getattr(env_cfg, 'm1_collision_cost_per_step', None))
        env._m1_collision_budget=self.budget

    def __call__(self, env):
        if self.budget.step != env.common_step_counter:
            geometry=m1_obstacle_collision_penalty(env,strict_obstacle_contact=True)
            contact=m1_non_support_obstacle_contact(env)
            signal=combine_collision_signals(geometry,contact)
            self.budget.update(signal,env.common_step_counter)
        return self.budget.snapshot['exhausted'].clone()

    def reset(self, env_ids=None):
        self.budget.reset(env_ids)
