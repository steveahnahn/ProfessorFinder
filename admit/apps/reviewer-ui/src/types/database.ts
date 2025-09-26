export type Database = {
  public: {
    Tables: {
      institutions: {
        Row: {
          id: string
          name: string
          website: string | null
          country: string
          priority_tier: number
          created_at: string
        }
        Insert: {
          id?: string
          name: string
          website?: string | null
          country: string
          priority_tier?: number
          created_at?: string
        }
        Update: {
          id?: string
          name?: string
          website?: string | null
          country?: string
          priority_tier?: number
          created_at?: string
        }
      }
      requirement_set: {
        Row: {
          id: string
          track_id: string
          term_id: string
          source_url: string
          confidence: number
          status: string
          last_verified_at: string | null
          parse_version: string | null
          extraction_method: string | null
          reviewer_id: string | null
          created_at: string
          updated_at: string
        }
        Insert: {
          id?: string
          track_id: string
          term_id: string
          source_url: string
          confidence?: number
          status?: string
          last_verified_at?: string | null
          parse_version?: string | null
          extraction_method?: string | null
          reviewer_id?: string | null
          created_at?: string
          updated_at?: string
        }
        Update: {
          id?: string
          track_id?: string
          term_id?: string
          source_url?: string
          confidence?: number
          status?: string
          last_verified_at?: string | null
          parse_version?: string | null
          extraction_method?: string | null
          reviewer_id?: string | null
          created_at?: string
          updated_at?: string
        }
      }
      validation_issue: {
        Row: {
          id: string
          requirement_set_id: string
          field_name: string
          severity: string
          message: string
          current_value: string | null
          expected_value: string | null
          resolved_at: string | null
          created_at: string
        }
      }
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      [_ in never]: never
    }
    Enums: {
      [_ in never]: never
    }
  }
}