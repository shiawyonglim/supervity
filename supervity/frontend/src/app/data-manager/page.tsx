'use client'

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

type TabType = 'buying-groups' | 'routing' | 'consent' | 'integrations' | 'quality'

const tabs = [
  { id: 'buying-groups' as TabType, label: 'Buying Groups', icon: Icons.users },
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
      const endpoint = `/api/data-manager/${tab}`
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
              <Card key={bg.group_id} className="bg-white">
                <CardHeader className="pb-2">
                  <CardTitle className="text-lg">{bg.account_name}</CardTitle>
                  <CardDescription>{bg.account_industry}</CardDescription>
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

      case 'routing':
        return (
          <div className="grid md:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>Routing Rules</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {data.routing_rules?.map((rule: any) => (
                    <div key={rule.rule_id} className="p-3 border rounded-lg">
                      <p className="font-semibold text-sm">{rule.rule_name}</p>
                      <p className="text-xs text-muted-foreground mt-1 font-mono bg-gray-50 p-1 rounded">
                        {rule.condition} ➔ {rule.action}
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
        return (
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Missing Values</CardTitle>
                <CardDescription>Empty cells detected across datasets.</CardDescription>
              </CardHeader>
              <CardContent>
                {data.missing_values?.length > 0 ? (
                  <div className="space-y-2">
                    {data.missing_values.map((mv: any, idx: number) => (
                      <div key={idx} className="flex justify-between items-center p-3 border rounded-lg bg-red-50/50">
                        <div>
                          <span className="font-medium text-sm text-red-800">{mv.dataset} • {mv.column}</span>
                          <span className="text-xs text-red-600 font-mono bg-red-100 px-2 py-1 rounded ml-2">{mv.count} missing ({mv.percentage}%)</span>
                        </div>
                        {mv.sample_records && (
                          <Button variant="outline" size="sm" onClick={() => openInspector(`Missing ${mv.column} in ${mv.dataset}`, mv.sample_records, mv.column)} className="h-7 text-xs border-red-200 text-red-700 hover:bg-red-100">
                            <Icons.search className="w-3 h-3 mr-1" /> Inspect
                          </Button>
                        )}
                      </div>
                    ))}
                  </div>
                ) : <p className="text-sm text-emerald-600 font-medium">✓ No missing values found.</p>}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Duplicates</CardTitle>
                <CardDescription>Exact row and primary key duplicates.</CardDescription>
              </CardHeader>
              <CardContent>
                {data.duplicates?.length > 0 ? (
                  <div className="space-y-2">
                    {data.duplicates.map((dup: any, idx: number) => (
                      <div key={idx} className="flex justify-between items-center p-3 border rounded-lg bg-orange-50/50">
                        <div>
                          <span className="font-medium text-sm text-orange-800">{dup.dataset}</span>
                          <span className="text-xs text-orange-600 font-mono bg-orange-100 px-2 py-1 rounded ml-2">{dup.count} {dup.type} {dup.column ? `(${dup.column})` : ''}</span>
                        </div>
                        {dup.sample_records && (
                          <Button variant="outline" size="sm" onClick={() => openInspector(`Duplicate ${dup.type} in ${dup.dataset}`, dup.sample_records, dup.column || (dup.type.includes('email') ? 'email' : undefined))} className="h-7 text-xs border-orange-200 text-orange-700 hover:bg-orange-100">
                            <Icons.search className="w-3 h-3 mr-1" /> Inspect
                          </Button>
                        )}
                      </div>
                    ))}
                  </div>
                ) : <p className="text-sm text-emerald-600 font-medium">✓ No duplicates found.</p>}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Format Inconsistencies</CardTitle>
                <CardDescription>Invalid emails, unparseable dates, or multiple date formats.</CardDescription>
              </CardHeader>
              <CardContent>
                {data.format_inconsistencies?.length > 0 ? (
                  <div className="space-y-2">
                    {data.format_inconsistencies.map((fi: any, idx: number) => (
                      <div key={idx} className="flex flex-col p-3 border rounded-lg bg-amber-50/50">
                        <div className="flex justify-between items-center">
                          <div>
                            <span className="font-medium text-sm text-amber-800">{fi.dataset} {fi.column ? `• ${fi.column}` : ''}</span>
                            <span className="text-xs text-amber-600 font-mono bg-amber-100 px-2 py-1 rounded ml-2">{fi.type} {fi.count ? `(${fi.count})` : ''}</span>
                          </div>
                          {fi.sample_records && (
                            <Button variant="outline" size="sm" onClick={() => openInspector(`Format Issue in ${fi.dataset}`, fi.sample_records, fi.column || (fi.type.includes('email') ? 'email' : undefined))} className="h-7 text-xs border-amber-200 text-amber-700 hover:bg-amber-100">
                              <Icons.search className="w-3 h-3 mr-1" /> Inspect
                            </Button>
                          )}
                        </div>
                        {fi.formats && (
                          <div className="mt-2 text-xs text-amber-700/80 font-mono">
                            Detected Formats: {Object.entries(fi.formats).map(([k,v]) => `${k}: ${v} rows`).join(', ')}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : <p className="text-sm text-emerald-600 font-medium">✓ No formatting issues found.</p>}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Business Logic Anomalies</CardTitle>
                <CardDescription>Negative amounts, over capacity SDRs, etc.</CardDescription>
              </CardHeader>
              <CardContent>
                {data.business_anomalies?.length > 0 ? (
                  <div className="space-y-2">
                    {data.business_anomalies.map((ba: any, idx: number) => (
                      <div key={idx} className="flex justify-between items-center p-3 border rounded-lg bg-rose-50/50">
                        <div>
                          <span className="font-medium text-sm text-rose-800">{ba.dataset} {ba.column ? `• ${ba.column}` : ''}</span>
                          <span className="text-xs text-rose-600 font-mono bg-rose-100 px-2 py-1 rounded ml-2">{ba.issue}: {ba.count}</span>
                        </div>
                        {ba.sample_records && (
                          <Button variant="outline" size="sm" onClick={() => openInspector(`Anomaly in ${ba.dataset}`, ba.sample_records, ba.column || (ba.issue.includes('capacity') ? 'current_capacity' : undefined))} className="h-7 text-xs border-rose-200 text-rose-700 hover:bg-rose-100">
                            <Icons.search className="w-3 h-3 mr-1" /> Inspect
                          </Button>
                        )}
                      </div>
                    ))}
                  </div>
                ) : <p className="text-sm text-emerald-600 font-medium">✓ No business anomalies found.</p>}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Foreign Key Mismatches</CardTitle>
                <CardDescription>Dangling identifiers that are completely missing in parent tables.</CardDescription>
              </CardHeader>
              <CardContent>
                {data.foreign_key_mismatches?.length > 0 ? (
                  <div className="space-y-2">
                    {data.foreign_key_mismatches.map((fk: any, idx: number) => (
                      <div key={idx} className="flex flex-col p-3 border rounded-lg bg-red-50/50">
                        <div className="flex justify-between items-center mb-2">
                          <div>
                            <span className="font-medium text-sm text-red-800">{fk.dataset}.{fk.column}</span>
                            <span className="text-xs text-red-600 font-mono bg-red-100 px-2 py-1 rounded ml-2">{fk.count} missing from {fk.missing_in}</span>
                          </div>
                          {fk.sample_records && (
                            <Button variant="outline" size="sm" onClick={() => openInspector(`Foreign Key Mismatch in ${fk.dataset}`, fk.sample_records, fk.column)} className="h-7 text-xs border-red-200 text-red-700 hover:bg-red-100">
                              <Icons.search className="w-3 h-3 mr-1" /> Inspect
                            </Button>
                          )}
                        </div>
                        <span className="text-[10px] text-red-700/80 font-mono">e.g. {fk.examples.join(', ')}</span>
                      </div>
                    ))}
                  </div>
                ) : <p className="text-sm text-emerald-600 font-medium">✓ No orphan records found.</p>}
              </CardContent>
            </Card>
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
                Displaying {inspectorData?.records?.length} raw record(s) extracted directly from the dataset.
              </DialogDescription>
            </DialogHeader>
          </div>
          <div className="flex-1 overflow-y-auto p-6 pt-2 space-y-6">
            {inspectorData?.records?.map((record, i) => (
              <div key={i} className="rounded-xl border bg-slate-50/50 overflow-hidden shadow-sm">
                <div className="bg-slate-100/80 px-4 py-2 border-b flex items-center space-x-2">
                  <Icons.table2 className="w-4 h-4 text-slate-400" />
                  <span className="text-xs font-semibold tracking-wider text-slate-500 uppercase">Record #{i + 1}</span>
                </div>
                <div className="p-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                  {Object.entries(record).map(([key, value]) => {
                    const isError = inspectorData.errorField === key;
                    return (
                      <div key={key} className={cn(
                        "flex flex-col space-y-1 p-3 rounded-lg transition-colors border",
                        isError ? "bg-red-50 border-red-200 ring-1 ring-red-200/50" : "bg-white border-slate-100 hover:border-slate-200"
                      )}>
                        <span className={cn(
                          "text-[10px] uppercase font-bold tracking-wider flex items-center justify-between",
                          isError ? "text-red-700" : "text-slate-400"
                        )}>
                          {key}
                          {isError && <Icons.alertCircle className="w-3 h-3 text-red-500" />}
                        </span>
                        <span className={cn(
                          "text-sm font-mono break-all",
                          isError ? "text-red-900 font-semibold" : "text-slate-700",
                          (value === '' || value === null) ? "italic text-slate-400" : ""
                        )}>
                          {value === '' || value === null ? 'null' : String(value)}
                        </span>
                      </div>
                    )
                  })}
                </div>
              </div>
            ))}
          </div>
        </DialogContent>
      </Dialog>
    </motion.div>
  )
}
