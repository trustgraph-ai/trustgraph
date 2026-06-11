import type * as Atom from "effect/unstable/reactivity/Atom";
import type {
  FeatureSwitches,
  Settings,
  WorkbenchApiFactory,
} from "@/atoms/workbench";
import {
  apiFactoryAtom,
  DEFAULT_SETTINGS,
  flowIdAtom,
  settingsAtom,
} from "@/atoms/workbench";
import type { BaseApi } from "@trustgraph/client";
import { MockWorkbenchFixture, makeMockBaseApi, qaSettingsFromFixture, } from "@/qa/mock-api";
import { Schema as S } from "effect";

export class WorkbenchQaWindowConfig extends S.Class<WorkbenchQaWindowConfig>("WorkbenchQaWindowConfig")({
  enabled: S.optionalKey(S.Boolean),
  fixture: S.optionalKey(MockWorkbenchFixture),
  flowId: S.optionalKey(S.String),
}, { description: "Browser-provided workbench QA boot configuration." }) {}

declare global {
  interface Window {
    __TRUSTGRAPH_WORKBENCH_QA__?: WorkbenchQaWindowConfig;
    __TRUSTGRAPH_WORKBENCH_QA_API__?: BaseApi;
  }
}

function qaSettings(fixture: MockWorkbenchFixture | undefined): Settings {
  const fixtureSettings = qaSettingsFromFixture(fixture);
  return {
    ...DEFAULT_SETTINGS,
    ...fixtureSettings,
    featureSwitches: {
      ...DEFAULT_SETTINGS.featureSwitches,
      ...fixtureSettings.featureSwitches,
    } as FeatureSwitches,
  };
}

export function getWorkbenchQaInitialValues(): Iterable<readonly [Atom.Atom<unknown>, unknown]> | undefined {
  if (typeof window === "undefined") return undefined;
  const config = window.__TRUSTGRAPH_WORKBENCH_QA__;
  if (config?.enabled !== true) return undefined;
  const fixture = config.fixture ?? {};
  const api = makeMockBaseApi(fixture);
  const apiFactory: WorkbenchApiFactory = {
    create: () => api,
  };
  window.__TRUSTGRAPH_WORKBENCH_QA_API__ = api;
  return [
    [apiFactoryAtom as Atom.Atom<unknown>, apiFactory],
    [settingsAtom as Atom.Atom<unknown>, qaSettings(fixture)],
    [flowIdAtom as Atom.Atom<unknown>, config.flowId ?? "default"],
  ];
}
