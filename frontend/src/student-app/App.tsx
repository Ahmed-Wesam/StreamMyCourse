import { lazy } from 'react'
import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import HomePage from '../pages/HomePage'
import { AuthGate } from '../components/auth/AuthGate'
import { StudentAccountAuth } from '../components/auth/StudentAccountAuth'
import { AccountLayout } from '../pages/account/AccountLayout'
import { StudentHeader } from './StudentHeader'
import { StudentSessionGuard } from './StudentSessionGuard'
import { Layout } from '../components/layout/Layout'
import { LazyRoute } from '../components/layout/RouteChunkFallback'
import { ScrollToTop } from './ScrollToTop'

const CoursePage = lazy(() => import('../pages/CoursePage'))
const CourseDetailPage = lazy(() => import('../pages/CourseDetailPage'))
const LearnRedirectPage = lazy(() => import('../pages/LearnRedirectPage'))
const MyCoursePage = lazy(() => import('../pages/MyCoursePage'))
const StudentLessonAuth = lazy(() =>
  import('../components/auth/StudentLessonAuth').then((m) => ({ default: m.StudentLessonAuth })),
)
const StudentModuleQuizAuth = lazy(() =>
  import('../components/auth/StudentModuleQuizAuth').then((m) => ({ default: m.StudentModuleQuizAuth })),
)
const StudentLoginPage = lazy(() => import('../pages/StudentLoginPage'))
const AccountProfilePage = lazy(() => import('../pages/account/AccountProfilePage'))
const AccountSubscriptionPage = lazy(() => import('../pages/account/AccountSubscriptionPage'))
const BillingSuccessPage = lazy(() => import('../pages/BillingSuccessPage'))
const BillingCancelPage = lazy(() => import('../pages/BillingCancelPage'))
const PrivacyPage = lazy(() => import('../pages/legal/PrivacyPage'))
const TermsPage = lazy(() => import('../pages/legal/TermsPage'))

function LegacyPathRedirect({ to }: { to: string }) {
  const location = useLocation()
  return <Navigate to={`${to}${location.hash}`} replace />
}

function StudentApp() {
  return (
    <AuthGate>
      <StudentSessionGuard>
        <Layout chromeHeader={<StudentHeader />}>
        <ScrollToTop />
        <Routes>
        <Route path="/" element={<HomePage />} />
        <Route
          path="/details"
          element={
            <LazyRoute>
              <CoursePage />
            </LazyRoute>
          }
        />
        <Route path="/course" element={<LegacyPathRedirect to="/details" />} />
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
              <MyCoursePage />
            </LazyRoute>
          }
        />
        <Route path="/catalog" element={<LegacyPathRedirect to="/courses" />} />
        <Route path="/my-course" element={<Navigate to="/courses" replace />} />
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
              path="subscription"
              element={
                <LazyRoute>
                  <AccountSubscriptionPage />
                </LazyRoute>
              }
            />
          </Route>
        </Route>
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
          path="/courses/:courseId/lessons/:lessonId"
          element={
            <LazyRoute>
              <StudentLessonAuth />
            </LazyRoute>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Layout>
      </StudentSessionGuard>
    </AuthGate>
  )
}

export default StudentApp
