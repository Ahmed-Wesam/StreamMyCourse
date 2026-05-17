import {
  Award,
  BarChart2,
  BookOpen,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Clock,
  Play,
  Shield,
  Star,
  Users,
  Zap,
} from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { PricingSection } from '../components/course/PricingSection'
import { ImageWithFallback } from '../components/figma/ImageWithFallback'

const modules = [
  {
    number: '01',
    title: 'Getting Started with SPSS',
    lessons: 5,
    duration: '3h 20m',
    topics: [
      'Installing & activating SPSS',
      'Interface overview',
      'Variable View vs Data View',
      'Importing data from Excel/CSV',
      'Basic navigation shortcuts',
    ],
  },
  {
    number: '02',
    title: 'Data Management & Transformation',
    lessons: 7,
    duration: '4h 45m',
    topics: [
      'Coding and labeling variables',
      'Recoding & computing new variables',
      'Handling missing data',
      'Merging and splitting datasets',
      'Sorting and selecting cases',
    ],
  },
  {
    number: '03',
    title: 'Descriptive Statistics & Visualization',
    lessons: 6,
    duration: '3h 55m',
    topics: [
      'Frequencies and descriptives',
      'Histograms & bar charts',
      'Box plots & scatter plots',
      'Cross-tabulations',
      'Exploring normality',
    ],
  },
  {
    number: '04',
    title: 'Inferential Statistics I — t-tests & ANOVA',
    lessons: 8,
    duration: '5h 30m',
    topics: [
      'One-sample t-test',
      'Independent samples t-test',
      'Paired samples t-test',
      'One-way ANOVA',
      'Post-hoc tests (Tukey, Bonferroni)',
    ],
  },
  {
    number: '05',
    title: 'Inferential Statistics II — Chi-square & Non-parametrics',
    lessons: 6,
    duration: '4h 10m',
    topics: [
      'Chi-square test of independence',
      'Mann-Whitney U',
      'Kruskal-Wallis',
      'Wilcoxon signed-rank',
      'Choosing parametric vs non-parametric',
    ],
  },
  {
    number: '06',
    title: 'Correlation & Regression Analysis',
    lessons: 9,
    duration: '6h 20m',
    topics: [
      'Pearson & Spearman correlation',
      'Simple linear regression',
      'Multiple regression',
      'Checking assumptions',
      'Interpreting R² and coefficients',
    ],
  },
  {
    number: '07',
    title: 'Factor Analysis & Scale Reliability',
    lessons: 7,
    duration: '5h 00m',
    topics: [
      'Exploratory factor analysis (EFA)',
      'Confirmatory approaches',
      "Cronbach’s α reliability",
      'Item-total statistics',
      'Scale construction',
    ],
  },
  {
    number: '08',
    title: 'Reporting & Communicating Results',
    lessons: 5,
    duration: '3h 15m',
    topics: [
      'APA-style result writing',
      'Exporting SPSS output tables',
      'Creating publication-ready charts',
      'Writing a results section',
      'Common mistakes to avoid',
    ],
  },
]

const features = [
  {
    icon: <Play className="w-5 h-5 text-primary" />,
    title: '50+ HD Video Lessons',
    desc: 'Step-by-step screencasts with real SPSS files.',
  },
  {
    icon: <BookOpen className="w-5 h-5 text-primary" />,
    title: '20 Real-World Datasets',
    desc: 'Practice with data from health, social, and business research.',
  },
  {
    icon: <Zap className="w-5 h-5 text-primary" />,
    title: 'Instant Access',
    desc: 'Start learning immediately after enrollment.',
  },
  {
    icon: <Users className="w-5 h-5 text-primary" />,
    title: 'Community Forum',
    desc: 'Ask questions and collaborate with fellow learners.',
  },
  {
    icon: <Shield className="w-5 h-5 text-primary" />,
    title: '7-Day Money-Back Guarantee',
    desc: 'Not satisfied? Get a full refund, no questions asked.',
  },
  {
    icon: <Award className="w-5 h-5 text-primary" />,
    title: 'Certificate of Completion',
    desc: 'Shareable certificate to showcase on LinkedIn or your CV.',
  },
]

function ModuleAccordion({ mod }: { mod: (typeof modules)[number] }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="bg-card border border-border rounded-lg overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-4 px-6 py-4 text-left hover:bg-muted/30 transition-colors"
      >
        <span
          className="text-primary shrink-0"
          style={{ fontWeight: 700, fontSize: '0.85rem', minWidth: '2rem' }}
        >
          {mod.number}
        </span>
        <span className="flex-1" style={{ fontWeight: 600 }}>
          {mod.title}
        </span>
        <span className="text-muted-foreground text-sm shrink-0 mr-3">
          {mod.lessons} lessons · {mod.duration}
        </span>
        {open ? (
          <ChevronUp className="w-4 h-4 text-muted-foreground shrink-0" />
        ) : (
          <ChevronDown className="w-4 h-4 text-muted-foreground shrink-0" />
        )}
      </button>
      {open && (
        <div className="px-6 pb-5 pt-1 border-t border-border bg-muted/10">
          <ul className="space-y-1.5">
            {mod.topics.map((topic) => (
              <li
                key={topic}
                className="flex items-start gap-2 text-sm text-muted-foreground"
              >
                <CheckCircle2 className="w-4 h-4 text-primary mt-0.5 shrink-0" />
                {topic}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

export default function CoursePage() {
  return (
    <div className="min-h-screen bg-background">
      <section className="bg-primary text-primary-foreground">
        <div className="max-w-6xl mx-auto px-6 py-16">
          <div className="grid md:grid-cols-2 gap-10 items-center">
            <div>
              <div className="inline-flex items-center gap-2 bg-white/15 rounded-full px-4 py-1.5 mb-5">
                <BarChart2 className="w-4 h-4" />
                <span className="text-sm tracking-wide uppercase">
                  Details
                </span>
              </div>
              <h1
                className="mb-4"
                style={{
                  fontSize: 'clamp(1.8rem, 4vw, 2.8rem)',
                  fontWeight: 700,
                  lineHeight: 1.2,
                }}
              >
                SPSS Spectrum
              </h1>
              <p className="opacity-90 mb-6 leading-relaxed">
                A comprehensive, practical course designed to take you from complete
                beginner to confident SPSS user — with real datasets, clear
                explanations, and immediate, applicable skills.
              </p>
              <div className="flex flex-wrap gap-4 text-sm">
                {[
                  { icon: <Clock className="w-4 h-4" />, label: '10 Weeks' },
                  { icon: <BookOpen className="w-4 h-4" />, label: '53 Lessons' },
                  { icon: <Users className="w-4 h-4" />, label: '3,000+ Students' },
                  { icon: <Star className="w-4 h-4 fill-white" />, label: '4.9 Rating' },
                ].map((s) => (
                  <div
                    key={s.label}
                    className="flex items-center gap-1.5 bg-white/10 rounded-full px-3 py-1.5"
                  >
                    {s.icon}
                    <span>{s.label}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-xl overflow-hidden shadow-2xl border border-white/20">
              <ImageWithFallback
                src="https://images.unsplash.com/photo-1762427354051-a9bdb181ae3b?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=800"
                alt="SPSS Course Preview"
                className="w-full h-56 object-cover"
              />
              <div className="bg-white/10 backdrop-blur-sm p-4 flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-white flex items-center justify-center shrink-0">
                  <Play className="w-5 h-5 text-primary fill-primary" />
                </div>
                <div>
                  <p className="text-sm opacity-75">Preview Lesson</p>
                  <p style={{ fontWeight: 600 }}>
                    Introduction to the SPSS Interface
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="py-16 border-b border-border">
        <div className="max-w-6xl mx-auto px-6">
          <h2 className="text-center mb-10">Everything Included</h2>
          <div className="grid sm:grid-cols-2 md:grid-cols-3 gap-6">
            {features.map((f) => (
              <div
                key={f.title}
                className="flex gap-4 bg-card border border-border rounded-lg p-5"
              >
                <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
                  {f.icon}
                </div>
                <div>
                  <p style={{ fontWeight: 600 }}>{f.title}</p>
                  <p className="text-muted-foreground text-sm mt-0.5">{f.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="py-16">
        <div className="max-w-4xl mx-auto px-6">
          <h2 className="text-center mb-3">Course Curriculum</h2>
          <p className="text-center text-muted-foreground mb-10">
            8 modules · 53 lessons · 36+ hours of content
          </p>
          <div className="space-y-3">
            {modules.map((mod) => (
              <ModuleAccordion key={mod.number} mod={mod} />
            ))}
          </div>
        </div>
      </section>

      <PricingSection id="pricing" />

      <section className="py-16 bg-primary text-primary-foreground">
        <div className="max-w-6xl mx-auto px-6 text-center">
          <h2 style={{ color: 'white' }} className="mb-3">
            Start Learning SPSS Today
          </h2>
          <p className="opacity-90 mb-8 max-w-xl mx-auto">
            Choose your plan above and get instant access to all course materials,
            datasets, and community support.
          </p>
          <div className="flex flex-wrap gap-4 justify-center">
            <a
              href="#pricing"
              className="bg-white text-primary px-10 py-4 rounded-lg hover:bg-blue-50 transition-colors inline-block"
              style={{ fontWeight: 600 }}
            >
              View Pricing Plans
            </a>
            <Link
              to="/learn"
              className="border border-white/40 text-white px-10 py-4 rounded-lg hover:bg-white/10 transition-colors inline-block"
              style={{ fontWeight: 600 }}
            >
              Preview Course →
            </Link>
          </div>
        </div>
      </section>
    </div>
  )
}

