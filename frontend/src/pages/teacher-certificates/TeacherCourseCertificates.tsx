import { useCallback, useEffect, useState } from 'react'
import {
  listCourseCertificates,
  revokeCourseCertificate,
  type CourseCertificate,
} from '../../lib/api/certificates'
import { catalogApiUserMessage } from '../../lib/apiUserMessages'
import { Badge } from '../../components/ui/Badge'
import { Button } from '../../components/ui/Button'
import { Card } from '../../components/ui/Card'

type Props = {
  courseId: string
}

export function TeacherCourseCertificates({ courseId }: Props) {
  const [certificates, setCertificates] = useState<CourseCertificate[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [revokingId, setRevokingId] = useState<string | null>(null)

  const load = useCallback(async () => {
    if (!courseId) return
    try {
      setLoading(true)
      setError(null)
      const data = await listCourseCertificates(courseId)
      setCertificates(data.certificates)
    } catch (err) {
      setError(catalogApiUserMessage(err))
      setCertificates([])
    } finally {
      setLoading(false)
    }
  }, [courseId])

  useEffect(() => {
    void load()
  }, [load])

  const handleRevoke = async (certificateId: string) => {
    if (!window.confirm('Revoke this certificate? This cannot be undone.')) return
    try {
      setError(null)
      setRevokingId(certificateId)
      const result = await revokeCourseCertificate(courseId, certificateId)
      setCertificates((prev) =>
        prev.map((row) =>
          row.id === certificateId
            ? { ...row, status: result.status === 'revoked' ? 'revoked' : row.status }
            : row,
        ),
      )
    } catch (err) {
      setError(catalogApiUserMessage(err))
    } finally {
      setRevokingId(null)
    }
  }

  return (
    <Card className="mb-6 p-6" data-testid="teacher-course-certificates">
      <h2 className="mb-4 text-xl font-extrabold text-rs-navy">Certificates</h2>

      {error ? (
        <div
          className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700"
          role="alert"
        >
          {error}
        </div>
      ) : null}

      {loading ? (
        <p className="text-sm text-rs-body">Loading certificates…</p>
      ) : certificates.length === 0 ? (
        <p className="text-sm text-rs-body">No certificates issued</p>
      ) : (
        <div className="space-y-3">
          {certificates.map((cert) => {
            const isValid = cert.status === 'valid'
            return (
              <div
                key={cert.id}
                className="flex flex-wrap items-start justify-between gap-4 rounded-lg border border-rs-line p-4"
              >
                <div className="min-w-0 space-y-1">
                  <div className="font-semibold text-rs-navy">{cert.studentName}</div>
                  <div className="text-sm text-rs-body">
                    Credential ID: <span className="font-medium text-rs-ink">{cert.credentialId}</span>
                  </div>
                  <div className="text-sm text-rs-body">Issued: {cert.issueDate}</div>
                  <div className="pt-1">
                    <Badge tone={isValid ? 'success' : 'neutral'}>{cert.status}</Badge>
                  </div>
                </div>
                {isValid ? (
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="!text-red-700 hover:!bg-red-50"
                    disabled={revokingId === cert.id}
                    onClick={() => void handleRevoke(cert.id)}
                  >
                    {revokingId === cert.id ? 'Revoking…' : 'Revoke'}
                  </Button>
                ) : null}
              </div>
            )
          })}
        </div>
      )}
    </Card>
  )
}
