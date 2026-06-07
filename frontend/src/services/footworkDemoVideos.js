/** 运行时必需。步伐示范视频 URL（/videos/footwork/{stepType}.mp4）。 */
import { PRESET_STEP_OPTION_GROUPS } from './presetSteps.js';

export const FOOTWORK_DEMO_BASE = '/videos/footwork';

export function getFootworkDemoVideoUrl(stepType) {
  return `${FOOTWORK_DEMO_BASE}/${stepType}.mp4`;
}

export function getFootworkDemoPosterUrl(stepType) {
  return `${FOOTWORK_DEMO_BASE}/${stepType}.jpg`;
}

export function listFootworkDemoGroups() {
  return PRESET_STEP_OPTION_GROUPS;
}

export function listFootworkDemoOptions() {
  return PRESET_STEP_OPTION_GROUPS.flatMap((group) =>
    group.options.map((option) => ({
      value: option.value,
      label: option.label,
      groupLabel: group.label,
    })),
  );
}
