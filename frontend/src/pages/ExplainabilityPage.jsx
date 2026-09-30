import Panel from '../components/common/Panel.jsx';
import { LoadingState, ErrorState } from '../components/common/AsyncStates.jsx';
import ExplanationPanel from '../components/explainability/ExplanationPanel.jsx';
import MitrePanel from '../components/explainability/MitrePanel.jsx';
import { useExplanation } from '../hooks/useExplanation.js';

export default function ExplainabilityPage() {
  const explanation = useExplanation();

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold text-text-primary">Explainability</h1>
        <p className="text-xs text-text-secondary mt-0.5">
          Why the model forecast what it did, and how that maps to known attacker techniques.
        </p>
      </div>

      <Panel title="Forecast Explanation">
        {explanation.loading && <LoadingState label="Retrieving contributing signals…" />}
        {!explanation.loading && explanation.error && <ErrorState onRetry={explanation.refresh} />}
        {!explanation.loading && !explanation.error && <ExplanationPanel explanation={explanation.data} />}
      </Panel>

      <Panel title="MITRE ATT&CK Interpretation">
        <MitrePanel />
      </Panel>
    </div>
  );
}
