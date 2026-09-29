"""Who may be issued a certificate (RS-12).

Playback access is a different rule: course owners and admins can watch without
a purchase, and a non-owner loses playback when a course is unpublished.
Certificates do not use that bypass.
"""

from __future__ import annotations


def is_certificate_entitled(
    *,
    has_paid_course_purchase: bool,
    has_paid_bundle: bool,
    course_published: bool,
    has_course_activity: bool = False,
) -> bool:
    """Paid course purchase at any status, or a paid bundle of a published course.

    A bundle also covers an unpublished course when the student already has a
    quiz attempt or assignment submission there, so unpublishing does not drop
    someone who already started. Ownership and admin role are not inputs.
    Untouched drafts stay off the certificates page.
    """
    if has_paid_course_purchase:
        return True
    if not has_paid_bundle:
        return False
    if course_published or has_course_activity:
        return True
    return False
