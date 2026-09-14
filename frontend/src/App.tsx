import { useState } from 'react';
import { ArtifactViewer } from './components/ArtifactViewer';
import type { ArtifactData } from './components/ArtifactViewer';
import { Sparkles, FileText, Code } from 'lucide-react';
import './App.css';

const SAMPLE_ARTIFACTS: ArtifactData[] = [
  {
    id: 'art-ship30-demo',
    type: 'ship30',
    title: 'The 4-Part Growth Competency Engine',
    word_count: 1245,
    citations: [
      {
        guest: 'Adam Fishman',
        episode_title: 'How to build a high-performing growth team',
        source_url: 'https://www.lennyspodcast.com/transcript',
      },
    ],
    content: `# The 4-Part Growth Competency Engine: Unlocking High-Performing Growth Teams

In a world where growth teams are the primary competitive advantage, building a high-performing team is no longer a nicety, but a survival imperative. Yet, founders continuously make the fatal error of hiring for "generalist grit" rather than tactical competency.

As Adam Fishman, legendary growth leader at Patreon, Lyft, and Imperfect Foods notes:
> "You cannot simply clone a background or resume and expect high-velocity execution. Growth is a specific discipline comprised of four interlocking competencies."

## The Status Quo: The Trap of Generalist Hiring

Traditionally, founders look for a lone "growth hacker" — someone who knows a few conversion rate optimization tricks or paid acquisition channels. This model fails because:
* **Tactics decay rapidly**: Channel arbitrage evaporates within months.
* **No systemic customer loop**: Without deep instrumentation, learnings stay trapped in spreadsheets.
* **Organizational friction**: Product and engineering reject rogue growth experiments that lack cross-functional buy-in.

## The Tension: The 4 Interlocking Competencies

To build an enduring growth engine, leaders must evaluate and hire against Adam Fishman's **Growth Competency Framework**:

### 1. Growth Execution
- **Channel Fluency**: Mastery of channel dynamics across organic, viral, and paid ecosystems.
- **Experimentation Rigor**: High-tempo hypothesis drafting, statistical significance testing, and sample sizing.
- **Productizing Learnings**: Turning successful one-off experiments into permanent core product mechanics.

### 2. Customer Knowledge & Instrumentation
- **Data Fluency**: Ability to write queries, configure amplitude events, and diagnose drop-off funnels.
- **User Psychology**: Knowing the underlying emotional triggers of onboarding activation.
- **Qualitative Synthesis**: Translating messy user interviews into structured experiment ideas.

### 3. Growth Strategy & Modeling
- **Loop Modeling**: Formalizing compounding retention and acquisition loops.
- **Capital Allocation**: Knowing when to invest in top-of-funnel acquisition vs. mid-funnel expansion.
- **Prioritization Cadence**: ICE/RICE scoring tuned for business model leverage.

### 4. Communication & Influence
- **Strategic Alignment**: Winning over skeptical product and engineering peers to the growth perspective.
- **Executive Reporting**: Framing growth volatility cleanly to board and executive leadership.

## The Resolution: Implementation Playbook

If you are structuring or auditing your growth function this quarter, execute this 3-step playbook:

1. **Conduct a Team Competency Audit**: Score every operator from 1 to 5 across the 4 pillars.
2. **Hire for Complementary Spikes**: Do not hire another channel executor if your data instrumentation is broken.
3. **Establish a Weekly Learning Cadence**: Measure and celebrate *learnings per week*, not just win rates.

## The One Takeaway

**Growth is not a personality trait or a lone hacker; it is an organizational competency.** Evaluate your team across Execution, Customer Knowledge, Strategy, and Influence — and hire deliberately for the gaps.

## Provenance Sources
- Adam Fishman, *How to build a high-performing growth team | Adam Fishman (Patreon, Lyft, Imperfect Foods)*, Lenny's Podcast.`,
  },
  {
    id: 'art-md-demo',
    type: 'markdown',
    title: 'Executive Brief: B2B Growth Loop Architecture',
    word_count: 680,
    citations: [
      {
        guest: 'Elena Verna',
        episode_title: 'The Ultimate Guide to Product-Led Growth',
        source_url: 'https://www.lennyspodcast.com/transcript',
      },
    ],
    content: `# Executive Brief: B2B Growth Loop Architecture

## Executive Summary
Product-led growth (PLG) is not merely a freemium pricing tier; it is an architectural commitment to having the product deliver value before capturing revenue. Growth loops must replace linear marketing funnels to achieve compounding, capital-efficient ARR expansion.

## Strategic Pillars
* **Self-Serve Activation**: The user must reach the "Aha!" moment within 5 minutes without sales assistance.
* **Viral Collaboration Loops**: Workspaces that naturally invite colleagues (e.g., Figma, Miro, Slack).
* **Usage-Based Expansion Triggers**: Pricing models that scale directly with product usage and business value.

## Tactical Checklist
1. Audit time-to-value (TTV) for all self-serve signups.
2. Strip mandatory credit card requirements from freemium onboarding.
3. Implement product-qualified lead (PQL) scoring based on collaborative activity.
4. Establish self-serve in-app upgrade flows without requiring sales interaction.

## Key Metrics & KPIs
- Self-Serve Activation Rate (>40%)
- Time-to-Value (<5 minutes)
- Natural Net Retention Rate (NRR >120%)

## Sources & Citations
- Elena Verna, *The Ultimate Guide to Product-Led Growth*, Lenny's Podcast`,
  },
  {
    id: 'art-html-demo',
    type: 'html',
    title: 'Interactive CAC Payback & Growth Loop Simulator',
    word_count: 420,
    citations: [
      {
        guest: 'Elena Verna',
        episode_title: 'B2B Growth & Payback Period Benchmarks',
        source_url: 'https://www.lennyspodcast.com/transcript',
      },
    ],
    content: `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src data:; script-src 'unsafe-inline';">
    <title>CAC Payback & Loop Simulator</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #090d16;
            color: #f1f5f9;
            padding: 2rem;
            display: flex;
            justify-content: center;
        }
        .widget-card {
            background: #111827;
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 2rem;
            max-width: 580px;
            width: 100%;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5);
        }
        h2 { font-size: 1.35rem; color: #38bdf8; margin-bottom: 0.5rem; }
        p.subtitle { color: #94a3b8; font-size: 0.85rem; margin-bottom: 1.5rem; line-height: 1.5; }
        .form-group { margin-bottom: 1.25rem; }
        label { display: flex; justify-content: space-between; font-size: 0.85rem; font-weight: 600; color: #cbd5e1; margin-bottom: 0.5rem; }
        .val-badge { color: #38bdf8; font-family: ui-monospace, monospace; }
        input[type="range"] {
            width: 100%;
            height: 6px;
            background: #1e293b;
            border-radius: 3px;
            outline: none;
            accent-color: #38bdf8;
            cursor: pointer;
        }
        .results-box {
            margin-top: 1.5rem;
            padding: 1.25rem;
            background: #1e293b;
            border-radius: 8px;
            border: 1px solid rgba(56, 189, 248, 0.2);
            text-align: center;
        }
        .metric-title { font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; color: #94a3b8; }
        .metric-value { font-size: 2.25rem; font-weight: 700; color: #38bdf8; margin: 0.25rem 0; font-family: ui-monospace, monospace; }
        .metric-verdict { font-size: 0.85rem; font-weight: 500; }
        .verdict-good { color: #34d399; }
        .verdict-warn { color: #fbbf24; }
        .verdict-bad { color: #f87171; }
    </style>
</head>
<body>
    <div class="widget-card">
        <h2>CAC Payback Simulator</h2>
        <p class="subtitle">Evaluate your capital efficiency against Lenny's Podcast benchmarks (Target: &lt;12 months for Good, &lt;6 months for Elite PLG).</p>
        
        <div class="form-group">
            <label>Customer Acquisition Cost (CAC): <span id="cac-val" class="val-badge">$600</span></label>
            <input type="range" id="cac" min="50" max="2500" step="25" value="600">
        </div>

        <div class="form-group">
            <label>Monthly ARPU: <span id="arpu-val" class="val-badge">$100</span></label>
            <input type="range" id="arpu" min="10" max="500" step="10" value="100">
        </div>

        <div class="form-group">
            <label>Gross Margin (%): <span id="margin-val" class="val-badge">75%</span></label>
            <input type="range" id="margin" min="30" max="95" step="5" value="75">
        </div>

        <div class="results-box">
            <div class="metric-title">Calculated Payback Period</div>
            <div id="payback-result" class="metric-value">8.0 Mo</div>
            <div id="verdict-result" class="metric-verdict verdict-good">✓ Healthy Payback Window (&lt;12 months)</div>
        </div>
    </div>

    <script>
        const cac = document.getElementById('cac');
        const arpu = document.getElementById('arpu');
        const margin = document.getElementById('margin');
        const cacVal = document.getElementById('cac-val');
        const arpuVal = document.getElementById('arpu-val');
        const marginVal = document.getElementById('margin-val');
        const paybackResult = document.getElementById('payback-result');
        const verdictResult = document.getElementById('verdict-result');

        function recalculate() {
            const c = parseFloat(cac.value);
            const a = parseFloat(arpu.value);
            const m = parseFloat(margin.value) / 100.0;

            cacVal.textContent = '$' + c.toLocaleString();
            arpuVal.textContent = '$' + a.toLocaleString();
            marginVal.textContent = (m * 100).toFixed(0) + '%';

            const monthlyGrossProfit = a * m;
            const months = (c / monthlyGrossProfit).toFixed(1);
            paybackResult.textContent = months + ' Mo';

            const numMonths = parseFloat(months);
            if (numMonths <= 6) {
                verdictResult.className = 'metric-verdict verdict-good';
                verdictResult.textContent = '★ Elite PLG Benchmark (&le;6 months)';
            } else if (numMonths <= 12) {
                verdictResult.className = 'metric-verdict verdict-good';
                verdictResult.textContent = '✓ Healthy B2B Benchmark (&le;12 months)';
            } else if (numMonths <= 18) {
                verdictResult.className = 'metric-verdict verdict-warn';
                verdictResult.textContent = '⚠ Borderline Payback Window (12-18 months)';
            } else {
                verdictResult.className = 'metric-verdict verdict-bad';
                verdictResult.textContent = '✕ High Capital Burn (&gt;18 months)';
            }
        }

        cac.addEventListener('input', recalculate);
        arpu.addEventListener('input', recalculate);
        margin.addEventListener('input', recalculate);
        recalculate();
    </script>
</body>
</html>`,
  },
];

export function App() {
  const [selectedIdx, setSelectedIdx] = useState<number>(0);
  const currentArtifact = SAMPLE_ARTIFACTS[selectedIdx];

  return (
    <div className="app-container">
      <header className="app-header">
        <div className="header-brand">
          <div className="brand-logo">LG</div>
          <div>
            <h1 className="brand-title">The Lenny Growth Assistant</h1>
            <span className="brand-subtitle">Artifact Generation & Sandboxed Viewer</span>
          </div>
        </div>

        <div className="artifact-selector-pills">
          {SAMPLE_ARTIFACTS.map((art, idx) => (
            <button
              key={art.id}
              className={`pill-btn ${selectedIdx === idx ? 'active' : ''}`}
              onClick={() => setSelectedIdx(idx)}
            >
              {art.type === 'ship30' && <Sparkles size={14} />}
              {art.type === 'markdown' && <FileText size={14} />}
              {art.type === 'html' && <Code size={14} />}
              <span>{art.title}</span>
            </button>
          ))}
        </div>
      </header>

      <main className="app-main">
        <ArtifactViewer artifact={currentArtifact} />
      </main>
    </div>
  );
}

export default App;
