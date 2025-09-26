'use client'

import { useEffect, useState } from 'react'
import { Header } from '@/components/layout/header'
import { Sidebar } from '@/components/layout/sidebar'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { api } from '@/lib/api'
import { formatConfidence, getConfidenceColor, formatDate } from '@/lib/utils'
import {
  AlertCircle,
  CheckCircle,
  Clock,
  Database,
  TrendingUp,
} from 'lucide-react'

interface DashboardStats {
  total_programs: number
  total_institutions: number
  total_countries: number
  average_confidence: number
  high_confidence_programs: number
  programs_with_requirements: number
}

interface ReviewStats {
  status_counts: Array<{
    status: string
    count: number
    avg_confidence: number
  }>
  validation_issues: Array<{
    severity: string
    count: number
  }>
  high_confidence_pending: number
}

export default function Dashboard() {
  const [dashboardStats, setDashboardStats] = useState<DashboardStats | null>(null)
  const [reviewStats, setReviewStats] = useState<ReviewStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function fetchDashboardData() {
      try {
        setLoading(true)
        setError(null)

        const [statsData, reviewData] = await Promise.all([
          api.getStats(),
          api.getReviewStats(),
        ])

        setDashboardStats(statsData)
        setReviewStats(reviewData)
      } catch (err) {
        console.error('Dashboard fetch error:', err)
        setError(err instanceof Error ? err.message : 'Failed to load dashboard data')
      } finally {
        setLoading(false)
      }
    }

    fetchDashboardData()
  }, [])

  if (loading) {
    return (
      <div className="flex h-screen">
        <Sidebar />
        <div className="flex-1">
          <Header title="Dashboard" />
          <main className="p-6">
            <div className="flex items-center justify-center h-64">
              <div className="text-center">
                <div className="w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
                <p className="text-gray-500">Loading dashboard...</p>
              </div>
            </div>
          </main>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex h-screen">
        <Sidebar />
        <div className="flex-1">
          <Header title="Dashboard" />
          <main className="p-6">
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <div className="flex items-center">
                <AlertCircle className="w-5 h-5 text-red-500 mr-2" />
                <p className="text-red-800">Error loading dashboard: {error}</p>
              </div>
            </div>
          </main>
        </div>
      </div>
    )
  }

  const pendingReviews = reviewStats?.status_counts.find(s => s.status === 'needs_review')?.count || 0
  const approvedPrograms = reviewStats?.status_counts.find(s => s.status === 'approved')?.count || 0

  return (
    <div className="flex h-screen">
      <Sidebar />
      <div className="flex-1">
        <Header
          title="Dashboard"
          user={{
            name: "Admin User",
            email: "admin@gradschool.com"
          }}
          notifications={pendingReviews}
        />

        <main className="p-6">
          {/* Overview Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Total Programs</CardTitle>
                <Database className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{dashboardStats?.total_programs.toLocaleString()}</div>
                <p className="text-xs text-muted-foreground">
                  Across {dashboardStats?.total_institutions} institutions
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Pending Reviews</CardTitle>
                <Clock className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-yellow-600">{pendingReviews}</div>
                <p className="text-xs text-muted-foreground">
                  {reviewStats?.high_confidence_pending || 0} high confidence
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Approved Programs</CardTitle>
                <CheckCircle className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-green-600">{approvedPrograms}</div>
                <p className="text-xs text-muted-foreground">
                  Ready for public access
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Avg Confidence</CardTitle>
                <TrendingUp className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className={`text-2xl font-bold ${getConfidenceColor(dashboardStats?.average_confidence || 0)}`}>
                  {formatConfidence(dashboardStats?.average_confidence || 0)}
                </div>
                <p className="text-xs text-muted-foreground">
                  {dashboardStats?.high_confidence_programs || 0} above 90%
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Quick Actions */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
            <Card>
              <CardHeader>
                <CardTitle>Quick Actions</CardTitle>
                <CardDescription>
                  Common review tasks and batch operations
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <Button className="w-full justify-start" variant="outline">
                  <Clock className="w-4 h-4 mr-2" />
                  Review Queue ({pendingReviews} pending)
                </Button>
                <Button className="w-full justify-start" variant="outline">
                  <CheckCircle className="w-4 h-4 mr-2" />
                  Batch Approve High Confidence ({reviewStats?.high_confidence_pending || 0})
                </Button>
                <Button className="w-full justify-start" variant="outline">
                  <Database className="w-4 h-4 mr-2" />
                  Search Programs
                </Button>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>System Status</CardTitle>
                <CardDescription>
                  Current system health and processing status
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm">Database Connection</span>
                  <Badge variant="success">Healthy</Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm">ETL Pipeline</span>
                  <Badge variant="success">Running</Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm">Last Update</span>
                  <span className="text-sm text-muted-foreground">
                    {formatDate(new Date())}
                  </span>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Validation Issues Summary */}
          {reviewStats?.validation_issues && reviewStats.validation_issues.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Validation Issues</CardTitle>
                <CardDescription>
                  Current validation issues that need attention
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {reviewStats.validation_issues.map((issue) => (
                    <div key={issue.severity} className="text-center">
                      <div className="text-2xl font-bold text-red-600">
                        {issue.count}
                      </div>
                      <div className="text-sm text-muted-foreground capitalize">
                        {issue.severity} Issues
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </main>
      </div>
    </div>
  )
}