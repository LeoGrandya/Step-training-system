import { driver } from 'driver.js';

const BASE_CONFIG = {
  animate: true,
  allowClose: true,
  overlayOpacity: 0.65,
  smoothScroll: true,
  showProgress: true,
  progressText: '{{current}} / {{total}}',
  nextBtnText: '下一步',
  prevBtnText: '上一步',
  doneBtnText: '完成',
  popoverClass: 'app-guide-popover',
  showButtons: ['next', 'previous', 'close'],
};

export function createGuideDriver(steps, { onDestroyed } = {}) {
  const driverObj = driver({
    ...BASE_CONFIG,
    steps,
    onDestroyed: (element, step, { driver: activeDriver }) => {
      onDestroyed?.(element, step, activeDriver);
    },
  });

  return driverObj;
}

export function startGuide(steps, options = {}) {
  const driverObj = createGuideDriver(steps, options);
  driverObj.drive();
  return driverObj;
}
