import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import CourseDetailPage from '../pages/CourseDetailPage'
import { StudentModuleQuizAuth } from '../components/auth/StudentModuleQuizAuth'
import CoursePage from '../pages/CoursePage'
import HomePage from '../pages/HomePage'
import LearnRedirectPage from '../pages/LearnRedirectPage'
import MyCoursePage from '../pages/MyCoursePage'
import BillingCancelPage from '../pages/BillingCancelPage'
import BillingSuccessPage from '../pages/BillingSuccessPage'
import StudentLoginPage from '../pages/StudentLoginPage'
import { PostLoginRedirect } from '../components/auth/PostLoginRedirect'
import { StudentProfileBootstrap } from '../components/auth/StudentProfileBootstrap'
import { StudentAccountAuth } from '../components/auth/StudentAccountAuth'
import { StudentLessonAuth } from '../components/auth/StudentLessonAuth'
import AccountProfilePage from '../pages/account/AccountProfilePage'
import AccountSubscriptionPage from '../pages/account/AccountSubscriptionPage'
import { AccountLayout } from '../pages/account/AccountLayout'
import { StudentHeader } from './StudentHeader'
import { Layout } from '../components/layout/Layout'
import { ScrollToTop } from './ScrollToTop'

function LegacyPathRedirect({ to }: { to: string }) {
  const location = useLocation()
  return <Navigate to={`${to}${location.hash}`} replace />
}

function StudentApp() {
  return (
    <Layout chromeHeader={<StudentHeader />}>
      <ScrollToTop />
      <PostLoginRedirect />
      <StudentProfileBootstrap />
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/details" element={<CoursePage />} />
        <Route path="/course" element={<LegacyPathRedirect to="/details" />} />
        <Route path="/learn" element={<LearnRedirectPage />} />
        <Route path="/courses" element={<MyCoursePage />} />
        <Route path="/catalog" element={<LegacyPathRedirect to="/courses" />} />
        <Route path="/my-course" element={<Navigate to="/courses" replace />} />
        <Route path="/courses/:courseId" element={<CourseDetailPage />} />
        <Route path="/courses/:courseId/modules/:moduleId/quiz" element={<StudentModuleQuizAuth />} />
        <Route path="/login" element={<StudentLoginPage />} />
        <Route path="/account" element={<StudentAccountAuth />}>
          <Route element={<AccountLayout />}>
            <Route index element={<Navigate to="profile" replace />} />
            <Route path="profile" element={<AccountProfilePage />} />
            <Route path="subscription" element={<AccountSubscriptionPage />} />
          </Route>
        </Route>
        <Route path="/billing/success" element={<BillingSuccessPage />} />
        <Route path="/billing/cancel" element={<BillingCancelPage />} />
        <Route path="/courses/:courseId/lessons/:lessonId" element={<StudentLessonAuth />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  )
}

export default StudentApp
