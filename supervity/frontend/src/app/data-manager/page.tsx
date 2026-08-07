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

type TabType = 'buying-groups' | 'dedup' | 'routing' | 'consent' | 'integrations' | 'quality' | 'database'

const tabs = [
  { id: 'buying-groups' as TabType, label: 'Buying Groups', icon: Icons.users },
  { id: 'dedup' as TabType, label: 'Deduplication', icon: Icons.layers },
  { id: 'routing' as TabType, label: 'Routing & Territories', icon: Icons.share },
  { id: 'consent' as TabType, label: 'Consent Registry', icon: Icons.checkCircle },
  { id: 'integrations' as TabType, label: 'Integrations', icon: Icons.zap },
  { id: 'quality' as TabType, label: 'Data Quality', icon: Icons.shield },
  { id: 'database' as TabType, label: 'Database Viewer', icon: Icons.table },
]

export default function DataManagerPage() {
  const [activeTab, setActiveTab] = useState<TabType>('buying-groups')
  const [data, setData] = useState<any>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [inspectorOpen, setInspectorOpen] = useState(false)
  const [inspectorData, setInspectorData] = useState<{title: string, records: any[], errorField?: string} | null>(null)
  
  const [dedupResult, setDedupResult] = useState<{merged: number, exceptions: number} | null>(null)
  const [routingResult, setRoutingResult] = useState<any>(null)

  // Dedup config state
  const [dedupThreshold, setDedupThreshold] = useState(80)
  const [dedupStrategy, setDedupStrategy] = useState('Exact Email Match')
  const [dedupSaving, setDedupSaving] = useState(false)
  const [dedupRunning, setDedupRunning] = useState(false)
  const [routingRunning, setRoutingRunning] = useState(false)

  // Database Viewer state
  const [dbTables, setDbTables] = useState<string[]>([])
  const [activeTable, setActiveTable] = useState<string | null>(null)
  const [tableData, setTableData] = useState<any[]>([])

  const openInspector = (title: string, records: any[], errorField?: string) => {
    setInspectorData({ title, records, errorField })
    setInspectorOpen(true)
  }

  const fetchData = useCallback(async (tab: TabType) => {
    setIsLoading(true)
    setDedupResult(null)
    setRoutingResult(null)
    
    try {
      if (tab === 'database') {
        const response = await apiClient.get<any>('/api/data-manager/database/tables')
        setDbTables(response.tables || [])
        setData(true)
      } else {
        let endpoint = `/api/data-manager/${tab}`
        if (tab === 'dedup') endpoint = `/api/data-manager/dedup/config`
        const response = await apiClient.get<any>(endpoint)
        setData(response)
        // Sync dedup config state
        if (tab === 'dedup' && response) {
          setDedupThreshold(response.confidence_threshold ?? 80)
          setDedupStrategy(response.match_strategy ?? 'Exact Email Match')
        }
      }
    } catch (err) {
      console.error(`Failed to load ${tab}:`, err)
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData(activeTab)
  }, [activeTab, fetchData])

  const fetchTableData = async (tableName: string) => {
    setActiveTable(tableName)
    setTableData([])
    try {
      const res = await apiClient.get<any>(`/api/data-manager/database/table/${tableName}`)
      setTableData(res.rows || [])
    } catch (e) {
      console.error(e)
    }
  }

  const saveDedupConfig = async () => {
    setDedupSaving(true)
    try {
      const res = await apiClient.post<any>('/api/data-manager/dedup/config', {
        confidence_threshold: dedupThreshold,
        match_strategy: dedupStrategy,
      })
      setData(res)
    } catch (e) {
      console.error(e)
    } finally {
      setDedupSaving(false)
    }
  }

  const runDedup = async () => {
    setDedupRunning(true)
    setDedupResult(null)
    try {
      const res = await apiClient.post<any>('/api/data-manager/dedup/run', {})
      if (res?.results) setDedupResult(res.results)
    } catch (e) {
      console.error(e)
    } finally {
      setDedupRunning(false)
    }
  }

  const runRouting = async () => {
    setRoutingRunning(true)
    setRoutingResult(null)
    try {
      const res = await apiClient.post<any>('/api/data-manager/routing/run', { contact_ids: [] })
      if (res?.results) setRoutingResult(res.results)
    } catch (e) {
      console.error(e)
    } finally {
      setRoutingRunning(false)
    }
  }

  const renderContent = () => {
    if (isLoading) {
      return <div className="flex justify-center p-12"><Icons.loader className="h-8 w-8 animate-spin text-muted-foreground" /></div>
    }

    if (!data) return null

    switch (activeTab) {
      case 'database':
        return (
          <div className="flex flex-col md:flex-row gap-6">
            <Card className="md:w-1/4 h-fit">
              <CardHeader>
                <CardTitle className="text-lg">Tables</CardTitle>
              </CardHeader>
              <CardContent className="space-y-1">
                {dbTables.map(t => (
                  <Button 
                    key={t} 
                    variant={activeTable === t ? 'default' : 'ghost'} 
                    className="w-full justify-start font-mono text-xs"
                    onClick={() => fetchTableData(t)}
                  >
                    <Icons.table className="w-3 h-3 mr-2" />
                    {t}
                  </Button>
                ))}
              </CardContent>
            </Card>
            <Card className="md:w-3/4 flex-1">
              <CardHeader>
                <CardTitle>{activeTable ? `Table: ${activeTable}` : 'Select a table'}</CardTitle>
                <CardDescription>
                  {activeTable ? `Showing top 100 records from the cleaned database.` : 'View raw database records.'}
                </CardDescription>
              </CardHeader>
              <CardContent>
                {tableData.length > 0 ? (
                   <div className="overflow-x-auto border rounded-md">
                     <table className="w-full text-xs text-left">
                       <thead className="text-[10px] text-muted-foreground bg-gray-50 uppercase">
                         <tr>
                           {Object.keys(tableData[0]).map(key => (
                             <th key={key} className="px-3 py-2 whitespace-nowrap">{key}</th>
                           ))}
                         </tr>
                       </thead>
                       <tbody className="font-mono">
                         {tableData.map((row, idx) => (
                           <tr key={idx} className="border-b last:border-0 hover:bg-gray-50/50">
                             {Object.values(row).map((val: any, vIdx) => (
                               <td key={vIdx} className="px-3 py-2 whitespace-nowrap max-w-[200px] truncate">
                                 {val === null ? <span className="text-gray-300 italic">null</span> : String(val)}
                               </td>
                             ))}
                           </tr>
                         ))}
                       </tbody>
                     </table>
                   </div>
                ) : activeTable ? (
                  <p className="text-sm text-muted-foreground">No records found or table is empty.</p>
                ) : null}
              </CardContent>
            </Card>
          </div>
        )

      case 'buying-groups':
        return (
          <div className="space-y-6">
            {/* Summary stats */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <Card className="bg-brand-navy text-white">
                <CardContent className="p-4">
                  <p className="text-sm text-brand-cloud">Total Groups</p>
                  <p className="text-3xl font-display font-bold">{data.count ?? 0}</p>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="p-4">
                  <p className="text-sm text-muted-foreground">Existing (Confirmed)</p>
                  <p className="text-3xl font-display font-bold text-brand-cornflower">{data.existing_count ?? 0}</p>
                </CardContent>
              </Card>
              <Card className="border-amber-200 bg-amber-50/30">
                <CardContent className="p-4">
                  <p className="text-sm text-amber-700">Proposed (Needs Review)</p>
                  <p className="text-3xl font-display font-bold text-amber-600">{data.proposed_count ?? 0}</p>
                </CardContent>
              </Card>
            </div>

            {data.buying_groups?.map((bg: any) => (
              <Card key={bg.group_id} className={cn("border-l-4", bg.is_proposed ? "border-l-amber-400" : "border-l-brand-cornflower")}>
                <CardHeader className="pb-2 flex flex-row items-center justify-between">
                  <div>
                    <CardTitle className="text-lg flex items-center gap-2">
                      {bg.account_name} 
                      {bg.is_proposed && <Badge variant="secondary" className="bg-amber-100 text-amber-800 hover:bg-amber-100">Proposed</Badge>}
                      {!bg.is_proposed && <Badge variant="secondary" className="bg-blue-100 text-blue-800 hover:bg-blue-100">Confirmed</Badge>}
                    </CardTitle>
                    <CardDescription>{bg.account_industry} • {bg.contacts?.length} member(s)</CardDescription>
                  </div>
                  {bg.is_proposed && (
                    <Button variant="outline" size="sm" className="h-8">
                      <Icons.alertTriangle className="w-3 h-3 mr-1" /> Review in Workbench
                    </Button>
                  )}
                </CardHeader>
                <CardContent>
                  <div className="space-y-2 mt-2">
                    {bg.contacts?.map((c: any) => (
                      <div key={c.contact_id} className="flex justify-between items-center p-3 bg-gray-50 rounded-lg border">
                        <div>
                          <p className="font-medium text-sm text-brand-navy">
                            {c.name}
                            {c.is_primary && <Badge variant="default" className="ml-2 text-[10px]">Primary</Badge>}
                          </p>
                          <p className="text-xs text-muted-foreground">{c.title} • {c.email}</p>
                          {c.activity_count && (
                            <p className="text-xs text-amber-600 mt-1">
                              <Icons.zap className="w-3 h-3 inline mr-1" />
                              {c.activity_count} high-intent activities
                            </p>
                          )}
                        </div>
                        {c.role ? (
                          <Badge variant="outline">{c.role}</Badge>
                        ) : (
                          <Badge variant="outline" className="border-amber-300 text-amber-600 bg-amber-50">Unresolved</Badge>
                        )}
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
                <CardTitle className="font-display">Deduplication Settings</CardTitle>
                <CardDescription>Configure auto-merge thresholds and match strategies. Changes are saved to the database.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="flex flex-col gap-2">
                  <label className="text-sm font-medium">
                    Confidence Threshold: <span className="text-brand-cornflower font-bold">{dedupThreshold}%</span>
                  </label>
                  <p className="text-xs text-muted-foreground">
                    Contacts with confidence ≥ {dedupThreshold}% are auto-merged. Below this, they&apos;re routed to Workbench.
                  </p>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    step="1"
                    value={dedupThreshold}
                    onChange={(e) => setDedupThreshold(Number(e.target.value))}
                    className="w-full max-w-md accent-brand-cornflower"
                  />
                  <div className="flex justify-between text-[10px] text-muted-foreground max-w-md">
                    <span>0% (merge everything)</span>
                    <span>100% (manual only)</span>
                  </div>
                </div>
                <div className="flex flex-col gap-2">
                  <label className="text-sm font-medium">Match Strategy</label>
                  <select
                    value={dedupStrategy}
                    onChange={(e) => setDedupStrategy(e.target.value)}
                    className="w-full max-w-md h-10 px-3 rounded-lg border border-border bg-muted/20 text-sm focus:border-primary/50 outline-none"
                  >
                    <option value="Exact Email Match">Exact Email Match</option>
                    <option value="Fuzzy Name + Company Match">Fuzzy Name + Company Match</option>
                  </select>
                  <p className="text-xs text-muted-foreground">
                    &ldquo;Fuzzy Name + Company Match&rdquo; is reserved for future extension — currently only Exact Email Match runs.
                  </p>
                </div>

                <div className="flex gap-3 pt-2">
                  <Button
                    variant="outline"
                    onClick={saveDedupConfig}
                    disabled={dedupSaving}
                  >
                    {dedupSaving ? <Icons.loader className="w-4 h-4 animate-spin mr-2" /> : <Icons.checkCircle className="w-4 h-4 mr-2" />}
                    Save Settings
                  </Button>
                  <Button
                    variant="gradient"
                    onClick={runDedup}
                    disabled={dedupRunning}
                  >
                    {dedupRunning ? <Icons.loader className="w-4 h-4 animate-spin mr-2" /> : <Icons.zap className="w-4 h-4 mr-2" />}
                    Run Deduplication Now
                  </Button>
                </div>

                {dedupResult && (
                  <div className="mt-4 p-4 bg-emerald-50 text-emerald-800 rounded-lg border border-emerald-200">
                    <p className="font-semibold flex items-center gap-2"><Icons.checkCircle className="w-5 h-5"/> Deduplication Complete!</p>
                    <ul className="text-sm mt-2 space-y-1 list-disc list-inside">
                      <li><strong>{dedupResult.merged}</strong> records were merged automatically based on high confidence.</li>
                      <li><strong>{dedupResult.exceptions}</strong> conflicts were routed to Workbench for manual review.</li>
                    </ul>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        )

      case 'routing':
        return (
          <div className="grid md:grid-cols-2 gap-6">
            {/* Header card with routing engine */}
            <Card className="md:col-span-2 flex flex-col md:flex-row justify-between items-start md:items-center bg-brand-navy text-white p-6 rounded-xl">
               <div>
                 <h3 className="text-lg font-display font-bold">Routing Engine</h3>
                 <p className="text-sm text-brand-cloud mt-1">Assign unowned contacts to SDRs based on territory, segment, and availability.</p>
               </div>
               <Button variant="secondary" onClick={runRouting} disabled={routingRunning} className="mt-4 md:mt-0">
                 {routingRunning ? <Icons.loader className="w-4 h-4 animate-spin mr-2" /> : null}
                 Run Routing Engine <Icons.zap className="w-4 h-4 ml-2" />
               </Button>
            </Card>

            {routingResult && (
              <Card className="md:col-span-2 bg-emerald-50 border-emerald-200">
                 <CardContent className="p-4 text-emerald-800">
                    <p className="font-semibold mb-2">Routing Complete!</p>
                    <div className="text-sm space-y-1">
                       <p>✅ <strong>{routingResult.assigned}</strong> prospects automatically assigned.</p>
                       <p>⚠️ <strong>{routingResult.exceptions}</strong> prospects fell through (no rules matched or capacity hit) and were sent to Workbench.</p>
                    </div>
                 </CardContent>
              </Card>
            )}

            {/* Collisions & Warnings */}
            {(data.collisions?.length > 0 || data.warnings?.length > 0) && (
              <Card className="md:col-span-2 border-amber-200 bg-amber-50/30">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-amber-800">
                    <Icons.alertTriangle className="w-5 h-5 text-amber-500" />
                    Routing Health — Collisions & Warnings
                  </CardTitle>
                  <CardDescription className="text-amber-700">
                    {data.collisions?.length ?? 0} collision(s), {data.warnings?.length ?? 0} warning(s) detected
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  {data.collisions?.map((col: any, idx: number) => (
                    <div key={`col-${idx}`} className="p-3 bg-red-50 border border-red-200 rounded-lg">
                      <div className="flex items-center gap-2 mb-1">
                        <Badge variant="destructive" className="text-[10px]">Collision</Badge>
                        <span className="text-sm font-medium text-red-800">
                          Rules {col.rules?.join(', ')} (Priority {col.priority})
                        </span>
                      </div>
                      <p className="text-xs text-red-700">{col.description}</p>
                    </div>
                  ))}
                  {data.warnings?.map((warn: any, idx: number) => (
                    <div key={`warn-${idx}`} className="p-3 bg-amber-50 border border-amber-200 rounded-lg">
                      <div className="flex items-center gap-2 mb-1">
                        <Badge variant="secondary" className="bg-amber-100 text-amber-800 text-[10px]">
                          {warn.type === 'capacity_overflow' ? 'Over Capacity' : 'Inactive SDR'}
                        </Badge>
                        <span className="text-sm font-medium text-amber-800">{warn.name} ({warn.owner_id})</span>
                      </div>
                      <p className="text-xs text-amber-700">{warn.description}</p>
                    </div>
                  ))}
                </CardContent>
              </Card>
            )}

            {/* SDR Roster */}
            <Card className="md:col-span-2">
              <CardHeader>
                <CardTitle>SDR Roster & Coverage</CardTitle>
                <CardDescription>Rep coverage is computed from all routing_rules where owner_id matches — not just sdr_roster.region.</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {data.sdr_roster?.map((sdr: any) => {
                    const currentCap = parseFloat(sdr.current_capacity || '0')
                    const maxCap = parseFloat(sdr.max_capacity || '1')
                    const capacityRatio = currentCap / (maxCap || 1);
                    const isInactive = String(sdr.active).toLowerCase() === 'false' || sdr.active === false
                    return (
                    <div key={sdr.owner_id} className={cn(
                      "p-4 border rounded-lg flex flex-col md:flex-row gap-4 items-start md:items-center justify-between",
                      isInactive && "border-red-200 bg-red-50/30",
                      capacityRatio >= 1 && !isInactive && "border-amber-200 bg-amber-50/30",
                    )}>
                      <div>
                        <p className="font-semibold text-sm flex items-center gap-2">
                          {sdr.name} <span className="text-muted-foreground font-mono text-xs">({sdr.owner_id})</span>
                          {isInactive && <Badge variant="destructive">Inactive</Badge>}
                          {capacityRatio >= 1 && !isInactive && <Badge className="bg-amber-500 hover:bg-amber-600">Over Capacity</Badge>}
                        </p>
                        <p className="text-xs text-muted-foreground mt-1">
                          Roster Region: {sdr.region} • Segment: {sdr.segment}
                        </p>
                        {sdr.coverage_rules && sdr.coverage_rules.length > 0 && (
                           <div className="flex flex-wrap gap-1 mt-2">
                              <span className="text-[10px] text-muted-foreground mr-1">Coverage:</span>
                              {sdr.coverage_rules.map((cr: any) => (
                                <Badge key={cr.rule_id} variant="secondary" className={cn(
                                  "text-[10px]",
                                  (String(cr.active).toLowerCase() === 'false') && "opacity-50 line-through"
                                )}>
                                  {cr.rule_id}: {cr.rule_name}
                                </Badge>
                              ))}
                           </div>
                        )}
                      </div>
                      <div className="flex flex-col items-end">
                         <span className={cn("text-sm font-medium", capacityRatio >= 1 ? "text-red-500" : "text-green-600")}>
                           {currentCap} / {maxCap} Capacity
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

            {/* Routing Rules */}
            <Card>
              <CardHeader>
                <CardTitle>Routing Rules</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {data.routing_rules?.map((rule: any) => {
                    const isActive = String(rule.active).toLowerCase() === 'true'
                    return (
                    <div key={rule.rule_id} className={cn("p-3 border rounded-lg", !isActive && "opacity-50")}>
                      <p className="font-semibold text-sm flex items-center gap-2">
                        {rule.rule_id}
                        <span className="text-muted-foreground font-normal text-xs">(Priority {rule.priority})</span>
                        {!isActive && <Badge variant="secondary" className="text-[10px]">Inactive</Badge>}
                      </p>
                      <p className="text-xs text-muted-foreground mt-1 font-mono bg-gray-50 p-1 rounded">
                        {rule.region || '*'} / {rule.segment || '*'} / {rule.industry || '*'} ➔ {rule.owner_id}
                      </p>
                    </div>
                  )})}
                </div>
              </CardContent>
            </Card>

            {/* Territories */}
            <Card>
              <CardHeader>
                <CardTitle>Territories</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {data.territories?.map((t: any) => (
                    <div key={t.territory_id} className="flex justify-between items-center p-3 border rounded-lg">
                      <div>
                        <span className="font-medium text-sm">{t.name || t.territory_name}</span>
                        <p className="text-xs text-muted-foreground">Owner: {t.primary_owner_id}</p>
                      </div>
                      <Badge variant="outline">{t.region} / {t.segment}</Badge>
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
                        <td className="px-4 py-3 font-medium text-brand-navy">{record.contact_name || <span className="text-slate-400 italic">Unknown Contact</span>}</td>
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
        const rpt = data.report || data;
        const renderQualitySection = (title: string, items: any[], icon: any, color: string) => (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                {icon}
                {title}
                {items?.length > 0 && (
                  <Badge variant="secondary" className="ml-auto">{items.length} issue{items.length !== 1 ? 's' : ''}</Badge>
                )}
              </CardTitle>
            </CardHeader>
            <CardContent>
              {items?.length > 0 ? (
                <div className="space-y-2">
                  {items.map((item: any, idx: number) => (
                    <div key={idx} className={`flex justify-between items-center p-3 border rounded-lg ${color}`}>
                      <div className="flex-1 min-w-0">
                        <span className="font-medium text-sm text-slate-800">{item.issue}</span>
                        <div className="flex items-center gap-2 mt-1">
                          <Badge variant="outline" className={cn(
                            "bg-white/50",
                            item.severity === 'high' && "border-red-300 text-red-700",
                            item.severity === 'warning' && "border-amber-300 text-amber-700",
                          )}>{item.severity}</Badge>
                          <span className="text-xs text-slate-600 font-mono bg-white/50 px-2 py-1 rounded">{item.count} rows affected</span>
                        </div>
                      </div>
                      {item.examples?.length > 0 && (
                        <Button variant="outline" size="sm" onClick={() => openInspector(`Issue: ${item.issue}`, item.examples)} className="h-7 text-xs bg-white/50 ml-3 shrink-0">
                          <Icons.search className="w-3 h-3 mr-1" /> Inspect
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
             {renderQualitySection("Chronological Anomalies", rpt.chronological, <Icons.clock className="w-5 h-5 text-purple-500" />, "bg-purple-50/50 border-purple-100")}
             {renderQualitySection("Relational Mismatches", rpt.relational, <Icons.network className="w-5 h-5 text-blue-500" />, "bg-blue-50/50 border-blue-100")}
             {renderQualitySection("State & Logic Errors", rpt.state_logic, <Icons.alertTriangle className="w-5 h-5 text-amber-500" />, "bg-amber-50/50 border-amber-100")}
             {renderQualitySection("Format Violations", rpt.format, <Icons.fileText className="w-5 h-5 text-rose-500" />, "bg-rose-50/50 border-rose-100")}
          </div>
        )

      default:
        return null
    }
  }

  return (
    <motion.div className="space-y-8" variants={containerVariants} initial="hidden" animate="visible">
      <motion.div variants={itemVariants}>
        <h1 className="text-display-3 font-bold tracking-tight text-brand-navy font-display">Data Manager</h1>
        <p className="mt-2 text-lg text-muted-foreground font-sans">Manage your centralized master data, routing, and integrations.</p>
      </motion.div>

      <motion.div variants={itemVariants} className="flex space-x-1 border-b overflow-x-auto">
        {tabs.map((tab) => {
          const Icon = tab.icon
          const isActive = activeTab === tab.id
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                'flex items-center space-x-2 px-4 py-2 text-sm font-medium transition-colors border-b-2 whitespace-nowrap',
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
