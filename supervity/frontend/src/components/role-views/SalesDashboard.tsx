'use client'

import { useState, useEffect, useCallback, useMemo } from 'react'
import { motion } from 'framer-motion'
import { apiClient } from '@/lib/api-client'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { CardWatermark } from '@/components/ui/card-watermark'
import { Icons } from '@/components/ui/icons'
import { Badge } from '@/components/ui/badge'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import type { AppRole } from '@/context/RoleContext'
import { ROLE_META } from '@/context/RoleContext'

interface DashboardStats {
  total_leads: number
  active_opportunities: number
  pipeline_value: number
  win_rate: number
  active_sdrs: number
  total_activities: number
  pending_exceptions: number
  active_policies: number
}

interface Policy {
  id: string
  name: string
  natural_language: string
  is_active: boolean
  priority: number
}

interface Lead {
  id: string
  first_name: string | null
  last_name: string | null
  email: string | null
  account_name: string | null
  lead_stage: string | null
  owner_name: string | null
}

const containerVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { staggerChildren: 0.08 } },
}

const itemVariants = {
  hidden: { opacity: 0, y: 16 },
  visible: { opacity: 1, y: 0 },
}

const ALLOWED_STAGES: Record<AppRole, string[]> = {
  sdr: ['Open'],
  sales_agent: ['MQL', 'Opportunity'],
  manager: ['SQL'],
  admin: ['Open', 'MQL', 'Opportunity', 'SQL'],
  cro: ['Open', 'MQL', 'Opportunity', 'SQL', 'Customer'],
}

export function SalesDashboard({ role }: { role: AppRole }) {
  const meta = ROLE_META[role]
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [leads, setLeads] = useState<Lead[]>([])
  const [policies, setPolicies] = useState<Policy[]>([])
  const [loading, setLoading] = useState(true)

  const [selectedLead, setSelectedLead] = useState<Lead | null>(null)
  const [draftSubject, setDraftSubject] = useState('')
  const [draftBody, setDraftBody] = useState('')
  const [isDrafting, setIsDrafting] = useState(false)
  const [isSending, setIsSending] = useState(false)
  const [sendNotice, setSendNotice] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [s, l, p] = await Promise.all([
        apiClient.get<DashboardStats>('/api/dashboard/stats'),
        apiClient.get<Lead[]>('/api/contacts?limit=20'),
        apiClient.get<Policy[]>('/api/policies?limit=20'),
      ])
      setStats(s)
      setLeads(l)
      setPolicies(p.filter((pol: Policy) => pol.is_active).slice(0, 5))
    } catch (err) {
      console.error('Sales dashboard load failed:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const handleDraft = async (lead: Lead) => {
    setSelectedLead(lead)
    setDraftSubject('')
    setDraftBody('')
    setIsDrafting(true)
    try {
      const res = await apiClient.post<{ subject: string; body: string }>(`/api/contacts/${lead.id}/draft`, {
        prompt_context: `You are a ${meta.label}. Draft a concise, personalized outreach email to this lead based on their stage (${lead.lead_stage || 'new'}).`,
      })
      setDraftSubject(res.subject)
      setDraftBody(res.body)
    } catch (err) {
      console.error('Draft failed:', err)
      setDraftBody('Failed to draft email.')
    } finally {
      setIsDrafting(false)
    }
  }

  const handleSend = async () => {
    setIsSending(true)
    try {
      await apiClient.post(`/api/contacts/${selectedLead?.id}/send-email`, {
        subject: draftSubject,
        body: draftBody,
      })
      setSendNotice(`Email queued to ${selectedLead?.first_name || ''} ${selectedLead?.last_name || ''}`.trim())
      setSelectedLead(null)
    } catch (err) {
      console.error('Send failed:', err)
      setSendNotice('Email send not wired to a real provider in this environment.')
    } finally {
      setIsSending(false)
      setTimeout(() => setSendNotice(null), 4000)
    }
  }

  const visibleLeads = useMemo(() => {
    const allowed = ALLOWED_STAGES[role]
    return leads.filter((l) => allowed.includes(l.lead_stage || ''))
  }, [leads, role])

  const togglePolicy = async (id: string, current: boolean) => {
    try {
      await apiClient.patch(`/api/policies/${id}/toggle`)
      setPolicies((prev) => prev.map((p) => (p.id === id ? { ...p, is_active: !current } : p)))
    } catch (err) {
      console.error('Toggle policy failed:', err)
    }
  }

  const kpiCards = [
    { title: 'Total Leads', value: stats?.total_leads ?? 0, icon: Icons.users, color: 'bg-blue-500' },
    { title: 'Active Policies', value: stats?.active_policies ?? 0, icon: Icons.brain, color: 'bg-purple-500' },
    { title: 'Open Pipeline', value: `$${Math.round(stats?.pipeline_value ?? 0).toLocaleString()}`, icon: Icons.trendingUp, color: 'bg-emerald-500', isText: true },
    { title: 'Active Opps', value: stats?.active_opportunities ?? 0, icon: Icons.activity, color: 'bg-amber-500' },
  ]

  return (
    <motion.div className='space-y-8' variants={containerVariants} initial='hidden' animate='visible'>
      <motion.div variants={itemVariants} className='flex items-center justify-between'>
        <div>
          <h1 className='text-display-3 font-bold tracking-tight text-brand-navy'>
            {meta.label} Dashboard
          </h1>
          <p className='mt-2 text-lg text-muted-foreground'>
            KPIs, new leads, and active policies for your role.
          </p>
        </div>
        <Badge
          className={cn(
            'rounded-md border px-2.5 py-1 text-xs font-bold uppercase tracking-wide',
            meta.color
          )}
        >
          {meta.label}
        </Badge>
      </motion.div>

      {sendNotice && (
        <div className='rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700'>
          {sendNotice}
        </div>
      )}

      {/* KPI Cards */}
      <motion.div variants={itemVariants} className='grid gap-4 sm:grid-cols-2 lg:grid-cols-4'>
        {kpiCards.map((card) => (
          <Card key={card.title} className='relative overflow-hidden'>
            <CardWatermark opacity={2} scale={0.95} />
            <CardContent className='relative z-10 p-5'>
              <div className='flex items-start justify-between'>
                <div className='space-y-2'>
                  <p className='text-micro uppercase text-brand-muted'>{card.title}</p>
                  <p className='font-display text-2xl font-bold text-brand-navy'>
                    {card.isText ? card.value : (card.value as number).toLocaleString()}
                  </p>
                </div>
                <div className={cn('rounded-xl p-2.5 text-white shadow-lg', card.color)}>
                  <card.icon className='h-5 w-5' strokeWidth={1.5} />
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </motion.div>

      {/* New Leads */}
      <motion.div variants={itemVariants}>
        <Card className='overflow-hidden'>
          <CardHeader className='flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between'>
            <div>
              <CardTitle className='flex items-center gap-2'>
                <Icons.users className='h-5 w-5 text-brand-primary' />
                Total New Leads
              </CardTitle>
              <CardDescription>Draft and send emails directly from the dashboard.</CardDescription>
            </div>
            <Button variant='outline' size='sm' onClick={load} disabled={loading}>
              {loading ? <Icons.loader className='mr-2 h-4 w-4 animate-spin' /> : <Icons.refresh className='mr-2 h-4 w-4' />}
              Refresh
            </Button>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className='flex justify-center p-8'>
                <Icons.loader className='h-8 w-8 animate-spin text-muted-foreground' />
              </div>
            ) : visibleLeads.length === 0 ? (
              <p className='text-center text-muted-foreground'>No leads found for {meta.label} stage view.</p>
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
                    {visibleLeads.map((lead) => (
                      <tr key={lead.id} className='border-b last:border-0 hover:bg-slate-50'>
                        <td className='py-3 px-4 font-medium text-brand-navy'>
                          {lead.first_name} {lead.last_name}
                        </td>
                        <td className='py-3 px-4 text-muted-foreground'>{lead.email}</td>
                        <td className='py-3 px-4'>{lead.account_name || '-'}</td>
                        <td className='py-3 px-4'>
                          <Badge variant='outline'>{lead.lead_stage || 'Unknown'}</Badge>
                        </td>
                        <td className='py-3 px-4'>{lead.owner_name || 'Unassigned'}</td>
                        <td className='py-3 px-4 text-right'>
                          <Button size='sm' onClick={() => handleDraft(lead)} disabled={isDrafting}>
                            <Icons.mail className='mr-2 h-4 w-4' />
                            Draft Email
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

      {/* Active Policies */}
      <motion.div variants={itemVariants}>
        <Card>
          <CardHeader>
            <CardTitle className='flex items-center gap-2'>
              <Icons.brain className='h-5 w-5 text-brand-purple' />
              Active Policies
            </CardTitle>
            <CardDescription>Toggle policies on or off for this role.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className='space-y-3'>
              {policies.map((pol) => (
                <div
                  key={pol.id}
                  className={cn(
                    'flex items-center justify-between rounded-xl border p-4 transition-colors',
                    pol.is_active ? 'border-brand-cornflower/30 bg-brand-cornflower/5' : 'border-border/50 bg-muted/20'
                  )}
                >
                  <div className='min-w-0'>
                    <p className='font-medium text-foreground'>{pol.name}</p>
                    <p className='truncate text-xs text-muted-foreground'>{pol.natural_language}</p>
                  </div>
                  <Button
                    variant={pol.is_active ? 'default' : 'outline'}
                    size='sm'
                    onClick={() => togglePolicy(pol.id, pol.is_active)}
                  >
                    {pol.is_active ? (
                      <>
                        <Icons.checkCircle className='mr-1.5 h-4 w-4' /> On
                      </>
                    ) : (
                      'Off'
                    )}
                  </Button>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* Draft / Send Dialog */}
      <Dialog open={!!selectedLead} onOpenChange={(open) => !open && setSelectedLead(null)}>
        <DialogContent className='sm:max-w-2xl'>
          <DialogHeader>
            <DialogTitle>Draft Email to {selectedLead?.first_name} {selectedLead?.last_name}</DialogTitle>
            <DialogDescription>Review and send this AI-drafted email.</DialogDescription>
          </DialogHeader>

          {isDrafting ? (
            <div className='flex justify-center p-8'>
              <Icons.loader className='h-8 w-8 animate-spin text-muted-foreground' />
            </div>
          ) : (
            <div className='space-y-4'>
              <div className='space-y-2'>
                <Label>Subject</Label>
                <input
                  type='text'
                  className='flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm'
                  value={draftSubject}
                  onChange={(e) => setDraftSubject(e.target.value)}
                />
              </div>
              <div className='space-y-2'>
                <Label>Body</Label>
                <textarea
                  className='min-h-[160px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm'
                  value={draftBody}
                  onChange={(e) => setDraftBody(e.target.value)}
                />
              </div>
            </div>
          )}

          <DialogFooter>
            <Button variant='outline' onClick={() => setSelectedLead(null)}>Cancel</Button>
            <Button onClick={handleSend} disabled={isDrafting || isSending || !draftBody}>
              {isSending ? <Icons.loader className='mr-2 h-4 w-4 animate-spin' /> : <Icons.send className='mr-2 h-4 w-4' />}
              {isSending ? 'Sending...' : 'Send Email'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </motion.div>
  )
}
