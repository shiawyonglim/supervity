'use client'

import { useParams, notFound } from 'next/navigation'
import { isAppRole } from '@/context/RoleContext'
import { SalesDataManager } from '@/components/role-views/SalesDataManager'
import { CRODataManager } from '@/components/role-views/CRODataManager'

export default function RoleDataManagerPage() {
  const params = useParams()
  const role = params.role as string

  if (!isAppRole(role)) return notFound()
  if (role === 'admin') return notFound()

  if (role === 'cro') return <CRODataManager />
  return <SalesDataManager role={role} />
}
