import VM from 'scratch-vm';
import { ScratchStorage } from 'scratch-storage';
/** No wall-clock scheduler: tests explicitly advance ticks. Private API isolated here. */
export async function loadVM(project) {
  const vm = new VM();
  vm.attachStorage(new ScratchStorage());
  vm.runtime.currentStepTime = 1000 / 30;
  await vm.loadProject(Buffer.from(project));
  return {
    vm,
    flag() { vm.greenFlag(); },
    tick(count = 1) { for (let i = 0; i < count; i++) vm.runtime._step(); },
    key(key, isDown) { vm.postIOData('keyboard', { key, isDown }); },
    sprite(name) { const target = vm.runtime.targets.find(t => !t.isStage && t.getName() === name); if (!target) throw new Error(`Missing sprite ${name}`); return target; },
    variable(name) { return vm.runtime.getTargetForStage().lookupVariableByNameAndType(name, '').value; },
    close() { vm.quit(); },
  };
}
