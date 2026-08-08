'use client'

import { useCallback, useEffect, useState } from 'react'
import { cn } from '@/lib/utils'
import { apiClient } from '@/lib/api-client'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Icons } from '@/components/ui/icons'

// ============================================================================
// Types
// ============================================================================

interface SDR {
  owner_id: string
  name: string
  region?: string
  segment?: string
  active: boolean
  current_capacity?: number
  max_capacity?: number
}
interface Agent {
  agent_id: string
  name: string
  region?: string
  segment?: string
  active: boolean
  current_capacity?: number
  max_capacity?: number
  manager_id?: string
  sdrs: SDR[]
}
interface ManagerNode {
  manager_id: string
  name: string
  region?: string
  active: boolean
  current_capacity?: number
  max_capacity?: number
  cro_id?: string
  agents: Agent[]
}
interface CRONode {
  cro_id: string
  name: string
  active: boolean
  managers: ManagerNode[]
}
interface Hierarchy {
  hierarchy: CRONode[]
  counts: { cros: number; managers: number; agents: number; sdrs: number }
}
interface HandoverEntry {
  id: number
  contact_id: string
  reason: string
  from: { owner_id: string; role: string }
  to: { owner_id: string; role: string }
  stage: { from?: string; to?: string }
  note: string
  created_at: string
}

const roleColor: Record<string, string> = {
  CRO: 'bg-purple-100 text-purple-700 border-purple-200',
  Manager: 'bg-blue-100 text-blue-700 border-blue-200',
  'Sales Agent': 'bg-emerald-100 text-emerald-700 border-emerald-200',
  SDR: 'bg-amber-100 text-amber-700 border-amber-200',
}

function Capacity({ cur, max }: { cur?: number; max?: number }) {
  if (cur == null || max == null) return null
  const over = cur > max
  const pct = Math.min(100, Math.round((cur / Math.max(1, max)) * 100))
  return (
    <div className="flex items-center gap-1.5">
      <div className="h-1.5 w-16 rounded-full bg-gray-200 overflow-hidden">
        <div className={cn('h-full', over ? 'bg-red-500' : pct > 80 ? 'bg-amber-500' : 'bg-emerald-500')} style={{ width: `${pct}%` }} />
      </div>
      <span className={cn('text-[11px] font-mono', over && 'text-red-600 font-semibold')}>{cur}/{max}</span>
    </div>
  )
}

function ActiveToggle({ active, onToggle }: { active: boolean; onToggle: () => void }) {
  return (
    <button
      onClick={onToggle}
      className={cn(
        'rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase transition-colors',
        active ? 'bg-emerald-100 text-emerald-700 hover:bg-emerald-200' : 'bg-gray-200 text-gray-500 hover:bg-gray-300'
      )}
      title="Click to toggle active / inactive"
    >
      {active ? 'Active' : 'Inactive'}
    </button>
  )
}

// ============================================================================
// Component
// ============================================================================

export function OrgHandoverTab() {
  const [tree, setTree] = useState<Hierarchy | null>(null)
  const [handovers, setHandovers] = useState<HandoverEntry[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [busy, setBusy] = useState(false)

  const [contactId, setContactId] = useState('')
  const [flowResult, setFlowResult] = useState<{ ok: boolean; msg: string } | null>(null)

  const load = useCallback(async () => {
    setIsLoading(true)
    try {
      const [h, hist] = await Promise.all([
        apiClient.get<Hierarchy>('/api/org/hierarchy'),
        apiClient.get<{ handovers: HandoverEntry[] }>('/api/org/handovers?limit=15'),
      ])
      setTree(h)
      setHandovers(hist.handovers || [])
    } catch (err) {
      console.error('Failed to load org hierarchy:', err)
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  // Flat lists for the re-point dropdowns
  const allAgents = tree?.hierarchy.flatMap(c => c.managers.flatMap(m => m.agents)) ?? []
  const allManagers = tree?.hierarchy.flatMap(c => c.managers) ?? []
  const allCros = tree?.hierarchy ?? []

  const patch = useCallback(async (url: string, body: Record<string, unknown>) => {
    setBusy(true)
    try {
      await apiClient.patch(url, body)
      await load()
    } catch (err) {
      console.error('Update failed:', err)
    } finally {
      setBusy(false)
    }
  }, [load])

  const runFlow = useCallback(async (kind: 'handover' | 'close') => {
    if (!contactId.trim()) return
    setBusy(true)
    setFlowResult(null)
    try {
      const url = kind === 'handover'
        ? `/api/org/handover/${contactId.trim()}`
        : `/api/org/close/${contactId.trim()}`
      const res = await apiClient.post<{ note?: string }>(url, {})
      setFlowResult({ ok: true, msg: res.note || 'Done.' })
      await load()
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Action failed'
      setFlowResult({ ok: false, msg })
    } finally {
      setBusy(false)
    }
  }, [contactId, load])

  const reassignStalled = useCallback(async () => {
    setBusy(true)
    setFlowResult(null)
    try {
      const res = await apiClient.post<{ reassigned_count: number }>('/api/org/cro/reassign-stalled', {})
      setFlowResult({ ok: true, msg: `CRO reassigned ${res.reassigned_count} stalled contact(s) from inactive owners to active peers.` })
      await load()
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Reassign failed'
      setFlowResult({ ok: false, msg })
    } finally {
      setBusy(false)
    }
  }, [load])

  if (isLoading) {
    return <div className="flex items-center justify-center py-16"><Icons.loader className="h-8 w-8 animate-spin text-brand-cornflower" /></div>
  }

  return (
    <div className="space-y-6">
      {/* Explainer + flow runner */}
      <Card className="relative overflow-hidden">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Icons.network className="h-5 w-5 text-brand-cornflower" strokeWidth={1.5} />
            Revenue Org & Handover Chain
          </CardTitle>
          <CardDescription>
            Leads climb the chain <span className="font-medium">SDR → Sales Agent → Manager → CRO</span>. Each link
            lives in the database — change who reports to whom below, and the handover follows the new links on the next run.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap items-end gap-3">
            <div className="flex-1 min-w-[220px]">
              <label className="block text-xs font-medium text-muted-foreground mb-1">Contact ID</label>
              <input
                type="text"
                value={contactId}
                onChange={(e) => setContactId(e.target.value)}
                placeholder="e.g. 003rSxXve61Lq38YFh"
                className="w-full px-3 py-2 rounded-lg border border-input font-mono text-sm focus:outline-none focus:ring-2 focus:ring-brand-cornflower/50"
              />
            </div>
            <Button variant="default" disabled={busy || !contactId.trim()} onClick={() => runFlow('handover')}>
              <Icons.arrowRight className="mr-1.5 h-4 w-4" /> Hand Up
            </Button>
            <Button variant="outline" disabled={busy || !contactId.trim()} onClick={() => runFlow('close')}>
              <Icons.checkCircle className="mr-1.5 h-4 w-4" /> Close Deal
            </Button>
            <Button variant="glass" disabled={busy} onClick={reassignStalled} title="CRO: reassign contacts stranded under inactive owners">
              <Icons.refresh className="mr-1.5 h-4 w-4" /> CRO: Reassign Stalled
            </Button>
          </div>
          {flowResult && (
            <div className={cn('rounded-lg border p-3 text-sm',
              flowResult.ok ? 'bg-emerald-50 border-emerald-200 text-emerald-700' : 'bg-red-50 border-red-200 text-red-700')}>
              {flowResult.msg}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Hierarchy tree */}
      <div className="space-y-4">
        {tree?.hierarchy.map(cro => (
          <Card key={cro.cro_id}>
            <CardContent className="p-4 space-y-3">
              {/* CRO */}
              <div className="flex items-center gap-2 flex-wrap">
                <span className={cn('rounded-md border px-2 py-0.5 text-[10px] font-bold uppercase', roleColor.CRO)}>CRO</span>
                <span className="font-semibold text-brand-navy">{cro.name}</span>
                <span className="font-mono text-xs text-muted-foreground">{cro.cro_id}</span>
              </div>

              {/* Managers */}
              {cro.managers.map(mgr => (
                <div key={mgr.manager_id} className="ml-4 border-l-2 border-blue-100 pl-4 space-y-2">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className={cn('rounded-md border px-2 py-0.5 text-[10px] font-bold uppercase', roleColor.Manager)}>Manager</span>
                    <span className="font-medium text-foreground">{mgr.name}</span>
                    <span className="font-mono text-xs text-muted-foreground">{mgr.manager_id}</span>
                    <Capacity cur={mgr.current_capacity} max={mgr.max_capacity} />
                    <ActiveToggle active={mgr.active} onToggle={() => patch(`/api/org/manager/${mgr.manager_id}`, { active: !mgr.active })} />
                  </div>

                  {/* Agents */}
                  {mgr.agents.map(agent => (
                    <div key={agent.agent_id} className="ml-4 border-l-2 border-emerald-100 pl-4 space-y-2">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className={cn('rounded-md border px-2 py-0.5 text-[10px] font-bold uppercase', roleColor['Sales Agent'])}>Agent</span>
                        <span className="font-medium text-foreground">{agent.name}</span>
                        <span className="font-mono text-xs text-muted-foreground">{agent.agent_id}</span>
                        <Capacity cur={agent.current_capacity} max={agent.max_capacity} />
                        <ActiveToggle active={agent.active} onToggle={() => patch(`/api/org/agent/${agent.agent_id}`, { active: !agent.active })} />
                        {/* Re-point manager */}
                        <label className="flex items-center gap-1 text-[11px] text-muted-foreground ml-auto">
                          reports to
                          <select
                            value={agent.manager_id || ''}
                            onChange={(e) => patch(`/api/org/agent/${agent.agent_id}`, { manager_id: e.target.value })}
                            className="rounded border border-input bg-white px-1.5 py-0.5 text-xs"
                          >
                            {allManagers.map(m => <option key={m.manager_id} value={m.manager_id}>{m.name}</option>)}
                          </select>
                        </label>
                      </div>

                      {/* SDRs */}
                      {agent.sdrs.map(sdr => (
                        <div key={sdr.owner_id} className="ml-4 flex items-center gap-2 flex-wrap border-l-2 border-amber-100 pl-4 py-1">
                          <span className={cn('rounded-md border px-2 py-0.5 text-[10px] font-bold uppercase', roleColor.SDR)}>SDR</span>
                          <span className="text-sm text-foreground">{sdr.name}</span>
                          <span className="font-mono text-xs text-muted-foreground">{sdr.owner_id}</span>
                          {sdr.region && <span className="text-[11px] text-muted-foreground">{sdr.region}/{sdr.segment}</span>}
                          <Capacity cur={sdr.current_capacity} max={sdr.max_capacity} />
                          <ActiveToggle active={sdr.active} onToggle={() => patch(`/api/org/sdr/${sdr.owner_id}`, { active: !sdr.active })} />
                          <label className="flex items-center gap-1 text-[11px] text-muted-foreground ml-auto">
                            hands to
                            <select
                              value={agent.agent_id}
                              onChange={(e) => patch(`/api/org/sdr/${sdr.owner_id}`, { sales_agent_id: e.target.value })}
                              className="rounded border border-input bg-white px-1.5 py-0.5 text-xs"
                            >
                              {allAgents.map(a => <option key={a.agent_id} value={a.agent_id}>{a.name}</option>)}
                            </select>
                          </label>
                        </div>
                      ))}
                      {agent.sdrs.length === 0 && <p className="ml-4 text-xs text-muted-foreground italic">No SDRs assigned</p>}
                    </div>
                  ))}
                </div>
              ))}
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Handover history */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Recent Handovers & Escalations</CardTitle>
          <CardDescription>Every move up the chain and every CRO reassignment is logged.</CardDescription>
        </CardHeader>
        <CardContent>
          {handovers.length === 0 ? (
            <p className="text-sm text-muted-foreground italic">No handovers yet. Enter a contact ID above and click Hand Up.</p>
          ) : (
            <div className="space-y-2">
              {handovers.map(h => (
                <div key={h.id} className="flex items-start gap-2 text-sm border-b border-gray-100 pb-2 last:border-0">
                  <span className={cn('rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase mt-0.5',
                    h.reason === 'cro_reassign' ? 'bg-purple-100 text-purple-700' : h.reason === 'close' ? 'bg-emerald-100 text-emerald-700' : 'bg-blue-100 text-blue-700')}>
                    {h.reason === 'cro_reassign' ? 'CRO' : h.reason}
                  </span>
                  <div className="min-w-0">
                    <p className="text-foreground">{h.note}</p>
                    <p className="text-[11px] text-muted-foreground font-mono">{h.contact_id} · {new Date(h.created_at).toLocaleString()}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
