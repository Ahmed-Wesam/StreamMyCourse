import {
  Award,
  ArrowRight,
  BarChart2,
  BookOpen,
  ChevronRight,
  Clock,
  FileText,
  GraduationCap,
  Star,
  Users,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { ImageWithFallback } from '../components/figma/ImageWithFallback'
import { FIGMA_MOCK_COURSE_INSTRUCTOR_IMAGE_SRC, FIGMA_MOCK_COURSE_INSTRUCTOR_NAME } from '../lib/figma-mocks'

const publications = [
  {
    title: 'Applied Statistics in Social Sciences: A Practical SPSS Approach',
    journal: 'Journal of Statistical Education',
    year: '2022',
  },
  {
    title: 'Multivariate Analysis Using SPSS: Techniques and Applications',
    journal: 'Educational and Psychological Measurement',
    year: '2021',
  },
  {
    title: 'Reliability and Validity Testing with SPSS: A Step-by-Step Guide',
    journal: 'Practical Assessment, Research & Evaluation',
    year: '2020',
  },
  {
    title: 'Regression Modeling for Behavioral Research: An SPSS Workbook',
    journal: 'Behavior Research Methods',
    year: '2019',
  },
]

const accomplishments = [
  'Ph.D. in Applied Statistics, University of Michigan',
  '15+ years teaching quantitative research methods',
  'Trained 3,000+ students and researchers worldwide',
  'Certified IBM SPSS Statistics Specialist',
  'Recipient of the Excellence in Teaching Award (2021)',
  'Consultant for government and NGO research projects',
]

const testimonials = [
  {
    name: 'Sarah Johnson',
    role: 'Public Health Researcher',
    text: 'SPSS Spectrum completely transformed how I approach data analysis. The instructor breaks down complex statistical concepts into clear, manageable steps. I now run full regression models with confidence.',
  },
  {
    name: 'Michael Chen',
    role: 'PhD Student, Psychology',
    text: "This course is hands-down the best SPSS resource I've found. The real-world datasets and guided exercises made everything click. I finished my dissertation's analysis chapter in half the time.",
  },
  {
    name: 'Emily Rodriguez',
    role: 'Market Research Analyst',
    text: 'I had no stats background at all. SPSS Spectrum walked me through everything from data entry to advanced analysis. My team is now amazed by the reports I produce.',
  },
]

export default function HomePage() {
  return (
    <div className="min-h-screen bg-background">
      <section className="bg-primary text-primary-foreground">
        <div className="max-w-6xl mx-auto px-6 py-20 text-center">
          <div className="inline-flex items-center gap-2 bg-white/15 rounded-full px-4 py-1.5 mb-6">
            <BarChart2 className="w-4 h-4" />
            <span className="text-sm tracking-wide uppercase">
              SPSS Statistics Course
            </span>
          </div>

          <h1
            className="mb-4"
            style={{
              fontSize: 'clamp(2.2rem, 6vw, 3.5rem)',
              fontWeight: 700,
              lineHeight: 1.15,
            }}
          >
            SPSS Spectrum
          </h1>
          <p className="text-xl opacity-90 mb-10 max-w-2xl mx-auto">
            The complete guide to mastering IBM SPSS Statistics — from data entry
            and descriptive analysis to advanced regression, factor analysis, and
            research reporting.
          </p>

          <div className="flex flex-wrap gap-4 justify-center text-sm mb-10">
            {[
              { icon: <Clock className="w-4 h-4" />, label: '10 Weeks' },
              { icon: <Users className="w-4 h-4" />, label: '3,000+ Students' },
              { icon: <BookOpen className="w-4 h-4" />, label: '50+ Video Lessons' },
              { icon: <Award className="w-4 h-4" />, label: 'Certificate of Completion' },
            ].map((stat) => (
              <div
                key={stat.label}
                className="flex items-center gap-2 bg-white/10 rounded-full px-4 py-2"
              >
                {stat.icon}
                <span>{stat.label}</span>
              </div>
            ))}
          </div>

          <div className="flex flex-wrap gap-4 justify-center">
            <Link
              to="/details#pricing"
              className="bg-white text-primary px-8 py-3.5 rounded-lg hover:bg-blue-50 transition-colors inline-flex items-center gap-2"
              style={{ fontWeight: 600 }}
            >
              View Course &amp; Pricing <ArrowRight className="w-4 h-4" />
            </Link>
            <Link
              to="/details"
              className="border border-white/40 text-white px-8 py-3.5 rounded-lg hover:bg-white/10 transition-colors"
              style={{ fontWeight: 500 }}
            >
              Learn More
            </Link>
          </div>
        </div>
      </section>

      <section className="border-b border-border bg-white">
        <div className="max-w-6xl mx-auto px-6 py-8 grid grid-cols-2 md:grid-cols-4 gap-6 text-center">
          {[
            { value: '3,000+', label: 'Students Enrolled' },
            { value: '4.9 / 5', label: 'Average Rating' },
            { value: '50+', label: 'Video Lessons' },
            { value: '15+', label: 'Years of Experience' },
          ].map((s) => (
            <div key={s.label}>
              <p
                className="text-primary"
                style={{ fontWeight: 700, fontSize: '1.6rem' }}
              >
                {s.value}
              </p>
              <p className="text-muted-foreground text-sm">{s.label}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="py-20 bg-secondary/40">
        <div className="max-w-6xl mx-auto px-6">
          <div className="grid md:grid-cols-3 gap-10 items-start">
            <div className="flex flex-col items-center text-center gap-4">
              <div className="w-48 h-48 rounded-full overflow-hidden border-4 border-primary shadow-lg">
                <ImageWithFallback
                  src={FIGMA_MOCK_COURSE_INSTRUCTOR_IMAGE_SRC}
                  alt={FIGMA_MOCK_COURSE_INSTRUCTOR_NAME}
                  className="w-full h-full object-cover"
                />
              </div>
              <div>
                <h3 className="text-foreground" style={{ fontWeight: 700 }}>
                  {FIGMA_MOCK_COURSE_INSTRUCTOR_NAME}
                </h3>
                <p className="text-muted-foreground text-sm mt-1">
                  Applied Statistician &amp; Educator
                </p>
              </div>

              <div className="flex flex-wrap gap-2 justify-center">
                <span className="inline-flex items-center gap-1 bg-primary/10 text-primary text-xs rounded-full px-3 py-1">
                  <GraduationCap className="w-3 h-3" /> Ph.D. Statistics
                </span>
                <span className="inline-flex items-center gap-1 bg-primary/10 text-primary text-xs rounded-full px-3 py-1">
                  <Award className="w-3 h-3" /> IBM SPSS Certified
                </span>
              </div>

              <div className="grid grid-cols-2 gap-3 w-full mt-2">
                {[
                  { value: '15+', label: 'Years Teaching' },
                  { value: '3K+', label: 'Students Trained' },
                  { value: '4', label: 'Publications' },
                  { value: '4.9★', label: 'Avg. Rating' },
                ].map((stat) => (
                  <div
                    key={stat.label}
                    className="bg-card border border-border rounded-lg py-3 px-2 text-center"
                  >
                    <p
                      className="text-primary"
                      style={{ fontWeight: 700, fontSize: '1.15rem' }}
                    >
                      {stat.value}
                    </p>
                    <p
                      className="text-muted-foreground"
                      style={{ fontSize: '0.72rem' }}
                    >
                      {stat.label}
                    </p>
                  </div>
                ))}
              </div>
            </div>

            <div className="md:col-span-2 space-y-8">
              <div>
                <h2 className="mb-3">Meet Your Instructor</h2>
                <p className="text-muted-foreground leading-relaxed">
                  {FIGMA_MOCK_COURSE_INSTRUCTOR_NAME} is an applied statistician and university educator
                  with over 15 years of experience teaching quantitative research
                  methods to students, healthcare professionals, and organizational
                  researchers.
                </p>
                <p className="text-muted-foreground leading-relaxed mt-3">
                  SPSS Spectrum was designed from the ground up based on common pain
                  points students and researchers face — making the course practical,
                  approachable, and immediately applicable to your own data.
                </p>
              </div>

              <div>
                <h3 className="mb-4 flex items-center gap-2">
                  <Award className="w-5 h-5 text-primary" /> Accomplishments
                </h3>
                <ul className="space-y-2">
                  {accomplishments.map((item) => (
                    <li
                      key={item}
                      className="flex items-start gap-3 text-muted-foreground"
                    >
                      <ChevronRight className="w-4 h-4 text-primary mt-0.5 shrink-0" />
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <div>
                <h3 className="mb-4 flex items-center gap-2">
                  <FileText className="w-5 h-5 text-primary" /> Selected Publications
                </h3>
                <div className="space-y-3">
                  {publications.map((pub) => (
                    <div
                      key={`${pub.title}-${pub.year}`}
                      className="bg-card border border-border rounded-lg p-4"
                    >
                      <p className="text-foreground" style={{ fontWeight: 500 }}>
                        {pub.title}
                      </p>
                      <p className="text-muted-foreground text-sm mt-1">
                        {pub.journal} · {pub.year}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="py-20 bg-muted/30">
        <div className="max-w-6xl mx-auto px-6">
          <h2 className="text-center mb-12">What Students Say</h2>
          <div className="grid md:grid-cols-3 gap-8">
            {testimonials.map((testimonial) => (
              <div
                key={testimonial.name}
                className="bg-card rounded-lg border border-border p-6 flex flex-col"
              >
                <div className="flex gap-1 mb-4">
                  {[...Array(5)].map((_, i) => (
                    <Star
                      key={i}
                      className="w-5 h-5 fill-primary text-primary"
                    />
                  ))}
                </div>
                <p className="text-muted-foreground mb-6 flex-1">
                  "{testimonial.text}"
                </p>
                <div>
                  <p className="text-sm" style={{ fontWeight: 600 }}>
                    {testimonial.name}
                  </p>
                  <p className="text-sm text-muted-foreground">
                    {testimonial.role}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="py-16 bg-primary text-primary-foreground">
        <div className="max-w-6xl mx-auto px-6 text-center">
          <h2 className="mb-3" style={{ color: 'white' }}>
            Ready to Master SPSS Statistics?
          </h2>
          <p className="opacity-90 mb-8 max-w-xl mx-auto">
            Join thousands of students and researchers who have transformed their data
            analysis skills with SPSS Spectrum.
          </p>
          <Link
            to="/details#pricing"
            className="bg-white text-primary px-10 py-4 rounded-lg hover:bg-blue-50 transition-colors inline-flex items-center gap-2"
            style={{ fontWeight: 600 }}
          >
            See Pricing &amp; Enroll <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>
    </div>
  )
}

