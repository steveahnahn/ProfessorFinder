import { createClientComponentClient, createServerComponentClient } from '@supabase/ssr'
import { cookies } from 'next/headers'
import { Database } from '@/types/database'

export const createClient = () =>
  createClientComponentClient<Database>()

export const createServerClient = () =>
  createServerComponentClient<Database>({
    cookies,
  })