'use client'

import { useParams, notFound } from 'next/navigation'
import { isAppRole } from '@/context/RoleContext'
import { RoleAIInsights } from '@/components/role-views/RoleAIInsights'

export default function RoleAIInsightsPage() {
  const params = useParams()
  const role = params.role as string

  if (!isAppRole(role)) return notFound()
  if (role === 'admin') return notFound()

  return <RoleAIInsights role={role} />
}
