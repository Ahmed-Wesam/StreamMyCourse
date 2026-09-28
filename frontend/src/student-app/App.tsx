import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { AuthGate } from '../components/auth/AuthGate'
import { StudentAccountAuth } from '../components/auth/StudentAccountAuth'
import { StudentDashboardAuth } from '../components/auth/StudentDashboardAuth'
import { StudentTermsGate } from '../components/auth/StudentTermsGate'
import { AccountLayout } from '../pages/account/AccountLayout'
import { StudentHeader } from './StudentHeader'
const StudentSessionGuard = lazy(() =>
  import('./StudentSessionGuard').then((m) => ({ default: m.StudentSessionGuard })),
)
import { Layout } from '../components/layout/Layout'
import { LazyRoute } from '../components/layout/RouteChunkFallback'
import { ScrollToTop } from './ScrollToTop'

const HomePage = lazy(() => import('../pages/HomePage'))
const AboutInstructorPage = lazy(() => import('../pages/AboutInstructorPage'))
const FaqPage = lazy(() => import('../pages/FaqPage'))
const ContactPage = lazy(() => import('../pages/ContactPage'))
const ResearchTeamPage = lazy(() => import('../pages/ResearchTeamPage'))
const CoursesCatalogPage = lazy(() => import('../pages/CoursesCatalogPage'))
const StudentDashboardPage = lazy(() => import('../pages/StudentDashboardPage'))
const CourseDetailPage = lazy(() => import('../pages/CourseDetailPage'))
const LearnRedirectPage = lazy(() => import('../pages/LearnRedirectPage'))
const StudentLessonAuth = lazy(() =>
  import('../components/auth/StudentLessonAuth').then((m) => ({ default: m.StudentLessonAuth })),
)
const StudentAssignmentAuth = lazy(() =>
  import('../components/auth/StudentAssignmentAuth').then((m) => ({
    default: m.StudentAssignmentAuth,
  })),
)
const StudentModuleQuizAuth = lazy(() =>
  import('../components/auth/StudentModuleQuizAuth').then((m) => ({ default: m.StudentModuleQuizAuth })),
)
const StudentLoginPage = lazy(() => import('../pages/StudentLoginPage'))
const StudentRegisterPage = lazy(() => import('../pages/StudentRegisterPage'))
const VerifyEmailPage = lazy(() => import('../pages/VerifyEmailPage'))
const ForgotPasswordPage = lazy(() => import('../pages/ForgotPasswordPage'))
const ResetPasswordPage = lazy(() => import('../pages/ResetPasswordPage'))
const AccountProfilePage = lazy(() => import('../pages/account/AccountProfilePage'))
const AccountPurchasesPage = lazy(() => import('../pages/account/AccountPurchasesPage'))
const CheckoutPage = lazy(() => import('../pages/CheckoutPage'))
const BillingSuccessPage = lazy(() => import('../pages/BillingSuccessPage'))
const BillingCancelPage = lazy(() => import('../pages/BillingCancelPage'))
const PrivacyPage = lazy(() => import('../pages/legal/PrivacyPage'))
const TermsPage = lazy(() => import('../pages/legal/TermsPage'))
const RefundPage = lazy(() => import('../pages/legal/RefundPage'))
const DeliveryPage = lazy(() => import('../pages/legal/DeliveryPage'))
const EducationalDisclaimerPage = lazy(() => import('../pages/legal/EducationalDisclaimerPage'))

function LegacyPathRedirect({ to }: { to: string }) {
  const location = useLocation()
  return <Navigate to={`${to}${location.hash}`} replace />
}

function StudentApp() {
  return (
    <AuthGate>
      <Suspense fallback={null}>
        <StudentSessionGuard>
        <StudentTermsGate>
        <Layout chromeHeader={<StudentHeader />}>
        <ScrollToTop />
        <Routes>
        <Route
          path="/"
          element={
            <LazyRoute>
              <HomePage />
            </LazyRoute>
          }
        />
        <Route
          path="/about"
          element={
            <LazyRoute>
              <AboutInstructorPage />
            </LazyRoute>
          }
        />
        <Route
          path="/faq"
          element={
            <LazyRoute>
              <FaqPage />
            </LazyRoute>
          }
        />
        <Route
          path="/contact"
          element={
            <LazyRoute>
              <ContactPage />
            </LazyRoute>
          }
        />
        <Route
          path="/research-team"
          element={
            <LazyRoute>
              <ResearchTeamPage />
            </LazyRoute>
          }
        />
        <Route path="/details" element={<LegacyPathRedirect to="/courses" />} />
        <Route path="/course" element={<LegacyPathRedirect to="/courses" />} />
        <Route
          path="/learn"
          element={
            <LazyRoute>
              <LearnRedirectPage />
            </LazyRoute>
          }
        />
        <Route
          path="/courses"
          element={
            <LazyRoute>
              <CoursesCatalogPage />
            </LazyRoute>
          }
        />
        <Route path="/catalog" element={<LegacyPathRedirect to="/courses" />} />
        <Route path="/my-course" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<StudentDashboardAuth />}>
          <Route
            index
            element={
              <LazyRoute>
                <StudentDashboardPage />
              </LazyRoute>
            }
          />
        </Route>
        <Route
          path="/courses/:courseId"
          element={
            <LazyRoute>
              <CourseDetailPage />
            </LazyRoute>
          }
        />
        <Route
          path="/courses/:courseId/modules/:moduleId/quiz"
          element={
            <LazyRoute>
              <StudentModuleQuizAuth />
            </LazyRoute>
          }
        />
        <Route
          path="/login"
          element={
            <LazyRoute>
              <StudentLoginPage />
            </LazyRoute>
          }
        />
        <Route
          path="/register"
          element={
            <LazyRoute>
              <StudentRegisterPage />
            </LazyRoute>
          }
        />
        <Route
          path="/verify-email"
          element={
            <LazyRoute>
              <VerifyEmailPage />
            </LazyRoute>
          }
        />
        <Route
          path="/forgot-password"
          element={
            <LazyRoute>
              <ForgotPasswordPage />
            </LazyRoute>
          }
        />
        <Route
          path="/reset-password"
          element={
            <LazyRoute>
              <ResetPasswordPage />
            </LazyRoute>
          }
        />
        <Route path="/account" element={<StudentAccountAuth />}>
          <Route element={<AccountLayout />}>
            <Route index element={<Navigate to="profile" replace />} />
            <Route
              path="profile"
              element={
                <LazyRoute>
                  <AccountProfilePage />
                </LazyRoute>
              }
            />
            <Route
              path="purchases"
              element={
                <LazyRoute>
                  <AccountPurchasesPage />
                </LazyRoute>
              }
            />
            <Route path="subscription" element={<Navigate to="../purchases" replace />} />
          </Route>
        </Route>
        <Route
          path="/checkout"
          element={
            <LazyRoute>
              <CheckoutPage />
            </LazyRoute>
          }
        />
        <Route
          path="/billing/success"
          element={
            <LazyRoute>
              <BillingSuccessPage />
            </LazyRoute>
          }
        />
        <Route
          path="/billing/cancel"
          element={
            <LazyRoute>
              <BillingCancelPage />
            </LazyRoute>
          }
        />
        <Route
          path="/privacy"
          element={
            <LazyRoute>
              <PrivacyPage />
            </LazyRoute>
          }
        />
        <Route
          path="/terms"
          element={
            <LazyRoute>
              <TermsPage />
            </LazyRoute>
          }
        />
        <Route
          path="/refund"
          element={
            <LazyRoute>
              <RefundPage />
            </LazyRoute>
          }
        />
        <Route
          path="/delivery"
          element={
            <LazyRoute>
              <DeliveryPage />
            </LazyRoute>
          }
        />
        <Route
          path="/educational-disclaimer"
          element={
            <LazyRoute>
              <EducationalDisclaimerPage />
            </LazyRoute>
          }
        />
        <Route
          path="/courses/:courseId/lessons/:lessonId"
          element={
            <LazyRoute>
              <StudentLessonAuth />
            </LazyRoute>
          }
        />
        <Route
          path="/courses/:courseId/assignments/:assignmentId"
          element={
            <LazyRoute>
              <StudentAssignmentAuth />
            </LazyRoute>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Layout>
        </StudentTermsGate>
        </StudentSessionGuard>
      </Suspense>
    </AuthGate>
  )
}

export default StudentApp
