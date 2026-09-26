/** Static About Instructor marketing copy (no JSX). Prototype text for RS-2 Slice D1. */

export const aboutHero = {
  eyebrow: 'Meet Your Instructor',
  nameLine1: 'Dr. Bahaa',
  nameHighlight: 'Aburayya',
  /** Full display name used in profile card and photo alt. */
  fullName: 'Dr. Bahaa Aburayya',
  titleLine: 'Researcher & Educator',
  sub: 'Researcher, educator, and founder of Research Spectrum. Dedicated to helping students and healthcare professionals develop the skills needed to conduct, analyze, write, and publish high-quality research independently.',
  roles: ['Researcher', 'Educator', 'Founder'] as const,
  stats: [
    { value: '4', label: 'Flagship Courses' },
    { value: 'Research Team', label: 'Pathway Available' },
    { value: 'End-to-End Curriculum', label: 'Full Research Cycle' },
    { value: 'Certificate Per Course', label: 'Verified Learning' },
  ] as const,
  primaryCta: 'Explore Courses',
  secondaryCta: 'Read My Story',
} as const

export const aboutCredentials = {
  kicker: 'Evidence of Expertise',
  title: 'Research Credentials',
  lead: "Don't just take our word for it — verify it. Formal medical training, active research fellowships, and a peer-reviewed publication record you can check for yourself.",
  name: 'Dr. Bahaa Aburayya',
  subtitle: 'MD · Researcher · Educator · Founder of Research Spectrum',
  bio: 'Published researcher with peer-reviewed publications, national and international presentations, and ongoing collaborative research in surgery, clinical outcomes research, systematic reviews, and artificial intelligence in medicine.',
  profileLinks: [
    {
      label: 'View PubMed Profile',
      href: 'https://pubmed.ncbi.nlm.nih.gov/?term=Aburayya+BI&cauthor_id=36180807',
      variant: 'primary' as const,
    },
    {
      label: 'Google Scholar',
      href: 'https://scholar.google.com/citations?user=-1hFR1wAAAAJ&hl=en&authuser=1',
      variant: 'ghost' as const,
    },
    {
      label: 'ResearchGate',
      href: 'https://www.researchgate.net/profile/Bahaa-Aburayya',
      variant: 'ghost' as const,
    },
  ] as const,
  items: [
    {
      role: 'Medical Doctor',
      org: 'Jordan University of Science and Technology',
      detail: 'Faculty of Medicine — Doctor of Medicine (MD)',
      icon: 'graduation' as const,
    },
    {
      role: 'Postdoctoral Research Fellow',
      org: 'Mayo Clinic, Arizona',
      detail: 'Department of Surgery — Division of Cardiothoracic Surgery',
      icon: 'shield' as const,
    },
    {
      role: 'Remote Research Collaborator',
      org: 'University of California, San Francisco (UCSF)',
      detail: 'Department of Surgery — Division of Surgical Oncology',
      icon: 'building' as const,
    },
    {
      role: 'Published Researcher',
      org: 'Peer-Reviewed Medical Research',
      detail: 'General surgery, systematic reviews, and clinical outcomes research',
      icon: 'book' as const,
    },
    {
      role: 'Founder, Research Spectrum',
      org: 'Research Education Platform',
      detail: 'Structured, end-to-end research education for healthcare professionals worldwide',
      icon: 'chart' as const,
    },
  ] as const,
} as const

export const aboutPublications = {
  kicker: 'Peer-Reviewed Research',
  title: 'Featured Publications',
  lead: 'A selection of peer-reviewed work in surgery, systematic reviews, and clinical outcomes research. Every entry is verifiable through the linked profiles above.',
  fullListSummary: 'View Full Publication List',
  fullListHeading: 'Peer-Reviewed Publications',
  featured: [
    {
      venue: 'Cancers · 2025',
      title:
        'Minimally invasive distal pancreatectomy as the standard of care in the US: are we there yet?',
      href: 'https://doi.org/10.3390/cancers17183015',
    },
    {
      venue: 'Updates in Surgery · 2024',
      title:
        'Critical view of safety approach vs. infundibular technique in laparoscopic cholecystectomy',
      href: 'https://doi.org/10.1007/s13304-024-02029-5',
    },
    {
      venue: 'Neurosurgical Review · 2022',
      title:
        'Risk of meningitis after posterior fossa decompression with duraplasty using different graft types',
      href: 'https://doi.org/10.1007/s10143-022-01873-6',
    },
    {
      venue: 'Int. J. Surg. Case Rep. · 2024',
      title:
        'Complete Common Bile Duct Injury after Laparoscopic Cholecystectomy in Situs Inversus Totalis',
      href: 'https://doi.org/10.1016/j.ijscr.2024.109265',
    },
  ] as const,
  /**
   * Full citation list. Each entry is plain text segments plus a DOI link.
   * `authorsBefore` / `authorsAfter` wrap the highlighted surname; citation body is plain text.
   */
  fullList: [
    {
      authorsBefore: 'Foroutani L, Gonzalez A, Wang JJ, ',
      highlight: 'Aburayya BI',
      authorsAfter: ', Ganjouei AA, Feng J, Thornblade LW, Hirose K, Maker AV, Nakakura E, Corvera CU, Alseidi A, Adam MA. ',
      citation:
        'Minimally invasive distal pancreatectomy as the standard of care in the US: are we there yet? Cancers. 2025;17(18):3015. ',
      doiLabel: 'doi:10.3390/cancers17183015',
      href: 'https://doi.org/10.3390/cancers17183015',
    },
    {
      authorsBefore: 'Mansour S, ',
      highlight: 'Aburayya BI',
      authorsAfter: ', Al Ramadneh J, Shakhatreh Z, Alsmadi AS, Ali AA, Shahait AD. ',
      citation:
        'A global registry-based analysis of clinical trials on robotic-assisted inguinal hernia repair: current landscape and research gaps. J Robot Surg. 2025 Aug 4;19(1):447. ',
      doiLabel: 'doi:10.1007/s11701-025-02614-9',
      href: 'https://doi.org/10.1007/s11701-025-02614-9',
    },
    {
      authorsBefore: 'Foroutani L, Ashraf Ganjouei A, Wang JJ, ',
      highlight: 'Aburayya BI',
      authorsAfter: ', Corvera C, Alseidi A, Adam MA. ',
      citation:
        'ASO Author Reflections: Innovative Robot-Assisted Endoluminal Resection for Gastroesophageal Junction Leiomyomas. Ann Surg Oncol. 2025 Feb;32(2):1251-1252. ',
      doiLabel: 'doi:10.1245/s10434-024-16613-x',
      href: 'https://doi.org/10.1245/s10434-024-16613-x',
    },
    {
      authorsBefore: 'Foroutani L, Ashraf Ganjouei A, Wang J, ',
      highlight: 'Aburayya BI',
      authorsAfter: ', Corvera C, Alseidi A, Adam MA. ',
      citation:
        'Robotic-Assisted Endoluminal Resection of Gastroesophageal Junction Leiomyoma with Transoral Specimen Extraction: Technique, Outcome, and Safety. Ann Surg Oncol. 2025 Feb;32(2):1218-1219. ',
      doiLabel: 'doi:10.1245/s10434-024-16426-y',
      href: 'https://doi.org/10.1245/s10434-024-16426-y',
    },
    {
      authorsBefore: '',
      highlight: 'Aburayya BI',
      authorsAfter: ', Al-Hayk AK, Toubasi AA, Ali A, Shahait AD. ',
      citation:
        'Critical view of safety approach vs. infundibular technique in laparoscopic cholecystectomy, which one is safer? A systematic review and meta-analysis. Updates Surg. 2024 Nov 11. ',
      doiLabel: 'doi:10.1007/s13304-024-02029-5',
      href: 'https://doi.org/10.1007/s13304-024-02029-5',
    },
    {
      authorsBefore: '',
      highlight: 'Aburayya BI',
      authorsAfter: ', Obeidat LR, Kitana FI, Al Khatib O, Romman S, Hamed OH. ',
      citation:
        'Complete Common Bile Duct Injury after Laparoscopic Cholecystectomy in Situs Inversus Totalis: A Case Report, Review of the Literature and Illustrative Case Video. Int J Surg Case Rep. 2024 Feb;115:109265. ',
      doiLabel: 'doi:10.1016/j.ijscr.2024.109265',
      href: 'https://doi.org/10.1016/j.ijscr.2024.109265',
    },
    {
      authorsBefore: 'Jbarah OF, ',
      highlight: 'Aburayya BI',
      authorsAfter:
        ', Shatnawi AR, Alkhasoneh MA, Toubasi AA, Alharahsheh SM, Nukho SK, Nassar AS, Jamous MA. ',
      citation:
        'Risk of meningitis after posterior fossa decompression with duraplasty using different graft types in patients with Chiari malformation type I and syringomyelia: a systematic review and meta-analysis. Neurosurg Rev. 2022 Dec;45(6):3537-3550. ',
      doiLabel: 'doi:10.1007/s10143-022-01873-6',
      href: 'https://doi.org/10.1007/s10143-022-01873-6',
    },
  ] as const,
} as const

export const aboutPresentations = {
  kicker: 'Academic Engagement',
  title: 'Presentation Highlights',
  lead: 'Selected podium and poster presentations at national and international surgical meetings — evidence of active participation in the research community.',
  items: [
    {
      year: '2025',
      name: 'SSO ACT Meeting',
      detail: 'Society of Surgical Oncology — Scottsdale, AZ',
    },
    {
      year: '2025',
      name: 'NCC-ACS Annual Meeting',
      detail: 'Northern California Chapter, American College of Surgeons',
    },
    {
      year: '2025',
      name: 'EAES Congress',
      detail: '33rd International EAES Congress — Belgrade, Serbia',
    },
    {
      year: '2024',
      name: 'SAGES Annual Meeting',
      detail:
        'Society of American Gastrointestinal and Endoscopic Surgeons — Cleveland, OH',
    },
  ] as const,
} as const

export const aboutStory = {
  titleBefore: 'Why I Created',
  titleHighlight: 'Research Spectrum',
  paragraphs: [
    'Research training is often fragmented. Students are expected to learn statistics from one source, scientific writing from another, and systematic reviews from somewhere else entirely — with no single path that connects these skills into a cohesive, publishable research capability.',
    'Many talented clinicians and students abandon research not because they lack the intellectual ability, but because they lack structured guidance. I watched this happen repeatedly — colleagues with genuine curiosity and valuable clinical observations who had no framework for converting those observations into publishable work.',
  ] as const,
  pullQuote:
    '"I also lived through this confusion myself. My own research education was self-directed, scattered, and inefficient. The skills I eventually developed came from years of trial, error, reading, and mentorship — a path that was far harder than it needed to be."',
  closing:
    "Research Spectrum is my answer to that problem — built so the next person doesn't have to find their own way through the confusion the way I did.",
} as const

export const aboutCourses = {
  kicker: 'The Curriculum',
  title: 'Courses I Teach',
  lead: 'Four flagship courses covering the complete research lifecycle — from study design to peer-reviewed publication.',
  emptyMessage: 'Courses will appear here',
  viewCourse: 'View Course',
  retryLabel: 'Try again',
} as const

export const aboutDifference = {
  kicker: 'The Difference',
  title: 'What Makes Research Spectrum Different',
  lead: 'Most research education teaches you about research — Research Spectrum teaches you to do it.',
  cards: [
    {
      title: 'Four Connected Courses',
      body: 'A single curriculum that covers the full research cycle — methodology, statistics, writing, and systematic reviews — built to work together, not as standalone topics.',
      tone: 'blue' as const,
    },
    {
      title: 'Real Datasets, Real Practice',
      body: 'Every concept is reinforced with authentic datasets and research scenarios, so skills are built through application rather than abstract theory.',
      tone: 'blue' as const,
    },
    {
      title: 'Competency-Based Learning',
      body: 'Progress is measured by what you can actually do — design a study, run an analysis, write a manuscript — not just by lessons completed.',
      tone: 'blue' as const,
    },
    {
      title: 'Research Team Pathway',
      body: 'Graduates of all four courses become eligible to apply for the Research Team and continue their development beyond the curriculum.',
      tone: 'success' as const,
    },
    {
      title: 'Authorship Opportunities',
      body: 'Research Team members contribute to active studies and can earn authorship on peer-reviewed publications through meaningful, documented work.',
      tone: 'amber' as const,
    },
    {
      title: 'Publication-Oriented Training',
      body: 'From the first lesson, every course is oriented toward one outcome: a publication-ready research capability you can use independently.',
      tone: 'blue' as const,
    },
  ] as const,
} as const

export const aboutAudience = {
  kicker: 'Is This For You?',
  title: 'Who Research Spectrum Is For',
  lead: 'If you see yourself here, these courses were built for you.',
  cards: [
    {
      title: 'Medical Students',
      body: 'Building your research skills early — before residency, before fellowship, and before the pressure begins.',
    },
    {
      title: 'Residents & Fellows',
      body: 'Time-limited and training-focused — you need practical, efficient research skills that fit your schedule.',
    },
    {
      title: 'Physicians & Clinicians',
      body: 'You have clinical observations and questions — you just need the tools to turn them into publishable research.',
    },
    {
      title: 'Nurses & Allied Health',
      body: 'Research literacy and publication skills are increasingly important across all healthcare roles, not just physicians.',
    },
    {
      title: 'Early-Career Researchers',
      body: 'Stepping into research without a mentor or structured program — you need a clear, self-directed learning path.',
    },
    {
      title: 'Aspiring Academic Researchers',
      body: 'Working toward a career built on publications and academic standing — you need a reliable system for producing research consistently.',
    },
  ] as const,
} as const

export const aboutFinalCta = {
  kicker: 'Begin Your Journey',
  title: 'Start Your Research Journey',
  lead: "Whether you're taking your first steps into research or looking to strengthen your existing skills, Research Spectrum is designed to help you build practical, publication-ready research capabilities.",
  primaryCta: 'Explore Courses',
  secondaryCta: 'Read My Story',
} as const
