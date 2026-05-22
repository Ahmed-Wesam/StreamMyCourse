import { lazy, Suspense } from 'react'
import { PostLoginRedirect } from '../components/auth/PostLoginRedirect'
import { Navigate, Route, Routes } from 'react-router-dom'
import InstructorDashboard from '../pages/InstructorDashboard'
import { ProtectedRoute } from '../components/auth/ProtectedRoute'
import { TeacherHeader } from './TeacherHeader'
import { Layout } from '../components/layout/Layout'
import { LazyRoute, RouteChunkFallback } from '../components/layout/RouteChunkFallback'

const SignIn = lazy(() =>
  import('../components/auth/SignIn').then((mod) => ({ default: mod.SignIn })),
)

const CourseManagement = lazy(() => import('../pages/CourseManagement'))
const QuestionBanksListPage = lazy(() => import('../pages/QuestionBanksListPage'))
const QuestionBankStudioPage = lazy(() => import('../pages/QuestionBankStudioPage'))
const TeacherPaymentSetup = lazy(() => import('../pages/TeacherPaymentSetup'))

function TeacherShell() {
  return (
    <ProtectedRoute>
      <Layout chromeHeader={<TeacherHeader />}>
        <Routes>
          <Route path="/" element={<InstructorDashboard />} />
          <Route
            path="/courses/:courseId/question-banks/:bankId"
            element={
              <LazyRoute>
                <QuestionBankStudioPage />
              </LazyRoute>
            }
          />
          <Route
            path="/courses/:courseId/question-banks"
            element={
              <LazyRoute>
                <QuestionBanksListPage />
              </LazyRoute>
            }
          />
          <Route
            path="/courses/:courseId"
            element={
              <LazyRoute>
                <CourseManagement />
              </LazyRoute>
            }
          />
          <Route
            path="/settings/payments"
            element={
              <LazyRoute>
                <TeacherPaymentSetup />
              </LazyRoute>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Layout>
    </ProtectedRoute>
  )
}

function TeacherApp() {
  return (
    <>
      <PostLoginRedirect />
      <Suspense fallback={<RouteChunkFallback />}>
        <SignIn>
          <TeacherShell />
        </SignIn>
      </Suspense>
    </>
  )
}

export default TeacherApp
