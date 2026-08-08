'use client'

import { useParams, notFound } from 'next/navigation'
import { isAppRole } from '@/context/RoleContext'
import { RoleAIManager } from '@/components/role-views/RoleAIManager'

export default function RoleAIManagerPage() {
  const params = useParams()
  const role = params.role as string

  if (!isAppRole(role)) return notFound()
  if (role === 'admin') return notFound()

  return <RoleAIManager role={role} />
}
