import { StatusBadge } from '../../components/shared/StatusBadge';
import type { LocationStatus } from '../../lib/types/api';

export function LocationStatusBadge({ status }: { status: LocationStatus }) {
  return <StatusBadge status={status} />;
}
