-- Migration V2: Add missing engagement columns for unified metrics
ALTER TABLE public.twitter ADD COLUMN IF NOT EXISTS comments bigint DEFAULT 0;
ALTER TABLE public.twitter ADD COLUMN IF NOT EXISTS reactions bigint DEFAULT 0;

-- Refresh schema cache if using PostgREST/Supabase API
NOTIFY pgrst, 'reload schema';
