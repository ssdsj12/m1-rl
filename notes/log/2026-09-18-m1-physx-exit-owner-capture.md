# M1 run10: native exit owner identified

## 本次结论（当前状态）

- 已完成用户批准的隔离定位方案 A；定位到 `_physx` 的 replicator attach 返回列表被保存在 C++ 静态对象中，在 Python 已关闭后才析构。
- run10 的 8 env × 32 steps 全部执行完成，随后关闭阶段原生退出 134；GDB shell 返回 0 不能当作子进程成功。**根因定位完成，修复尚未通过。**
- 独立诊断测试 22 项、复制 adapter 测试 170 项通过；规格和质量审查通过。它们不替代实际正常退出或跨越行为验收。
- 正式 adapter、amp/SDK/驱动、参考源码与 15GB 占位进程均未改动。两个诊断进程自然结束，没有自动重启。
- 下一步候选是在新进程、场景创建前设置 `replicate_physics=False`，用普通克隆路径做隔离 8×32 对照；当前等待用户选择，尚未实施。需检查正常退出、场景几何、关节/刚体绑定与显式碰撞过滤，不能仅凭 exit0 认定物理行为等价。
- 这是针对 SDK 生命周期缺陷的受支持路径规避，不是 SDK 二进制修复；启动耗时和内存可能增加。3 次 8×1600 严格验收之前不进入 1024 env；未启动 10000 轮训练。
- 历史长训中途退出不能仅凭本次 post-close 栈归为同一原因。

`replicate_physics` 是 [Isaac Sim 4.5 公开支持的参数](https://docs.isaacsim.omniverse.nvidia.com/4.5.0/py/source/extensions/isaacsim.core.cloner/docs/index.html#isaacsim.core.cloner.Cloner.clone)。事后 unregister 或删除 Python interface 缓存不会清除已经初始化的 C++ 静态列表。

## Purpose / Stage / Todo

T306.6h.5c.1: execute approved isolated routeA, identify the native callback in the cache-off09 failure without modifying amp/SDK/production adapter. User continuedimplementation. [Design](../../docs/superpowers/specs/2026-09-18-m1-native-exit-owner-design.md),[plan](../../docs/superpowers/plans/2026-09-18-m1-native-exit-owner.md).

## Implementation / CPU verification

Separate toolroot `/home/hexinkun/m1_debug_tools/gdb-jammy/exit_owner_20260918`; copied baselineadapter supportfiles plus four exact archivedcacheofffiles. Productiondiffagainstb60ca0f remainszero. New opt-in__cxa_atexitregistrationandcurrent-libc-callsite tracing, bounded ledger,per-threadnestedinvocations,event-timeowner,late symbolresolution. LoadedlibcBuild-ID andcall/returnopcodes validated. No targetfunctioncalls/registerwrites/signal suppression.

TDD RED confirmedmissingtracer,returnopcodeguard,independentinvocationowner,snapshotfailurepersistence; GREEN21agenttests17.377s. Main independent22tests17.471s,thenpersistedraw`cpu-tests.log`22tests18.161s,allpass. Includes10ledger,5nativefixture,6existingcapture,1launcher. Separatecopiedadapter suite170passed23.64s. Spec andqualityreviewsAPPROVE; limitationsdocumentedbelow.

Frozen hashes:

```text
capture_gdb.py         339210ff1ec3b215fc7bf054a72a1c42b34be452bad9bbebc55c223852909e26
exit_callbacks.py      11ec30a2443d8102b44ee5606581af283644302a25d0bbfbaac45b06c111c23b
test_exit_callbacks.py 9c2f0c0d5145ca038935214c5c909a08b19dfd78c65fd276cee42e4f6d37ab6c
exit_owner_fixture.c  e697607ae9bb9390c1b18fa57c28f2853f23a640d3d9870ccc53943b135c407b
test_exit_owner_gdb.py d7fffb85832da99b3c53e05b602e1492c1ead0a32fc3c73ea87f294ceb23759a
```

## Real run conditions / result

Command:`bash /home/hexinkun/m1_debug_tools/gdb-jammy/exit_owner_20260918/run_exit_owner_gdb.sh /home/hexinkun/m1_rl/run_logs/m1_reference_validation/20260918_gpu7_8x32_10_exit_owner`.

One ownchildPID3297237,GDB3297107,startticks149690210. ampPython3.10.21,physicalGPU7UUID46a1bc7e-093f-ab76-2bf1-35b0ae1fd66e,8env32steps; samecacheoffeffectivefalse/standardimportlibhook as09,fast_shutdownFalse. Outputprefix`run_logs/m1_reference_validation/20260918_gpu7_8x32_10_exit_owner`; sibling.log,.gdb.json,.summary.json. Logs40MB/report92MB retainedremotely; compactsummarycopiedlocally.

Full32steps+32prepare/IK in130.8837449s underheavydebuginstrumentation. runID3c60b94f-47df-4b60-ae8a-dab50b84ee6c. AllENV_CLOSED/LAUNCHER_OWNERS_DETACHED/RUNTIME_REFS_RELEASED/APP_CLOSED/POST_CLEANUP markersoccurbeforeabort. Nativeexit134(SIGABRT),GDBshell0; confirmednativeexittrue,tracecompleteTrue,noerrors/nooverflow. Noacceptancefinalizerinvoked; diagnosticisnotstartupPASS.

53,562registrations,294invocations. Soleunreturnedinvocation294(thread1:1,status0)callback`0x7f6db46ef080`,arg`0x7f6db4971d70`;uniquehistoricalmatchregistration53235,callerreturnPC`0x7f6db46ed4ed`,DSOhandle`0x7f6db495c220`. Bothregistrationandinvocationevent-timeowner areinstalled`isaacsim/extsPhysics/omni.physx/omni/physx/bindings/_physx.cpython-310-x86_64-linux-gnu.so`.

Librarymappingbase`0x7f6db4600000`:callbackoffset0xef080,registrationreturn0xed4ed,staticarg0x371d70. Finalstack:Py_Exit(0)→libcexit→list_dealloc(object0x7f6fb2f8bc80)→PyThreadState_Get(NULL)→abort. Symbolsstripped; conclusionusesobservedowner/mapping/calladdresses,notguessednames.

Bothownprocessesendednaturally, no signalsfromagent. Protectedreservation2795762survives; GPU7returns15754used/8328freeMiB0%. NootherIsaacrunorlongtrain.

## Binary and source root-cause investigation

Readonlyobjdumpconfirms+0xef080dereferencesarg, decrementsPyObjectrefcount andtail-jumps_Py_Deallocwhenzero. Registrationat+0xed4e8 calls__cxa_atexit withthatcallbackandstatic.bssslot+0x371d70;return+0xed4edmatchescaptureexactly. Guard+0x371d68 initializesaPythonlistonce. Function+0xed1e0 readsPyList_Size/GetItem→SdfPath; pointerxref+0xeca73 belongsIPhysxReplicator.register_replicator wrapper+0xee750 anditslist-returningattachcallback. Unregisteronlyerasesstagecallbacks,notthestaticslot.

Currentdisk_physx SHA2562e88c44ddec4e9b76f2b8b2b520a003cd19e3466ede7b7db7402825ce731f420,Build-ID7983b02e485fb76d9f7624f13acccc3403ffed52,mtime/ctime2026-09-16beforecapture. Runtime_physxBuild-IDwasnotcaptured; donotclaimhistoricalbyte-for-bytehashproof. Runtimeowner/mapsandoffset-correspondingdiskinstructionsaretheevidence.

Official107.3source has`replicatorAttachGlobal`withfunction-staticPythonlistinitializedfromattachcallback,usedforSdfPathconversion. `unregister_replicator`onlyerasescallbackmap;`release_physx_replicator_interface_scripting`onlyreleasesaCarboniteinterfaceclient. [NVIDIA source](https://raw.githubusercontent.com/NVIDIA-Omniverse/PhysX/107.3-omni-and-physx-5.6.1/omni/extensions/runtime/source/omni.physx/bindings/BindingsPhysXReplicator.cpp). Thisisacross-versionmechanismreference,corroboratedbyinstalled106.5.7binary,notaclaim107.3sourceistheinstalledsource.

InstalledCloner.replicate_physicsregistersattachcallbackreturning[clone_root]. IsaacLabInteractiveScenewithreplicate_physicsTrueinvokesthatpath;Falseusesnormalper-objectcloningandcollisiongroupfilteringinstead. A supportedreversiblecandidateistoavoidthisfastreplicationpathintheisolatedadapter; itmaychangestartuptime/memoryandrequiresgeometry/collision/sourcechecks. NoSDKbinaryorprivatepointerpatchisproposed. ThisisaworkaroundforSDKlifetimebug,notproofSDKbinaryisrepaired.

## Follow-up / limitations / refs

NewT306.6h.5c.2: proposedisolatedcacheoff+replicate_physicsFalse8×32A/B;awaitinguseransweratthetimeofthischeckpoint. Noimplementationofthecandidateyet. Onlythisflagwouldvaryfromrun08/10; mustlogactualconfigurationdiff andchecknormalnative0withoutdebuggerbeforeanyintegration.

Diagnosticperformance: symbolizingall53kregistrationsdelayedfatalreportandmadeitlarge, butcompletedwithin4minuteswithcompleteevidence. Futureruns,ifneeded,shouldpersistrawledgerfirstandresolveonlyactivecallback/registrationmatchesoffline; thisperformancechangehasnotbeenimplemented. MatchingIDsarehistoricalcandidates,notuniversallyuniqueowners; thisrunhasonecandidateandcorroboratingbinary/sourcechain.

Shutdownfailureafterrequested32stepsisnotaprematuretrainingiterationstop. Existing120/1000completionsdonotestablish10000; nolearning/crossing/avoidanceclaims. Lastacceptedproductionfeatureb60ca0f,design6addb50,onlyisolateddiagnostictoolsadded. [Branch](../todo/T306-m1-ame-long-train-stability.md).
