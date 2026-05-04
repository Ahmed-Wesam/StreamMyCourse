/**
 * Extract a JPEG frame at `percent` of the video's duration (0–1) using a local File.
 * Used when no lesson thumbnail image is uploaded.
 */
export async function captureFrameAtVideoPercent(file: File, percent: number): Promise<Blob> {
  const url = URL.createObjectURL(file)
  const video = document.createElement('video')
  video.muted = true
  video.playsInline = true
  video.setAttribute('playsinline', '')
  video.preload = 'auto'
  video.src = url

  try {
    await new Promise<void>((resolve, reject) => {
      video.onloadedmetadata = () => resolve()
      video.onerror = () => reject(new Error('Could not read video metadata'))
    })

    const duration = video.duration
    if (!Number.isFinite(duration) || duration <= 0) {
      throw new Error('Invalid video duration')
    }

    const t = Math.min(Math.max(duration * percent, 0), Math.max(duration - 0.05, 0))

    await new Promise<void>((resolve, reject) => {
      const done = () => {
        video.removeEventListener('seeked', done)
        video.removeEventListener('error', onErr)
        resolve()
      }
      const onErr = () => {
        video.removeEventListener('seeked', done)
        video.removeEventListener('error', onErr)
        reject(new Error('Could not seek in video'))
      }
      video.addEventListener('seeked', done, { once: true })
      video.addEventListener('error', onErr, { once: true })
      video.currentTime = t
    })

    const w = video.videoWidth
    const h = video.videoHeight
    if (!w || !h) {
      throw new Error('Video has no frame dimensions')
    }

    const canvas = document.createElement('canvas')
    canvas.width = w
    canvas.height = h
    const ctx = canvas.getContext('2d')
    if (!ctx) {
      throw new Error('Canvas not available')
    }
    ctx.drawImage(video, 0, 0, w, h)

    return new Promise((resolve, reject) => {
      canvas.toBlob(
        (blob) => {
          if (blob) resolve(blob)
          else reject(new Error('Could not encode thumbnail'))
        },
        'image/jpeg',
        0.85,
      )
    })
  } finally {
    URL.revokeObjectURL(url)
  }
}
