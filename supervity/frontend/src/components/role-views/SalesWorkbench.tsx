'use client'

import { useState, useEffect, useCallback, useMemo } from 'react'
import { motion } from 'framer-motion'
import { apiClient } from '@/lib/api-client'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Icons } from '@/components/ui/icons'
import { Badge } from '@/components/ui/badge'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { useRole, ROLE_META } from '@/context/RoleContext'
import type { AppRole } from '@/context/RoleContext'

interface Contact {
  Id: string
  FirstName: string | null
  LastName: string | null
  Email: string | null
  Title: string | null
  AccountId: string | null
  Lead_Stage__c: string | null
  OwnerId: string
  Owner_Name: string | null
  Account?: { Name: string }
}

interface Handover {
  id: number
  contact_id: string
  from: { owner_id: string; name: string; role: string }
  to: { owner_id: string; name: string; role: string }
  stage: { from?: string; to?: string }
  note: string
  created_at: string
}

interface OrgNode {
  owner_id?: string
  agent_id?: string
  manager_id?: string
  cro_id?: string
  name: string
  role: string
  active: boolean
  sdrs?: OrgNode[]
  agents?: OrgNode[]
  managers?: OrgNode[]
}

interface OrgHierarchy {
  hierarchy: OrgNode[]
}

const containerVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { staggerChildren: 0.08 } },
}

const itemVariants = {
  hidden: { opacity: 0, y: 16 },
  visible: { opacity: 1, y: 0 },
}

const ROLE_STEP: Record<AppRole, { next: string; action: string; stage: string }> = {
  sdr: { next: 'sales_agent', action: 'Hand to Sales Agent', stage: 'MQL' },
  sales_agent: { next: 'manager', action: 'Hand to Manager', stage: 'SQL' },
  manager: { next: 'customer', action: 'Close Deal', stage: 'Customer' },
  admin: { next: '', action: '', stage: '' },
  cro: { next: '', action: '', stage: '' },
}

const ALLOWED_STAGES: Record<Exclude<AppRole, 'admin' | 'cro'>, string[]> = {
  sdr: ['Open'],
  sales_agent: ['MQL', 'Opportunity'],
  manager: ['SQL'],
}

export function SalesWorkbench({ role }: { role: Exclude<AppRole, 'admin' | 'cro'> }) {
  const meta = ROLE_META[role]
  const { activeUserId } = useRole()
  const step = ROLE_STEP[role]
  const [contacts, setContacts] = useState<Contact[]>([])
  const [handovers, setHandovers] = useState<Handover[]>([])
  const [hierarchy, setHierarchy] = useState<OrgHierarchy | null>(null)
  const [loading, setLoading] = useState(true)
  const [ownerFilter, setOwnerFilter] = useState<string>('')

  const [selectedContact, setSelectedContact] = useState<Contact | null>(null)
  const [handoverNote, setHandoverNote] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [result, setResult] = useState<{ ok: boolean; msg: string } | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const qs = activeUserId ? `&viewer_role=${role}&viewer_id=${activeUserId}` : ''
      const [c, h, o] = await Promise.all([
        apiClient.get<{ data: Contact[] }>(`/api/data/contact?limit=200${qs}`),
        apiClient.get<{ handovers: Handover[] }>('/api/org/handovers?limit=15'),
        apiClient.get<OrgHierarchy>('/api/org/hierarchy'),
      ])
      setContacts(c.data || [])
      setHandovers(h.handovers || [])
      setHierarchy(o)
    } catch (err) {
      console.error('Workbench load failed:', err)
    } finally {
      setLoading(false)
    }
  }, [role, activeUserId])

  useEffect(() => {
    load()
  }, [load])

  const owners = useMemo(() => {
    const list: Array<{ id: string; name: string }> = []
    const add = (n: OrgNode) => {
      if (n && n.active) {
        const id = n.owner_id || n.agent_id || n.manager_id || n.cro_id || ''
        if (id) list.push({ id, name: n.name })
      }
    }
    hierarchy?.hierarchy.forEach((cro) => {
      cro.managers?.forEach((m) => {
        if (role === 'manager' && m.active) add(m)
        m.agents?.forEach((a) => {
          if (role === 'sales_agent' && a.active) add(a)
          a.sdrs?.forEach((s) => {
            if (role === 'sdr' && s.active) add(s)
          })
        })
      })
    })
    return list
  }, [hierarchy, role])

  const allowedStages = ALLOWED_STAGES[role]

  const filteredContacts = useMemo(() => {
    const byStage = contacts.filter((c) => allowedStages.includes(c.Lead_Stage__c || ''))
    if (!ownerFilter) return byStage
    return byStage.filter((c) => c.OwnerId === ownerFilter)
  }, [contacts, ownerFilter, allowedStages])

  const openApprove = (contact: Contact) => {
    setSelectedContact(contact)
    setHandoverNote('')
    setResult(null)
  }

  const submitApprove = async () => {
    if (!selectedContact) return
    setIsSubmitting(true)
    setResult(null)
    try {
      let res: { note?: string }
      if (role === 'manager') {
        res = await apiClient.post(`/api/org/close/${selectedContact.Id}`, {
          note: handoverNote || `Closed by Manager from stage ${selectedContact.Lead_Stage__c || 'Unknown'}.`,
        })
      } else {
        res = await apiClient.post(`/api/org/handover/${selectedContact.Id}`, {
          note: handoverNote || `Approved by ${meta.label} for next step.`,
          stage: step.stage,
        })
      }
      setResult({ ok: true, msg: res.note || 'Done.' })
      setSelectedContact(null)
      await load()
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Handover failed.'
      setResult({ ok: false, msg })
    } finally {
      setIsSubmitting(false)
    }
  }

  const myPendingCount = filteredContacts.length

  return (
    <motion.div className='space-y-8' variants={containerVariants} initial='hidden' animate='visible'>
      <motion.div variants={itemVariants} className='flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between'>
        <div>
          <h1 className='text-display-3 font-bold tracking-tight text-brand-navy'>
            {meta.label} Workbench
          </h1>
          <p className='mt-2 text-lg text-muted-foreground'>
            Approve leads, pass context to the next step, and track handovers.
          </p>
        </div>
        <Badge className={cn('rounded-md border px-2.5 py-1 text-xs font-bold uppercase tracking-wide', meta.color)}>
          {meta.label}
        </Badge>
      </motion.div>

      {result && (
        <div className={cn('rounded-lg border p-3 text-sm', result.ok ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-700')}>
          {result.msg}
        </div>
      )}

      {/* Filters */}
      <motion.div variants={itemVariants} className='flex flex-col gap-3 sm:flex-row sm:items-center'>
        <label className='text-sm font-medium text-muted-foreground'>Owner filter</label>
        <select
          className='h-10 rounded-md border border-input bg-background px-3 py-2 text-sm'
          value={ownerFilter}
          onChange={(e) => setOwnerFilter(e.target.value)}
        >
          <option value=''>All {meta.label} leads</option>
          {owners.map((o) => (
            <option key={o.id} value={o.id}>{o.name}</option>
          ))}
        </select>
        <p className='ml-auto text-sm text-muted-foreground'>
          <strong>{myPendingCount}</strong> leads awaiting action
        </p>
      </motion.div>

      {/* Leads to approve */}
      <motion.div variants={itemVariants}>
        <Card>
          <CardHeader>
            <CardTitle className='flex items-center gap-2'>
              <Icons.users className='h-5 w-5 text-brand-primary' />
              {role === 'manager' ? 'Deals to Close' : 'Leads to Approve'}
            </CardTitle>
            <CardDescription>Press approve to advance the lead and pass notes to the next step.</CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className='flex justify-center p-8'>
                <Icons.loader className='h-8 w-8 animate-spin text-muted-foreground' />
              </div>
            ) : filteredContacts.length === 0 ? (
              <p className='text-center text-muted-foreground'>No leads found for the selected filter.</p>
            ) : (
              <div className='overflow-x-auto'>
                <table className='w-full text-sm'>
                  <thead className='border-b text-left text-xs text-muted-foreground uppercase'>
                    <tr>
                      <th className='py-3 px-4 font-medium'>Name</th>
                      <th className='py-3 px-4 font-medium'>Email</th>
                      <th className='py-3 px-4 font-medium'>Company</th>
                      <th className='py-3 px-4 font-medium'>Stage</th>
                      <th className='py-3 px-4 font-medium'>Owner</th>
                      <th className='py-3 px-4 font-medium text-right'>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredContacts.map((c) => (
                      <tr key={c.Id} className='border-b last:border-0 hover:bg-slate-50'>
                        <td className='py-3 px-4 font-medium text-brand-navy'>
                          {c.FirstName} {c.LastName}
                        </td>
                        <td className='py-3 px-4 text-muted-foreground'>{c.Email}</td>
                        <td className='py-3 px-4'>{c.Account?.Name || c.AccountId || '-'}</td>
                        <td className='py-3 px-4'>
                          <Badge variant='outline'>{c.Lead_Stage__c || 'Unknown'}</Badge>
                        </td>
                        <td className='py-3 px-4'>{c.Owner_Name || c.OwnerId}</td>
                        <td className='py-3 px-4 text-right'>
                          <Button size='sm' onClick={() => openApprove(c)}>
                            <Icons.checkCircle className='mr-1.5 h-4 w-4' />
                            {role === 'manager' ? 'Close' : 'Approve'}
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      </motion.div>

      {/* Context / Handover History */}
      <motion.div variants={itemVariants}>
        <Card>
          <CardHeader>
            <CardTitle className='flex items-center gap-2'>
              <Icons.activity className='h-5 w-5 text-brand-cornflower' />
              Handover Context Log
            </CardTitle>
            <CardDescription>Recent notes and lead advances between roles.</CardDescription>
          </CardHeader>
          <CardContent>
            {handovers.length === 0 ? (
              <p className='text-center text-muted-foreground'>No handovers yet.</p>
            ) : (
              <div className='space-y-3'>
                {handovers.map((h) => (
                  <div key={h.id} className='rounded-xl border p-4 text-sm'>
                    <div className='flex flex-wrap items-center gap-2 text-muted-foreground'>
                      <span className='font-medium text-foreground'>{h.from.name}</span>
                      <Badge variant='outline' className='text-[10px]'>{h.from.role}</Badge>
                      <Icons.arrowRight className='h-3 w-3' />
                      <span className='font-medium text-foreground'>{h.to.name}</span>
                      <Badge variant='outline' className='text-[10px]'>{h.to.role}</Badge>
                      <span className='ml-auto text-xs'>{new Date(h.created_at).toLocaleString()}</span>
                    </div>
                    <p className='mt-2 text-foreground'>
                      Stage <strong>{h.stage.from || '-'}</strong> → <strong>{h.stage.to || '-'}</strong>
                    </p>
                    {h.note && (
                      <p className='mt-1 rounded-md bg-muted/30 p-2 text-xs text-muted-foreground'>{h.note}</p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </motion.div>

      {/* Approve / Handover Modal */}
      <Dialog open={!!selectedContact} onOpenChange={(open) => !open && setSelectedContact(null)}>
        <DialogContent className='sm:max-w-lg'>
          <DialogHeader>
            <DialogTitle>
              {role === 'manager' ? 'Close Deal' : 'Approve to Next Lead Status'}
            </DialogTitle>
            <DialogDescription>
              Add relevant information to pass to the {role === 'sdr' ? 'Sales Agent' : role === 'sales_agent' ? 'Sales Manager' : 'customer record'}.
            </DialogDescription>
          </DialogHeader>

          <div className='space-y-4'>
            <div className='rounded-lg bg-muted/30 p-3 text-sm'>
              <p className='font-medium text-foreground'>
                {selectedContact?.FirstName} {selectedContact?.LastName}
              </p>
              <p className='text-muted-foreground'>
                {selectedContact?.Email} · Stage: {selectedContact?.Lead_Stage__c || 'Unknown'}
              </p>
            </div>
            <div className='space-y-2'>
              <Label>Information to pass forward</Label>
              <textarea
                className='min-h-[120px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm'
                placeholder='e.g. Budget confirmed, decision maker identified, pricing discussion needed...'
                value={handoverNote}
                onChange={(e) => setHandoverNote(e.target.value)}
              />
            </div>
            <p className='text-xs text-muted-foreground'>
              This note will be saved to the handover log so the next role has full context.
            </p>
          </div>

          <DialogFooter>
            <Button variant='outline' onClick={() => setSelectedContact(null)}>Cancel</Button>
            <Button onClick={submitApprove} disabled={isSubmitting}>
              {isSubmitting ? <Icons.loader className='mr-2 h-4 w-4 animate-spin' /> : <Icons.checkCircle className='mr-2 h-4 w-4' />}
              {role === 'manager' ? 'Close Deal' : 'Approve & Pass'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </motion.div>
  )
}
