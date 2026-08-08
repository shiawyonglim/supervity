'use client'

import dynamic from 'next/dynamic'
import { Suspense } from 'react'

const DataManagerPage = dynamic(() => import('@/app/data-manager/page'), { ssr: false })

export function CRODataManager() {
  return (
    <div className='-m-6'>
      <Suspense fallback={<div className='p-8 text-center text-muted-foreground'>Loading Data Manager...</div>}>
        <DataManagerPage />
      </Suspense>
    </div>
  )
}
