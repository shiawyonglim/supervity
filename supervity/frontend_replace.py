import os

new_page = """'use client'

import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Icons } from '@/components/ui/icons'
import { cn } from '@/lib/utils'
import { apiClient } from '@/lib/api-client'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog'
import { Badge } from '@/components/ui/badge'

const containerVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { staggerChildren: 0.1 } },
}

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 },
}

type TabType = 'buying-groups' | 'dedup' | 'routing' | 'consent' | 'integrations' | 'quality'

const tabs = [
  { id: 'buying-groups' as TabType, label: 'Buying Groups', icon: Icons.users },
  { id: 'dedup' as TabType, label: 'Deduplication', icon: Icons.layers },
  { id: 'routing' as TabType, label: 'Routing & Territories', icon: Icons.share },
  { id: 'consent' as TabType, label: 'Consent Registry', icon: Icons.checkCircle },
  { id: 'integrations' as TabType, label: 'Integrations', icon: Icons.zap },
  { id: 'quality' as TabType, label: 'Data Quality', icon: Icons.shield },
]

export default function DataManagerPage() {
  const [activeTab, setActiveTab] = useState<TabType>('buying-groups')
  const [data, setData] = useState<any>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [inspectorOpen, setInspectorOpen] = useState(false)
  const [inspectorData, setInspectorData] = useState<{title: string, records: any[], errorField?: string} | null>(null)

  const openInspector = (title: string, records: any[], errorField?: string) => {
    setInspectorData({ title, records, errorField })
    setInspectorOpen(true)
  }

  const fetchData = useCallback(async (tab: TabType) => {
    setIsLoading(true)
    try {
      let endpoint = `/api/data-manager/${tab}`
      if (tab === 'dedup') endpoint = `/api/data-manager/dedup/config`
      const response = await apiClient.get<any>(endpoint)
      setData(response)
    } catch (err) {
      console.error(`Failed to load ${tab}:`, err)
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData(activeTab)
  }, [activeTab, fetchData])

  const renderContent = () => {
    if (isLoading) {
      return <div className="flex justify-center p-12"><Icons.loader className="h-8 w-8 animate-spin text-muted-foreground" /></div>
    }

    if (!data) return null

    switch (activeTab) {
      case 'buying-groups':
        return (
          <div className="space-y-4">
            {data.buying_groups?.map((bg: any) => (
              <Card key={bg.group_id} className={cn("bg-white border-l-4", bg.is_proposed ? "border-l-amber-400" : "border-l-brand-cornflower")}>
                <CardHeader className="pb-2 flex flex-row items-center justify-between">
                  <div>
                    <CardTitle className="text-lg flex items-center gap-2">
                      {bg.account_name} 
                      {bg.is_proposed && <Badge variant="secondary" className="bg-amber-100 text-amber-800 hover:bg-amber-100">Proposed</Badge>}
                    </CardTitle>
                    <CardDescription>{bg.account_industry}</CardDescription>
                  </div>
                  {bg.is_proposed && (
                    <Button variant="outline" size="sm" onClick={() => {}} className="h-8">Review in Workbench</Button>
                  )}
                </CardHeader>
                <CardContent>
                  <div className="space-y-2 mt-2">
                    {bg.contacts?.map((c: any) => (
                      <div key={c.contact_id} className="flex justify-between items-center p-3 bg-gray-50 rounded-lg border">
                        <div>
                          <p className="font-medium text-sm text-brand-navy">{c.name} {c.is_primary && <Badge variant="default" className="ml-2 text-[10px]">Primary</Badge>}</p>
                          <p className="text-xs text-muted-foreground">{c.title} • {c.email}</p>
                        </div>
                        <Badge variant="outline">{c.role}</Badge>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )

      case 'dedup':
        return (
          <div className="space-y-6">
             <Card>
              <CardHeader>
                <CardTitle>Deduplication Settings</CardTitle>
                <CardDescription>Configure auto-merge thresholds and strategies.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex flex-col gap-1">
                  <label className="text-sm font-medium">Confidence Threshold ({data.confidence_threshold}%)</label>
                  <input type="range" min="0" max="100" value={data.confidence_threshold || 80} className="w-full max-w-md" readOnly />
                </div>
                <div className="flex flex-col gap-1">
                  <label className="text-sm font-medium">Match Strategy</label>
                  <p className="text-sm text-muted-foreground">{data.match_strategy}</p>
                </div>
                <Button onClick={async () => {
                    await apiClient.post('/api/data-manager/dedup/run', {})
                    alert('Deduplication job triggered!')
                }}>Run Deduplication Now</Button>
              </CardContent>
            </Card>
          </div>
        )

      case 'routing':
        return (
          <div className="grid md:grid-cols-2 gap-6">
            <Card className="md:col-span-2">
              <CardHeader>
                <CardTitle>SDR Roster & Coverage</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {data.sdr_roster?.map((sdr: any) => {
                    const capacityRatio = (sdr.current_capacity || 0) / (sdr.max_capacity || 1);
                    return (
                    <div key={sdr.owner_id} className="p-4 border rounded-lg flex flex-col md:flex-row gap-4 items-start md:items-center justify-between">
                      <div>
                        <p className="font-semibold text-sm flex items-center gap-2">
                          {sdr.name} ({sdr.owner_id})
                          {!sdr.active && <Badge variant="destructive">Inactive</Badge>}
                        </p>
                        <p className="text-xs text-muted-foreground mt-1">Region: {sdr.region} • Segment: {sdr.segment}</p>
                        {sdr.coverage_rules && sdr.coverage_rules.length > 0 && (
                           <div className="flex flex-wrap gap-1 mt-2">
                              {sdr.coverage_rules.map((cr: any) => (
                                <Badge key={cr.rule_id} variant="secondary" className="text-[10px]">{cr.rule_name}</Badge>
                              ))}
                           </div>
                        )}
                      </div>
                      <div className="flex flex-col items-end">
                         <span className={cn("text-sm font-medium", capacityRatio >= 1 ? "text-red-500" : "text-green-600")}>
                           {sdr.current_capacity || 0} / {sdr.max_capacity || 0} Capacity
                         </span>
                         <div className="w-32 h-2 bg-gray-200 rounded-full mt-1 overflow-hidden">
                           <div 
                             className={cn("h-full", capacityRatio >= 1 ? "bg-red-500" : "bg-green-500")}
                             style={{width: `${Math.min(capacityRatio * 100, 100)}%`}}
                           />
                         </div>
                      </div>
                    </div>
                  )})}
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Routing Rules</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {data.routing_rules?.map((rule: any) => (
                    <div key={rule.rule_id} className="p-3 border rounded-lg">
                      <p className="font-semibold text-sm">{rule.rule_name} <span className="text-muted-foreground font-normal text-xs">(Priority {rule.priority})</span></p>
                      <p className="text-xs text-muted-foreground mt-1 font-mono bg-gray-50 p-1 rounded">
                        {rule.region || '*'} / {rule.segment || '*'} / {rule.industry || '*'} ➔ {rule.owner_id}
                      </p>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Territories</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {data.territories?.map((t: any) => (
                    <div key={t.territory_id} className="flex justify-between p-3 border rounded-lg">
                      <span className="font-medium text-sm">{t.territory_name}</span>
                      <span className="text-xs text-muted-foreground">{t.region}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        )

      case 'consent':
        return (
          <Card>
            <CardHeader>
              <CardTitle>Consent Registry</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full text-sm text-left">
                  <thead className="text-xs text-muted-foreground bg-gray-50 uppercase">
                    <tr>
                      <th className="px-4 py-3 rounded-tl-lg">Contact</th>
                      <th className="px-4 py-3">Region</th>
                      <th className="px-4 py-3">Basis</th>
                      <th className="px-4 py-3">Status</th>
                      <th className="px-4 py-3 rounded-tr-lg">Channel</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.consent_records?.map((record: any) => (
                      <tr key={record.consent_id} className="border-b last:border-0">
                        <td className="px-4 py-3 font-medium text-brand-navy">{record.contact_name}</td>
                        <td className="px-4 py-3">{record.region}</td>
                        <td className="px-4 py-3">{record.basis}</td>
                        <td className="px-4 py-3">
                          <Badge variant={record.status === 'granted' ? 'default' : 'secondary'}>{record.status}</Badge>
                        </td>
                        <td className="px-4 py-3">{record.channel}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        )

      case 'integrations':
        return (
          <div className="grid md:grid-cols-2 gap-4">
            {data.integrations?.map((integ: any, idx: number) => (
              <Card key={idx}>
                <CardHeader>
                  <div className="flex justify-between items-start">
                    <CardTitle className="text-base">{integ.name}</CardTitle>
                    <Badge variant={integ.status === 'healthy' ? 'default' : 'destructive'} className={integ.status === 'healthy' ? 'bg-emerald-500 hover:bg-emerald-600' : ''}>
                      {integ.status}
                    </Badge>
                  </div>
                  <CardDescription>{integ.type}</CardDescription>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">{integ.description}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        )

      case 'quality':
        const renderQualitySection = (title: string, items: any[], icon: any, color: string) => (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                {icon}
                {title}
              </CardTitle>
            </CardHeader>
            <CardContent>
              {items?.length > 0 ? (
                <div className="space-y-2">
                  {items.map((item: any, idx: number) => (
                    <div key={idx} className={`flex justify-between items-center p-3 border rounded-lg ${color}`}>
                      <div>
                        <span className="font-medium text-sm text-slate-800">{item.issue}</span>
                        <Badge variant="outline" className="ml-2 bg-white/50">{item.severity}</Badge>
                        <span className="text-xs text-slate-600 font-mono bg-white/50 px-2 py-1 rounded ml-2">{item.count} rows affected</span>
                      </div>
                      {item.examples?.length > 0 && (
                        <Button variant="outline" size="sm" onClick={() => openInspector(`Issue: ${item.issue}`, item.examples.map((id:any) => ({ id })))} className="h-7 text-xs bg-white/50">
                          <Icons.search className="w-3 h-3 mr-1" /> Inspect Examples
                        </Button>
                      )}
                    </div>
                  ))}
                </div>
              ) : <p className="text-sm text-emerald-600 font-medium">✓ All checks passed.</p>}
            </CardContent>
          </Card>
        );

        return (
          <div className="space-y-6">
             {renderQualitySection("Chronological Anomalies", data.chronological, <Icons.clock className="w-5 h-5 text-purple-500" />, "bg-purple-50/50 border-purple-100")}
             {renderQualitySection("Relational Mismatches", data.relational, <Icons.network className="w-5 h-5 text-blue-500" />, "bg-blue-50/50 border-blue-100")}
             {renderQualitySection("State & Logic Errors", data.state_logic, <Icons.alertTriangle className="w-5 h-5 text-amber-500" />, "bg-amber-50/50 border-amber-100")}
             {renderQualitySection("Format Violations", data.format, <Icons.fileText className="w-5 h-5 text-rose-500" />, "bg-rose-50/50 border-rose-100")}
          </div>
        )

      default:
        return null
    }
  }

  return (
    <motion.div className="space-y-8" variants={containerVariants} initial="hidden" animate="visible">
      <motion.div variants={itemVariants}>
        <h1 className="text-display-3 font-bold tracking-tight text-brand-navy">Data Manager</h1>
        <p className="mt-2 text-lg text-muted-foreground">Manage your centralized master data, routing, and integrations.</p>
      </motion.div>

      <motion.div variants={itemVariants} className="flex space-x-1 border-b">
        {tabs.map((tab) => {
          const Icon = tab.icon
          const isActive = activeTab === tab.id
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                'flex items-center space-x-2 px-4 py-2 text-sm font-medium transition-colors border-b-2',
                isActive
                  ? 'border-brand-cornflower text-brand-navy'
                  : 'border-transparent text-muted-foreground hover:text-foreground hover:border-border'
              )}
            >
              <Icon className="h-4 w-4" />
              <span>{tab.label}</span>
            </button>
          )
        })}
      </motion.div>

      <motion.div variants={itemVariants}>
        {renderContent()}
      </motion.div>

      <Dialog open={inspectorOpen} onOpenChange={setInspectorOpen}>
        <DialogContent className="max-w-4xl max-h-[85vh] overflow-hidden flex flex-col p-0">
          <div className="p-6 pb-2">
            <DialogHeader>
              <DialogTitle className="flex items-center space-x-2 text-xl">
                <Icons.alertTriangle className="w-6 h-6 text-amber-500" />
                <span>{inspectorData?.title}</span>
              </DialogTitle>
              <DialogDescription className="text-sm mt-1">
                Displaying {inspectorData?.records?.length} affected ID(s).
              </DialogDescription>
            </DialogHeader>
          </div>
          <div className="flex-1 overflow-y-auto p-6 pt-2 space-y-6">
            <div className="p-4 grid grid-cols-2 md:grid-cols-4 gap-3 bg-slate-50 border rounded-lg">
               {inspectorData?.records?.map((record, i) => (
                  <div key={i} className="font-mono text-xs bg-white border p-2 rounded">
                     {record.id || JSON.stringify(record)}
                  </div>
               ))}
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </motion.div>
  )
}
"""

with open('frontend/src/app/data-manager/page.tsx', 'w') as f:
    f.write(new_page)

print("Successfully replaced frontend page!")
