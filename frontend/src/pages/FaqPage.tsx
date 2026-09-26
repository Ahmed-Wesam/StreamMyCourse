import { usePageTitle } from '../lib/page-title'
import { FaqCategoriesSection } from './faq/FaqCategoriesSection'
import { FaqCategoryNav } from './faq/FaqCategoryNav'
import { FaqHeroSection } from './faq/FaqHeroSection'
import { FaqStillNeedHelpSection } from './faq/FaqStillNeedHelpSection'

export default function FaqPage() {
  usePageTitle('FAQ')

  return (
    <div className="min-h-screen bg-white text-rs-ink" data-testid="student-page-faq">
      <FaqHeroSection />
      <FaqCategoryNav />
      <FaqCategoriesSection />
      <FaqStillNeedHelpSection />
    </div>
  )
}
