export const TASK_STATUSES = ['TODO', 'IN_PROGRESS', 'DONE']
export const PRIORITIES = ['LOW', 'MEDIUM', 'HIGH']
export const RELEASE_STATUSES = ['PLANNED', 'READY', 'DEPLOYING', 'DEPLOYED', 'FAILED']
export const ENVIRONMENTS = ['dev', 'staging', 'prod']

export const releaseStatusVariant = {
  PLANNED: 'secondary',
  READY: 'warning',
  DEPLOYING: 'warning',
  DEPLOYED: 'success',
  FAILED: 'destructive',
}

export const taskStatusVariant = {
  TODO: 'secondary',
  IN_PROGRESS: 'warning',
  DONE: 'success',
}

export const priorityVariant = {
  LOW: 'secondary',
  MEDIUM: 'warning',
  HIGH: 'destructive',
}

export function humanize(value) {
  return value
    .toLowerCase()
    .split('_')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ')
}

export function formatTime(iso) {
  return new Date(iso).toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}
