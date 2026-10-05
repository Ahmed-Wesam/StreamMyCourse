import { Link } from 'react-router-dom'

import { IconBook, IconChat, IconChevron, IconFlame, IconGear, IconMedal } from './dashboardIcons'

type StudentDashboardQuickRowProps = {
  streakDays: number
}

export function StudentDashboardQuickRow({ streakDays }: StudentDashboardQuickRowProps) {
  return (
    <section className="db" style={{ paddingBottom: 70 }}>
      <div className="wrap">
        <div className="split-2">
          <div>
            <div className="db-head">
              <div className="ht">
                <h2>Quick Actions</h2>
                <span className="htmeta">Common shortcuts</span>
              </div>
            </div>
            <div className="qa reveal">
              <div className="qa-grid">
                <Link className="qa-card" to="/courses#courses-catalog">
                  <span className="qi">
                    <IconBook />
                  </span>
                  <span className="qt">
                    <b>Explore Courses</b>
                    <span>Explore the full catalog</span>
                  </span>
                  <span className="qarr">
                    <IconChevron />
                  </span>
                </Link>
                <Link className="qa-card" to="/certificates">
                  <span className="qi">
                    <IconMedal />
                  </span>
                  <span className="qt">
                    <b>View Certificates</b>
                    <span>Download &amp; share</span>
                  </span>
                  <span className="qarr">
                    <IconChevron />
                  </span>
                </Link>
                <Link className="qa-card" to="/account/profile">
                  <span className="qi">
                    <IconGear />
                  </span>
                  <span className="qt">
                    <b>Account Settings</b>
                    <span>Profile &amp; preferences</span>
                  </span>
                  <span className="qarr">
                    <IconChevron />
                  </span>
                </Link>
                <Link className="qa-card" to="/contact">
                  <span className="qi">
                    <IconChat />
                  </span>
                  <span className="qt">
                    <b>Contact Support</b>
                    <span>We&apos;re here to help</span>
                  </span>
                  <span className="qarr">
                    <IconChevron />
                  </span>
                </Link>
              </div>
            </div>
          </div>

          <div>
            <div className="db-head">
              <div className="ht">
                <h2>Learning Streak</h2>
                <span className="htmeta">Keep the momentum going</span>
              </div>
            </div>
            <div className="streak reveal">
              <div className="top">
                <h3>Current Streak</h3>
                <div className="flame">
                  <IconFlame />
                </div>
              </div>
              <div className="big">
                {streakDays}
                <span className="u">days</span>
              </div>
              <div className="lbl">Personal Best · 0 Days</div>
              <div className="streak-stats">
                <div className="s">
                  <b>0</b>
                  <span>Lessons</span>
                </div>
                <div className="s">
                  <b>0h</b>
                  <span>Learned</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
