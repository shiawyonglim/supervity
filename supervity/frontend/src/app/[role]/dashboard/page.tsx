'use client'

import { useParams, notFound } from 'next/navigation'
import { isAppRole } from '@/context/RoleContext'
import { SalesDashboard } from '@/components/role-views/SalesDashboard'
import { CRODashboard } from '@/components/role-views/CRODashboard'

export default function RoleDashboardPage() {
  const params = useParams()
  const role = params.role as string

  if (!isAppRole(role)) return notFound()
  if (role === 'admin') return notFound()

  if (role === 'cro') return <CRODashboard />
  return <SalesDashboard role={role} />
}
