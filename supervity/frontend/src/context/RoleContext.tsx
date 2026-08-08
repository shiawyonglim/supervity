'use client'

import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react'
import { usePathname, useRouter } from 'next/navigation'

// ============================================================================
// Types & constants
// ============================================================================

export type AppRole = 'admin' | 'cro' | 'manager' | 'sales_agent' | 'sdr'

interface RoleMeta {
  label: string
  shortLabel: string
  description: string
  color: string
  isSales: boolean
}

export const ROLE_META: Record<AppRole, RoleMeta> = {
  admin: { label: 'Admin', shortLabel: 'Admin', description: 'Full system access', color: 'bg-slate-100 text-slate-700 border-slate-200', isSales: false },
  cro: { label: 'CRO', shortLabel: 'CRO', description: 'Revenue oversight & full access', color: 'bg-purple-100 text-purple-700 border-purple-200', isSales: false },
  manager: { label: 'Sales Manager', shortLabel: 'Manager', description: 'Closes deals & runs the team', color: 'bg-blue-100 text-blue-700 border-blue-200', isSales: true },
  sales_agent: { label: 'Sales Agent', shortLabel: 'Agent', description: 'Qualifies and pitches leads', color: 'bg-emerald-100 text-emerald-700 border-emerald-200', isSales: true },
  sdr: { label: 'SDR', shortLabel: 'SDR', description: 'First net for new leads', color: 'bg-amber-100 text-amber-700 border-amber-200', isSales: true },
}

export const SALES_ROLES: AppRole[] = ['sdr', 'sales_agent', 'manager']
export const ALL_ROLES: AppRole[] = ['admin', 'cro', 'manager', 'sales_agent', 'sdr']

export function isAppRole(value: unknown): value is AppRole {
  return typeof value === 'string' && (ALL_ROLES as string[]).includes(value)
}

const STORAGE_KEY = 'autopilot-active-role'

function roleFromPath(pathname: string): AppRole | null {
  const first = pathname.split('/').filter(Boolean)[0]
  if (!first || first === 'admin') return 'admin'
  if (ALL_ROLES.includes(first as AppRole)) return first as AppRole
  return null
}

// ============================================================================
// Context
// ============================================================================

interface RoleContextValue {
  activeRole: AppRole
  setRole: (role: AppRole) => void
  activeUserId: string
  setUserId: (id: string) => void
  roleMeta: RoleMeta
  isSalesRole: boolean
  isAdminOrCro: boolean
  isCro: boolean
  isAdmin: boolean
  roleLabel: string
  roleHref: (path?: string) => string
}

const RoleContext = createContext<RoleContextValue | null>(null)

export function useRole(): RoleContextValue {
  const ctx = useContext(RoleContext)
  if (!ctx) throw new Error('useRole must be used within a RoleProvider')
  return ctx
}

// ============================================================================
// Provider
// ============================================================================

export function RoleProvider({ children }: { children: ReactNode }) {
  const pathname = usePathname()
  const router = useRouter()

  const [activeRole, setActiveRole] = useState<AppRole>(() => {
    const fromPath = roleFromPath(pathname || '')
    if (fromPath) return fromPath
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem(STORAGE_KEY) as AppRole | null
      return stored && ALL_ROLES.includes(stored) ? stored : 'admin'
    }
    return 'admin'
  })

  // DEMO AUTH: This is a temporary stand-in for real per-user auth via JWT.
  const [activeUserId, setActiveUserId] = useState<string>(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem(`${STORAGE_KEY}-user-id`) || ''
    }
    return ''
  })

  // Sync active role with URL (back/forward buttons, direct links)
  useEffect(() => {
    const fromPath = roleFromPath(pathname || '')
    if (fromPath && fromPath !== activeRole) {
      setActiveRole(fromPath)
      localStorage.setItem(STORAGE_KEY, fromPath)
    }
  }, [pathname, activeRole])

  const setRole = useCallback(
    (role: AppRole) => {
      setActiveRole(role)
      if (typeof window !== 'undefined') {
        localStorage.setItem(STORAGE_KEY, role)
      }
      if (role === 'admin') {
        router.push('/')
      } else {
        router.push(`/${role}/dashboard`)
      }
    },
    [router]
  )

  const setUserId = useCallback((id: string) => {
    setActiveUserId(id)
    if (typeof window !== 'undefined') {
      localStorage.setItem(`${STORAGE_KEY}-user-id`, id)
    }
  }, [])

  const roleMeta = ROLE_META[activeRole]
  const isSalesRole = roleMeta.isSales
  const isAdminOrCro = activeRole === 'admin' || activeRole === 'cro'
  const isCro = activeRole === 'cro'
  const isAdmin = activeRole === 'admin'

  const roleHref = useCallback(
    (path = '') => {
      if (activeRole === 'admin') return path ? `/${path}` : '/'
      return `/${activeRole}${path ? `/${path}` : '/dashboard'}`
    },
    [activeRole]
  )

  return (
    <RoleContext.Provider
      value={{
        activeRole,
        setRole,
        activeUserId,
        setUserId,
        roleMeta,
        isSalesRole,
        isAdminOrCro,
        isCro,
        isAdmin,
        roleLabel: roleMeta.label,
        roleHref,
      }}
    >
      {children}
    </RoleContext.Provider>
  )
}
