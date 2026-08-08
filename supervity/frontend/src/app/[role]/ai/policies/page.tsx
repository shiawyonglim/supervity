'use client'

import { useParams, notFound } from 'next/navigation'
import { isAppRole } from '@/context/RoleContext'
import { RoleAIPolicies } from '@/components/role-views/RoleAIPolicies'

export default function RoleAIPoliciesPage() {
  const params = useParams()
  const role = params.role as string

  if (!isAppRole(role)) return notFound()
  if (role === 'admin') return notFound()

  return <RoleAIPolicies role={role} />
}
