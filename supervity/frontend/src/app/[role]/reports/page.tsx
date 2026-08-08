'use client'

import { useParams, notFound } from 'next/navigation'
import { isAppRole } from '@/context/RoleContext'
import { WeeklyReport } from '@/components/reports/WeeklyReport'

export default function RoleReportsPage() {
  const params = useParams()
  const role = params.role as string

  if (!isAppRole(role)) return notFound()

  return <WeeklyReport />
}
