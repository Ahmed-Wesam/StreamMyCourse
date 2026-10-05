import { CheckIcon } from './CourseDetailMarks'
import type { CourseVisualKey } from './coursePrototype'

function CheckRow({ label }: { label: string }) {
  return (
    <span>
      <CheckIcon />
      {label}
    </span>
  )
}

function MethodologyVisual() {
  return (
    <div className="chero-visual">
      <div className="win">
        <div className="win-top">
          <i></i><i></i><i></i>
          <span className="wt">Study Protocol — Builder</span>
        </div>
        <div className="win-body">
          <div className="wgrid">
            <div className="wpanel">
              <div className="ph">Study Design</div>
              <div className="dz">
                <div className="d2">Cross-Sectional</div>
                <div className="d2 on">Cohort Study <span className="tag">Selected</span></div>
                <div className="d2">Case-Control</div>
                <div className="d2">Randomized Trial</div>
              </div>
            </div>
            <div className="wpanel">
              <div className="ph">Research Workflow</div>
              <div className="flow">
                <div className="fstep on"><span className="fn">1</span> Research Question</div>
                <div className="fstep on"><span className="fn">2</span> Study Design</div>
                <div className="fstep"><span className="fn">3</span> Sampling Plan</div>
                <div className="fstep"><span className="fn">4</span> Methodology</div>
              </div>
              <div className="float-card fc-2">
                <div className="ic"><CheckIcon sw="2.2" /></div>
                <div><small>Protocol</small><strong>Ready to Run</strong></div>
              </div>
            </div>
          </div>
          <div className="wpanel">
            <div className="ph">Protocol Checklist</div>
            <div className="chk">
              <CheckRow label="Objectives defined" />
              <CheckRow label="Variables specified" />
              <CheckRow label="Sample size set" />
              <CheckRow label="Ethics & IRB ready" />
            </div>
          </div>
        </div>
      </div>
      <div className="float-card fc-1">
        <div className="ic">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2" />
            <rect x="9" y="3" width="6" height="4" rx="1" />
          </svg>
        </div>
        <div><small>Study Design</small><strong>Cohort Study</strong></div>
      </div>
    </div>
  )
}

function StatisticsVisual() {
  return (
    <div className="chero-visual">
      <div className="win">
        <div className="win-top">
          <i></i><i></i><i></i>
          <span className="wt">SPSS — Output Viewer</span>
        </div>
        <div className="win-body">
          <div className="wgrid">
            <div className="wpanel">
              <div className="ph">Group Comparison</div>
              <div className="bars"><i></i><i></i><i></i><i></i><i></i></div>
            </div>
            <div className="wpanel">
              <div className="ph">Correlation</div>
              <div className="scatter">
                <span className="dot" style={{ left: '12%', bottom: '18%' }}></span>
                <span className="dot" style={{ left: '28%', bottom: '30%' }}></span>
                <span className="dot" style={{ left: '42%', bottom: '40%' }}></span>
                <span className="dot" style={{ left: '58%', bottom: '52%' }}></span>
                <span className="dot" style={{ left: '72%', bottom: '64%' }}></span>
                <span className="dot" style={{ left: '86%', bottom: '78%' }}></span>
                <span className="ln"></span>
              </div>
            </div>
          </div>
          <div className="float-card fc-2" style={{ position: 'relative', top: 'auto', right: 'auto', animation: 'none', justifySelf: 'start', margin: 0 }}>
            <div className="ic"><CheckIcon sw="2.2" /></div>
            <div><small>Methods & Results</small><strong>Publication Ready</strong></div>
          </div>
          <div className="wpanel">
            <div className="ph">Regression Coefficients</div>
            <table className="coef">
              <thead>
                <tr><th>Variable</th><th>B</th><th>SE</th><th>p</th></tr>
              </thead>
              <tbody>
                <tr><td>Age</td><td>0.42</td><td>0.08</td><td className="sig">&lt;.001</td></tr>
                <tr><td>BMI</td><td>0.27</td><td>0.11</td><td className="sig">.014</td></tr>
                <tr><td>Treatment</td><td>1.18</td><td>0.34</td><td className="sig">&lt;.001</td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
      <div className="float-card fc-1">
        <div className="ic"><em>p</em>&thinsp;&lt;&thinsp;0.05</div>
        <div><small>Result</small><strong>Significant</strong></div>
      </div>
    </div>
  )
}

function WritingVisual() {
  return (
    <div className="chero-visual">
      <div className="win">
        <div className="win-top">
          <i></i><i></i><i></i>
          <span className="wt">Manuscript Editor</span>
        </div>
        <div className="win-body">
          <div className="wpanel">
            <div className="ph">Manuscript Sections</div>
            <div className="flow">
              <div className="fstep on"><span className="fn"><CheckIcon sw="3" /></span> Introduction</div>
              <div className="fstep on"><span className="fn"><CheckIcon sw="3" /></span> Methods</div>
              <div className="fstep on"><span className="fn">3</span> Results</div>
              <div className="fstep"><span className="fn">4</span> Discussion</div>
              <div className="fstep"><span className="fn">5</span> References</div>
            </div>
          </div>
          <div className="wgrid">
            <div className="wpanel">
              <div className="ph">Current Draft</div>
              <div className="lines">
                <i style={{ width: '100%' }}></i>
                <i style={{ width: '94%' }}></i>
                <i style={{ width: '97%' }}></i>
                <i style={{ width: '68%' }}></i>
              </div>
            </div>
            <div className="wpanel">
              <div className="ph">Completion</div>
              <div style={{ fontSize: 22, fontWeight: 800, color: 'var(--navy)', letterSpacing: '-.02em', marginBottom: 10 }}>60%</div>
              <div className="hbar"><i style={{ width: '60%' }}></i></div>
            </div>
          </div>
        </div>
      </div>
      <div className="float-card fc-1">
        <div className="ic">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 11.5a8.38 8.38 0 0 1-9 8.5 8.5 8.5 0 0 1-3.8-.9L3 21l1.9-5.2A8.5 8.5 0 1 1 21 11.5z" />
          </svg>
        </div>
        <div><small>Reviewer Comments</small><strong>3 Addressed</strong></div>
      </div>
      <div className="float-card fc-2">
        <div className="ic"><CheckIcon sw="2.2" /></div>
        <div><small>Manuscript</small><strong>Submitted</strong></div>
      </div>
      <div className="float-card fc-3">
        <div className="ic">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <path d="M14 2v6h6M9 15l2 2 4-4" />
          </svg>
        </div>
        <div><small>Status</small><strong>Publication Ready</strong></div>
      </div>
    </div>
  )
}

function ReviewVisual() {
  return (
    <div className="chero-visual">
      <div className="win">
        <div className="win-top">
          <i></i><i></i><i></i>
          <span className="wt">Systematic Review Workflow</span>
        </div>
        <div className="win-body">
          <div className="wpanel">
            <div className="ph">PRISMA Flow</div>
            <div className="flow">
              <div className="fstep on"><span className="fn">1</span> Records Identified <span className="ct">1,247</span></div>
              <div className="fstep on"><span className="fn">2</span> After Screening <span className="ct">384</span></div>
              <div className="fstep on"><span className="fn">3</span> Full-Text Review <span className="ct">92</span></div>
              <div className="fstep on"><span className="fn"><CheckIcon sw="3" /></span> Studies Included <span className="ct">18</span></div>
            </div>
          </div>
          <div className="wgrid">
            <div className="wpanel">
              <div className="ph">Forest Plot Preview</div>
              <svg className="forest-svg" viewBox="0 0 200 142" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                <line x1="100" y1="6" x2="100" y2="120" stroke="#7d92c2" strokeWidth="1.4" strokeDasharray="3,3" />
                <line x1="64" y1="20" x2="128" y2="20" stroke="#1e5eff" strokeWidth="2" />
                <rect x="92" y="16" width="8" height="8" rx="1.5" fill="#1e5eff" />
                <line x1="78" y1="40" x2="118" y2="40" stroke="#1e5eff" strokeWidth="2" />
                <rect x="92" y="36" width="10" height="8" rx="1.5" fill="#1e5eff" />
                <line x1="52" y1="60" x2="112" y2="60" stroke="#1e5eff" strokeWidth="2" />
                <rect x="76" y="56" width="8" height="8" rx="1.5" fill="#1e5eff" />
                <line x1="72" y1="80" x2="116" y2="80" stroke="#1e5eff" strokeWidth="2" />
                <rect x="88" y="76" width="9" height="8" rx="1.5" fill="#1e5eff" />
                <line x1="62" y1="100" x2="126" y2="100" stroke="#1e5eff" strokeWidth="2" />
                <rect x="88" y="96" width="9" height="8" rx="1.5" fill="#1e5eff" />
                <polygon points="75,130 100,123 125,130 100,137" fill="#0d1c40" />
              </svg>
            </div>
            <div className="wpanel">
              <div className="ph">Risk of Bias</div>
              <div className="rob">
                <div className="r"><span className="left"><span className="dot g"></span> Selection</span><span className="pill">Low</span></div>
                <div className="r"><span className="left"><span className="dot g"></span> Performance</span><span className="pill">Low</span></div>
                <div className="r"><span className="left"><span className="dot a"></span> Detection</span><span className="pill">Some</span></div>
                <div className="r"><span className="left"><span className="dot g"></span> Attrition</span><span className="pill">Low</span></div>
                <div className="r"><span className="left"><span className="dot g"></span> Reporting</span><span className="pill">Low</span></div>
              </div>
            </div>
          </div>
        </div>
      </div>
      <div className="float-card fc-1">
        <div className="ic">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="11" cy="11" r="7" />
            <path d="m21 21-4.3-4.3" />
          </svg>
        </div>
        <div><small>Search Strategy</small><strong>PubMed Ready</strong></div>
      </div>
      <div className="float-card fc-2">
        <div className="ic"><CheckIcon sw="2.2" /></div>
        <div><small>Quality</small><strong>Risk Assessed</strong></div>
      </div>
      <div className="float-card fc-3">
        <div className="ic">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <path d="M14 2v6h6M9 15l2 2 4-4" />
          </svg>
        </div>
        <div><small>Review</small><strong>Publication Ready</strong></div>
      </div>
    </div>
  )
}

export function CourseDetailHeroVisual({ visual }: { visual: CourseVisualKey }) {
  if (visual === 'methodology') return <MethodologyVisual />
  if (visual === 'statistics') return <StatisticsVisual />
  if (visual === 'writing') return <WritingVisual />
  return <ReviewVisual />
}
