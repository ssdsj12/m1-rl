"""Producer provenance cannot select an ambient device or bypass certification."""
import copy
import json
from dataclasses import asdict

import pytest
import torch

from test_m1_teacher_probe_contract import probe,episode,transaction_fixture,real_video_files,verify_episode
from ame_baseline.m1_reference_teacher import TeacherConfig


def metadata():
    module=probe()
    if hasattr(module,'capture_producer_backend'): return module.capture_producer_backend('cpu')
    return dict(device='cpu',origin='producer_tensor_device_and_runtime_math_settings',
        torch_version=str(torch.__version__),cuda_version=torch.version.cuda,device_name='cpu',
        matmul_allow_tf32=bool(torch.backends.cuda.matmul.allow_tf32),
        float32_matmul_precision=torch.get_float32_matmul_precision())


@pytest.mark.parametrize('change',[
    lambda m:m.update(device='cuda:99999'),
    lambda m:m.update(torch_version='different producer'),
    lambda m:m.update(matmul_allow_tf32=not m['matmul_allow_tf32']),
])
def test_sample_cannot_elect_backend_or_spoof_runtime_source(change):
    sample=episode()['samples'][2]; sample['producer_backend']=metadata(); change(sample['producer_backend'])
    assert probe().verify_feedback_transaction(sample,TeacherConfig()), 'untrusted provenance must not be ignored'


def test_context_none_does_not_bypass_backend_provenance():
    from test_m1_teacher_probe_contract import no_transaction_diagnostic
    sample=dict(feedback_context=None,teacher_valid=False,teacher_diagnostic=no_transaction_diagnostic(),
        producer_backend={**metadata(),'device':'cuda:99999'})
    sample['teacher_diagnostic']['reference_valid']=0
    assert probe().verify_feedback_transaction(sample,TeacherConfig())


def test_record_and_sample_backend_mismatch_rejects_episode():
    record=episode(); record['producer_backend']=metadata()
    for sample in record['samples']: sample['producer_backend']=metadata()
    record['terminal']=copy.deepcopy(record['samples'][-1])
    record['samples'][2]['producer_backend']['float32_matmul_precision']='forged'
    checked=verify_episode(record)
    assert checked['errors'] and not checked['success'] and not checked['student_demonstration_usable']


def test_explicit_cpu_tensor_creation_does_not_change_default_device(monkeypatch):
    sample=episode()['samples'][2]; module=probe()
    module.replay_feedback_transaction.cache_clear(); module.decoded_request_targets.cache_clear()
    original=torch.tensor; devices=[]; ambient=torch.get_default_device()
    def tensor(*args,**kwargs):
        devices.append(str(kwargs.get('device')))
        return original(*args,**kwargs)
    monkeypatch.setattr(torch,'tensor',tensor)
    monkeypatch.setattr(torch,'set_default_device',lambda *_:pytest.fail('global device change'))
    assert module.verify_feedback_transaction(sample,TeacherConfig(),replay_backend='cpu')==[]
    assert devices and set(devices)=={'cpu'}
    assert torch.get_default_device()==ambient


def test_explicit_cpu_ignores_ambient_default_device_without_changing_it():
    sample=episode()['samples'][2]; module=probe()
    module.replay_feedback_transaction.cache_clear(); module.decoded_request_targets.cache_clear()
    with torch.device('meta'):
        assert torch.empty(()).device.type=='meta'
        assert module.verify_feedback_transaction(sample,TeacherConfig(),replay_backend='cpu')==[]
        assert torch.empty(()).device.type=='meta'
        replay_hits=module.replay_feedback_transaction.cache_info().hits
        decoder_hits=module.decoded_request_targets.cache_info().hits
        assert module.verify_feedback_transaction(sample,TeacherConfig(),replay_backend='cpu')==[]
        assert module.replay_feedback_transaction.cache_info().hits==replay_hits+1
        assert module.decoded_request_targets.cache_info().hits==decoder_hits+1
        assert torch.empty(()).device.type=='meta'


@pytest.mark.parametrize('which',['replay','decoder'])
def test_local_backend_guard_restores_ambient_on_exception(monkeypatch,which):
    module=probe()
    def failed(*_):
        assert torch.empty(()).device.type=='cpu'
        raise RuntimeError('controlled math failure')
    target='_cached_replay_feedback_transaction' if which=='replay' else '_cached_decoded_request_targets'
    monkeypatch.setattr(module,target,failed)
    with torch.device('meta'):
        with pytest.raises(RuntimeError,match='controlled math failure'):
            if which=='replay': module.replay_feedback_transaction('{}','{}','float32',0,replay_backend='cpu')
            else: module.decoded_request_targets((),(),'float32',replay_backend='cpu')
        assert torch.empty(()).device.type=='meta'


def test_replay_cache_separates_math_modes(monkeypatch):
    module=probe(); tx=transaction_fixture(); cfg=json.dumps(asdict(TeacherConfig()),sort_keys=True)
    args=(json.dumps(tx['context'],sort_keys=True),cfg,'float32',0)
    module.replay_feedback_transaction.cache_clear(); module.replay_feedback_transaction(*args)
    first=module.replay_feedback_transaction.cache_info()
    original=torch.get_float32_matmul_precision()
    monkeypatch.setattr(torch,'get_float32_matmul_precision',lambda:'high' if original!='high' else 'highest')
    module.replay_feedback_transaction(*args)
    assert module.replay_feedback_transaction.cache_info().misses==first.misses+1


def test_missing_trusted_cuda_rejects_without_cpu_fallback(monkeypatch):
    module=probe(); sample=episode()['samples'][2]
    sample['producer_backend']={**metadata(),'device':'cuda:0'}
    monkeypatch.setattr(torch.cuda,'is_available',lambda:False)
    errors=module.verify_feedback_transaction(sample,TeacherConfig(),replay_backend='cuda:0')
    assert errors and any('backend' in error for error in errors)


def test_required_provenance_cannot_be_omitted_even_on_abort():
    module=probe(); record=episode(); record.update(end='teacher_nonexecutable',samples=[],terminal=None)
    checked=module.verify_episode(record,replay_backend='cpu',require_backend_evidence=True)
    assert any('backend' in error for error in checked['errors'])


def test_explicit_cpu_still_rejects_forged_diagnostic_and_actual_action():
    module=probe(); original=episode()['samples'][2]; original['producer_backend']=metadata()
    assert module.verify_feedback_transaction(original,TeacherConfig(),replay_backend='cpu')==[]
    for change in (
        lambda s:s['teacher_diagnostic'].update(accepted_q_5=.1),
        lambda s:s['teacher_action'].__setitem__(0,.01),
        lambda s:s['applied_targets'].__setitem__(0,.01),
    ):
        sample=copy.deepcopy(original); change(sample)
        assert module.verify_feedback_transaction(sample,TeacherConfig(),replay_backend='cpu')


@pytest.mark.parametrize('scenario',['prepared','bad-evidence','abort-0'])
def test_native_finish_gate_rewrite_and_suite_pass_trusted_backend(tmp_path,monkeypatch,scenario):
    from test_m1_teacher_probe_contract import diagnostic_runner
    module=probe(); run=diagnostic_runner(tmp_path,monkeypatch,scenario)
    original=module.verify_episode; calls=[]
    def checked(record,**kwargs):
        calls.append(kwargs)
        assert kwargs==dict(replay_backend='cpu',require_backend_evidence=True)
        assert record['producer_backend']==run.producer_backend
        assert all(s['producer_backend']==record['producer_backend'] for s in record['samples'])
        return original(record,**kwargs)
    monkeypatch.setattr(module,'verify_episode',checked)
    run.teacher(acceptance=False,diagnostic_steps=8,scope='flat-preparation')
    assert calls
    result=json.loads((tmp_path/'result.json').read_text())
    if scenario=='prepared': assert not result['diagnostic_stopped']
    else: assert result['diagnostic_stopped']


def test_native_missing_sample_provenance_fails_gate_without_repair(tmp_path,monkeypatch):
    from test_m1_teacher_probe_contract import diagnostic_runner
    module=probe(); run=diagnostic_runner(tmp_path,monkeypatch,'prepared')
    original=run.action_evidence.row
    def missing(*args):
        sample=original(*args); sample.pop('producer_backend'); return sample
    monkeypatch.setattr(run.action_evidence,'row',missing)
    run.teacher(acceptance=False,diagnostic_steps=8,scope='flat-preparation')
    result=json.loads((tmp_path/'result.json').read_text())
    assert result['diagnostic_stop']['reason']=='evidence_invalid'
    record=json.loads(next(tmp_path.glob('stage*.json')).read_text())
    assert all('producer_backend' not in s for s in record['samples'])
    assert any('backend' in e for e in record['verification']['errors'])


def test_cpu_legacy_compatible_but_native_strict_suite_rejects_missing_metadata():
    module=probe(); record=episode()
    assert module.verify_episode(record)['errors']==[]
    legacy=module.verify_suite([record],diagnostic=True)
    assert legacy['stage3_success']==1 and legacy['complete_episodes']==1
    checked=module.verify_suite([record],diagnostic=True,replay_backend='cpu',require_backend_evidence=True)
    assert checked['milestone_a']=='FAILED_DIAGNOSTIC'
    assert checked['stage3_success']==0 and checked['complete_episodes']==0


def test_replay_cache_backend_key_is_distinct_without_allocating_cuda(monkeypatch):
    """Pure cache-key routing test; real CUDA arithmetic is checked separately."""
    module=probe(); seen=[]
    original=module.capture_producer_backend
    def captured(device):
        return {**original('cpu'),'device':device}
    def replay(*args):
        seen.append(args[-2:]); return ('{}',(),False)
    monkeypatch.setattr(module,'capture_producer_backend',captured)
    monkeypatch.setattr(module,'_cached_replay_feedback_transaction',replay)
    module.replay_feedback_transaction('{}','{}','float32',0,replay_backend='cpu')
    module.replay_feedback_transaction('{}','{}','float32',0,replay_backend='cuda:0')
    assert seen[0]!=seen[1]
    assert [key[0] for key in seen]==['cpu','cuda:0']
