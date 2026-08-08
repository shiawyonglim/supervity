'use client'

import { useState, useEffect, useCallback, useMemo } from 'react'
import { motion } from 'framer-motion'
import { apiClient } from '@/lib/api-client'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Icons } from '@/components/ui/icons'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'

interface OrgNode {
  owner_id?: string
  agent_id?: string
  manager_id?: string
  cro_id?: string
  name: string
  role: string
  active: boolean
  current_capacity?: number
  max_capacity?: number
  sdrs?: OrgNode[]
  agents?: OrgNode[]
  managers?: OrgNode[]
}

interface OrgHierarchy {
  hierarchy: OrgNode[]
  counts: { cros: number; managers: number; agents: number; sdrs: number }
}

interface TeamMember {
  id: string
  name: string
  role: 'SDR' | 'Sales Agent' | 'Manager'
  active: boolean
  current_capacity: number
  max_capacity: number
  sales_agent_id?: string
  manager_id?: string
  cro_id?: string
}

const containerVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { staggerChildren: 0.05 } },
}

const itemVariants = {
  hidden: { opacity: 0, y: 16 },
  visible: { opacity: 1, y: 0 },
}

function roleColor(role: string) {
  switch (role) {
    case 'CRO': return 'bg-purple-100 text-purple-700 border-purple-200'
    case 'Manager': return 'bg-blue-100 text-blue-700 border-blue-200'
    case 'Sales Agent': return 'bg-emerald-100 text-emerald-700 border-emerald-200'
    default: return 'bg-amber-100 text-amber-700 border-amber-200'
  }
}

function flattenHierarchy(hierarchy: OrgHierarchy | null): TeamMember[] {
  const out: TeamMember[] = []
  if (!hierarchy) return out
  hierarchy.hierarchy.forEach((cro) => {
    cro.managers?.forEach((m) => {
      out.push({
        id: m.manager_id || '',
        name: m.name,
        role: 'Manager',
        active: m.active,
        current_capacity: m.current_capacity || 0,
        max_capacity: m.max_capacity || 15,
        cro_id: cro.cro_id,
      })
      m.agents?.forEach((a) => {
        out.push({
          id: a.agent_id || '',
          name: a.name,
          role: 'Sales Agent',
          active: a.active,
          current_capacity: a.current_capacity || 0,
          max_capacity: a.max_capacity || 40,
          manager_id: m.manager_id,
        })
        a.sdrs?.forEach((s) => {
          out.push({
            id: s.owner_id || '',
            name: s.name,
            role: 'SDR',
            active: s.active,
            current_capacity: s.current_capacity || 0,
            max_capacity: s.max_capacity || 50,
            sales_agent_id: a.agent_id,
          })
        })
      })
    })
  })
  return out
}

export function CROWorkbench() {
  const [members, setMembers] = useState<TeamMember[]>([])
  const [edits, setEdits] = useState<Record<string, { max_capacity: number; active: boolean }>>({})
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState<{ ok: boolean; msg: string } | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const h = await apiClient.get<OrgHierarchy>('/api/org/hierarchy')
      const flat = flattenHierarchy(h)
      setMembers(flat)
      const initialEdits: Record<string, { max_capacity: number; active: boolean }> = {}
      flat.forEach((m) => {
        initialEdits[m.id] = { max_capacity: m.max_capacity, active: m.active }
      })
      setEdits(initialEdits)
    } catch (err) {
      console.error('CRO workbench load failed:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const changedIds = useMemo(() => {
    return Object.keys(edits).filter((id) => {
      const m = members.find((x) => x.id === id)
      if (!m) return false
      const e = edits[id]
      return e.max_capacity !== m.max_capacity || e.active !== m.active
    })
  }, [edits, members])

  const updateEdit = (id: string, patch: Partial<{ max_capacity: number; active: boolean }>) => {
    setEdits((prev) => ({
      ...prev,
      [id]: { ...prev[id], ...patch },
    }))
  }

  const saveChanges = async () => {
    setSaving(true)
    setResult(null)
    try {
      const promises = changedIds.map(async (id) => {
        const member = members.find((m) => m.id === id)
        if (!member) return
        const edit = edits[id]
        const body: Record<string, unknown> = { active: edit.active }
        if (member.role === 'Manager') {
          body.max_capacity = edit.max_capacity
          await apiClient.patch(`/api/org/manager/${id}`, body)
        } else if (member.role === 'Sales Agent') {
          body.max_capacity = edit.max_capacity
          await apiClient.patch(`/api/org/agent/${id}`, body)
        } else {
          // SDR — try to update max_capacity in addition to active
          try {
            await apiClient.patch(`/api/org/sdr/${id}`, { ...body, max_capacity: edit.max_capacity })
          } catch {
            await apiClient.patch(`/api/org/sdr/${id}`, body)
          }
        }
      })
      await Promise.all(promises)
      setResult({ ok: true, msg: 'Team KPIs saved.' })
      await load()
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Save failed.'
      setResult({ ok: false, msg })
    } finally {
      setSaving(false)
    }
  }

  const reassignStalled = async () => {
    setBusy(true)
    setResult(null)
    try {
      const res = await apiClient.post<{ reassigned_count: number }>('/api/org/cro/reassign-stalled', {})
      setResult({ ok: true, msg: `CRO reassigned ${res.reassigned_count} stalled contact(s).` })
      await load()
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Reassign failed.'
      setResult({ ok: false, msg })
    } finally {
      setBusy(false)
    }
  }

  return (
    <motion.div className='space-y-8' variants={containerVariants} initial='hidden' animate='visible'>
      <motion.div variants={itemVariants} className='flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between'>
        <div>
          <h1 className='text-display-3 font-bold tracking-tight text-brand-navy'>CRO Workbench</h1>
          <p className='mt-2 text-lg text-muted-foreground'>Adjust KPIs and capacity targets for each sales member.</p>
        </div>
        <div className='flex items-center gap-2'>
          <Button variant='outline' onClick={reassignStalled} disabled={busy}>
            <Icons.refresh className={cn('mr-2 h-4 w-4', busy && 'animate-spin')} />
            Reassign Stalled
          </Button>
          <Button onClick={saveChanges} disabled={changedIds.length === 0 || saving}>
            {saving ? <Icons.loader className='mr-2 h-4 w-4 animate-spin' /> : <Icons.check className='mr-2 h-4 w-4' />}
            Save KPIs
          </Button>
        </div>
      </motion.div>

      {result && (
        <div className={cn('rounded-lg border p-3 text-sm', result.ok ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-700')}>
          {result.msg}
        </div>
      )}

      <motion.div variants={itemVariants}>
        <Card>
          <CardHeader>
            <CardTitle className='flex items-center gap-2'>
              <Icons.users className='h-5 w-5 text-brand-cornflower' />
              Team KPIs
            </CardTitle>
            <CardDescription>Set capacity (max leads / deals) and active status for every member.</CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className='flex justify-center p-8'>
                <Icons.loader className='h-8 w-8 animate-spin text-muted-foreground' />
              </div>
            ) : members.length === 0 ? (
              <p className='text-center text-muted-foreground'>No team members found.</p>
            ) : (
              <div className='overflow-x-auto'>
                <table className='w-full text-sm'>
                  <thead className='border-b text-left text-xs text-muted-foreground uppercase'>
                    <tr>
                      <th className='py-3 px-4 font-medium'>Name</th>
                      <th className='py-3 px-4 font-medium'>Role</th>
                      <th className='py-3 px-4 font-medium'>Active</th>
                      <th className='py-3 px-4 font-medium'>Capacity KPI</th>
                      <th className='py-3 px-4 font-medium'>Current Load</th>
                      <th className='py-3 px-4 font-medium text-right'>Utilization</th>
                    </tr>
                  </thead>
                  <tbody>
                    {members.map((m) => {
                      const edit = edits[m.id] || { max_capacity: m.max_capacity, active: m.active }
                      const pct = edit.max_capacity ? Math.min(100, Math.round((m.current_capacity / edit.max_capacity) * 100)) : 0
                      const changed = edit.max_capacity !== m.max_capacity || edit.active !== m.active
                      return (
                        <tr key={m.id} className={cn('border-b last:border-0', changed && 'bg-amber-50/50')}>
                          <td className='py-3 px-4 font-medium text-brand-navy'>{m.name}</td>
                          <td className='py-3 px-4'>
                            <Badge className={cn('border px-1.5 py-0.5 text-[10px] font-bold uppercase', roleColor(m.role))}>
                              {m.role}
                            </Badge>
                          </td>
                          <td className='py-3 px-4'>
                            <button
                              onClick={() => updateEdit(m.id, { active: !edit.active })}
                              className={cn(
                                'rounded-full px-2.5 py-0.5 text-[10px] font-bold uppercase transition-colors',
                                edit.active ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-200 text-gray-600'
                              )}
                            >
                              {edit.active ? 'Active' : 'Inactive'}
                            </button>
                          </td>
                          <td className='py-3 px-4'>
                            <Input
                              type='number'
                              min={0}
                              className='h-8 w-24 text-right text-sm'
                              value={edit.max_capacity}
                              onChange={(e) => updateEdit(m.id, { max_capacity: Math.max(0, parseInt(e.target.value, 10) || 0) })}
                            />
                          </td>
                          <td className='py-3 px-4'>{m.current_capacity}</td>
                          <td className='py-3 px-4 text-right'>
                            <div className='flex items-center justify-end gap-2'>
                              <div className='h-1.5 w-16 rounded-full bg-gray-200'>
                                <div
                                  className={cn('h-full rounded-full', pct > 90 ? 'bg-red-500' : pct > 70 ? 'bg-amber-500' : 'bg-emerald-500')}
                                  style={{ width: `${pct}%` }}
                                />
                              </div>
                              <span className='text-xs text-muted-foreground'>{pct}%</span>
                            </div>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      </motion.div>
    </motion.div>
  )
}
