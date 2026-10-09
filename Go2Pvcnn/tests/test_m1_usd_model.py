"""Authored USD extraction must match the previously audited inventory."""
import ast
import contextlib
import importlib
import io
from pathlib import Path
import runpy
import pytest


def test_source_model_matches_audited_inventory():
    pytest.importorskip('pxr.Usd')
    package=Path(__file__).parents[1]
    source=package.parent/'m1/ZJ_V3_URDF_V1_0/ZJ_V3_URDF_V1_0.usd'
    with contextlib.redirect_stdout(io.StringIO()):
        inv=runpy.run_path(str(package/'scripts/inspect_m1_mass_tree.py'))
    expected=dict(root='BASE_LINK',bodies=[{k:b[k] for k in ('name','mass','com')} for b in inv['bodies']],joints=[])
    for j in inv['joints']:
        if j['type']=='PhysicsRevoluteJoint':
            expected['joints'].append(dict(name=j['name'],parent=j['parent'][0].split('/')[-1],
                child=j['child'][0].split('/')[-1],pos0=j['pos0'],pos1=j['pos1'],
                rot0=list(ast.literal_eval(j['rot0'])),rot1=list(ast.literal_eval(j['rot1'])),axis=j['axis']))
    load=getattr(importlib.import_module('ame_baseline.m1_mass_predictor'),'load_usd_model')
    actual=load(str(source))
    assert actual['root']==expected['root'] and actual['bodies']==expected['bodies']
    assert len(actual['joints'])==len(expected['joints'])
    for got,want in zip(actual['joints'],expected['joints']):
        for key in got:
            # Gf's inventory string truncates quaternion components.
            if key in ('rot0','rot1'):assert got[key]==pytest.approx(want[key],rel=0.,abs=1e-10)
            else:assert got[key]==want[key]
