import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import StudentApp from './student-app/App'
import './style.css'

void import('./lib/install-session-superseded-rejection-handler').then(
  ({ installSessionSupersededRejectionHandler }) => {
    installSessionSupersededRejectionHandler()
  },
)

ReactDOM.createRoot(document.getElementById('app')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <StudentApp />
    </BrowserRouter>
  </React.StrictMode>,
)
