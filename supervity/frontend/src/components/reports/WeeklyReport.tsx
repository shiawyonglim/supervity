'use client'

import React, { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { apiClient } from '@/lib/api-client'
import { cn } from '@/lib/utils'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Icons } from '@/components/ui/icons'

interface LeaderboardRow {
  owner_id: string
  name: string
  role: string
  opportunities: number
  revenue: number
  won: number
  lost: number
  expected_closes: number
  expected_revenue: number
}

interface RoleSummary {
  owners: { owner_id: string; name: string; opportunities: number; revenue: number; expected_closes: number }[]
  opportunities: number
  revenue: number
  won: number
  lost: number
  expected_closes: number
  expected_revenue: number
}

interface WeeklyReportData {
  week_of: string
  total_revenue: number
  pipeline_value: number
  total_opportunities: number
  won_opportunities: number
  lost_opportunities: number
  open_opportunities: number
  expected_closes_next_week: number
  expected_revenue_next_week: number
  leaderboard: LeaderboardRow[]
  by_role: Record<string, RoleSummary>
  what_to_expect_next_week: string
}

const containerVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { staggerChildren: 0.08 } },
}

const itemVariants = {
  hidden: { opacity: 0, y: 16 },
  visible: { opacity: 1, y: 0 },
}

export function WeeklyReport() {
  const [report, setReport] = useState<WeeklyReportData | null>(null)
  const [loading, setLoading] = useState(true)
  const [weeksAhead, setWeeksAhead] = useState(1)

  const load = async () => {
    setLoading(true)
    try {
      const res = await apiClient.get<WeeklyReportData>(`/api/reports/weekly?weeks_ahead=${weeksAhead}`)
      setReport(res)
    } catch (err) {
      console.error('Failed to load weekly report:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [weeksAhead])

  const kpiCards = report
    ? [
        { title: 'Total Revenue', value: `$${report.total_revenue.toLocaleString()}`, icon: Icons.trendingUp, color: 'bg-emerald-500' },
        { title: 'Pipeline Value', value: `$${report.pipeline_value.toLocaleString()}`, icon: Icons.barChart, color: 'bg-amber-500' },
        { title: 'Open Opps', value: report.open_opportunities, icon: Icons.activity, color: 'bg-brand-primary' },
        { title: 'Expected Closes', value: report.expected_closes_next_week, icon: Icons.calendar, color: 'bg-violet-500' },
      ]
    : []

  return (
    <motion.div className='space-y-8' variants={containerVariants} initial='hidden' animate='visible'>
      <motion.div variants={itemVariants} className='flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between'>
        <div>
          <h1 className='text-display-3 font-bold tracking-tight text-brand-navy'>Weekly Report</h1>
          <p className='mt-2 text-lg text-muted-foreground'>Revenue, pipeline, and leaderboards across every role.</p>
        </div>
        <div className='flex items-center gap-2'>
          <select
            className='h-10 rounded-md border border-input bg-background px-3 py-2 text-sm'
            value={weeksAhead}
            onChange={(e) => setWeeksAhead(parseInt(e.target.value))}
          >
            <option value={1}>Next 1 week</option>
            <option value={2}>Next 2 weeks</option>
            <option value={4}>Next 4 weeks</option>
          </select>
          <Button onClick={load} disabled={loading} variant='outline'>
            {loading ? <Icons.loader className='mr-2 h-4 w-4 animate-spin' /> : <Icons.refresh className='mr-2 h-4 w-4' />}
            Refresh
          </Button>
        </div>
      </motion.div>

      {report && (
        <motion.div variants={itemVariants} className='rounded-xl border bg-slate-50 p-4 text-sm text-brand-navy'>
          <strong>What to expect next week:</strong> {report.what_to_expect_next_week}
        </motion.div>
      )}

      {loading || !report ? (
        <div className='flex justify-center p-12'>
          <Icons.loader className='h-8 w-8 animate-spin text-muted-foreground' />
        </div>
      ) : (
        <>
          {/* KPI Cards */}
          <motion.div variants={itemVariants} className='grid gap-4 sm:grid-cols-2 lg:grid-cols-4'>
            {kpiCards.map((card) => (
              <Card key={card.title} className='relative overflow-hidden'>
                <CardContent className='relative z-10 p-5'>
                  <div className='flex items-start justify-between'>
                    <div className='space-y-2'>
                      <p className='text-micro uppercase text-brand-muted'>{card.title}</p>
                      <p className='font-display text-2xl font-bold text-brand-navy'>{card.value}</p>
                    </div>
                    <div className={cn('rounded-xl p-2.5 text-white shadow-lg', card.color)}>
                      <card.icon className='h-5 w-5' strokeWidth={1.5} />
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </motion.div>

          {/* Leaderboard */}
          <motion.div variants={itemVariants}>
            <Card>
              <CardHeader>
                <CardTitle className='flex items-center gap-2'>
                  <Icons.star className='h-5 w-5 text-brand-primary' />
                  Leaderboard
                </CardTitle>
                <CardDescription>Performance by owner for the selected time horizon.</CardDescription>
              </CardHeader>
              <CardContent>
                <div className='overflow-x-auto'>
                  <table className='w-full text-sm'>
                    <thead className='border-b text-left text-xs text-muted-foreground uppercase'>
                      <tr>
                        <th className='py-3 px-4 font-medium'>Owner</th>
                        <th className='py-3 px-4 font-medium'>Role</th>
                        <th className='py-3 px-4 font-medium text-right'>Opportunities</th>
                        <th className='py-3 px-4 font-medium text-right'>Revenue</th>
                        <th className='py-3 px-4 font-medium text-right'>Won</th>
                        <th className='py-3 px-4 font-medium text-right'>Expected Closes</th>
                        <th className='py-3 px-4 font-medium text-right'>Expected Revenue</th>
                      </tr>
                    </thead>
                    <tbody>
                      {report.leaderboard.map((row) => (
                        <tr key={row.owner_id} className='border-b last:border-0 hover:bg-slate-50'>
                          <td className='py-3 px-4 font-medium text-brand-navy'>{row.name}</td>
                          <td className='py-3 px-4'>
                            <Badge variant='outline' className='text-[10px]'>{row.role}</Badge>
                          </td>
                          <td className='py-3 px-4 text-right'>{row.opportunities}</td>
                          <td className='py-3 px-4 text-right'>${Number(row.revenue).toLocaleString()}</td>
                          <td className='py-3 px-4 text-right'>{row.won}</td>
                          <td className='py-3 px-4 text-right'>{row.expected_closes}</td>
                          <td className='py-3 px-4 text-right'>${Number(row.expected_revenue).toLocaleString()}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          </motion.div>

          {/* By Role */}
          <motion.div variants={itemVariants}>
            <Card>
              <CardHeader>
                <CardTitle>By Role</CardTitle>
                <CardDescription>Aggregated view across SDR, Sales Agent, Manager, and CRO.</CardDescription>
              </CardHeader>
              <CardContent>
                <div className='grid gap-4 sm:grid-cols-2 lg:grid-cols-4'>
                  {Object.entries(report.by_role).map(([role, data]) => (
                    <div key={role} className='rounded-xl border p-4'>
                      <p className='text-micro uppercase text-brand-muted'>{role}</p>
                      <p className='mt-1 font-display text-2xl font-bold text-brand-navy'>${data.revenue.toLocaleString()}</p>
                      <div className='mt-2 space-y-1 text-xs text-muted-foreground'>
                        <p>{data.opportunities} opps · {data.won} won</p>
                        <p>{data.expected_closes} expected closes</p>
                        <p>${data.expected_revenue.toLocaleString()} expected revenue</p>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </motion.div>
        </>
      )}
    </motion.div>
  )
}
