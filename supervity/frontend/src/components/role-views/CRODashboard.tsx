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

interface OrgNode {
  cro_id?: string
  manager_id?: string
  agent_id?: string
  owner_id?: string
  name: string
  email?: string
  active: boolean
  current_capacity?: number
  max_capacity?: number
  managers?: OrgNode[]
  agents?: OrgNode[]
  sdrs?: OrgNode[]
}

interface OrgHierarchy {
  hierarchy: OrgNode[]
  counts: { cros: number; managers: number; agents: number; sdrs: number }
}

interface Opportunity {
  Id: string
  Name: string
  AccountId: string
  Amount: number | string
  StageName: string
  IsWon: boolean
  IsClosed: boolean
  OwnerId: string
}

interface Contact {
  Id: string
  OwnerId: string
  Owner_Name: string
  Lead_Stage__c: string
  FirstName: string
  LastName: string
  Email: string
}

interface Account {
  Id: string
  Name: string
}

const containerVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { staggerChildren: 0.08 } },
}

const itemVariants = {
  hidden: { opacity: 0, y: 16 },
  visible: { opacity: 1, y: 0 },
}

export function CRODashboard() {
  const [loading, setLoading] = useState(true)
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [forecast, setForecast] = useState<string>('')
  const [hierarchy, setHierarchy] = useState<OrgHierarchy | null>(null)
  const [opportunities, setOpportunities] = useState<Opportunity[]>([])
  const [accounts, setAccounts] = useState<Account[]>([])
  const [contacts, setContacts] = useState<Contact[]>([])
  const [weeklyOpen, setWeeklyOpen] = useState(false)
  const [weeklyDraft, setWeeklyDraft] = useState<{ subject: string; body: string; to: string } | null>(null)
  const [weeklyLoading, setWeeklyLoading] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [s, f, h, o, a, c] = await Promise.all([
        apiClient.get<DashboardStats>('/api/dashboard/stats'),
        apiClient.get<{ forecast: string }>('/api/insights/forecast'),
        apiClient.get<OrgHierarchy>('/api/org/hierarchy'),
        apiClient.get<{ data: Opportunity[] }>('/api/data/opportunity?limit=200'),
        apiClient.get<{ data: Account[] }>('/api/data/account?limit=200'),
        apiClient.get<{ data: Contact[] }>('/api/data/contact?limit=200'),
      ])
      setStats(s)
      setForecast(f.forecast)
      setHierarchy(h)
      setOpportunities(o.data || [])
      setAccounts(a.data || [])
      setContacts(c.data || [])
    } catch (err) {
      console.error('CRO dashboard load failed:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const revenue = useMemo(() => {
    return opportunities
      .filter((o) => o.IsWon)
      .reduce((sum, o) => sum + (Number(o.Amount) || 0), 0)
  }, [opportunities])

  const openPipeline = useMemo(() => {
    return opportunities
      .filter((o) => !o.IsClosed)
      .reduce((sum, o) => sum + (Number(o.Amount) || 0), 0)
  }, [opportunities])

  const accountRevenue = useMemo(() => {
    const map: Record<string, number> = {}
    opportunities
      .filter((o) => o.IsWon)
      .forEach((o) => {
        map[o.AccountId] = (map[o.AccountId] || 0) + (Number(o.Amount) || 0)
      })
    return Object.entries(map)
      .map(([accountId, value]) => ({
        accountId,
        name: accounts.find((a) => a.Id === accountId)?.Name || accountId,
        value,
      }))
      .sort((a, b) => b.value - a.value)
  }, [opportunities, accounts])

  const sdrPerformance = useMemo(() => {
    const counts: Record<string, { name: string; count: number; closed: number; value: number }> = {}
    contacts.forEach((c) => {
      if (!counts[c.OwnerId]) counts[c.OwnerId] = { name: c.Owner_Name || c.OwnerId, count: 0, closed: 0, value: 0 }
      counts[c.OwnerId].count += 1
    })
    opportunities
      .filter((o) => o.IsWon)
      .forEach((o) => {
        if (!counts[o.OwnerId]) counts[o.OwnerId] = { name: 'Unknown', count: 0, closed: 0, value: 0 }
        counts[o.OwnerId].closed += 1
        counts[o.OwnerId].value += Number(o.Amount) || 0
      })
    return Object.values(counts).sort((a, b) => b.value - a.value)
  }, [contacts, opportunities])

  const topSdr = sdrPerformance[0]
  const topCustomer = accountRevenue[0]

  const generateWeeklyEmail = async () => {
    setWeeklyLoading(true)
    try {
      const res = await apiClient.post<{ subject: string; body: string; to: string }>('/api/cro/weekly-email', {
        revenue,
        top_sdr: topSdr,
        top_customer: topCustomer,
      })
      setWeeklyDraft(res)
      setWeeklyOpen(true)
    } catch (err) {
      console.error('Weekly email draft failed:', err)
      setWeeklyDraft({
        subject: 'Weekly Revenue Summary',
        body: `Weekly revenue: $${revenue.toLocaleString()}\nTop SDR: ${topSdr?.name || 'N/A'}\nTop paying customer: ${topCustomer?.name || 'N/A'}`,
        to: 'cro@supervity.ai',
      })
      setWeeklyOpen(true)
    } finally {
      setWeeklyLoading(false)
    }
  }

  const sendWeeklyEmail = async () => {
    if (!weeklyDraft) return
    try {
      await apiClient.post('/api/cro/weekly-email/send', weeklyDraft)
      setWeeklyOpen(false)
      setWeeklyDraft(null)
    } catch (err) {
      console.error('Weekly email send failed:', err)
    }
  }

  const teamNodes: Array<{ id: string; name: string; role: string; color: string; capacity?: number; max?: number; active: boolean }> = useMemo(() => {
    const out: Array<{ id: string; name: string; role: string; color: string; capacity?: number; max?: number; active: boolean }> = []
    hierarchy?.hierarchy.forEach((cro) => {
      cro.managers?.forEach((m) => {
        out.push({ id: m.manager_id!, name: m.name, role: 'Manager', color: 'bg-blue-100 text-blue-700', capacity: m.current_capacity, max: m.max_capacity, active: m.active })
        m.agents?.forEach((a) => {
          out.push({ id: a.agent_id!, name: a.name, role: 'Sales Agent', color: 'bg-emerald-100 text-emerald-700', capacity: a.current_capacity, max: a.max_capacity, active: a.active })
          a.sdrs?.forEach((s) => {
            out.push({ id: s.owner_id!, name: s.name, role: 'SDR', color: 'bg-amber-100 text-amber-700', capacity: s.current_capacity, max: s.max_capacity, active: s.active })
          })
        })
      })
    })
    return out
  }, [hierarchy])

  return (
    <motion.div className='space-y-8' variants={containerVariants} initial='hidden' animate='visible'>
      <motion.div variants={itemVariants} className='flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between'>
        <div>
          <h1 className='text-display-3 font-bold tracking-tight text-brand-navy'>CRO Command Center</h1>
          <p className='mt-2 text-lg text-muted-foreground'>Scoreboard, revenue, and team performance.</p>
        </div>
        <Button variant='gradient' onClick={generateWeeklyEmail} disabled={weeklyLoading || loading}>
          {weeklyLoading ? <Icons.loader className='mr-2 h-4 w-4 animate-spin' /> : <Icons.mail className='mr-2 h-4 w-4' />}
          Weekly Email
        </Button>
      </motion.div>

      {/* KPIs */}
      <motion.div variants={itemVariants} className='grid gap-4 sm:grid-cols-2 lg:grid-cols-4'>
        {[
          { title: 'Total Revenue', value: `$${Math.round(revenue).toLocaleString()}`, icon: Icons.trendingUp, color: 'bg-emerald-500' },
          { title: 'Open Pipeline', value: `$${Math.round(openPipeline).toLocaleString()}`, icon: Icons.activity, color: 'bg-blue-500' },
          { title: 'Active Opps', value: stats?.active_opportunities ?? 0, icon: Icons.zap, color: 'bg-amber-500' },
          { title: 'Team Members', value: (hierarchy?.counts.sdrs ?? 0) + (hierarchy?.counts.agents ?? 0) + (hierarchy?.counts.managers ?? 0), icon: Icons.users, color: 'bg-purple-500' },
        ].map((card) => (
          <Card key={card.title} className='relative overflow-hidden'>
            <CardWatermark opacity={2} scale={0.95} />
            <CardContent className='relative z-10 p-5'>
              <div className='flex items-start justify-between'>
                <div className='space-y-2'>
                  <p className='text-micro uppercase text-brand-muted'>{card.title}</p>
                  <p className='font-display text-2xl font-bold text-brand-navy'>
                    {typeof card.value === 'string' ? card.value : card.value.toLocaleString()}
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

      {/* Forecast & Top Performers */}
      <div className='grid gap-6 lg:grid-cols-3'>
        <motion.div variants={itemVariants} className='lg:col-span-2'>
          <Card className='h-full'>
            <CardHeader>
              <CardTitle className='flex items-center gap-2'>
                <Icons.trendingUp className='h-5 w-5 text-brand-cornflower' />
                Expected Revenue This Month
              </CardTitle>
              <CardDescription>{forecast}</CardDescription>
            </CardHeader>
            <CardContent>
              <div className='rounded-xl border border-brand-cornflower/20 bg-brand-cornflower/5 p-4 text-sm leading-relaxed text-brand-navy'>
                {forecast || 'Forecast loading...'}
              </div>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div variants={itemVariants}>
          <Card className='h-full'>
            <CardHeader>
              <CardTitle className='flex items-center gap-2'>
                <Icons.star className='h-5 w-5 text-brand-cornflower' />
                Top Performers
              </CardTitle>
            </CardHeader>
            <CardContent className='space-y-4'>
              <div>
                <p className='text-xs font-semibold uppercase text-muted-foreground'>Top SDR</p>
                <p className='font-medium text-brand-navy'>{topSdr ? topSdr.name : '-'}</p>
                <p className='text-xs text-muted-foreground'>
                  {topSdr ? `${topSdr.closed} closed won · $${Math.round(topSdr.value).toLocaleString()}` : ''}
                </p>
              </div>
              <div>
                <p className='text-xs font-semibold uppercase text-muted-foreground'>Top Paying Customer</p>
                <p className='font-medium text-brand-navy'>{topCustomer ? topCustomer.name : '-'}</p>
                <p className='text-xs text-muted-foreground'>
                  {topCustomer ? `$${Math.round(topCustomer.value).toLocaleString()} revenue` : ''}
                </p>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>

      {/* Team Scoreboard */}
      <motion.div variants={itemVariants}>
        <Card>
          <CardHeader>
            <CardTitle className='flex items-center gap-2'>
              <Icons.users className='h-5 w-5 text-brand-cornflower' />
              Sales Team Scoreboard
            </CardTitle>
            <CardDescription>Capacity, load, and status for every rep in the org.</CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className='flex justify-center p-8'>
                <Icons.loader className='h-8 w-8 animate-spin text-muted-foreground' />
              </div>
            ) : teamNodes.length === 0 ? (
              <p className='text-center text-muted-foreground'>No team members found.</p>
            ) : (
              <div className='overflow-x-auto'>
                <table className='w-full text-sm'>
                  <thead className='border-b text-left text-xs text-muted-foreground uppercase'>
                    <tr>
                      <th className='py-3 px-4 font-medium'>Name</th>
                      <th className='py-3 px-4 font-medium'>Role</th>
                      <th className='py-3 px-4 font-medium'>Status</th>
                      <th className='py-3 px-4 font-medium'>Capacity</th>
                      <th className='py-3 px-4 font-medium text-right'>Load</th>
                    </tr>
                  </thead>
                  <tbody>
                    {teamNodes.map((node) => {
                      const pct = node.max ? Math.min(100, Math.round(((node.capacity || 0) / node.max) * 100)) : 0
                      return (
                        <tr key={node.id} className='border-b last:border-0 hover:bg-slate-50'>
                          <td className='py-3 px-4 font-medium text-brand-navy'>{node.name}</td>
                          <td className='py-3 px-4'>
                            <Badge className={cn('border px-1.5 py-0.5 text-[10px] font-bold uppercase', node.color)}>
                              {node.role}
                            </Badge>
                          </td>
                          <td className='py-3 px-4'>
                            <Badge variant={node.active ? 'default' : 'destructive'}>
                              {node.active ? 'Active' : 'Inactive'}
                            </Badge>
                          </td>
                          <td className='py-3 px-4'>
                            <div className='flex items-center gap-2'>
                              <div className='h-1.5 w-24 rounded-full bg-gray-200'>
                                <div
                                  className={cn('h-full rounded-full', pct > 90 ? 'bg-red-500' : pct > 70 ? 'bg-amber-500' : 'bg-emerald-500')}
                                  style={{ width: `${pct}%` }}
                                />
                              </div>
                              <span className='text-xs text-muted-foreground'>{node.capacity ?? 0}/{node.max ?? '-'}</span>
                            </div>
                          </td>
                          <td className='py-3 px-4 text-right'>{pct}%</td>
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

      {/* Weekly Email Dialog */}
      <Dialog open={weeklyOpen} onOpenChange={setWeeklyOpen}>
        <DialogContent className='sm:max-w-2xl'>
          <DialogHeader>
            <DialogTitle>Weekly CRO Email Preview</DialogTitle>
            <DialogDescription>Review before sending to {weeklyDraft?.to || 'cro@supervity.ai'}.</DialogDescription>
          </DialogHeader>
          {weeklyDraft ? (
            <div className='space-y-4'>
              <div className='space-y-1'>
                <p className='text-xs font-semibold uppercase text-muted-foreground'>Subject</p>
                <p className='text-sm font-medium'>{weeklyDraft.subject}</p>
              </div>
              <div className='space-y-1'>
                <p className='text-xs font-semibold uppercase text-muted-foreground'>Body</p>
                <pre className='whitespace-pre-wrap rounded-lg border bg-muted/30 p-4 text-sm'>{weeklyDraft.body}</pre>
              </div>
            </div>
          ) : (
            <p className='text-muted-foreground'>No draft.</p>
          )}
          <DialogFooter>
            <Button variant='outline' onClick={() => setWeeklyOpen(false)}>Close</Button>
            <Button onClick={sendWeeklyEmail} disabled={!weeklyDraft}>
              <Icons.send className='mr-2 h-4 w-4' />
              Send to CRO
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </motion.div>
  )
}
