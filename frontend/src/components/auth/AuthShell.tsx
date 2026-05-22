import 'aws-amplify/auth/enable-oauth-listener'

import { AuthenticatorProvider } from '@aws-amplify/ui-react-core'
import type { ReactNode } from 'react'

import { configureAmplify } from '../../lib/auth'
import { PostLoginRedirect } from './PostLoginRedirect'
import { StudentProfileBootstrap } from './StudentProfileBootstrap'

/** Run once when the auth chunk loads so OAuth callback on `/` can complete before paint. */
configureAmplify()

export default function AuthShell({ children }: { children: ReactNode }) {
  return (
    <AuthenticatorProvider>
      <PostLoginRedirect />
      <StudentProfileBootstrap />
      {children}
    </AuthenticatorProvider>
  )
}
