'use client'

import { useParams, notFound } from 'next/navigation'
import { isAppRole } from '@/context/RoleContext'
import { SalesWorkbench } from '@/components/role-views/SalesWorkbench'
import { CROWorkbench } from '@/components/role-views/CROWorkbench'

export default function RoleWorkbenchPage() {
  const params = useParams()
  const role = params.role as string

  if (!isAppRole(role)) return notFound()
  if (role === 'admin') return notFound()

  if (role === 'cro') return <CROWorkbench />
  return <SalesWorkbench role={role} />
}
