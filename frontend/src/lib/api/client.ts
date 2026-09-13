import ky, { isHTTPError, isTimeoutError } from 'ky'
import { getAuthHeader } from '@/lib/auth/session-manager'
import { ApplicationError } from './errors'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export const api = ky.create({
  prefix: API_BASE_URL,
  timeout: 30_000,
  hooks: {
    beforeRequest: [
      async ({ request }) => {
        const authHeader = await getAuthHeader()
        if (authHeader) {
          request.headers.set('Authorization', authHeader)
        }
      },
    ],
    beforeError: [
      async ({ error }) => {
        if (isHTTPError(error)) {
          const response = error.response
          let details: Record<string, unknown> | undefined
          let message = `Request failed with status ${response.status}`

          try {
            const body = await response.json()
            if (typeof body === 'object' && body !== null) {
              details = body as Record<string, unknown>
              if ('detail' in body && typeof body.detail === 'string') {
                message = body.detail
              } else if ('message' in body && typeof body.message === 'string') {
                message = body.message
              }
            }
          } catch {
            // Non-JSON error body
          }

          if (response.status === 401) {
            return new ApplicationError({
              kind: 'AUTH',
              code: 'UNAUTHORIZED',
              message: message || 'Authentication required.',
            })
          }

          if (response.status === 403) {
            return new ApplicationError({
              kind: 'AUTH',
              code: 'FORBIDDEN',
              message: message || 'You do not have permission to access this resource.',
            })
          }

          return new ApplicationError({
            kind: 'HTTP',
            status: response.status,
            code: `HTTP_${response.status}`,
            message,
            details,
          })
        }

        if (isTimeoutError(error) || error.name === 'TimeoutError') {
          return new ApplicationError({
            kind: 'TIMEOUT',
            durationMs: 30_000,
            message: 'Request timed out. Please try again.',
          })
        }

        if (error.name === 'AbortError') {
          return new ApplicationError({
            kind: 'ABORT',
            reason: 'Request cancelled by user.',
            message: 'Request cancelled by user.',
          })
        }

        return new ApplicationError({
          kind: 'NETWORK',
          message: error.message || 'Network error occurred.',
          isOffline: typeof navigator !== 'undefined' ? !navigator.onLine : false,
        })
      },
    ],
  },
})
