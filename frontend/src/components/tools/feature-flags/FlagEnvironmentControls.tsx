import { useState } from 'react';
import { Badge } from '../../common/Badge';
import { useToggleFlag, useUpdateFlagState } from '../../../hooks/useFeatureFlags';
import type { FeatureFlag, FeatureFlagState } from '../../../types';
import { humanize } from '../../../utils/format';

/** On/off switch plus rollout slider for one environment of one flag. */
function EnvironmentRow({
  flag,
  state,
  editable,
}: {
  flag: FeatureFlag;
  state: FeatureFlagState;
  editable: boolean;
}): JSX.Element {
  const toggle = useToggleFlag();
  const updateState = useUpdateFlagState();
  const [rollout, setRollout] = useState(state.rollout_percentage);

  return (
    <div className="flex items-center gap-3 py-1">
      <span className="w-24 text-xs font-medium uppercase tracking-wide text-slate-500">
        {humanize(state.environment)}
      </span>

      <button
        type="button"
        role="switch"
        aria-checked={state.enabled}
        aria-label={`${flag.name} in ${state.environment}`}
        disabled={!editable || toggle.isPending}
        onClick={() =>
          toggle.mutate({
            flagId: flag.id,
            environment: state.environment,
            enabled: !state.enabled,
          })
        }
        className={[
          'relative h-5 w-9 rounded-full transition',
          state.enabled ? 'bg-emerald-500' : 'bg-slate-300',
          editable ? 'cursor-pointer' : 'cursor-not-allowed opacity-60',
        ].join(' ')}
      >
        <span
          className={[
            'absolute top-0.5 h-4 w-4 rounded-full bg-white transition',
            state.enabled ? 'left-4.5 translate-x-0.5' : 'left-0.5',
          ].join(' ')}
        />
      </button>

      {editable ? (
        <div className="flex flex-1 items-center gap-2">
          <input
            type="range"
            min={0}
            max={100}
            step={5}
            value={rollout}
            onChange={(event) => setRollout(Number(event.target.value))}
            onMouseUp={() =>
              updateState.mutate({
                flagId: flag.id,
                environment: state.environment,
                rolloutPercentage: rollout,
              })
            }
            onTouchEnd={() =>
              updateState.mutate({
                flagId: flag.id,
                environment: state.environment,
                rolloutPercentage: rollout,
              })
            }
            className="w-32 accent-brand-600"
            aria-label={`Rollout percentage for ${state.environment}`}
          />
          <span className="w-10 text-xs text-slate-600">{rollout}%</span>
        </div>
      ) : (
        <Badge tone={state.enabled ? 'success' : 'neutral'}>{state.rollout_percentage}%</Badge>
      )}
    </div>
  );
}

export function FlagEnvironmentControls({
  flag,
  editable,
}: {
  flag: FeatureFlag;
  editable: boolean;
}): JSX.Element {
  return (
    <div className="divide-y divide-slate-100">
      {flag.environments.map((state) => (
        <EnvironmentRow
          key={state.environment}
          flag={flag}
          state={state}
          editable={editable}
        />
      ))}
    </div>
  );
}
