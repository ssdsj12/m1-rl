import importlib.util
from pathlib import Path
import copy
import numpy as np
import pytest
from scipy.spatial.transform import Rotation


def implementation():
    path = Path(__file__).parents[1]/'ame_baseline/m1_wbc_kinematics.py'
    assert path.exists(), 'kinematic acceleration bias adapter missing'
    spec = importlib.util.spec_from_file_location('bias', path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod.kinematic_bias


def fixture():
    return dict(root='base', bodies=[dict(name=n, com=c) for n,c in
        [('base',[.03,-.02,.04]),('a',[.08,.01,.02]),('b',[.02,-.03,.07])]],
        joints=[dict(name='j0',parent='base',child='a',pos0=[.2,.04,.02],
            pos1=[.01,.03,-.04],rot0=[1.,0,0,0],rot1=[1.,0,0,0],axis='Y'),
            dict(name='j1',parent='a',child='b',pos0=[.06,-.07,.1],
            pos1=[.02,0,-.06],rot0=[1.,0,0,0],rot1=[1.,0,0,0],axis='X')])


def poses(model, t, speed=1.):
    # Independent FK oracle, with constant root COM velocity/world angular
    # velocity and joint velocities: generalized qdd is exactly zero.
    w0=np.array([.2,-.3,.4])*speed
    qd=np.array([.7,-.5])*speed
    rootR=Rotation.from_rotvec(w0*t).as_matrix()@Rotation.from_euler('xyz',[.1,.2,-.3]).as_matrix()
    rotations={'base':rootR}; angular={'base':w0}
    origins={'base':np.array([.4,.3,.5])+np.array([.1,.02,-.03])*t-rootR@model['bodies'][0]['com']}
    for idx,j in enumerate(model['joints']):
        rp=rotations[j['parent']]
        r0=Rotation.from_quat(np.roll(j['rot0'],-1)).as_matrix()
        r1=Rotation.from_quat(np.roll(j['rot1'],-1)).as_matrix()
        axis=np.eye(3)['XYZ'.index(j['axis'])]
        rc=rp@r0@Rotation.from_rotvec(axis*([.3,-.2][idx]+qd[idx]*t)).as_matrix()@r1.T
        rotations[j['child']]=rc
        origins[j['child']]=origins[j['parent']]+rp@j['pos0']-rc@j['pos1']
        angular[j['child']]=angular[j['parent']]+rp@r0@axis*qd[idx]
    names=[b['name'] for b in model['bodies']]
    centers=np.array([origins[b['name']]+rotations[b['name']]@b['com'] for b in model['bodies']])
    return centers,np.array([rotations[n] for n in names]),np.array([angular[n] for n in names]),qd


@pytest.mark.parametrize('rotated_frames',[False,True])
def test_bias_matches_independent_second_difference(rotated_frames):
    fn=implementation(); m=fixture()
    if rotated_frames:
        for j in m['joints']:
            j['rot0']=np.roll(Rotation.from_euler('xyz',[.2,.4,-.1]).as_quat(),1).tolist()
            j['rot1']=np.roll(Rotation.from_euler('xyz',[-.3,.2,.1]).as_quat(),1).tolist()
    c,r,w,qd=poses(m,0.); h=1e-4
    expected=(poses(m,h)[0]-2*c+poses(m,-h)[0])/h**2
    result=fn(m,['j0','j1'],['base','a','b'],r,w,qd)
    np.testing.assert_allclose(result['com_linear'],expected,atol=2e-6,rtol=0)
    np.testing.assert_allclose(result['com_linear'][0],0.,atol=1e-12)
    offset=r[0]@m['bodies'][0]['com']
    np.testing.assert_allclose(result['origin_linear'][0],-np.cross(w[0],np.cross(w[0],offset)),atol=1e-12)


def test_names_permute_without_changing_result():
    fn=implementation(); m=fixture(); _,r,w,qd=poses(m,0.)
    a=fn(m,['j0','j1'],['base','a','b'],r,w,qd)
    p=[2,0,1]
    b=fn(m,['j1','j0'],['b','base','a'],r[p],w[p],qd[::-1])
    for key in ('origin_linear','com_linear','angular'):
        np.testing.assert_allclose(b[key],a[key][p],atol=1e-12)


def test_zero_velocities_have_zero_bias():
    fn=implementation(); m=fixture(); _,r,w,qd=poses(m,0.,speed=0.)
    a=fn(m,['j0','j1'],['base','a','b'],r,w,qd)
    for key in ('origin_linear','com_linear','angular'):
        np.testing.assert_allclose(a[key],0.,atol=1e-12)


@pytest.mark.parametrize('fault',['nan','frame','duplicate','cycle','velocity','quaternion'])
def test_invalid_state_rejected(fault):
    fn=implementation(); m=copy.deepcopy(fixture()); _,r,w,qd=poses(m,0.)
    names=['base','a','b']
    if fault=='nan': qd[0]=np.nan
    elif fault=='frame': r[0,0,0]=3.
    elif fault=='duplicate': names[2]='a'
    elif fault=='cycle': m['joints'][0]['parent']='b'
    elif fault=='velocity': w[2,0]+=.1
    else: m['joints'][0]['rot0']=[0.,0,0,0]
    with pytest.raises(ValueError): fn(m,['j0','j1'],names,r,w,qd)
