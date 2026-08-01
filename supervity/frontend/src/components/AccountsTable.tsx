"use client";

import { useEffect, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

export default function AccountsTable() {
  const [records, setRecords] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function fetchData() {
      try {
        const response = await fetch(`${API_URL}/api/data/account?limit=15`);
        if (!response.ok) throw new Error("Network response failed");
        
        const json = await response.json();
        setRecords(json.data || []);
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, []);

  if (loading) return <div className="p-4 text-gray-500">Loading Postgres data...</div>;
  if (error) return <div className="p-4 text-red-500">Crash report: {error}</div>;
  if (records.length === 0) return <div className="p-4">No data found in table.</div>;

  // Dynamically extract column headers from the first JSON object
  const headers = Object.keys(records[0]);

  return (
    <div className="overflow-x-auto bg-white rounded-lg shadow ring-1 ring-black ring-opacity-5">
      <table className="min-w-full divide-y divide-gray-300">
        <thead className="bg-gray-50">
          <tr>
            {headers.map((header) => (
              <th 
                key={header} 
                className="py-3.5 pl-4 pr-3 text-left text-sm font-semibold text-gray-900 uppercase tracking-wide"
              >
                {header.replace(/_/g, " ")}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200 bg-white">
          {records.map((row, rowIndex) => (
            <tr key={rowIndex} className="hover:bg-gray-50 transition-colors">
              {headers.map((column) => (
                <td 
                  key={column} 
                  className="whitespace-nowrap py-4 pl-4 pr-3 text-sm text-gray-500"
                >
                  {/* Convert nulls or booleans into readable strings before rendering */}
                  {String(row[column] ?? "—")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}