export type AppError =
  | {
      kind: 'HTTP'
      status: number
      code: string
      message: string
      details?: Record<string, unknown>
    }
  | {
      kind: 'NETWORK'
      message: string
      isOffline: boolean
    }
  | {
      kind: 'TIMEOUT'
      durationMs: number
      message: string
    }
  | {
      kind: 'ABORT'
      reason: string
      message: string
    }
  | {
      kind: 'AUTH'
      code: 'SESSION_EXPIRED' | 'UNAUTHORIZED' | 'FORBIDDEN'
      message: string
    }

export class ApplicationError extends Error {
  readonly appError: AppError

  constructor(appError: AppError) {
    super(appError.message)
    this.name = 'ApplicationError'
    this.appError = appError
  }
}

export function isAppError(error: unknown): error is ApplicationError {
  return error instanceof ApplicationError
}

export function formatErrorMessage(error: unknown): string {
  if (isAppError(error)) {
    return error.appError.message
  }
  if (error instanceof Error) {
    return error.message
  }
  return 'An unexpected error occurred. Please try again.'
}
